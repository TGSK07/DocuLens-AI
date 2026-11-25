"""Pydantic models for each supported document type.

These do double duty:
  - They validate Gemini's output server-side.
  - Their JSON Schema is passed to Gemini as the `response_schema`,
    forcing structured JSON output.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ─────────────────────────── Common pieces ───────────────────────────

class Address(BaseModel):
    line1: str | None = Field(default=None, description="Street address, first line.")
    line2: str | None = Field(default=None, description="Additional address line (suite, apt).")
    city: str | None = Field(default=None)
    region: str | None = Field(default=None, description="State / province / region.")
    postal_code: str | None = Field(default=None)
    country: str | None = Field(default=None, description="Country, in English if possible.")


class Party(BaseModel):
    name: str | None = Field(default=None, description="Full legal name of the party.")
    tax_id: str | None = Field(default=None, description="Tax / VAT / company registration number if printed.")
    email: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    address: Address | None = Field(default=None)


# ─────────────────────────── Invoice ───────────────────────────

class InvoiceLineItem(BaseModel):
    description: str = Field(..., description="The text describing this line item.")
    quantity: float | None = Field(default=None, description="Quantity as a number.")
    unit_price: float | None = Field(default=None, description="Unit price in document currency.")
    discount: float | None = Field(default=None, description="Discount applied, if any.")
    total: float | None = Field(default=None, description="Line total (quantity × unit_price - discount).")


class Invoice(BaseModel):
    invoice_number: str | None = Field(default=None, description="Invoice / document number.")
    issue_date: str | None = Field(default=None, description="ISO 8601 (YYYY-MM-DD) if possible, otherwise the original printed date.")
    due_date: str | None = Field(default=None, description="ISO 8601 due date.")
    currency: str | None = Field(default=None, description="ISO 4217 code (USD, EUR, AZN) inferred from symbol or text.")
    vendor: Party = Field(default_factory=Party, description="The party issuing the invoice (seller).")
    customer: Party = Field(default_factory=Party, description="The party being invoiced (buyer).")
    line_items: list[InvoiceLineItem] = Field(default_factory=list)
    subtotal: float | None = Field(default=None)
    tax: float | None = Field(default=None, description="Total tax amount.")
    tax_rate_pct: float | None = Field(default=None, description="Effective tax rate as a percentage if printed.")
    total: float | None = Field(default=None, description="Grand total in document currency.")
    payment_terms: str | None = Field(default=None, description="Free-form payment terms (e.g. 'Net 30').")
    notes: str | None = Field(default=None, description="Anything the model wasn't sure about.")


# ─────────────────────────── Receipt ───────────────────────────

class ReceiptItem(BaseModel):
    name: str
    quantity: float | None = None
    price: float | None = Field(default=None, description="Line total for this item.")


class Receipt(BaseModel):
    merchant_name: str | None = None
    merchant_address: str | None = None
    transaction_date: str | None = Field(default=None, description="ISO 8601 date.")
    transaction_time: str | None = Field(default=None, description="HH:MM if visible.")
    items: list[ReceiptItem] = Field(default_factory=list)
    subtotal: float | None = None
    tax: float | None = None
    tip: float | None = None
    total: float | None = None
    currency: str | None = None
    payment_method: str | None = Field(default=None, description="cash / card / contactless / etc.")
    card_last4: str | None = Field(default=None, description="Last 4 digits of the card if printed.")
    notes: str | None = None


# ─────────────────────────── Resume / CV ───────────────────────────

class ResumeContact(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    website: str | None = None


class ResumeExperience(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = Field(default=None, description='Either a date or the literal string "Present".')
    bullets: list[str] = Field(default_factory=list, description="Achievement bullets.")


class ResumeEducation(BaseModel):
    degree: str | None = None
    institution: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    notes: str | None = None


class Resume(BaseModel):
    contact: ResumeContact = Field(default_factory=ResumeContact)
    headline: str | None = Field(default=None, description="Short professional title under the name.")
    summary: str | None = Field(default=None, description="The professional summary paragraph if present.")
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    notes: str | None = None


# ─────────────────────────── ID / Passport ───────────────────────────

class IdDocument(BaseModel):
    document_type: str | None = Field(default=None, description='e.g. "Passport", "National ID", "Driving Licence".')
    document_number: str | None = None
    full_name: str | None = None
    given_names: str | None = None
    surname: str | None = None
    date_of_birth: str | None = Field(default=None, description="ISO 8601 date.")
    sex: str | None = Field(default=None, description='"M" or "F" or as printed.')
    nationality: str | None = Field(default=None, description="Country name in English.")
    place_of_birth: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    issuing_authority: str | None = None
    mrz_line1: str | None = Field(default=None, description="Machine-readable zone line 1 if visible.")
    mrz_line2: str | None = Field(default=None, description="Machine-readable zone line 2 if visible.")
    notes: str | None = None


# ─────────────────────────── Contract ───────────────────────────

class ContractParty(BaseModel):
    name: str | None = None
    role: str | None = Field(default=None, description='Their role in this contract (e.g. "Landlord", "Tenant", "Employer", "Employee").')
    address: str | None = None
    tax_id: str | None = None


class ContractTerm(BaseModel):
    label: str = Field(..., description='Short label, e.g. "Monthly rent", "Notice period", "Term length".')
    value: str = Field(..., description="The value as printed.")


class Contract(BaseModel):
    title: str | None = Field(default=None, description='e.g. "Tenancy Agreement", "Employment Contract", "NDA".')
    parties: list[ContractParty] = Field(default_factory=list)
    effective_date: str | None = Field(default=None, description="ISO 8601 if possible.")
    expiry_date: str | None = None
    governing_law: str | None = Field(default=None, description='e.g. "Republic of Azerbaijan", "England and Wales".')
    key_terms: list[ContractTerm] = Field(
        default_factory=list,
        description="3-10 most important clauses — rent, salary, notice, scope, exclusivity, payment, etc.",
    )
    signatures_present: bool | None = Field(default=None, description="Are signatures visible on the page?")
    notes: str | None = None


# ─────────────────────────── Business card ───────────────────────────

class BusinessCard(BaseModel):
    full_name: str | None = None
    job_title: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    website: str | None = None
    address: str | None = None
    linkedin: str | None = None
    notes: str | None = None


# ─────────────────────────── Custom schema (runtime) ───────────────────────────

class CustomFieldSpec(BaseModel):
    name: str
    type: str = Field(..., description='One of: string, number, integer, boolean, date, list-string.')
    description: str = Field(default="")


def build_custom_schema(fields: list[CustomFieldSpec]) -> dict[str, Any]:
    """Build a Gemini-compatible schema object from a list of user-supplied field specs."""
    json_type_map: dict[str, dict[str, Any]] = {
        "string":      {"type": "string", "nullable": True},
        "number":      {"type": "number", "nullable": True},
        "integer":     {"type": "integer", "nullable": True},
        "boolean":     {"type": "boolean", "nullable": True},
        "date":        {"type": "string", "nullable": True, "format": "date"},
        "list-string": {"type": "array", "items": {"type": "string"}},
    }
    properties: dict[str, dict[str, Any]] = {}
    for f in fields:
        base = dict(json_type_map.get(f.type, {"type": "string", "nullable": True}))
        if f.description:
            base["description"] = f.description
        properties[f.name] = base
    properties["notes"] = {
        "type": "string",
        "nullable": True,
        "description": "Anything the model wasn't sure about; null otherwise.",
    }
    return {"type": "object", "properties": properties}


# ─────────────────────────── Registry ───────────────────────────

class SchemaInfo:
    def __init__(
        self,
        key: str,
        label: str,
        description: str,
        model: type[BaseModel] | None,
        guidance: str,
    ):
        self.key = key
        self.label = label
        self.description = description
        self.model = model
        self.guidance = guidance

    def json_schema(self) -> dict[str, Any]:
        if self.model is None:
            raise ValueError("Custom schemas are built at runtime")
        # Pydantic v2 emits a $defs section — Gemini accepts it as-is
        return self.model.model_json_schema()


SCHEMAS: dict[str, SchemaInfo] = {
    "invoice": SchemaInfo(
        key="invoice",
        label="Invoice",
        description="Vendor invoices with line items, taxes, totals.",
        model=Invoice,
        guidance=(
            "Extract every line item — do not aggregate them. Keep amounts in document currency. "
            "Normalise dates to ISO 8601 when unambiguous. Currency MUST be an ISO 4217 code."
        ),
    ),
    "receipt": SchemaInfo(
        key="receipt",
        label="Receipt",
        description="Retail / restaurant receipts.",
        model=Receipt,
        guidance=(
            "Include each item as printed (no merging duplicates). Capture transaction_time only "
            "if a clock value is actually printed on the receipt."
        ),
    ),
    "resume": SchemaInfo(
        key="resume",
        label="Resume / CV",
        description="One-person professional history.",
        model=Resume,
        guidance=(
            "Reverse-chronological experience. For end_date use the literal 'Present' for current "
            "roles. Preserve the candidate's exact bullet wording — do not rewrite it."
        ),
    ),
    "id": SchemaInfo(
        key="id",
        label="ID / Passport",
        description="Passports, national IDs, driving licences.",
        model=IdDocument,
        guidance=(
            "Capture MRZ lines verbatim if visible. Do NOT redact anything you can read clearly. "
            "Country names in English."
        ),
    ),
    "contract": SchemaInfo(
        key="contract",
        label="Contract",
        description="Rental, employment, NDA, service agreements.",
        model=Contract,
        guidance=(
            "Pick the 3-10 most consequential clauses for key_terms. Phrase labels in plain "
            "English. Do not invent terms not on the page."
        ),
    ),
    "business-card": SchemaInfo(
        key="business-card",
        label="Business card",
        description="Personal / company business cards.",
        model=BusinessCard,
        guidance=(
            "Phone numbers in their printed format (do not normalise). The 'address' may be a "
            "single-line free-form value."
        ),
    ),
}


def get_schema(key: str) -> SchemaInfo:
    info = SCHEMAS.get(key)
    if info is None:
        raise KeyError(f"Unknown schema: {key}")
    return info
