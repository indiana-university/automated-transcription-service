# Define custom function directory
ARG FUNCTION_DIR="/function"

FROM python:3.12 AS build-image

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Copy function code
RUN  mkdir -p ${FUNCTION_DIR}
COPY transcribe_to_docx.py ${FUNCTION_DIR}

# Install the function's dependencies
COPY requirements.txt  .
RUN  pip install --target ${FUNCTION_DIR} awslambdaric
RUN  pip install -r requirements.txt --target ${FUNCTION_DIR}

# Use a slim version of the base Python image to reduce the final image size
FROM python:3.12-slim

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

# Set runtime interface client as default command for the container runtime
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
