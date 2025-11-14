from google.adk.agents.llm_agent import Agent
from tvt_agent.prompts import STYLE_VALIDATOR_INSTRUCTION

style_validator = Agent(
    model='gemini-2.5-pro',
    name='style_validator',
    description='An agent that validates the style and tone of a translated text.',
    instruction=STYLE_VALIDATOR_INSTRUCTION,
    output_key="suggested_style_edits" 
)
