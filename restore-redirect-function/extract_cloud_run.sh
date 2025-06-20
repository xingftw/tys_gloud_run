#!/bin/bash

# Create directory for the code
mkdir -p restore-redirect-code
cd restore-redirect-code

# Get the container image URL
IMAGE_URL=$(gcloud run services describe restore-redirect --region=us-central1 --format="value(spec.template.spec.containers[0].image)")
echo "Found image: $IMAGE_URL"

# Pull the container image
echo "Pulling container image..."
docker pull $IMAGE_URL

# Create a temporary container
echo "Creating temporary container..."
docker create --name temp-container $IMAGE_URL

# Extract the code
echo "Extracting code from container..."
docker cp temp-container:/app ./app
docker cp temp-container:/workspace ./workspace

# Clean up
echo "Cleaning up..."
docker rm temp-container

echo "Done! Code extracted to $(pwd)"