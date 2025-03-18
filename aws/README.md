# AWS code for Automated Transcription Service (ATS)
### Deploy infrastructure

The deployment is set up to store remote state in an S3 bucket, so begin by creating that bucket:
```
aws s3 mb s3://<TF_STATE_BUCKET_NAME>
```

Switch to the `terraform` directory:

```
cd ./terraform
```

Rename the auto.tfvars template:

```
mv ats.auto.tfvars.template ats.auto.tfvars
```

Edit the variables in the ats.auto.tfvars as necessary.

Run `terraform init` to download the necessary provider(s). Note that you must provide the name of remote state bucket created above. If you are not using the default AWS profile for access then you should also include an AWS named profile:

```
terraform init -backend-config="bucket=<TF_STATE_BUCKET_NAME>" -backend-config="profile=<AWS named profile>"
```

Now run `terraform plan` to preview the deployment:

```
terraform plan
```

Finally, run `terraform apply` to actually deploy the components of the application:

```
terraform apply
```
This will take a few minutes to complete. Once it is done, you should see the outputs and can test the application by uploading a file to the upload bucket. The upload bucket name is in the outputs of the terraform apply command. The output will be in the download bucket, also in the outputs of the terraform apply command.

### Clean up
To clean up the resources created by terraform, run:

```
terraform destroy
```
>[!WARNING]
>This will remove all the resources created by terraform.

>[!NOTE]
>Note that this will not remove the S3 bucket used for remote state, so you will need to do that manually if you want to remove it.
>If you get an error about the bucket(s) not being empty, you will need to empty the bucket(s) first. You can do this from the AWS console or by using the AWS CLI:
```
aws s3 rm s3://<BUCKET_NAME> --recursive
```
