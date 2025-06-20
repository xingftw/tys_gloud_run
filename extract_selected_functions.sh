#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Check if services were provided
if [ $# -eq 0 ]; then
  echo "Usage: $0 <service1> <service2> ..."
  echo "Example: $0 restore-redirect my-other-function"
  exit 1
fi

# Base directory for all extracted code
BASE_DIR="$(pwd)/extracted_functions"
mkdir -p "$BASE_DIR"
echo "Will extract specified functions to: $BASE_DIR"

# Process each service provided as an argument
for SERVICE in "$@"; do
  echo "==============================================="
  echo "Processing service: $SERVICE"
  
  # Check if the service exists
  if ! gcloud run services describe "$SERVICE" --region=us-central1 &>/dev/null; then
    echo "Service $SERVICE not found. Skipping."
    continue
  fi
  
  # Create directory for this service
  SERVICE_DIR="$BASE_DIR/$SERVICE"
  mkdir -p "$SERVICE_DIR"
  cd "$SERVICE_DIR"
  
  # Get the container image URL
  IMAGE_URL=$(gcloud run services describe "$SERVICE" --region=us-central1 --format="value(spec.template.spec.containers[0].image)")
  echo "Found image: $IMAGE_URL"
  
  # Download the container image using Google Cloud Build
  echo "Creating a Cloud Build job to extract code..."
  cat > cloudbuild.yaml << EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  entrypoint: 'bash'
  args:
  - '-c'
  - |
    docker pull $IMAGE_URL
    docker create --name temp-container $IMAGE_URL
    mkdir -p /workspace/app
    mkdir -p /workspace/workspace

    # Inspect the container to see what's available
    echo "Inspecting container:"
    docker inspect temp-container || echo "Could not inspect container"

    # Try to list directories by starting the container temporarily
    echo "Trying to list directories in the container:"
    docker start temp-container || echo "Could not start container"
    docker exec temp-container ls -la / || echo "Could not list root directory"
    docker exec temp-container ls -la /workspace/ || echo "Could not list workspace directory"
    docker stop temp-container || echo "Could not stop container"

    # Try to copy from various possible locations
    docker cp temp-container:/app/. /workspace/app/ || echo "No /app directory found"
    docker cp temp-container:/workspace/. /workspace/workspace/ || echo "No /workspace directory found"
    docker cp temp-container:/function/. /workspace/app/ || echo "No /function directory found"
    docker cp temp-container:/srv/. /workspace/app/ || echo "No /srv directory found"

    # List what we extracted
    echo "Contents of extracted directories:"
    ls -la /workspace/app/ || echo "App directory is empty"
    ls -la /workspace/workspace/ || echo "Workspace directory is empty"

    # Make sure we have something to upload
    touch /workspace/app/extracted_files.txt
    echo "Files extracted from $IMAGE_URL" > /workspace/app/extracted_files.txt

    docker rm temp-container
artifacts:
  objects:
    location: 'gs://tys-bi-temp-bucket/$SERVICE/'
    paths: ['app/**', 'workspace/**']
EOF

  # Run the Cloud Build job
  gcloud builds submit --config=cloudbuild.yaml --no-source
  
  # Create a local directory structure
  mkdir -p app
  mkdir -p workspace
  
  # Download the extracted code
  echo "Downloading extracted code..."
  # First, list what's in the bucket to see the actual paths
  echo "Files in bucket:"
  gsutil ls -r gs://tys-bi-temp-bucket/$SERVICE/ || echo "No files found in bucket"
  
  # Download files with correct paths
  gsutil -m cp -r gs://tys-bi-temp-bucket/$SERVICE/* ./ || echo "No files found in bucket"
  
  echo "Done! Code extracted to $(pwd)"
  
  # List the extracted files
  echo "Extracted files:"
  find . -type f | grep -v "cloudbuild.yaml" | sort
  
  # Go back to the base directory
  cd "$BASE_DIR"
  echo ""
done

echo "All specified services processed. Code extracted to $BASE_DIR"
