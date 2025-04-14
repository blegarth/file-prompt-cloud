#!/bin/bash

# Exit on error
set -e

# Load environment variables
if [ -f ../.env ]; then
    export $(cat ../.env | xargs)
fi

# Default values
PROJECT_ID=${GCP_PROJECT_ID:-"file-prompt"}
REGION=${REGION:-"us-east1"}
SERVICE_NAME=${SERVICE_NAME:-"file-prompt-service"}

# Function to update Docker image
update_image() {
    echo "Building and pushing new Docker image..."
    docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME} ..
    docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}

    echo "Deploying to Cloud Run..."
    gcloud run deploy ${SERVICE_NAME} \
        --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
        --platform managed \
        --region ${REGION}
}

# Function to update environment variables
update_env() {
    echo "Updating environment variables..."
    gcloud run services update ${SERVICE_NAME} \
        --update-env-vars="GCS_BUCKET=${GCS_BUCKET_NAME},PUBSUB_TOPIC=${PUBSUB_TOPIC},PUBSUB_SUBSCRIPTION=${PUBSUB_SUBSCRIPTION},PUBSUB_RESULTS_TOPIC=${PUBSUB_RESULTS_TOPIC},PUBSUB_RESULTS_SUBSCRIPTION=${PUBSUB_RESULTS_SUBSCRIPTION},GOOGLE_API_KEY_SECRET=${GOOGLE_API_KEY_SECRET}" \
        --region ${REGION}
}

# Function to update secrets
update_secret() {
    if [ -z "$1" ]; then
        echo "Please provide the new secret value"
        exit 1
    fi

    echo "Updating secret..."
    echo -n "$1" | gcloud secrets versions add google-api-key --data-file=-
}

# Function to update infrastructure
update_infra() {
    echo "Updating infrastructure..."
    gcloud deployment-manager deployments update file-prompt-deployment \
        --config=deployment.yaml
}

# Main script
case "$1" in
"image")
    update_image
    ;;
"env")
    update_env
    ;;
"secret")
    update_secret "$2"
    ;;
"infra")
    update_infra
    ;;
"all")
    update_image
    update_env
    update_infra
    ;;
*)
    echo "Usage: $0 {image|env|secret|infra|all}"
    echo "  image   - Update Docker image and deploy to Cloud Run"
    echo "  env     - Update environment variables"
    echo "  secret  - Update secret value (requires new value as second argument)"
    echo "  infra   - Update infrastructure using Deployment Manager"
    echo "  all     - Update everything"
    exit 1
    ;;
esac
