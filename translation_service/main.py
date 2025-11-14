import argparse
import logging
import uuid
import sys
import os

# Import classes from your existing translation.py
# NOTE: This import will still trigger the global 'vertexai.init' 
# in translation.py, so infrastructure Env Vars (PROJECT_ID, LOCATION)
# must still be set in the Cloud Run configuration.
from translation import TranslationConfig, TranslationPipeline

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # 1. Setup Argument Parsing
    parser = argparse.ArgumentParser(description="Cloud Run Translation Job")
    
    # Required arguments
    parser.add_argument("--source-file", required=True, help="GCS URI of the source file")
    parser.add_argument("--target-language", required=True, help="Target language (e.g. 'French')")
    parser.add_argument("--gcs-bucket", required=True, help="GCS bucket for inputs and outputs.")
    parser.add_argument("--gcs-folder", required=True, help="GCS folder for this translation session.")
    # Optional arguments from web_app/main.py
    parser.add_argument("--max-chunk-size", type=int, help="Maximum size of a chunk in characters.")
    parser.add_argument("--max-number-of-chunks", type=int, default=None, help="Maximum number of chunks to process.")

    # Parse args
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Starting Translation Job (CLI Mode)")
    logger.info(f"Source: {args.source_file}")
    logger.info(f"Target: {args.target_language}")
    logger.info("=" * 60)

    # 2. Prepare Configuration
    config = TranslationConfig(
        source_file=args.source_file,
        target_language=args.target_language,
        gcs_bucket=args.gcs_bucket,
        gcs_folder=args.gcs_folder,
        max_chunk_size=args.max_chunk_size or 20000,
        max_number_of_chunks=args.max_number_of_chunks,
    )

    # 3. Execute Pipeline
    try:
        pipeline = TranslationPipeline(config)
        result = pipeline.execute()
        
        if result['success']:
            logger.info("Job completed successfully.")
            sys.exit(0)
        else:
            logger.error("Job reported failure.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Critical failure: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()