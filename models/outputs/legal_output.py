"""Pydantic output model for LegalAgent structured outputs."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class LegalAgentOutput(BaseModel):
    """Validated output from LegalAgent — India-law legal document generator.

    Covers DPDP Act 2023, Indian IT Act 2000, Consumer Protection Act 2019,
    Arbitration and Conciliation Act 1996.
    """

    model_config = ConfigDict(extra="ignore")

    terms_md: str = Field(..., min_length=2000, description="Terms and Conditions in Markdown")
    privacy_md: str = Field(..., min_length=2000, description="Privacy Policy in Markdown")
    refund_md: str = Field(..., min_length=500, description="Refund Policy in Markdown")
    jurisdiction: str = Field(
        default="Courts of Mumbai, Maharashtra",
        description="Governing jurisdiction for disputes",
    )
    dpdp_compliant: bool = Field(
        ..., description="True if DPDP Act 2023 compliance clauses are present"
    )
    gdpr_provisions: bool = Field(
        ..., description="True if GDPR-like data subject rights (access, erasure, portability) are included"
    )


class ProductContext(BaseModel):
    """Input context describing the product that needs legal documents."""

    model_config = ConfigDict(extra="ignore")

    product_name: str = Field(..., min_length=1, description="Name of the product/service")
    domain: str = Field(..., description="Primary domain, e.g. contractforge.in")
    data_collected: List[str] = Field(
        default_factory=list, description="Data types collected from users"
    )
    third_party_services: List[str] = Field(
        default_factory=list, description="Third-party data processors used"
    )
    jurisdiction: str = Field(
        default="Mumbai, Maharashtra", description="Jurisdiction city/state for disputes"
    )
    contact_email: str = Field(..., description="Privacy/legal contact email address")
