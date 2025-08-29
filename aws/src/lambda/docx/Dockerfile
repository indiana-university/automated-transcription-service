# Python version
ARG PYTHON_VERSION=3.11

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

# Use a distroless Python image to reduce the final image size
FROM gcr.io/distroless/python3:nonroot

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies with proper ownership
COPY --from=build-image --chown=nonroot:nonroot ${FUNCTION_DIR} ${FUNCTION_DIR}

# Switch to non-root user
USER nonroot

# Set runtime interface client as default command for the container runtime
#CMD [ "-m", "awslambdaric" ]
ENTRYPOINT [ "/usr/bin/python3", "-m", "awslambdaric" ]
