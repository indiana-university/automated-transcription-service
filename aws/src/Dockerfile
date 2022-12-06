FROM public.ecr.aws/lambda/python:3.9

# Install the function's dependencies using file requirements.txt
# from your project folder.
COPY requirements.txt  .
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy function code
COPY ats.py ${LAMBDA_TASK_ROOT}

# Set as EC/Image configuration/CMD override, can also be done inline if one entry point is used:
# CMD [ "ats.docx_handler" ]

# Notes:
# 1) ENTRYPOINT is not necessary if using AWS Lambda base image, as above
# 2) For AWS Batch, CMD is set in the batch job definition
# CMD ["python3","ats.py"]
