"""
This file contains the core prompt templates for the translation pipeline.
"""

EXTRACT_ENTITIES_PROMPT = """
Analyze the provided document below. Your task is to extract all critical entities that require consistent translation into {target_language}.

**Entities to Extract:**
* **Named Entities:** People, geographic locations, organizations.
* **Terminology:** Technical terms, specialized vocabulary, domain-specific jargon.
* **Branding:** Product names, brand names, trademarks.
* **Abbreviations:** Acronyms and initialisms.

**Output Format:**
Return ONLY a JSON dictionary.
* **Key:** The source term as it appears in the text.
* **Value:** An object containing:
    * `"context"`: A brief description of how the term is used.
    * `"suggested_translation"`: The recommended translation only in {target_language}.

**Document Content:**
{text}
"""

EXTRACT_STYLE_PROMPT = """
Analyze the provided document below. Your task is to generate a comprehensive style guide for its translation to {target_language}.

**Style Guide Components:**
* **Tone & Voice:** Define the formality level (e.g., highly technical, casual, persuasive) and emotional resonance.
* **Target Audience:** Identify who will read this text and their expected knowledge level.
* **Convention & Formatting:** Note any specific formatting rules, capitalization preferences, or structural requirements typical for this document type.
* **Cultural Nuances:** Highlight any cultural references, idioms, or sensitivities that must be adapted for the target locale ({target_language}).

**Document Content:**
{text}

**Output:** Provide clear, actionable style instructions that a human or AI translator can follow.
"""

TRANSLATION_PROMPT_TEMPLATE = """
# Translation Task

**Objective:** Translate the source content below into {target_language} while preserving the original format.
**Constraints:** You MUST strictly adhere to the provided Entity Dictionary and Style Guide.

## 1. Context & Guidelines

## 2. Style Guide
{style}

## 3. Entity Dictionary (Strict Adherence Required)
*Use these exact translations for the following terms:*
{entities}

## 4. Source Content
---
{chunk}
---

**Output:** Return ONLY the translated text.Preserve original format exactly. Do not include preamble or explanations.
"""