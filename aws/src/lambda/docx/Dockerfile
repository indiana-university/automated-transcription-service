# Python version passed via build_args in lambda.tf
ARG PYTHON_VERSION=3.13

# Define custom function directory
ARG FUNCTION_DIR="/function"

FROM python:${PYTHON_VERSION}-slim-trixie AS build-image

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Copy function code
RUN  mkdir -p ${FUNCTION_DIR}
COPY transcribe_to_docx.py ${FUNCTION_DIR}

# Install the function's dependencies
COPY requirements.txt  .
RUN  pip install --target ${FUNCTION_DIR} awslambdaric
RUN  pip install -r requirements.txt --target ${FUNCTION_DIR}

# Use a distroless Python image to reduce the final image size and attack surface
FROM gcr.io/distroless/python3-debian13:nonroot

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Set working directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies from build stage
COPY --from=build-image --chown=nonroot:nonroot ${FUNCTION_DIR} ${FUNCTION_DIR}

# Run as non-root user
USER nonroot

# Set the entry point for the Lambda function
ENTRYPOINT ["/usr/bin/python", "-m", "awslambdaric"]
