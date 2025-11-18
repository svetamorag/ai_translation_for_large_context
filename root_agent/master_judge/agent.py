from google.adk.agents import LlmAgent, SequentialAgent
from .sub_agents.entities_validator.agent import entity_validator
from .sub_agents.style_validator.agent import style_validator
from .gcs_utils import save_file_to_gcs,create_final_gcs_uri


EDITOR_AGENT_INSTRUCTION = """
You are a Finalizing Editor Agent. 

**Inputs:**
- translated_text: The original translated text
- suggested_style_edits: List of style corrections
- suggested_entity_edits: List of entity corrections

**Your Tasks:**
* Apply all edits and return the final corrected text only.
* Construct the output path with create_final_gcs_uri tool.
* Print the output path to the user
* Use the `save_file_to_gcs` tool to save the 'final_corrected_text' to this output path.

"""

editor_agent=LlmAgent(
    model='gemini-2.5-flash',
    name='editor_agent',
    description="""An agent that makes final edits to the validated translation to ensure clarity and coherence.""",
    instruction=EDITOR_AGENT_INSTRUCTION,
    tools=[save_file_to_gcs,create_final_gcs_uri],
)

master_judge = SequentialAgent(
    name='master_judge',
    description='A master judge orchestrating multiple validation agents to ensure the quality of a translated document.',
    sub_agents=[entity_validator, style_validator, editor_agent],
   
)

root_agent = master_judge

