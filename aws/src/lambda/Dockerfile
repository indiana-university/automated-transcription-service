FROM public.ecr.aws/lambda/python:3.10

# Install the function's dependencies using file requirements.txt
# from your project folder.
COPY requirements.txt  .
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy function code
COPY ats_utilities.py ${LAMBDA_TASK_ROOT}
COPY audio_to_transcribe.py ${LAMBDA_TASK_ROOT}
COPY transcribe_to_docx.py ${LAMBDA_TASK_ROOT}
