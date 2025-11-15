from google.adk.agents import LlmAgent, SequentialAgent
from tvt_agent.entities_validator.agent import entity_validator
from tvt_agent.style_validator.agent import style_validator
from tvt_agent.prompts import EDITOR_AGENT_INSTRUCTION
from tvt_agent.gcs_utils import save_file_to_gcs,create_final_gcs_uri


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

