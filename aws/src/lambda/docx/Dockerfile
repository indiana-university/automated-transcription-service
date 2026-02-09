# Python version
ARG PYTHON_VERSION=3.13

# Define custom function directory
ARG FUNCTION_DIR="/function"

FROM python:${PYTHON_VERSION} AS build-image

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Create a non-root user for building
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy function code
RUN  mkdir -p ${FUNCTION_DIR}
COPY transcribe_to_docx.py ${FUNCTION_DIR}

# Install the function's dependencies
COPY requirements.txt  .
RUN  pip install --target ${FUNCTION_DIR} awslambdaric
RUN  pip install -r requirements.txt --target ${FUNCTION_DIR}

# Change ownership of the function directory to the non-root user
RUN chown -R appuser:appuser ${FUNCTION_DIR}

# Use slim Python image to minimize size and attack surface
FROM python:${PYTHON_VERSION}-slim

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Set working directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies from build stage
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

#Set the entry point for the Lambda function
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
