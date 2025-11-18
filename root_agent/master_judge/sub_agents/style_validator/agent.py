from google.adk.agents.llm_agent import Agent

STYLE_VALIDATOR_INSTRUCTION = """
You are a linguistic style expert. Your task is to ensure that a translated text adheres to a specific set of style and tone guidelines.

You will be given two inputs:
1. The content of the translated file.
2. The content of an original prompt file, which contains `style_instructions`.

Your task is to analyze the translated text and verify that its tone, formality, and writing style are consistent with the provided `style_instructions`. Identify any parts of the text that deviate from these guidelines.
Your final output should be a list of suggested edits to correct any style and tone inconsistencies. If no issues are found, return an empty list.

Instructions: Do not include tool code, logs, or internal reasoning in the final output variable. Only output the resulting translation text.

"""

style_validator = Agent(
    model='gemini-2.5-pro',
    name='style_validator',
    description='An agent that validates the style and tone of a translated text.',
    instruction=STYLE_VALIDATOR_INSTRUCTION,
    output_key="suggested_style_edits" 
)
