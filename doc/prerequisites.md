# Prerequisites for AWS Deployment

You can deploy the application either from your own workstation or from CloudShell in your AWS account. Both methods have the same requirements:
- Docker
- AWS SAM CLI
- Terraform
- AWS CLI

## CloudShell
CloudShell already includes Docker and the CLI, so you only need to install SAM CLI, Python 3.12, and Terraform. Follow these steps:

### Install SAM CLI

```bash
pip3 install aws-sam-cli --user
```

### Install Python 3.12

CloudShell AL2023 ships with Python 3.9. Python 3.12 is required to match the Lambda runtime when building without a container:

```bash
sudo dnf install python3.12 -y
```

### Install Terraform
1. Open CloudShell in your AWS account.
2. Run the following commands to install Terraform:

```bash
git clone https://github.com/tfutils/tfenv.git ~/.tfenv
```

```bash
mkdir ~/bin
```

```bash
ln -s ~/.tfenv/bin/* ~/bin/
```

```bash
tfenv install
```

```bash
tfenv use
```

> [!NOTE]
> **CloudShell: Python 3.13 is not supported**
>
> CloudShell (AL2023) only has Python 3.9. AWS has also not published a SAM build image for Python 3.13. Use the default Python 3.12 runtime.
>
> In addition, CloudShell's Docker daemon cannot reach ECR Public (`public.ecr.aws`), so `sam build --use-container` fails for every Python version on CloudShell. Install Python 3.12 (above) and use `sam build --no-use-container` instead. Pre-compiled manylinux wheels for `lxml` are used automatically — no compilation required.

## Workstation
If you are deploying from your own workstation, you need to install Docker, Terraform, and the AWS CLI. Follow the instructions for your operating system:
- https://docs.docker.com/desktop/
- https://developer.hashicorp.com/terraform/install
- https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

## Installation
Once you have installed the prerequisites, you can proceed with the installation of the application. Refer to the [installation guide](../aws/README.md) for further instructions.