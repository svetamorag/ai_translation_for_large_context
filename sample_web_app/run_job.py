import logging
from google.cloud import run_v2
from config import Config  # Import the configuration class

logger = logging.getLogger(__name__)

def run_translation_job(overrides: dict):
    """
    Triggers a Google Cloud Run Job with specified container overrides.
    Configuration (Project, Region, Job Name) is loaded directly from config.py.

    Args:
        overrides (dict): A dictionary containing container override settings.
            Expected keys:
            - 'args' (list[str]): A list of command-line arguments to pass to the job's container.
            - 'env' (list[dict]): A list of environment variables to set in the container.
                                Each dict should have 'name' and 'value' keys.

    Returns:
        The operation object returned by the `run_job` API call.

    Raises:
        ValueError: If required GCP configuration is missing.
        Exception: If the Cloud Run job fails to trigger.
    """
    # Ensure critical configuration exists before attempting to call the API
    if not all([Config.GCP_PROJECT_ID, Config.GCP_REGION, Config.CLOUD_RUN_JOB_NAME]):
        raise ValueError(
            f"Missing required GCP configuration in config.py. "
            f"PROJECT_ID: {Config.GCP_PROJECT_ID}, REGION: {Config.GCP_REGION}, JOB_NAME: {Config.CLOUD_RUN_JOB_NAME}"
        )

    client = run_v2.JobsClient()

    # Use variables from Config class
    job_path = (
        f"projects/{Config.GCP_PROJECT_ID}/"
        f"locations/{Config.GCP_REGION}/"
        f"jobs/{Config.CLOUD_RUN_JOB_NAME}"
    )

    # Process environment variable overrides if present
    env_vars = [
        run_v2.EnvVar(name=env_var.get("name"), value=env_var.get("value"))
        for env_var in overrides.get("env", [])
    ]

    request = run_v2.RunJobRequest(
        name=job_path,
        overrides=run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(
                    args=overrides.get("args", []),
                    env=env_vars,
                    clear_args=False 
                )
            ]
        )
    )

    try:
        logger.info(f"Triggering Cloud Run Job '{Config.CLOUD_RUN_JOB_NAME}' "
                    f"in {Config.GCP_REGION} with overrides: {overrides.get('args')}")
        
        response = client.run_job(request=request)
        
        logger.info(f"Cloud Run Job triggered successfully. Operation details: {response}")
        return response
    except Exception as e:
        logger.error(f"Failed to trigger Cloud Run Job '{Config.CLOUD_RUN_JOB_NAME}': {e}", exc_info=True)
        raise