from google.adk.agents import SequentialAgent,LlmAgent
from google.adk.tools.agent_tool import AgentTool
from tvt_agent.entities_validator.agent import entity_validator
from tvt_agent.style_validator.agent import style_validator
from tvt_agent.prompts import EDITOR_AGENT_INSTRUCTION

editor_agent=LlmAgent(
    model='gemini-2.5-flash',
    name='editor_agent',
    description="""An agent that makes final edits to the validated translation to ensure clarity and coherence.""",
    instruction=EDITOR_AGENT_INSTRUCTION,
)

master_judge = SequentialAgent(
    name='master_judge',
    description='A master judge orchestrating multiple validation agents to ensure the quality of a translated document.',
    sub_agents=[entity_validator, style_validator, editor_agent],
)
