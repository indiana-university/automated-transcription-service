# AWS code for Automated Transcription Service (ATS)

>[!NOTE]
>This guide assumes you have the prerequisites installed and configured. If you haven't done so, please refer to the [prerequisites guide](../doc/prerequisites.md) before proceeding.

## Deploy infrastructure (AWS SAM / CloudFormation)

### Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed
- [Docker](https://docs.docker.com/get-docker/) installed and running (required to build the `transcribe-to-docx` Lambda with binary dependencies)
- AWS credentials configured (default profile or a named profile)

### 1 — Clone the repository

```bash
git clone https://github.com/indiana-university/automated-transcription-service.git
cd automated-transcription-service/aws/cloudformation/
```

### 2 — Configure deployment parameters

Copy the template config file and fill in the required values:

```bash
cp samconfig.toml.template samconfig.toml
```

Open `samconfig.toml` and set at minimum:
- `region` — your target AWS region (e.g. `us-east-1`)
- `s3_bucket` — an S3 bucket to stage deployment artifacts, **or** remove this line and add `--resolve-s3` to the deploy command to let SAM manage one automatically

All other parameters have sensible defaults. To enable Teams or Slack notifications, set `TeamsNotification=true` or `SlackNotification=true` and provide the corresponding webhook URLs.

### 3 — Build

The `--use-container` flag builds Lambda dependencies inside a Lambda-compatible Docker image, which is required for the `transcribe-to-docx` function (`lxml` binary dependency):

```bash
sam build --use-container
```

> [!NOTE]
> **CloudShell users:** The default runtime is Python 3.12. If you changed `PythonVersion` to `3.13`, be aware that AWS has not yet published a SAM build image for Python 3.13 and `sam build --use-container` will fail. Use Python 3.12 (the default) to deploy from CloudShell.

### 4 — Deploy

```bash
sam deploy
```

SAM will display a changeset preview and prompt for confirmation before creating resources. The first deployment takes a few minutes.

Once complete, the stack outputs show the bucket names:

```
Outputs:
  UploadBucketName   = ats-upload-<account>-<region>
  DownloadBucketName = ats-download-<account>-<region>
  DynamoDBTableName  = ats-jobs-table
```

>[!NOTE]
>To override a parameter on the command line (without editing `samconfig.toml`), pass `--parameter-overrides`. For example, to change the region:
>```bash
>sam deploy --parameter-overrides "Prefix=myats RetentionDays=60"
>```

### Testing

Download this short audio file to your workstation and then upload it to the upload bucket to test the application:
https://upload.wikimedia.org/wikipedia/commons/0/0a/Charles_Duke_Intro.ogg

```bash
aws s3 cp Charles_Duke_Intro.ogg s3://<UploadBucketName>/
```

The transcription output (DOCX file) will appear in the download bucket within a few minutes.

### Clean up

```bash
sam delete
```

>[!WARNING]
>The S3 buckets and DynamoDB table are created with `DeletionPolicy: Retain`. They will **not** be deleted by `sam delete` to prevent accidental data loss. You must delete them manually in the AWS Console or with the AWS CLI if you no longer need them.
