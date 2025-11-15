from google.adk.agents.llm_agent import Agent
from google.adk.tools.agent_tool import AgentTool
from tvt_agent.prompts import ROOT_AGENT_INSTRUCTION
from tvt_agent.master_judge.agent import master_judge
from tvt_agent.gcs_utils import read_file_from_gcs, save_file_to_gcs,create_final_gcs_uri

root_agent = Agent(
    model='gemini-2.5-flash-lite',
    name='tvt_agent',
    description='A master agent to validate a translated file by orchestrating multiple validation agents.',
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[read_file_from_gcs, save_file_to_gcs,create_final_gcs_uri],
    sub_agents=[master_judge],
)
