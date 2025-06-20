FROM python:3.9-slim

WORKDIR /app

# Install dependencies with specific versions to avoid compatibility issues
RUN pip install --no-cache-dir numpy==1.23.5
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the web service on container startup
CMD exec functions-framework --target=process_homebase_files --port=${PORT:-8080}
