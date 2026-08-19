"""System prompts for the vision extractor."""
from __future__ import annotations


def build_system_prompt(schema_label: str, guidance: str) -> str:
    """Build the system prompt for a single extraction call.

    The model is forced to call a single tool with the JSON Schema of the
    selected document type. The prompt frames the job, gives the schema
    label, and emits the schema-specific guidance.
    """
    return "\n".join(
        [
            f"You are a careful document analyst. You are given page images of a single document of type: {schema_label}.",
            "",
            "Your job is to extract every available field listed in the `submit_extraction` tool schema and call that tool exactly once.",
            "",
            "── HARD RULES ──",
            "  1. NEVER invent values. If a field is not visible or not unambiguous, leave it as null.",
            "  2. Numbers: extract them as numbers (not strings). Decimal separator is '.'. Do not include currency symbols in numeric fields.",
            "  3. Dates: prefer ISO 8601 (YYYY-MM-DD). If the year is ambiguous (e.g. only month/day printed), leave the field null and mention it in `notes`.",
            "  4. Trim whitespace from every string. Do not add quotes around values.",
            "  5. Preserve language. If the document is not in English, extract values in the original language.",
            "  6. The `notes` field is for things YOU were unsure about — leave it null if everything was clean.",
            "",
            f"── DOCUMENT-SPECIFIC GUIDANCE ──",
            guidance,
            "",
            "You MUST call the `submit_extraction` tool. No free-form prose response.",
        ]
    )


def build_custom_system_prompt(field_summary: str) -> str:
    return "\n".join(
        [
            "You are a careful document analyst. You are given page images of a document.",
            "",
            "The user has defined the fields they want extracted. Call the `submit_extraction` tool exactly once, filling every field they specified. Use null for any field you cannot read with confidence.",
            "",
            "── FIELDS THE USER WANTS ──",
            field_summary,
            "",
            "── HARD RULES ──",
            "  1. Do not invent values. If unsure, leave it as null and explain in `notes`.",
            "  2. Numbers as numbers, not strings.",
            "  3. Dates as YYYY-MM-DD where possible.",
            "  4. Preserve language.",
            "  5. Trim whitespace.",
            "",
            "Call the `submit_extraction` tool. No free-form response.",
        ]
    )
