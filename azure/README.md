# Azure serverless deployment

This implementation mirrors the committed AWS pipeline without creating or managing virtual machines. Uploading audio starts an asynchronous Azure AI Speech batch job; a Durable Functions orchestration waits without holding compute, creates a DOCX file, records job statistics, and optionally sends Teams or Slack notifications.

## Service mapping

| AWS | Azure | Notes |
| --- | --- | --- |
| S3 | Blob Storage | Private `upload` and `download` containers with lifecycle expiration. |
| S3 event + SQS/DLQ | Event Grid + Queue Storage | At-least-once delivery; Functions creates `audio-to-transcribe-poison` after three failed dequeues. |
| Lambda | Functions Flex Consumption | Python 3.12, scale-to-zero, no always-ready instances. |
| Transcribe | Azure AI Speech batch transcription | Entra ID authentication, diarization, language candidates, BYOS results. |
| Step Functions | Durable Functions | Durable timers poll Speech every ten minutes without a running worker. |
| DynamoDB on-demand | Table Storage | Stores the small job-reporting dataset. |
| Secrets Manager | Key Vault | Optional webhook URLs. |
| SNS notifications | Function activities + webhooks | Teams and Slack are implemented; see choices below for email/fan-out. |
| CloudWatch | Application Insights + Log Analytics | Function and orchestration telemetry. |

## Deploy

Prerequisites are Terraform 1.5.7 or newer, an Azure subscription, and an authenticated Azure CLI session. The deploying identity needs permission to create resources and role assignments.

```powershell
cd azure/terraform
Copy-Item ats.auto.tfvars.template ats.auto.tfvars
terraform init
terraform plan
terraform apply
```

Terraform packages and deploys the Function app. Upload audio with Entra ID credentials, for example:

```powershell
$account = terraform output -raw storage_account_name
az storage blob upload --auth-mode login --account-name $account --container-name upload --file interview.wav --name interview.wav
```

Audio submitted with speaker diarization must be mono. Before creating a Speech job, the first Durable activity reads at most 1 MiB of blob metadata and rejects empty, corrupt, unsupported, unverifiable, or multichannel files. Preflight supports WAV, FLAC, MP3, MP4, OGG, Opus, WMA, AAC, and Speex. An MP4 is accepted only when its audio metadata and mono channel count can be verified. Normalize rejected stereo recordings to mono before uploading them again. The smoke test used the repository's linked sample converted to a 48 kHz mono FLAC file.

The generated DOCX appears under a date prefix in the private `download` container. Invoke the function-authenticated `POST /api/reports/export` endpoint to create `download/export/transcribe_jobs.csv`.

When Azure Speech reports a successful transcription, the source blob is deleted from `upload` before DOCX generation. Rejected, failed, and timed-out uploads remain available for diagnosis until the storage lifecycle policy removes them.

## Security and serverless characteristics

- The Function app uses Flex Consumption with zero always-ready instances. There are no VM, VM scale set, AKS, App Service Dedicated, or Premium plan resources.
- Function, Event Grid, and Speech access use managed identities and RBAC. Storage account key access and Speech local-key authentication are disabled.
- Speech BYOS links the private storage account to the Speech resource. The application retrieves result files through the Speech API rather than relying on undocumented artifact paths.
- Storage and Function endpoints remain public so Azure managed services can reach them, but data access requires Entra ID. Private endpoints are a possible hardening phase and require choosing a network topology and checking regional Flex Consumption support.
- Webhook variables are marked sensitive and stored in Key Vault, but—like the AWS implementation—the values remain in Terraform state. Use a secured remote backend, or create secrets outside Terraform and change the code/configuration to reference pre-existing secret names.

## Choices that need product or security input

1. **Email and general fan-out.** SNS has no exact low-cost Azure equivalent for this pattern. Logic Apps Consumption is the simplest managed email option; Azure Communication Services Email offers more application control; an Event Grid custom topic is best when downstream teams own subscribers. None is included until delivery and recipient requirements are known.
2. **Locale detection.** Amazon Transcribe can broadly identify languages. Azure Speech requires a candidate locale list. `speech_locales` defaults to `en-US`; configure the likely languages (up to ten) for useful identification.
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
