FROM public.ecr.aws/lambda/python:3.9

# Install the function's dependencies using file requirements.txt
# from your project folder.
COPY requirements.txt  .
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy function code
COPY ats.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "ats.docx_handler" ]

# Notes:
# 1) ENTRYPOINT is not necessary if using AWS Lambda base image, as above
# 2) For AWS Batch, CMD is set in the batch job definition
# CMD ["python3","ats.py"]
