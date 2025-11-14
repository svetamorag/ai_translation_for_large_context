from google.cloud import storage
import re
import logging

logger = logging.getLogger(__name__)
storage_client = storage.Client()

def read_file_from_gcs(gcs_uri: str) -> str:
    """
    Reads the content of a file from a Google Cloud Storage URI.

    Args:
        gcs_uri: The GCS URI of the file to read (e.g., "gs://bucket-name/path/to/file.txt").

    Returns:
        The content of the file as a string.
    """
    logger.info(f"Reading file from GCS: {gcs_uri}")
    match = re.match(r"gs://([^/]+)/(.+)", gcs_uri)
    if not match:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")

    try:
        bucket_name, blob_name = match.groups()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        return blob.download_as_text()
    except Exception as e:
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