import os

class Config:
    # Use os.environ.get to read variables injected by Cloud Run
    GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
    GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
    CLOUD_RUN_JOB_NAME = os.environ.get("CLOUD_RUN_JOB_NAME", "translation-job")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/translation_uploads")

    # Validation (Optional but recommended)
    if not GCP_PROJECT_ID:
        # This prevents the app from starting if critical config is missing
        raise ValueError("No GCP_PROJECT_ID set for Flask application")