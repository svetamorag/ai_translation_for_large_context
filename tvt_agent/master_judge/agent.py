from google.adk.agents import LlmAgent
from tvt_agent.entities_validator.agent import entity_validator
from tvt_agent.style_validator.agent import style_validator
from tvt_agent.prompts import EDITOR_AGENT_INSTRUCTION

editor_agent=LlmAgent(
    model='gemini-2.5-flash',
    name='editor_agent',
    description="""An agent that makes final edits to the validated translation to ensure clarity and coherence.""",
    instruction=EDITOR_AGENT_INSTRUCTION,
)

master_judge = LlmAgent(
    name='master_judge',
    model='gemini-2.5-flash',
    description='A master judge orchestrating multiple validation agents to ensure the quality of a translated document.',
    instruction="""Your goal is to ensure the highest quality of the translated text by coordinating specialized validation agents.
    Pass the contents of both loaded files to the `master_judge` to all sub agents for validation and editing.
    Receive their outputs and compile the final, polished translation.""",

    sub_agents=[entity_validator, style_validator, editor_agent],
   
)

root_agent = master_judge

