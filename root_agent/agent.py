from google.adk.agents.llm_agent import Agent
from .master_judge.agent import master_judge
from .master_judge.gcs_utils import read_file_from_gcs, save_file_to_gcs,create_final_gcs_uri

ROOT_AGENT_INSTRUCTION = """
You are the Root Validation Orchestrator. Your primary role is to manage the end-to-end lifecycle of the translation validation process by coordinating specialized sub-agents and managing file I/O.

**Your Workflow:**

1.  **Input Acquisition**:
    * You will receive Google Cloud Storage (GCS) paths for a `translated_file` and an `original_prompt_file`.
    * Use the `read_file_from_gcs` tool to load the contents of both files into memory.
    * Build a valid JSON object containing the contents of both files to pass to the `master_judge` agent.

2.  **Validation Execution**:
    * Delegate the core validation task by invoking the `master_judge` agent.
    * Pass the contents of both loaded files to the `master_judge`.
"""

root_agent= Agent(
    model='gemini-2.5-flash-lite',
    name='root_agent',
    description='A master agent to validate a translated file by orchestrating multiple validation agents.',
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[read_file_from_gcs, save_file_to_gcs,create_final_gcs_uri],
    sub_agents=[master_judge],
)
