import os
import uuid
import logging
from flask import Flask, render_template, request, jsonify

from config import Config
from run_job import run_translation_job

app = Flask(__name__, template_folder='templates')

app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory store for job statuses. 
# NOTE: This is not suitable for production. In a real-world application, 
# you would use a persistent database (e.g., Redis, Firestore, or a relational DB)
# to store job state.
translation_jobs = {}

@app.route('/')
def index():
    """Render the main translation form."""
    return render_template('index.html')


@app.route('/translate', methods=['POST'])
def translate():
    """Handle the translation request and trigger the Cloud Run Job."""
    # --- Form Data ---
    source_file = request.form.get('source_file')
    target_language = request.form.get('target_language')
    max_chunk_size = int(request.form.get('max_chunk_size'))
    max_chunks_str = request.form.get('max_number_of_chunks')
    max_number_of_chunks = int(max_chunks_str) if max_chunks_str and max_chunks_str.isdigit() else None
    gcs_bucket = request.form.get('gcs_bucket')

    if not all([source_file, target_language, gcs_bucket]):
        return jsonify({
            "error": "Source File, Target Language, and GCS Bucket are required."
        }), 400

    entity_content = request.form.get('entity_instructions')
    style_content = request.form.get('style_instructions')

    entity_file = request.files.get('entity_file')
    style_file = request.files.get('style_file')

    if entity_file and entity_file.filename:
        entity_content = entity_file.read().decode('utf-8')

    if style_file and style_file.filename:
        style_content = style_file.read().decode('utf-8')

    session_id = str(uuid.uuid4()).replace('-', '')
    gcs_folder = f"translations/{session_id}"
    
    # Initialize job status
    translation_jobs[session_id] = {
        'status': 'initializing', 
        'gcs_bucket': gcs_bucket, 
        'gcs_folder': gcs_folder,
        'operation_name': None,
        'error': None
    }

    # --- Prepare arguments for Cloud Run Job ---
    job_args = [
        "--source-file", source_file,
        "--target-language", target_language,
        "--gcs-bucket", gcs_bucket,
        "--gcs-folder", gcs_folder,
    ]
    if max_chunk_size:
        job_args.extend(["--max-chunk-size", str(max_chunk_size)])
    if max_number_of_chunks:
        job_args.extend(["--max-number-of-chunks", str(max_number_of_chunks)])
    if entity_content:
        job_args.extend(["--entity-instructions", entity_content])
    if style_content:
        job_args.extend(["--style-instructions", style_content])

    try:
        logger.info(f"Triggering Cloud Run job for session: {session_id}")
        logger.info(f"Job arguments: {job_args}")
        
        # Execute the Cloud Run job
        operation = run_translation_job(overrides={"args": job_args})
        
        # Store operation details
        operation_name = operation.name if hasattr(operation, 'name') else str(operation)
        translation_jobs[session_id]['operation_name'] = operation_name
        translation_jobs[session_id]['status'] = 'running'
        
        logger.info(f"Job successfully triggered for session {session_id}")
        logger.info(f"Operation name: {operation_name}")
        
        return jsonify({
            "message": "Translation pipeline started successfully.",
            "session_id": session_id,
            "output_location": f"gs://{gcs_bucket}/{gcs_folder}",
            "operation_name": operation_name
        }), 200
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to trigger Cloud Run job for session {session_id}: {error_msg}", exc_info=True)
        
        # Update job status with detailed error
        translation_jobs[session_id]['status'] = 'failed'
        translation_jobs[session_id]['error'] = error_msg
        
        return jsonify({
            "error": "Failed to start the translation job.",
            "details": error_msg,
            "session_id": session_id
        }), 500


@app.route('/status/<session_id>', methods=['GET'])
def get_status(session_id):
    """Check the status of a translation job."""
    if session_id not in translation_jobs:
        return jsonify({"error": "Session not found"}), 404
    
    job_info = translation_jobs[session_id]
    return jsonify({
        "session_id": session_id,
        "status": job_info['status'],
        "gcs_bucket": job_info.get('gcs_bucket'),
        "gcs_folder": job_info.get('gcs_folder'),
        "operation_name": job_info.get('operation_name'),
        "error": job_info.get('error'),
        "output_location": f"gs://{job_info['gcs_bucket']}/{job_info['gcs_folder']}" if job_info.get('gcs_bucket') and job_info.get('gcs_folder') else None
    })


@app.route('/callback', methods=['POST'])
def job_callback():
    """
    Webhook endpoint for Cloud Run job to report completion status.
    The job should POST to this endpoint with session_id and status.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    status = data.get('status')  # 'completed' or 'failed'
    error = data.get('error')
    
    if not session_id or session_id not in translation_jobs:
        return jsonify({"error": "Invalid session_id"}), 400
    
    translation_jobs[session_id]['status'] = status
    if error:
        translation_jobs[session_id]['error'] = error
    
    logger.info(f"Job callback received for session {session_id}: status={status}")
    return jsonify({"message": "Status updated"}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5001)