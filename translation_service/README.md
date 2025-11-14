# Translation Service

Core translation engine that processes documents, generates translations using Gemini AI, and validates results with multi-agent system.

## Overview

Handles the complete translation pipeline:
- Document parsing (.txt, .po, .epub)
- Entities and style extraction
- Intelligent chunking at natural boundaries
- Gemini-powered translation
- Multi-agent validation
- Document reassembly

## Prerequisites

```bash
# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage-api.googleapis.com

# Deploy tvt_agent FIRST to get AGENT_ENGINE_ID!
# Save the AGENT_ENGINE_ID from output
```

## Installation

### 1. Configure Environment

Create `.env` file:
```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
AGENT_ENGINE_ID=projects/PROJECT_NUM/locations/LOCATION/reasoningEngines/ENGINE_ID
JOB_SERVICE_ACCOUNT=your-sa@project.iam.gserviceaccount.com
```

### 2. Deploy

```bash
chmod +x deploy_as_cloudrun_job.sh
./deploy_as_cloudrun_job.sh
```

This creates a Cloud Run Job named `translation-job`.

### 3. Test

To trigger the deployed Cloud Run job, run:
```bash
    chmod +x run_job.sh 
    ./run_job.sh
```

Or run manually: 
```bash
python main.py \
    --source-file gs://bucket/test.txt \
    --target-language French \
    --gcs-bucket output-bucket \
    --gcs-folder test-session \
    --gcs-folder-prefix="translations" \
    --max-chunk-size=20000
```

## Usage

Triggered automatically by the web app, or manually by running run_job.sh

## Output

Results saved to GCS:
```
gs://bucket/translations/session-id/
├── entity_extraction.txt
├── style_instructions.txt
├── original_chunks/
├── prompts_for_translation/
├── translated_chunks/
└── FINAL_document.txt
```

---
