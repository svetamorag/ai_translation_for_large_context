"""
Application Configuration Module.

This module loads environment variables from a .env file and exposes them
as constants for the rest of the application.
"""

import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists.
# This is especially useful for local development.
load_dotenv()

# --- GCP Configuration ---
PROJECT_ID: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION: str | None = os.getenv("GOOGLE_CLOUD_LOCATION")
AGENT_ENGINE_ID: str | None = os.getenv("AGENT_ENGINE_ID")

# ============================================================================
# APPLICATION CONSTANTS
# ============================================================================

class TranslationDefaults:
    """Default values for the translation process."""
    MAX_CHUNK_SIZE = 30000
    METADATA_PREVIEW_SIZE = 30000
    TEMPERATURE = 1.0
    MODEL = "gemini-2.5-flash"


class Session:
    """Constants related to session management."""
    VALIDATION_USER_ID_BYTES = 8


class GeminiLimits:
    """API limits for Gemini."""
    MAX_OUTPUT_TOKENS = 8192


class GCSConstants:
    """Constants for Google Cloud Storage interactions."""
    SIGNED_URL_EXPIRATION_MINUTES = 15


class FileTypes:
    """Supported file types."""
    TXT = '.txt'
    PO = '.po'
    EPUB = '.epub'
    SUPPORTED = {TXT, PO, EPUB}