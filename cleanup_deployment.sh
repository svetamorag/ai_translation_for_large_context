################################################################################
# Web Application cleanup script
################################################################################
#!/bin/bash
set -e

echo "Cleaning up Web App (Cloud Run Service)..."

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION=${REGION:-us-central1}
SERVICE_NAME=translation-app-service
REPO_NAME=translation-app

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Delete Cloud Run Service
if gcloud run services describe $SERVICE_NAME --region=$REGION &>/dev/null; then
    echo "Deleting Cloud Run Service: $SERVICE_NAME..."
    gcloud run services delete $SERVICE_NAME \
        --region=$REGION \
        --quiet
    echo "✓ Service deleted"
else
    echo "Service not found (already deleted)"
fi

echo ""
read -p "Delete Artifact Registry repository '$REPO_NAME'? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    if gcloud artifacts repositories describe $REPO_NAME --location=$REGION &>/dev/null; then
        echo "Deleting Artifact Registry: $REPO_NAME..."
        gcloud artifacts repositories delete $REPO_NAME \
            --location=$REGION \
            --quiet
        echo "✓ Repository deleted"
    else
        echo "Repository not found"
    fi
fi

echo ""
echo "Web App cleanup complete!"


################################################################################
# Translation Service cleanup script
################################################################################
#!/bin/bash
set -e

echo "Cleaning up Translation Service (Cloud Run Job)..."

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION=${REGION:-us-central1}
JOB_NAME=translation-job

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Delete Cloud Run Job
if gcloud run jobs describe $JOB_NAME --region=$REGION &>/dev/null; then
    echo "Deleting Cloud Run Job: $JOB_NAME..."
    gcloud run jobs delete $JOB_NAME \
        --region=$REGION \
        --quiet
    echo "✓ Job deleted"
else
    echo "Job not found (already deleted)"
fi


echo ""
echo "Translation Service cleanup complete!"


################################################################################
# Agent cleanup script
################################################################################
#!/bin/bash
set -e

echo "Cleaning up TVT Agent (Reasoning Engine)..."

if [ -f "tvt_agent/cleanup_agent.py" ]; then
    python3 tvt_agent/cleanup_agent.py
else
    echo "tvt_agent/cleanup_agent.py not found. Skipping agent cleanup."
fi

echo ""
echo "Agent cleanup complete!"
echo ""


################################################################################
# Verify all resources are deleted
################################################################################
#!/bin/bash

echo "Verifying cleanup..."
echo ""

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION=${REGION:-us-central1}

echo "=== Cloud Run Services ==="
gcloud run services list --region=$REGION --filter="metadata.name:translation" || echo "No services found"

echo ""
echo "=== Cloud Run Jobs ==="
gcloud run jobs list --region=$REGION --filter="metadata.name:translation" || echo "No jobs found"

echo ""
echo "=== Artifact Registry ==="
gcloud artifacts repositories list --location=$REGION --filter="name:translation" || echo "No repositories found"

echo ""

echo ""
echo "Verification complete!"
