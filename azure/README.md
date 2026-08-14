# Azure serverless deployment

This implementation mirrors the committed AWS pipeline without creating or managing virtual machines. Uploading audio starts an asynchronous Azure AI Speech batch job; a Durable Functions orchestration waits without holding compute, creates a DOCX file, records job statistics, and optionally sends Teams or Slack notifications.

## Service mapping

| AWS | Azure | Notes |
| --- | --- | --- |
| S3 | Blob Storage | Private `upload` and `download` containers with lifecycle expiration. |
| S3 event + SQS/DLQ | Event Grid + Queue Storage | At-least-once delivery; Functions creates `audio-to-transcribe-poison` after three failed dequeues. |
| Lambda | Functions Flex Consumption | Python 3.12, scale-to-zero, no always-ready instances. |
| Transcribe | Azure AI Speech batch transcription | Entra ID authentication, diarization, language candidates, BYOS results. |
| Step Functions | Durable Functions | A signed Speech webhook raises a Durable external event when transcription completes. |
| DynamoDB on-demand | Table Storage | Stores the small job-reporting dataset. |
| Secrets Manager | Key Vault | Optional webhook URLs. |
| SNS notifications | Function activities + webhooks | Teams and Slack are implemented; see choices below for email/fan-out. |
| CloudWatch | Application Insights + Log Analytics | Function and orchestration telemetry. |

## Deploy

Prerequisites are Terraform 1.5.7 or newer, an Azure subscription, and an authenticated Azure CLI session. The deploying identity needs permission to create resources and role assignments. Confirm that Azure CLI is using the intended subscription before continuing:

```powershell
az account show --query "{subscription:name, subscriptionId:id, tenantId:tenantId}" --output table
```

### Create the remote state backend

Create a dedicated resource group, storage account, and private blob container before deploying the application. This storage is intentionally separate from the application stack so that destroying or repairing the application cannot remove its own Terraform state. Storage account names are globally unique; retain the generated name for the backend configuration.

```powershell
$stateLocation = "eastus"
$stateResourceGroup = "ats-terraform-state-rg"
$stateContainer = "tfstate"
$stateStorageAccount = "atstfstate$(Get-Random -Minimum 10000000 -Maximum 99999999)"
$deployerObjectId = az ad signed-in-user show --query id --output tsv

az group create `
  --name $stateResourceGroup `
  --location $stateLocation `
  --output none

az storage account create `
  --name $stateStorageAccount `
  --resource-group $stateResourceGroup `
  --location $stateLocation `
  --kind StorageV2 `
  --sku Standard_LRS `
  --https-only true `
  --min-tls-version TLS1_2 `
  --allow-blob-public-access false `
  --output none

az storage container-rm create `
  --name $stateContainer `
  --storage-account $stateStorageAccount `
  --resource-group $stateResourceGroup `
  --public-access off `
  --output none

$stateAccountId = az storage account show `
  --name $stateStorageAccount `
  --resource-group $stateResourceGroup `
  --query id `
  --output tsv
$stateContainerId = "$stateAccountId/blobServices/default/containers/$stateContainer"

az role assignment create `
  --assignee-object-id $deployerObjectId `
  --assignee-principal-type User `
  --role "Storage Blob Data Contributor" `
  --scope $stateContainerId `
  --output none

az storage account blob-service-properties update `
  --account-name $stateStorageAccount `
  --resource-group $stateResourceGroup `
  --enable-versioning true `
  --enable-delete-retention true `
  --delete-retention-days 30 `
  --enable-container-delete-retention true `
  --container-delete-retention-days 30 `
  --output none

$stateStorageAccount
```

The commands grant the signed-in user access to state. Grant the same `Storage Blob Data Contributor` role on the container to every deployment or CI identity that will run Terraform. Azure role assignments can take several minutes to propagate.

Copy the backend template and replace its storage account placeholder with the name printed by the preceding commands:

```powershell
cd azure/terraform
Copy-Item backend.hcl.template backend.hcl
notepad backend.hcl
```

For a new deployment with no existing state, initialize the remote backend:

```powershell
terraform init "-backend-config=backend.hcl"
```

For an existing deployment currently using local state, migrate that state instead. Review the backend values carefully and answer `yes` when Terraform asks to copy the existing state:

```powershell
terraform init -migrate-state "-backend-config=backend.hcl"
```

Do not delete a local state file until `terraform plan` succeeds against the remote backend. The state blob is encrypted at rest, versioned, soft-deleted for 30 days, and automatically locked by the AzureRM backend during state-changing Terraform operations.

### Deploy the application

```powershell
Copy-Item ats.auto.tfvars.template ats.auto.tfvars
terraform plan
terraform apply
```

The generated application resource group is dedicated to this deployment. Do not add unrelated resources to it: `terraform destroy` is configured to remove the entire group, including monitoring artifacts that Azure creates automatically outside Terraform state.

The deploying identity receives read/write blob access to the private `upload` and `download` containers and read access to all tables in the ATS storage account. To grant the same access to Microsoft Entra groups, populate `blob_data_contributor_group_object_ids` in `ats.auto.tfvars` with group object IDs, not display names. The table role is assigned at storage-account scope and inherited by every table in that account. Management-plane `Owner` and `Contributor` assignments alone do not grant storage data access. For example:

```hcl
blob_data_contributor_group_object_ids = [
  "00000000-0000-0000-0000-000000000000",
  "11111111-1111-1111-1111-111111111111",
]
```

> [!NOTE]
> Resolve a Microsoft Entra group object ID from its display name with `az ad group show --group "Group Display Name" --query id --output tsv`.

> [!NOTE]
> Tables other than `jobs` are managed by Durable Functions and can contain orchestration metadata, inputs, and outputs. Treat their schema as an implementation detail and grant this read access only to groups that should be able to inspect operational data.

Terraform packages and deploys the Function app. Upload audio with Entra ID credentials, for example:

```powershell
$account = terraform output -raw storage_account_name
az storage blob upload --auth-mode login --account-name $account --container-name upload --file interview.wav --name interview.wav
```

Audio submitted with speaker diarization must be mono. Before creating a Speech job, the first Durable activity reads at most 1 MiB of blob metadata and rejects empty, corrupt, unsupported, unverifiable, or multichannel files. Preflight supports WAV, FLAC, MP3, MP4, OGG, Opus, WMA, AAC, and Speex. An MP4 is accepted only when its audio metadata and mono channel count can be verified. Normalize rejected stereo recordings to mono before uploading them again. The smoke test used the repository's linked sample converted to a 48 kHz mono FLAC file.

The generated DOCX appears under a date prefix in the private `download` container. The `jobs` table receives its reporting row only after processing completes; use the Function app's Durable Functions and Application Insights views for an active job. Invoke the function-authenticated `POST /api/reports/export` endpoint to create `download/export/transcribe_jobs.csv`.

When Azure Speech reports a successful transcription, the source blob is deleted from `upload` before DOCX generation. Rejected, failed, and timed-out uploads remain available for diagnosis until the storage lifecycle policy removes them.

Speech webhook payloads are authenticated with HMAC-SHA256 using a generated secret in Key Vault. The Function managed identity creates or repairs the resource-wide webhook registration before submitting a transcription, and the job's custom properties route the terminal event to its Durable orchestration. There is no recurring Speech status poll.

Each transcription job appends a zero-padded eight-digit random integer to the sanitized source filename. Resubmitting a filename therefore creates distinct Speech jobs, DOCX blobs, notifications, and jobs-table rows.

## Security and serverless characteristics

- The Function app uses Flex Consumption with zero always-ready instances. There are no VM, VM scale set, AKS, App Service Dedicated, or Premium plan resources.
- Function, Event Grid, and Speech access use managed identities and RBAC. Storage account key access and Speech local-key authentication are disabled.
- Speech BYOS links the private storage account to the Speech resource. The application retrieves result files through the Speech API rather than relying on undocumented artifact paths.
- Storage and Function endpoints remain public so Azure managed services can reach them, but data access requires Entra ID. Private endpoints are a possible hardening phase and require choosing a network topology and checking regional Flex Consumption support.
- Webhook variables are marked sensitive and stored in Key Vault, but—like the AWS implementation—the values remain in Terraform state. Use a secured remote backend, or create secrets outside Terraform and change the code/configuration to reference pre-existing secret names.

## Choices that need product or security input

1. **Email and general fan-out.** SNS has no exact low-cost Azure equivalent for this pattern. Logic Apps Consumption is the simplest managed email option; Azure Communication Services Email offers more application control; an Event Grid custom topic is best when downstream teams own subscribers. None is included until delivery and recipient requirements are known.
2. **Locale detection.** Amazon Transcribe can broadly identify languages. Azure Speech requires 2-10 candidate locales. `speech_locales` defaults to `en-US`, `es-US`, and `de-DE`, while `speech_language_identification_mode` defaults to `Continuous` so Speech can identify language changes within a recording. Keep the candidate list limited to languages the deployment actually expects.
3. **Network isolation.** The initial version is identity-secured over public Azure endpoints. Private Link is stronger but adds private DNS, subnets, regional constraints, and non-trivial cost. It should be a deliberate production profile rather than an invisible default.
4. **Frontend.** The untracked `aws/web/` directory in the source checkout was deliberately excluded. An Azure web interface should be handled after that work is committed and its authentication/upload contract is known.
5. **Retention versus recovery.** Blob lifecycle matches the AWS 30-day default. Table Storage does not provide DynamoDB point-in-time recovery or deletion protection; if those controls are mandatory, Cosmos DB serverless is the closer but more expensive replacement.

## Local verification

```powershell
python -m venv .venv
.venv/Scripts/pip install -r azure/src/functions/requirements.txt pytest ruff
.venv/Scripts/python -m pytest azure/tests
terraform -chdir=azure/terraform fmt -check -recursive
terraform -chdir=azure/terraform validate
```
