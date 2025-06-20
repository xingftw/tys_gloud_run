#!/bin/bash

# Create directory for the code
mkdir -p restore-redirect-code
cd restore-redirect-code

# Get the container image URL
IMAGE_URL=$(gcloud run services describe restore-redirect --region=us-central1 --format="value(spec.template.spec.containers[0].image)")
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
    docker cp temp-container:/app/. /workspace/app/ || echo "No /app directory found"
    docker cp temp-container:/workspace/. /workspace/workspace/ || echo "No /workspace directory found"
    docker rm temp-container
artifacts:
  objects:
    location: 'gs://tys-bi-temp-bucket/restore-redirect-code/'
    paths: ['app/**', 'workspace/**']
EOF

# Run the Cloud Build job
gcloud builds submit --config=cloudbuild.yaml --no-source

# Download the extracted code
echo "Downloading extracted code..."
gsutil -m cp -r gs://tys-bi-temp-bucket/restore-redirect-code/* .

echo "Done! Code extracted to $(pwd)"