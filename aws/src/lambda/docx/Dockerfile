# Python version passed via build_args in lambda.tf
ARG PYTHON_VERSION

# Define custom function directory
ARG FUNCTION_DIR="/function"

FROM python:${PYTHON_VERSION} AS build-image

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Copy function code
RUN  mkdir -p ${FUNCTION_DIR}
COPY transcribe_to_docx.py ${FUNCTION_DIR}

# Install the function's dependencies
COPY requirements.txt  .
RUN  pip install --target ${FUNCTION_DIR} awslambdaric
RUN  pip install -r requirements.txt --target ${FUNCTION_DIR}

# Use slim Python image to minimize size and attack surface
FROM python:${PYTHON_VERSION}-slim

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies from build stage
COPY --from=build-image --chown=appuser:appuser ${FUNCTION_DIR} ${FUNCTION_DIR}

# Run as non-root user
USER appuser

# Set the entry point for the Lambda function
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
