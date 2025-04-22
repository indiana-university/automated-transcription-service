# AWS code for Automated Transcription Service (ATS)
### Deploy infrastructure

>[!NOTE]
>This guide assumes you have the prerequisites installed and configured. If you haven't done so, please refer to the [prerequisites guide](../doc/prerequisites.md) before proceeding.

Clone the repository:

```bash
git clone https://github.com/indiana-university/automated-transcription-service.git
cd automated-transcription-service/aws/terraform/
```

Run `terraform init` to download the necessary provider(s). If you are not using the default AWS profile for access then you should also include an AWS named profile:

```bash
terraform init -backend-config="profile=<AWS named profile>"
```

Now run `terraform plan` to preview the deployment:

```bash
terraform plan
```

Finally, run `terraform apply` to actually deploy the components of the application:

```bash
terraform apply
```

>[!NOTE]
>There are default values for all variables. If you want to change any values you can either rename and use the provided `ats.auto.tfvars.template` file or pass variables in as command line arguments. For example, to change the region you can run:

```bash
terraform apply -var="region=us-west-2"
```

The deployment will take a few minutes to complete. Once it is done, you should see the outputs and can test the application by uploading a file to the upload bucket. The upload bucket name is in the outputs of the terraform apply command. The output will be in the download bucket, also in the outputs of the terraform apply command.

### Testing
Download this short audio file to your workstation and then upload it to the upload bucket to test the application: https://upload.wikimedia.org/wikipedia/commons/0/0a/Charles_Duke_Intro.ogg


### Clean up
To clean up the resources created by terraform, run:

```bash
terraform destroy
```
>[!WARNING]
>This will remove all the resources created by terraform.
