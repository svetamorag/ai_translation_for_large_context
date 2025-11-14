# Translation Validation Team (tvt_agent) - Multi-Agent Validation System

A translation validation team (tvt_agent) - multi-agent system built with Google Agent Development Kit (ADK) that provides three-tier validation for translated content, ensuring terminology consistency, style adherence, and overall translation quality.


## 🎯 Overview

The Translation Validation Team (tvt_agent) is a sophisticated multi-agent system that validates translations through a coordinated workflow of specialized agents. It ensures that translations maintain:

- **Terminology Consistency**: Named entities and technical terms match the glossary
- **Style Adherence**: Tone, formality, and writing style follow guidelines
- **Editorial Quality**: Overall coherence, clarity, and naturalness



## 🔧 Prerequisites

### Required

- **Google Cloud Project** with billing enabled
- **APIs Enabled**:
  ```bash
  gcloud services enable aiplatform.googleapis.com
  gcloud services enable storage-api.googleapis.com
  gcloud services enable artifactregistry.googleapis.com
  ```

You need the following resources configured to use this deployment path:

- `Google Cloud account`, with administrator access to:
- `Google Cloud Project`: An empty Google Cloud project with billing enabled.
- `Python Environment`: A Python version between 3.9 and 3.13.
- `Google Cloud CLI tool`: The gcloud command line interface. 

### Required IAM Permissions

Service account needs:
- `aiplatform.reasoningEngines.create` - Deploy agents
- `aiplatform.reasoningEngines.get` - Access agents
- `aiplatform.reasoningEngines.query` - Execute agents
- `storage.objects.get` - Read source files
- `storage.objects.create` - Write validated translations
- `storage.buckets.get` - Access GCS buckets

## 📦 Installation

### Local Development Setup


1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install ADK and dependencies**
```bash
pip install google-cloud-aiplatform[adk,agent_engines]>=1.111
pip install google-cloud-storage
```


4. **Test locally** (optional)
```bash
    adk run tvt_agent
```

## 🚀 Deployment

### Deploy to Agent Engine

1. **Configure staging bucket**
```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
export STAGING_BUCKET=gs://your-staging-bucket

# Create staging bucket if needed
gsutil mb -l $REGION $STAGING_BUCKET
```

2. **Review deployment script**
```bash
cat deploy_to_agent_engine.sh
```

3. **Deploy agents**
```bash
chmod +x deploy_to_agent_engine.sh
./deploy_to_agent_engine.sh
```

The script deploys the agent hierarchy to Agent Engines and returns an `agent_engine_id`.



### Manual Deployment (Optional)

```bash
adk deploy agent_engine \
    --project=$PROJECT_ID \
    --region=$REGION \
    --staging_bucket=$STAGING_BUCKET \
    --display_name="Translation Validation Team" \
    --agent_engine_id=OPTIONAL_EXISTING_ID \
    tvt_agent
```

### Update Existing Deployment

```bash
# Update with same agent_engine_id to maintain references
adk deploy agent_engine \
    --project=$PROJECT_ID \
    --region=$REGION \
    --staging_bucket=$STAGING_BUCKET \
    --display_name="Translation Validation Team" \
    --agent_engine_id=your_agent_engine_id \
    tvt_agent
```
