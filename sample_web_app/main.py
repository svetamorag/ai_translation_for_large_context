import argparse
import logging
import sys

# Import the shared triggering logic and configuration
# This requires run_job.py and config.py to be in the same directory
try:
    from run_job import run_translation_job
except ImportError:
    sys.exit("Error: Could not import 'run_translation_job'. Ensure 'run_job.py' and 'config.py' are in the current directory.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """
    Main function to parse arguments and trigger the translation pipeline.
    This script acts as a CLI wrapper around the logic defined in run_job.py.
    """
    parser = argparse.ArgumentParser(description="Trigger a translation pipeline Cloud Run job.")
    
    # CLI arguments (using standard hyphens for the user interface)
    parser.add_argument("--source-file", required=True, help="GCS path to the source file.")
    parser.add_argument("--target-language", required=True, help="Target language code.")
    parser.add_argument("--gcs-bucket", required=True, help="GCS bucket for inputs and outputs.")
    parser.add_argument("--gcs-folder", required=True, help="GCS folder for this translation session.")
    parser.add_argument("--max-chunk-size", type=int, help="Maximum size of a chunk in characters.")
    parser.add_argument("--max-number-of-chunks", type=int, help="Maximum number of chunks to process.")
    
    args = parser.parse_args()

    logger.info(f"Preparing to trigger Cloud Run job with arguments: {args}")

    try:
        job_args = [
            "--source-file", args.source_file,
            "--target-language", args.target_language,
            "--gcs-bucket", args.gcs_bucket,
            "--gcs-folder", args.gcs_folder,
        ]

        if args.max_chunk_size is not None:
            job_args.extend(["--max-chunk-size", str(args.max_chunk_size)])

        if args.max_number_of_chunks is not None:
            job_args.extend(["--max-number-of-chunks", str(args.max_number_of_chunks)])

        logger.info(f"Triggering Cloud Run job with container args: {job_args}")
        
        # Trigger the job using the shared logic from run_job.py
        # This will automatically use the config from config.py (GCP_PROJECT_ID, etc.)
        run_translation_job(
            overrides={"args": job_args}
        )
        
        logger.info("Cloud Run job triggered successfully.")

    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to trigger Cloud Run job: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()