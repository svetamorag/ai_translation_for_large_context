"""
Professional Translation System with Context-Aware Chunking and AI Validation

This module provides a comprehensive translation pipeline that:
- Extracts entities and style instructions from source documents
- Performs intelligent context-aware chunking at natural text boundaries
- Supports user-provided entity and style customization files
- Generates structured translation prompts with full context
- Executes translations using Gemini API with streaming support
- Validates translations using Google ADK Agent for quality assurance
- Supports multiple file formats (.txt, .po, .epub)
- Manages all artifacts in Google Cloud Storage

Architecture:
    DocumentReader -> MetadataExtractor -> ContextAwareChunker
    -> TranslationPipeline -> GeminiClient -> ValidationAgent

GCS Folder Structure:
    {session_id}/
    ├── entity_extraction.txt          # Extracted entities and glossary
    ├── style_instructions.txt         # Extracted style guidelines
    ├── original_chunks/               # Source text chunks
    │   ├── original_chunk_0001.txt
    │   └── ...
    ├── prompts_for_translation/       # Translation prompts with context
    │   ├── translation_prompt_chunk_0001.txt
    │   └── ...
    └── translated_chunks/             # Translated results
        ├── translated_chunk_0001.txt
        └── final_translated_chunk_0001.txt #After agent validation

Author: Translation System Team
Version: 2.0
"""

import os
import argparse
import re
import uuid
import logging
import mimetypes
import secrets
import datetime
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass

# Google Cloud imports
from google import genai
from google.genai import types
from google.cloud import storage
import vertexai
from vertexai import agent_engines

# Document processing imports
import polib
from epub_reader import EPUBHandler, read_epub_to_text


# Local imports
from prompts import (
    EXTRACT_ENTITIES_PROMPT,
    EXTRACT_STYLE_PROMPT,
    TRANSLATION_PROMPT_TEMPLATE
)
import translation_config
 
# Import readers for reference, but logic will be in-class
from po_reader import read_po_to_text, assemble_po_from_text

# ============================================================================
# GLOBAL INITIALIZATION
# ============================================================================

# Set up a module-level logger
logger = logging.getLogger(__name__)

# Initialize Vertex AI and connect to the deployed agent once at module load
if not translation_config.PROJECT_ID or not translation_config.LOCATION or not translation_config.AGENT_ENGINE_ID:
    raise ValueError(
        "PROJECT_ID, LOCATION, and AGENT_ENGINE_ID must be set in the environment."
    )
print (translation_config.PROJECT_ID, translation_config.LOCATION, translation_config.AGENT_ENGINE_ID)
vertexai.init(project=translation_config.PROJECT_ID, location=translation_config.LOCATION)
_remote_agent_app = agent_engines.get(translation_config.AGENT_ENGINE_ID)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class DocumentChunk:
    """
    Represents a chunk of the original document.

    Attributes:
        index: Sequential chunk number (1-based)
        content: The actual text content of the chunk
        gcs_uri: Google Cloud Storage URI where the chunk is stored
    """
    index: int
    content: str
    gcs_uri: Optional[str] = None


@dataclass
class TranslationConfig:
    """
    Configuration for translation operations.

    Attributes:
        source_file: Path or GCS URI to the source file
        target_language: Target language for translation
        gcs_bucket: GCS bucket name for storing artifacts
        gcs_folder: GCS folder path for this translation session
        max_chunk_size: Maximum characters per chunk
        metadata_preview_size: Characters to use for metadata extraction
        max_number_of_chunks: Optional limit on the number of chunks to process
        model: Gemini model to use
        temperature: Sampling temperature for generation
    """
    source_file: str
    target_language: str
    gcs_bucket: str
    gcs_folder: str
    max_chunk_size: int = translation_config.TranslationDefaults.MAX_CHUNK_SIZE
    metadata_preview_size: int = translation_config.TranslationDefaults.METADATA_PREVIEW_SIZE
    max_number_of_chunks: Optional[int] = None
    temperature: float = translation_config.TranslationDefaults.TEMPERATURE
    use_agent_validation: bool = True
    model: str = translation_config.TranslationDefaults.MODEL



@dataclass
class DocumentContent:
    """
    Structured document content with metadata.

    Attributes:
        text: The extracted text content
        file_type: File extension/type (txt, po, epub)
        metadata: Optional format-specific metadata
    """
    text: str
    file_type: str
    metadata: Optional[Any] = None


# ============================================================================
# AGENT VALIDATION
# ============================================================================

def validate_translation_with_agent(
    prompt_url: str,
    translated_url: str
) -> Dict[str, str]:
    """
    Validates a translated chunk using Google ADK Agent.

    This function creates an isolated agent session and streams the validation
    response. The agent receives both the translation prompt (containing source
    text, entities, and style instructions) and the translated result.

    Args:
        prompt_url: Signed URL to the translation prompt file containing
                   source text and translation instructions
        translated_url: Signed URL to the translated chunk file

    Returns:
        Dictionary containing the validation output:
        {'output': 'validation response text'}

    Raises:
        Exception: If agent API call fails or returns an error
    """
    logger.info(f"Starting validation for: {translated_url}")

    try:
        # Generate unique user_id for session isolation
        user_id = f"validation_user_{secrets.token_hex(translation_config.Session.VALIDATION_USER_ID_BYTES)}" # type: ignore
        # Create a new agent session
        remote_session_response = _remote_agent_app.create_session(user_id=user_id)
        session_id = remote_session_response["id"]

        # Construct validation prompt
        validation_prompt = (
            f"Help me validate the translation:\n"
            f"Source file (with instructions): {prompt_url}\n"
            f"Translated file: {translated_url}"
        )

        # Stream agent response
        response_text = ""
        for event in _remote_agent_app.stream_query(
            user_id=user_id,
            session_id=session_id,
            message=validation_prompt
        ):
            # Extract text from nested event structure
            if 'content' in event and 'parts' in event['content']:
                for part in event['content']['parts']:
                    if 'text' in part:
                        response_text += part['text']

        logger.info(f"Validation completed successfully for: {translated_url}")
        return {'output': response_text}

    except Exception as e:
        logger.error(f"Agent validation failed for {translated_url}: {e}", exc_info=True)
        error_msg = f"Agent validation failed: {str(e)}"
        raise Exception(error_msg) from e

# ============================================================================
# CORE CLASSES
# ============================================================================

class GeminiClient:
    """
    Handles all interactions with the Gemini API.

    This client provides streaming content generation with configurable
    safety settings and thinking budget for enhanced reasoning capabilities.
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        """
        Initialize Gemini client.

        Args:
            model: Gemini model identifier (default: gemini-2.5-flash)
        """
        self.model = model
        self.client = genai.Client(vertexai=True)
    
    def generate(
        self,
        prompt: str,
        temperature: float = 1.0
    ) -> str:
        """
        Generate content using Gemini API with streaming.

        Configures safety settings to OFF for translation tasks and enables
        Google Search tool with unlimited thinking budget.

        Args:
            prompt: Input prompt text for generation
            temperature: Sampling temperature (0.0-2.0, default: 1.0)

        Returns:
            Generated text response as a complete string

        Raises:
            Exception: If generation fails or API error occurs
        """
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)]
            )
        ]
        
        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=1.0,
            max_output_tokens=translation_config.GeminiLimits.MAX_OUTPUT_TOKENS,
            safety_settings=[
                types.SafetySetting(category=cat, threshold="OFF")
                for cat in [
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_HARASSMENT"
                ]
            ],
            tools=[types.Tool(google_search=types.GoogleSearch())],
            thinking_config=types.ThinkingConfig(thinking_budget=-1)
        )
        
        response_text = ""
        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=generation_config
        ):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                response_text += chunk.text
        
        return response_text

class GCSManager:
    """
    Manages all Google Cloud Storage operations.

    Provides high-level abstractions for file upload/download, signed URL
    generation, and blob listing operations.
    """

    def __init__(self, bucket_name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize GCS manager.

        Args:
            bucket_name: Name of the GCS bucket to use
            logger: Optional logger instance to use for logging.
        """
        self.client = storage.Client()
        self.logger = logger or logging.getLogger(__name__)
        self.bucket_name = bucket_name
        self.bucket = self.client.bucket(bucket_name)
    
    def download_file(self, gcs_uri: str, destination_dir: Optional[str] = None) -> str:
        """
        Download file from GCS to local filesystem.

        If the URI is not a GCS path, returns it unchanged (assumes local file).

        Args:
            gcs_uri: GCS URI (gs://bucket/path) or local file path
            destination: Local destination folder. NOTE: In a production environment, 
                         it is recommended to use a temporary directory created with 
                         the `tempfile` module instead of a hardcoded path.

        Returns:
            Local file path to the downloaded file

        Raises:
            ValueError: If GCS URI format is invalid
        """
        if not gcs_uri.startswith("gs://"):
            return gcs_uri

        match = re.match(r"gs://([^/]+)/(.+)", gcs_uri)
        if not match:
            raise ValueError(f"Invalid GCS URI format: {gcs_uri}")

        bucket_name, blob_name = match.groups()
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if destination_dir is None:
            destination_dir = tempfile.gettempdir()

        local_path = os.path.join(destination_dir, os.path.basename(blob_name))
        blob.download_to_filename(local_path)

        return local_path
    
    def upload(
        self,
        blob_path: str,
        content: Optional[str] = None,
        local_path: Optional[str] = None
    ) -> str:
        """
        Uploads content or a local file to GCS.

        Exactly one of 'content' or 'local_path' must be provided.

        Args:
            blob_path: Target blob path in the bucket.
            content: Text content to upload
            local_path: Path to the local file to upload.

        Returns:
            The GCS URI of the uploaded file.

        Raises:
            ValueError: If both or neither of 'content' and 'local_path' are provided.
        """
        if (content is None and local_path is None) or \
           (content is not None and local_path is not None):
            raise ValueError("Exactly one of 'content' or 'local_path' must be provided.")

        blob_path = blob_path.strip('/')
        blob = self.bucket.blob(blob_path)

        if local_path:
            content_type, _ = mimetypes.guess_type(local_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            blob.upload_from_filename(local_path, content_type=content_type)
        elif content is not None:
            content_type = 'text/plain'
            if blob_path.endswith('.po'):
                content_type = 'text/x-gettext-translation'
            blob.upload_from_string(content, content_type=content_type)
            
        return f"gs://{self.bucket_name}/{blob_path}"



    def generate_signed_url(
        self,
        blob_path: str,
        expiration_minutes: int = translation_config.GCSConstants.SIGNED_URL_EXPIRATION_MINUTES
    ) -> str:
        """
        Generate a temporary signed URL for blob access.

        Signed URLs allow temporary authenticated access without credentials.

        Args:
            blob_path: Target blob path in bucket (e.g., 'folder/file.txt')
            expiration_minutes: URL validity duration in minutes (default: 15)

        Returns:
            Signed URL string with v4 signature

        Raises:
            Exception: If URL generation fails
        """
        blob = self.bucket.blob(blob_path.strip('/'))
        return blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes)
        )
    
    def list_blobs(self, prefix: str) -> List[storage.Blob]:
        """
        List all blobs with a given prefix.

        Args:
            prefix: Blob path prefix (leading slashes are stripped)

        Returns:
            List of storage.Blob objects matching the prefix
        """
        return list(self.client.list_blobs(
            self.bucket_name,
            prefix=prefix.strip('/')
        ))

    def count_blobs(self, prefix: str) -> int:
        """
        Count the number of blobs with a given prefix.

        Args:
            prefix: Blob path prefix (leading slashes are stripped)

        Returns:
            The number of blobs matching the prefix.
        """
        blobs = self.client.list_blobs(
            self.bucket_name, prefix=prefix.strip('/')
        )
        return sum(1 for _ in blobs)

    def read_blob_text(self, blob_path: str) -> str:
        """
        Read text content from a blob.

        Args:
            blob_path: Path to blob in bucket (leading slashes are stripped)

        Returns:
            Text content as string

        Raises:
            Exception: If blob doesn't exist or read fails
        """
        blob = self.bucket.blob(blob_path.strip('/'))
        return blob.download_as_text()
class DocumentReader:
    """
    Reads and parses various document formats.

    Supports:
    - Plain text files (.txt)
    - Portable Object translation files (.po)
    - EPUB ebook files (.epub)
    """

    SUPPORTED_FORMATS = translation_config.FileTypes.SUPPORTED

    @staticmethod
    def read(file_path: str) -> DocumentContent:
        """
        Read document content based on file extension.

        Routes to appropriate format-specific reader based on file extension.

        Args:
            file_path: Path to the document file

        Returns:
            DocumentContent object with extracted text and metadata

        Raises:
            ValueError: If file format is not supported
        """
        extension = Path(file_path).suffix.lower()

        if extension == '.txt':
            return DocumentReader._read_text(file_path)
        elif extension == '.po':
            return DocumentReader._read_po(file_path)
        elif extension == '.epub':
            return DocumentReader._read_epub(file_path)
        else:
            supported = ', '.join(DocumentReader.SUPPORTED_FORMATS)
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported formats: {supported}"
            )
    
    @staticmethod
    def _read_text(file_path: str) -> DocumentContent:
        """
        Read plain text file with encoding detection.

        Attempts UTF-8 decoding first, falls back to Latin-1 if needed.

        Args:
            file_path: Path to .txt file

        Returns:
            DocumentContent with extracted text
        """
        with open(file_path, 'rb') as f:
            content = f.read()

        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')

        return DocumentContent(text=text, file_type='txt')
    
    @staticmethod
    def _read_po(file_path: str) -> DocumentContent:
        """
        Read PO (Portable Object) translation file.

        Extracts msgid, msgstr, and comments from each entry.

        Args:
            file_path: Path to .po file

        Returns:
            DocumentContent with structured text and PO metadata
        """
        text_content = read_po_to_text(file_path)
        po_object = polib.pofile(file_path)

        return DocumentContent(
            text=text_content,
            file_type='po',
            metadata=po_object
        )
    
    @staticmethod
    def _read_epub(file_path: str) -> DocumentContent:
        """
        Read EPUB ebook file using the new EPUBHandler.

        Preserves all HTML structure, tags, and formatting while extracting
        metadata (title, author) from the EPUB.

        Args:
            file_path: Path to .epub file

        Returns:
            DocumentContent with HTML content and EPUB metadata

        Raises:
            FileNotFoundError: If the EPUB file doesn't exist
            Exception: If EPUB parsing fails
        """
        try:
            # Use the new EPUBHandler
            handler = EPUBHandler(file_path)
            html_content = handler.read_epub_to_text()
            
            # Store the handler as metadata so we can access book info later
            metadata = {
                'title': handler.metadata.get('title', 'Unknown'),
                'author': handler.metadata.get('author', 'Unknown'),
                'handler': handler  # Keep handler reference for potential reuse
            }
            
            return DocumentContent(
                text=html_content,
                file_type='epub',
                metadata=metadata
            )
            
        except Exception as e:
            raise IOError(f"Failed to read EPUB file {file_path}: {e}") from e


class ContextAwareChunker:
    """
    Splits text into chunks while preserving context boundaries.

    Uses intelligent boundary detection to ensure chunks break at:
    1. Paragraph breaks (double newlines) - highest priority
    2. Section breaks (single newlines)
    3. Sentence endings (. ! ?)
    4. Word boundaries (spaces) - last resort

    This ensures translated chunks maintain natural reading flow and context.
    """

    def __init__(self, max_chunk_size: int = 30000):
        """
        Initialize chunker.

        Args:
            max_chunk_size: Maximum characters per chunk (default: 30000)
        """
        self.max_chunk_size = max_chunk_size
    
    def chunk(self, text: str) -> List[str]:
        """
        Split text into context-aware chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.max_chunk_size:
            return [text]
        
        chunks = []
        position = 0
        
        while position < len(text):
            chunk_end = self._find_chunk_boundary(text, position)
            chunks.append(text[position:chunk_end])
            position = chunk_end
        
        return chunks
    
    def _find_chunk_boundary(self, text: str, start: int) -> int:
        """
        Find the optimal boundary for a chunk.
        
        Attempts to break at:
        1. Paragraph boundary (double newline)
        2. Section boundary (single newline)
        3. Sentence boundary (. ! ?)
        4. Word boundary (space)
        
        Args:
            text: Full text
            start: Starting position
            
        Returns:
            End position for chunk
        """
        ideal_end = start + self.max_chunk_size
        
        if ideal_end >= len(text):
            return len(text)
        
        search_text = text[start:ideal_end]
        min_chunk_ratio = 0.7  # Minimum 70% of max size
        min_position = int(self.max_chunk_size * min_chunk_ratio)
        
        boundary = self._find_last_occurrence(search_text, '\n\n', min_position)
        if boundary >= 0:
            return start + boundary + 2
        
        boundary = self._find_last_occurrence(search_text, '\n', min_position)
        if boundary >= 0:
            return start + boundary + 1
        
        sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
        best_boundary = -1
        for ending in sentence_endings:
            pos = self._find_last_occurrence(search_text, ending, min_position)
            if pos > best_boundary:
                best_boundary = pos
        
        if best_boundary >= 0:
            return start + best_boundary + 2
        
        boundary = self._find_last_occurrence(search_text, ' ', min_position)
        if boundary >= 0:
            return start + boundary + 1
        
        return ideal_end
    
    @staticmethod
    def _find_last_occurrence(text: str, pattern: str, min_pos: int) -> int:
        """
        Find last occurrence of pattern after minimum position.
        
        Args:
            text: Text to search
            pattern: Pattern to find
            min_pos: Minimum position
            
        Returns:
            Position of last occurrence, or -1 if not found
        """
        pos = text.rfind(pattern)
        return pos if pos >= min_pos else -1

class MetadataExtractor:
    """
    Extracts translation metadata from documents.

    Uses Gemini to analyze document previews and extract:
    - Named entities (people, places, organizations, technical terms)
    - Style instructions (tone, formality, special formatting rules)
    """

    def __init__(self, gemini_client: GeminiClient):
        """
        Initialize metadata extractor.

        Args:
            gemini_client: Configured GeminiClient instance
        """
        self.client = gemini_client



    def _extract_entities(self, text: str, target_language: str) -> str:
        """
        Extract important entities for translation consistency.

        Args:
            text: Text to analyze
            target_language: The target language for translation.

        Returns:
            Extracted entities as formatted string
        """
        prompt = EXTRACT_ENTITIES_PROMPT.format(
            text=text,
            target_language=target_language
        )
        return self.client.generate(prompt)

    def _extract_style(self, text: str, target_language: str) -> str:
        """
        Extract style instructions for translation.

        Args:
            text: Text to analyze
            target_language: The target language for translation.

        Returns:
            Style instructions as formatted string
        """
        prompt = EXTRACT_STYLE_PROMPT.format(
            text=text, 
            target_language=target_language
            )
        return self.client.generate(prompt)

class TranslationPipeline:
    """
    Orchestrates the translation workflow, including document processing, translation, and validation.
    """

    FILE_TYPE_INSTRUCTIONS = {
        'txt': "Plain text document. Maintain paragraph structure and formatting.",
        'po': "PO (Portable Object) translation file. Preserve msgid/msgstr structure and formatting markers.",
        'epub': "EPUB ebook in HTML format. Preserve ALL HTML tags, attributes, and structure. Do not escape HTML entities. Maintain all formatting tags like <p>, <h1>, <div>, <em>, <strong>, etc."
    }

    def __init__(self, config: TranslationConfig, gcs_manager: Optional[GCSManager] = None):
        """
        Initialize translation pipeline.

        Args:
            config: Translation configuration with all necessary parameters
            gcs_manager: Optional GCSManager instance. If not provided, a new one will be created.
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.gcs = gcs_manager or GCSManager(config.gcs_bucket, logger=self.logger)
        self.gemini = GeminiClient(config.model)
        self.chunker = ContextAwareChunker(config.max_chunk_size)
        self.extractor = MetadataExtractor(self.gemini)
    
    def execute(
        self,
        entity_content: Optional[str] = None,
        style_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete translation pipeline from a local or GCS file.

        Orchestrates the full workflow from source document to validated
        translations, with optional user-provided metadata. All artifacts are
        stored in the configured GCS bucket.

        Args:
            entity_content: Optional user-provided entity glossary
            style_content: Optional user-provided style instructions

        Returns:
            Dictionary containing:
            - success: Boolean indicating overall success
            - prompts_created: Number of translation prompts generated
            - translations_completed: Number of translations completed
            - gcs_folder: GCS URI where all artifacts are stored

        Raises:
            Exception: If any step in the pipeline fails
        """
        local_file = None
        try:
            self.logger.info(f"Starting translation for {self.config.source_file}")
            self.logger.info(f"Output will be saved to: gs://{self.config.gcs_bucket}/{self.config.gcs_folder}")

            local_file, content = self._download_and_read_document()
            file_type = content.file_type

            metadata = self._handle_metadata(entity_content, style_content, content)

            num_prompts = self._chunk_and_create_prompts(content.text, file_type, metadata)

            num_translations = self._execute_and_validate_translations()

            self._reassemble_and_finalize(file_type, local_file)
            
            return {
                'success': True,
                'prompts_created': num_prompts,
                'translations_completed': num_translations,
                'gcs_folder': f"gs://{self.config.gcs_bucket}/{self.config.gcs_folder}",
            }

        except Exception as e:
            self.logger.error(f"Translation pipeline failed: {e}", exc_info=True)
            raise
        finally:
            # Cleanup temporary file
            if local_file and self.config.source_file.startswith("gs://") and os.path.exists(local_file):
                os.remove(local_file)

    def _download_and_read_document(self) -> tuple[str, DocumentContent]:
        """Downloads the source file and returns its content."""
        self.logger.info(f"Downloading source file: {self.config.source_file}...")
        local_file = self.gcs.download_file(self.config.source_file)
        self.logger.info("Source file downloaded.")

        self.logger.info("Reading and parsing document...")
        content = DocumentReader.read(local_file)
        self.logger.info("Document parsed successfully.")
        return local_file, content

    def _handle_metadata(self, entity_content: Optional[str], style_content: Optional[str], content: DocumentContent) -> Dict[str, str]:
        """Extracts or uses user-provided metadata and saves it to GCS."""
        entities = entity_content
        style = style_content

        if not entities:
            self.logger.info("Extracting entities from document...")
            entities = self.extractor._extract_entities(
                content.text[:self.config.metadata_preview_size],
                self.config.target_language
            )
            self.logger.info("Entity extraction complete.")

        if not style:
            self.logger.info("Extracting style instructions from document...")
            style = self.extractor._extract_style(
                content.text[:self.config.metadata_preview_size],
                self.config.target_language
            )
            self.logger.info("Style instruction extraction complete.")

        self.logger.info("Saving metadata to GCS...")
        metadata = self._save_provided_metadata(entities, style, self.logger.info)
        self.logger.info("Metadata processed and saved.")
        return metadata

    def _chunk_and_create_prompts(self, text: str, file_type: str, metadata: Dict[str, str]) -> int:
        """Chunks the document, uploads original chunks, and creates translation prompts."""
        self.logger.info("Chunking document and creating translation prompts...")
        original_chunks = self._chunk_and_upload_original(text, self.logger.info)
        num_prompts = self._create_prompts(original_chunks, file_type, metadata, self.logger.info)
        self.logger.info(f"Created {num_prompts} prompt files.")
        return num_prompts

    def _execute_and_validate_translations(self) -> int:
        """Executes the translation and validation for each chunk."""
        self.logger.info("Starting translation of chunks...")
        num_translations = self._execute_translations(self.logger.info)
        self.logger.info(f"Completed {num_translations} translations.")
        return num_translations

    def _reassemble_and_finalize(self, file_type: str, local_file: str) -> None:
        """
        Reassembles the final document and handles format-specific reassembly.
        
        Args:
            file_type: Original file type ('txt', 'po', 'epub')
            local_file: Path to the original local file
        """
        self.logger.info("Reassembling final translated document...")
        final_doc_path = self._reassemble_final_document(file_type, self.logger.info)
        self.logger.info(f"Final document saved to: {final_doc_path}")

        if file_type == 'po':
            self._reassemble_po_file(final_doc_path, local_file)
        elif file_type == 'epub':
            self._reassemble_epub_file(final_doc_path, local_file)

    def _reassemble_po_file(self, final_doc_path: str, local_file: str) -> None:
        """Reassemble PO file from translated text."""
        self.logger.info("  - Assembling final .po file from translated text...")
        try:
            final_text_local_path = self.gcs.download_file(final_doc_path)
            
            original_basename = os.path.basename(self.config.source_file)
            assembled_po_filename = f"assembled_{original_basename}"
            assembled_po_local_path = os.path.join("/tmp", assembled_po_filename)

            assemble_po_from_text(final_text_local_path, local_file, assembled_po_local_path)
            self.gcs.upload(
                local_path=assembled_po_local_path,
                blob_path=f"{self.config.gcs_folder.strip('/')}/{assembled_po_filename}"
            )
            self.logger.info(
                f"  - Final .po file saved to GCS: "
                f"{self.config.gcs_folder.strip('/')}/{assembled_po_filename}"
            )
        except Exception as e:
            self.logger.warning(f"Failed to assemble .po file: {e}", exc_info=True)

    def _reassemble_epub_file(self, final_doc_path: str, local_file: str) -> None:
        """
        Reassemble EPUB file from translated HTML content.
        
        Args:
            final_doc_path: GCS path to the final translated HTML document
            local_file: Path to the original EPUB file (unused in new implementation, kept for signature consistency)
        """
        self.logger.info("  - Saving final translated EPUB content as a text file...")
        try:
            # Read the final translated content directly from GCS
            final_content = self.gcs.read_blob_text(final_doc_path.replace(f"gs://{self.config.gcs_bucket}/", ""))
            
            # Create output filename
            original_basename = os.path.basename(self.config.source_file)
            # Change the extension to .txt to reflect the new format
            assembled_filename = f"assembled_{Path(original_basename).stem}.txt"
            
            final_blob_path = f"{self.config.gcs_folder.strip('/')}/{assembled_filename}"
            
            # Upload to GCS
            self.gcs.upload(
                blob_path=final_blob_path,
                content=final_content
            )
            
            self.logger.info(
                f"  - Final translated content saved to GCS as a text file: "
                f"{final_blob_path}"
            )
                
        except Exception as e:
            self.logger.warning(f"Failed to assemble .epub file: {e}", exc_info=True)


    def _save_provided_metadata(self, entity_content: str, style_content: str, status_callback: callable) -> Dict[str, str]:
        """Save user-provided metadata to GCS."""
        folder = self.config.gcs_folder.strip('/')

        if entity_content:
            self.gcs.upload(
                blob_path=f"{folder}/entity_extraction.txt",
                content=entity_content
            )
            status_callback("Provided entity extraction file saved to GCS.")

        if style_content:
            self.gcs.upload(
                blob_path=f"{folder}/style_instructions.txt",
                content=style_content
            )
            status_callback("Provided style instructions file saved to GCS.")

        return {
            'entities': entity_content,
            'style': style_content
        }
    
    def _chunk_and_upload_original(
        self,
        text: str,
        status_callback: Callable[[str], None]
    ) -> List[DocumentChunk]:
        """
        Chunk original text and upload to GCS.

        Args:
            text: The text content to chunk.
            status_callback: Callback for progress updates

        Returns:
            List of DocumentChunk objects with GCS URIs
        """
        chunks_text = self.chunker.chunk(text)

        # Limit the number of chunks if max_number_of_chunks is set
        if self.config.max_number_of_chunks and len(chunks_text) > self.config.max_number_of_chunks:
            status_callback(f"  - Warning: Document was truncated to {self.config.max_number_of_chunks} chunks from {len(chunks_text)}.")
            chunks_text = chunks_text[:self.config.max_number_of_chunks]

        document_chunks = []
        folder = f"{self.config.gcs_folder.strip('/')}/original_chunks"

        for idx, chunk_content in enumerate(chunks_text, start=1):
            status_callback(f"  - Uploading original chunk {idx}/{len(chunks_text)}...")
            filename = f"original_chunk_{idx:04d}.txt"
            gcs_uri = self.gcs.upload(blob_path=f"{folder}/{filename}", content=chunk_content)
            doc_chunk = DocumentChunk(index=idx, content=chunk_content, gcs_uri=gcs_uri)
            document_chunks.append(doc_chunk)

        return document_chunks

    def _create_prompts(
        self,
        original_chunks: List[DocumentChunk],
        file_type: str,
        metadata: Dict[str, str],
        status_callback: Callable[[str], None]
    ) -> int:
        """
        Create translation prompt files for all chunks.

        Generates comprehensive prompts containing source text, entities,
        style instructions, and context information.

        Args:
            original_chunks: List of document chunks
            file_type: The file type of the original document (e.g., 'po', 'txt').
            metadata: Extracted entities and style instructions
            status_callback: Callback for progress updates

        Returns:
            Number of prompts created
        """
        folder = f"{self.config.gcs_folder.strip('/')}/prompts_for_translation"
        
        type_instruction = self.FILE_TYPE_INSTRUCTIONS.get(
            file_type,
            "Document content." # Default instruction
        )
        
        for chunk_obj in original_chunks:
            status_callback(f"  - Creating prompt for chunk {chunk_obj.index}/{len(original_chunks)}...")
            prompt = self._build_prompt(
                chunk=chunk_obj.content,
                chunk_num=chunk_obj.index,
                total_chunks=len(original_chunks),
                type_instruction=type_instruction,
                metadata=metadata
            )
            
            filename = f"translation_prompt_chunk_{chunk_obj.index:04d}.txt"
            self.gcs.upload(blob_path=f"{folder}/{filename}", content=prompt)
            status_callback(f"  - Prompt for chunk {chunk_obj.index} saved to GCS.")
        
        return len(original_chunks)

    
    def _build_prompt(
        self,
        chunk: str,
        chunk_num: int,
        total_chunks: int,
        type_instruction: str,
        metadata: Dict[str, str]
    ) -> str:
        """Build translation prompt."""
        return TRANSLATION_PROMPT_TEMPLATE.format(
            chunk_num=chunk_num,
            total_chunks=total_chunks,
            target_language=self.config.target_language,
            type_instruction=type_instruction,
            entities=metadata['entities'],
            style=metadata['style'],
            chunk=chunk
        )
    
    def _execute_translations(
        self,
        status_callback: Callable[[str], None]
    ) -> int:
        """
        Execute translations and validations for all prompts.

        For each chunk:
        1. Translates using Gemini API
        2. Uploads translation to GCS
        3. Validates translation using ADK Agent

        Args:
            status_callback: Callback for progress updates

        Returns:
            Number of translations completed

        Raises:
            Exception: If translation generation fails (validation errors are logged but don't fail)
        """
        prompts_folder = f"{self.config.gcs_folder.strip('/')}/prompts_for_translation/"
        translated_folder = f"{self.config.gcs_folder.strip('/')}/translated_chunks/"

        prompt_blobs = self.gcs.list_blobs(prompts_folder)

        if not prompt_blobs:
            return 0

        # Sort blobs to process them in order
        prompt_blobs = sorted(prompt_blobs, key=lambda b: b.name)

        for idx, prompt_blob in enumerate(prompt_blobs, start=1):
            # Step 1: Translate
            status_callback(f"  - Translating chunk {idx}/{len(prompt_blobs)}...")
            prompt_content = prompt_blob.download_as_text()
            translated = self.gemini.generate(prompt_content, self.config.temperature)

            translated_filename = os.path.basename(prompt_blob.name).replace(
                'translation_prompt_',
                'translated_'
            )

            translated_blob_path = f"{translated_folder}{translated_filename}"
            self.gcs.upload(blob_path=translated_blob_path, content=translated)
            status_callback(f"  - Translated chunk {idx} saved to GCS.")

            # Step 2: Validate with Agent
            if self.config.use_agent_validation:
                status_callback(f"  - Validating translated chunk {idx} with ADK Agent...")
                try:
                  
                     # Use GCS URIs directly.
                    # This assumes the agent's service account has GCS read access.
                    prompt_url = f"gs://{self.config.gcs_bucket}/{prompt_blob.name}"
                    translated_url = f"gs://{self.config.gcs_bucket}/{translated_blob_path}"
                    print ("prompt URL:" + prompt_url)
                    print ("translated URL:" +translated_url)
                    # Call validation agent
                    validation_result = validate_translation_with_agent(
                        prompt_url,
                        translated_url
                    )
                    self.logger.info(f"Validation result for chunk {idx}: {validation_result['output'][:100]}...")
                    # The agent's output is the final, validated translation.
                    # The agent is instructed to save the final validated content to a specific GCS path.
                    # We need to read that content from GCS, not use the agent's chat response directly.
                    agent_saved_filename = os.path.basename(prompt_blob.name).replace(
                        'translation_prompt_',
                        'final_translated_',
                    )
                    agent_saved_gcs_path = f"{translated_folder}{agent_saved_filename}"

                    # Read the actual validated content that the agent saved to GCS.
                    #final_content = self.gcs.read_blob_text(agent_saved_gcs_path)

                    status_callback(
                        f"  - Validation complete for chunk {idx}. "
                        f"Final version retrieved from GCS: {agent_saved_gcs_path}"
                    )

                except Exception as e:
                    # Log validation errors but don't fail the pipeline
                    error_type = type(e).__name__
                    self.logger.warning(f"Validation failed for chunk {idx} ({error_type}): {e}", exc_info=True)
                    status_callback(
                        f"  - Warning: Validation failed for chunk {idx} "
                        f"({error_type}): {str(e)}"
                    )
                    # If validation fails, use the original translated content as a fallback.
                    final_content = translated
                    # And ensure this fallback content is saved to the expected final path.
                    final_blob_path_for_fallback = f"{translated_folder}{os.path.basename(prompt_blob.name).replace('translation_prompt_', 'final_translated_',)}"
                    self.gcs.upload(
                        blob_path=final_blob_path_for_fallback,
                        content=final_content
                    )
            else:
                # If validation is skipped, the 'translated' content is the 'final' content.
                status_callback(f"  - Skipping agent validation for chunk {idx}.")
                final_blob_path = f"{translated_folder}{os.path.basename(prompt_blob.name).replace('translation_prompt_', 'final_translated_',)}"
                self.gcs.upload(blob_path=final_blob_path, content=translated)

        return len(prompt_blobs)

    def _reassemble_final_document(
        self,
        original_file_type: str,
        status_callback: Callable[[str], None]
    ) -> str:
        """
        Reassembles the final translated document from validated chunks.

        Downloads all `final_translated_chunk_*.txt` files, concatenates
        them in order, and saves the result as a single file in the root
        of the session folder.

        Args:
            original_file_type: The file type of the original document (e.g., 'po', 'txt')
            status_callback: Callback for progress updates

        Returns:
            The GCS URI of the final assembled document.
        """
        chunks_folder = f"{self.config.gcs_folder.strip('/')}/translated_chunks/"
        final_chunk_prefix = f"{chunks_folder}final_translated_chunk_"

        status_callback("  - Listing final translated chunks from GCS...")
        final_blobs = self.gcs.list_blobs(final_chunk_prefix)

        if not final_blobs:
            status_callback("  - No final translated chunks found to assemble.")
            return "No final document created."

        # Sort blobs numerically to ensure correct order
        final_blobs = sorted(final_blobs, key=lambda b: b.name)
        status_callback(f"  - Found {len(final_blobs)} chunks to assemble.")

        # Concatenate content
        full_content_parts = []
        for blob in final_blobs:
            status_callback(f"  - Downloading {os.path.basename(blob.name)}...")
            full_content_parts.append(blob.download_as_text())

        final_content = "".join(full_content_parts)

        # Save the final assembled file
        original_basename = os.path.basename(self.config.source_file)
        final_filename = f"FINAL_{original_basename}"
        final_doc_path = f"{self.config.gcs_folder.strip('/')}/{final_filename}"

        status_callback(f"  - Uploading final assembled document to GCS...")
        final_gcs_uri = self.gcs.upload(blob_path=final_doc_path, content=final_content)

        return final_gcs_uri


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================




# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main() -> None:
    """
    Main entry point for standalone execution.
    """
    parser = argparse.ArgumentParser(description="Translation solution with AI Validation")
    parser.add_argument("--source-file", help="Path or GCS URI to the source file")
    parser.add_argument("--target-language", help="Target language (e.g., 'French')")
    parser.add_argument("--gcs-bucket", help="GCS bucket name for storing artifacts")
    parser.add_argument("--gcs-folder-prefix", default="/translations", help="GCS folder prefix")
    parser.add_argument("--max-chunk-size", type=int, default=translation_config.TranslationDefaults.MAX_CHUNK_SIZE, help="Maximum characters per chunk")
    parser.add_argument("--max-number-of-chunks", type=int, help="Maximum number of chunks to process")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=" * 70)
    logger.info("Translation solution with AI Validation")
    logger.info("=" * 70)

    gcs_folder = f"{args.gcs_folder_prefix.strip('/')}/{str(uuid.uuid4()).replace('-', '')}"

    job_cofig = TranslationConfig(
        source_file=args.source_file,
        target_language=args.target_language,
        gcs_bucket=args.gcs_bucket,
        gcs_folder=gcs_folder,
        max_chunk_size=args.max_chunk_size,
        max_number_of_chunks=args.max_number_of_chunks
    )

    logger.info(f"Source File:      {job_cofig.source_file}")
    logger.info(f"Target Language:  {job_cofig.target_language}")
    logger.info(f"Model:            {job_cofig.model}")
    logger.info(f"Max Chunk Size:   {job_cofig.max_chunk_size:,} characters")
    logger.info(f"Max Chunks:       {job_cofig.max_number_of_chunks or 'Unlimited'}")
    logger.info(f"GCS Location:     gs://{job_cofig.gcs_bucket}/{job_cofig.gcs_folder}")
    logger.info("=" * 70)

    pipeline = TranslationPipeline(job_cofig)

    try:
        result = pipeline.execute()

        if result['success']:
            logger.info("\n" + "=" * 70)
            logger.info("Translation Completed Successfully!")
            logger.info("=" * 70)
            logger.info(f"Prompts Created:         {result['prompts_created']}")
            logger.info(f"Translations Completed:  {result['translations_completed']}")
            logger.info(f"Output Location:         {result['gcs_folder']}")
            logger.info("=" * 70)

    except Exception as e:
        logger.error("=" * 70)
        logger.error("Translation Failed")
        logger.error("=" * 70)
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("=" * 70)
        raise

if __name__ == "__main__":
   main()
