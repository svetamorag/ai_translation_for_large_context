# Sample Web App

Flask web interface for submitting translation jobs.

## Overview

Provides:
- Web UI for translation job submission
- Cloud Run Job triggering via API


![assets/Sample_Web_App.png](/assets/Sample_Web_App.png)


## Prerequisites

```bash
# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Translation service must be deployed first

```

## Installation

### 1. Configure Environment

Create `.env` file:
```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
CLOUD_RUN_JOB_NAME="translation-job"

```

### 2. Deploy

```bash
chmod +x deploy_to_cloud_run.sh
./deploy_to_cloud_run.sh
```

This will:
- Create Artifact Registry repository
- Build Docker image
- Deploy Cloud Run service

### 3. Get Service URL

```bash
gcloud run services describe translation-app-service \
    --region=us-central1 \
    --format='value(status.url)'
```

## Usage

### Web Interface

1. Open the service URL in your browser
2. Fill in the translation form:
   - **Source File**: `gs://bucket/file.txt`
   - **Target Language**: `French`
   - **GCS Bucket**: `output-bucket`
3. Click "Translate"
4. Copy the session ID from response

## Configuration

Please update the config.py to include your environment variables.

---

