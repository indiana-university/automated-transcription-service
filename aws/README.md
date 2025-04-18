# AWS code for Automated Transcription Service (ATS)
### Deploy infrastructure

Clone the repository:

```bash
git clone https://github.com/indiana-university/automated-transcription-service.git
cd automated-transcription-service/aws/terraform/
```

Edit the variables in the ats.auto.tfvars as necessary.

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

### Clean up
To clean up the resources created by terraform, run:

```bash
terraform destroy
```
>[!WARNING]
>This will remove all the resources created by terraform.
