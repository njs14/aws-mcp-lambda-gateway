FROM public.ecr.aws/lambda/python:3.12

# Install Lambda Web Adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

# Set working directory
WORKDIR /var/task

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mcp_gateway.py .

# Lambda Web Adapter configuration
ENV AWS_LWA_PORT=8080
ENV AWS_LWA_READINESS_CHECK_PATH=/health
ENV AWS_LWA_INVOKE_MODE=response_stream

# Start the application
CMD ["uvicorn", "mcp_gateway:app", "--host", "0.0.0.0", "--port", "8080"]
