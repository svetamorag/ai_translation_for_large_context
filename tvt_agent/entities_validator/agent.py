from google.adk.agents import Agent
from tvt_agent.prompts import ENTITY_VALIDATOR_INSTRUCTION

entity_validator= Agent(
    model='gemini-2.5-flash',
    name='entity_validator',
    description='An agent that validates named entities in a translated text.',
    instruction=ENTITY_VALIDATOR_INSTRUCTION,
        output_key="suggested_entity_edits" 
)
