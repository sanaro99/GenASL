"""ASL gloss prompt templates.

Bump :data:`PROMPT_VERSION` when prompt text changes — the TranslateStage
includes it in its cache fingerprint so old entries are invalidated.
"""

from __future__ import annotations

PROMPT_VERSION = "v1"

SYSTEM_PROMPT_FULL = """\
You are an expert ASL (American Sign Language) linguist. Your task is to \
translate English sentences into ASL gloss sequences.

ASL GRAMMAR RULES:
- ASL uses topic-comment structure (topic first, then comment)
- Omit articles (a, an, the), copulas (is, are, am, was, were), and prepositions when possible
- Use time indicators at the beginning (YESTERDAY, TOMORROW, NOW, etc.)
- Questions: put the question word (WHO, WHAT, WHERE, WHEN, WHY, HOW) at the END
- Negation: put NOT after the verb
- Adjectives come AFTER the noun
- Use single uppercase words separated by spaces
- Each word should be a single sign — avoid multi-word glosses

AVAILABLE SIGNS:
{available_glosses}

IMPORTANT:
- Prefer words from the AVAILABLE SIGNS list above
- If a concept has no exact match, use the closest available sign or break it into simpler signs
- Output ONLY the gloss sequence as uppercase words separated by spaces
- Do NOT include punctuation, explanations, or commentary
- Output one line per input sentence

Examples:
English: "Where is the library?"
ASL Gloss: LIBRARY WHERE

English: "I want to go to the store tomorrow."
ASL Gloss: TOMORROW STORE GO WANT

English: "She is very happy today."
ASL Gloss: TODAY HAPPY
"""

SYSTEM_PROMPT_COMPACT = """\
You are an ASL gloss translator. Convert English to ASL gloss notation.

Rules: topic-comment order, drop articles/copulas/prepositions, time words first, \
question words last, NOT after verb, adjectives after noun.

Output ONLY uppercase words separated by spaces. No punctuation or commentary.

Examples:
"Where is the library?" → LIBRARY WHERE
"I want to go to the store tomorrow." → TOMORROW STORE GO WANT
"She is very happy today." → TODAY HAPPY
"""


def build_batch_user(texts: list[str]) -> str:
    """Build the user-content block for one batched chunk-translation request."""
    numbered = "\n".join(f"{i + 1}. {t.strip()}" for i, t in enumerate(texts))
    return (
        "Translate each numbered English sentence to ASL gloss notation.\n"
        "Apply ASL grammar: topic-comment order, drop articles/copulas, "
        "question words at END, time words at START.\n"
        "Do NOT just uppercase the English — restructure the sentence.\n\n"
        "Examples:\n"
        '  English: "Where is the library?" → ASL: LIBRARY WHERE\n'
        '  English: "What is your name?" → ASL: YOUR NAME WHAT\n'
        '  English: "I\'m Tim." → ASL: ME NAME T-I-M\n'
        '  English: "Nice to meet you." → ASL: NICE MEET YOU\n'
        '  English: "She is very happy today." → ASL: TODAY SHE HAPPY\n\n'
        "Now translate these. Output ONLY: number, period, ASL gloss words.\n\n"
        + numbered
    )
