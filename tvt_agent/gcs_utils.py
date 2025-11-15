from google.cloud import storage
from google.api_core import exceptions
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)
storage_client = storage.Client()


def read_file_from_gcs(gcs_uri: str) -> Optional[str]:
    """
    Reads the content of a file from a Google Cloud Storage URI.

    Args:
        gcs_uri: The GCS URI of the file to read (e.g., "gs://bucket-name/path/to/file.txt").

    Returns:
        The content of the file as a string, or None if the file does not exist.
    """
    logger.info(f"Reading file from GCS: {gcs_uri}")
    match = re.match(r"gs://([^/]+)/(.+)", gcs_uri)
    if not match:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")

    bucket_name, blob_name = match.groups()
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            logger.warning(f"File not found at GCS URI: {gcs_uri}")
            return None

        return blob.download_as_text(encoding="utf-8")
    except exceptions.GoogleAPICallError as e:
        logger.error(f"Error reading file from GCS: {e}", exc_info=True)
        raise

def save_file_to_gcs(gcs_uri: str, content: str) -> str:
    """
    Saves content to a file in Google Cloud Storage.

    Args:
        gcs_uri: The GCS URI where the file will be saved (e.g., "gs://bucket-name/path/to/file.txt").
        content: The string content to save to the file.

    Returns:
        A confirmation message indicating the file was saved.
    """
    match = re.match(r"gs://([^/]+)/(.+)", gcs_uri)
    if not match:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    bucket_name, blob_name = match.groups()
    
    logger.info(f"Saving file to GCS: {gcs_uri}")
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content, content_type='text/plain')
        return f"Successfully saved content to {gcs_uri}"
    except Exception as e:
        logger.error(f"Error saving file to GCS: {e}", exc_info=True)
        raise

def create_final_gcs_uri(original_gcs_uri: str) -> str:
    """
    Creates a new GCS URI for the final validated file.

    It takes an original GCS URI and prefixes the filename with "final_".

    Args:
        original_gcs_uri: The GCS URI of the translated file
                          (e.g., "gs://bucket/path/translated_chunk_0001.txt").

    Returns:
        A new GCS URI with the modified filename
        (e.g., "gs://bucket/path/final_translated_chunk_0001.txt").
    """
    if '/' not in original_gcs_uri:
        raise ValueError(f"Invalid GCS URI format: {original_gcs_uri}")

    path_prefix = original_gcs_uri.rsplit('/', 1)[0]
    original_filename = original_gcs_uri.rsplit('/', 1)[1]
    return f"{path_prefix}/final_{original_filename}"