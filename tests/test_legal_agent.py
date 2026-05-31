"""
TDD: LegalAgent — India-law T&C, Privacy Policy, Refund Policy generator.

DPDP Act 2023 + Indian IT Act + Consumer Protection Act 2019 compliance.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# These imports fail until the agent + model are created — confirms RED
from models.outputs.legal_output import LegalAgentOutput, ProductContext
from agents.legal_agent import LegalAgent


# ---------------------------------------------------------------------------
# Model-level tests (instant — no LLM needed)
# ---------------------------------------------------------------------------

class TestLegalAgentOutputModel:
    def test_valid_model_instantiates(self):
        out = LegalAgentOutput(
            terms_md="# Terms\n\n" + "content " * 500,
            privacy_md="# Privacy\n\n" + "content " * 500,
            refund_md="# Refund\n\n" + "content " * 150,
            jurisdiction="Courts of Mumbai, Maharashtra",
            dpdp_compliant=True,
            gdpr_provisions=True,
        )
        assert out.dpdp_compliant is True
        assert "Mumbai" in out.jurisdiction

    def test_terms_md_minimum_length(self):
        with pytest.raises(Exception):
            LegalAgentOutput(
                terms_md="too short",  # < 2000 chars
                privacy_md="x" * 2000,
                refund_md="x" * 500,
                jurisdiction="Courts of Mumbai, Maharashtra",
                dpdp_compliant=True,
                gdpr_provisions=False,
            )

    def test_privacy_md_minimum_length(self):
        with pytest.raises(Exception):
            LegalAgentOutput(
                terms_md="x" * 2000,
                privacy_md="too short",  # < 2000 chars
                refund_md="x" * 500,
                jurisdiction="Courts of Mumbai, Maharashtra",
                dpdp_compliant=True,
                gdpr_provisions=False,
            )

    def test_refund_md_minimum_length(self):
        with pytest.raises(Exception):
            LegalAgentOutput(
                terms_md="x" * 2000,
                privacy_md="x" * 2000,
                refund_md="short",  # < 500 chars
                jurisdiction="Courts of Mumbai, Maharashtra",
                dpdp_compliant=True,
                gdpr_provisions=False,
            )

    def test_default_jurisdiction(self):
        out = LegalAgentOutput(
            terms_md="x" * 2000,
            privacy_md="x" * 2000,
            refund_md="x" * 500,
            dpdp_compliant=True,
            gdpr_provisions=False,
        )
        assert "Mumbai" in out.jurisdiction


class TestProductContext:
    def test_valid_product_context(self):
        ctx = ProductContext(
            product_name="ContractForge",
            domain="contractforge.in",
            data_collected=["name", "email", "PAN"],
            third_party_services=["Supabase", "Lemon Squeezy"],
            jurisdiction="Mumbai, Maharashtra",
            contact_email="privacy@contractforge.in",
        )
        assert ctx.product_name == "ContractForge"
        assert len(ctx.data_collected) == 3

    def test_product_name_required(self):
        with pytest.raises(Exception):
            ProductContext(
                product_name="",
                domain="example.com",
                data_collected=["email"],
                third_party_services=[],
                jurisdiction="Mumbai",
                contact_email="test@test.com",
            )


# ---------------------------------------------------------------------------
# Integration tests — LegalAgent.run() must generate real legal content
# ---------------------------------------------------------------------------

class TestLegalAgentIntegration:
    @pytest.fixture
    def contractforge_ctx(self):
        return ProductContext(
            product_name="ContractForge",
            domain="contractforge.in",
            data_collected=["name", "email", "PAN", "GST number", "project scope", "payment info"],
            third_party_services=["Supabase", "Lemon Squeezy", "Resend", "Vercel", "Render"],
            jurisdiction="Mumbai, Maharashtra",
            contact_email="privacy@contractforge.in",
        )

    def test_agent_run_returns_success(self, tmp_path, contractforge_ctx):
        agent = LegalAgent()
        result = agent.run(contractforge_ctx, output_dir=str(tmp_path))
        assert result.status == "success", f"agent failed: {result.error}"

    def test_output_validates_as_pydantic_model(self, tmp_path, contractforge_ctx):
        agent = LegalAgent()
        result = agent.run(contractforge_ctx, output_dir=str(tmp_path))
        assert result.status == "success"
        output = LegalAgentOutput(**result.output)
        assert len(output.terms_md) >= 2000
        assert len(output.privacy_md) >= 2000
        assert len(output.refund_md) >= 500
        assert output.dpdp_compliant is True

    def test_files_written_to_output_dir(self, tmp_path, contractforge_ctx):
        agent = LegalAgent()
        result = agent.run(contractforge_ctx, output_dir=str(tmp_path))
        assert result.status == "success"
        assert (tmp_path / "terms.md").exists()
        assert (tmp_path / "privacy.md").exists()
        assert (tmp_path / "refund.md").exists()

    def test_terms_contains_required_india_laws(self, tmp_path, contractforge_ctx):
        agent = LegalAgent()
        result = agent.run(contractforge_ctx, output_dir=str(tmp_path))
        assert result.status == "success"
        output = LegalAgentOutput(**result.output)
        terms_lower = output.terms_md.lower()
        assert "mumbai" in terms_lower or "maharashtra" in terms_lower, "jurisdiction missing"
        # Must reference Indian legal framework
        assert any(kw in terms_lower for kw in ["indian contract act", "it act", "information technology"]), \
            "Indian legal reference missing from terms"

    def test_privacy_contains_dpdp_reference(self, tmp_path, contractforge_ctx):
        agent = LegalAgent()
        result = agent.run(contractforge_ctx, output_dir=str(tmp_path))
        assert result.status == "success"
        output = LegalAgentOutput(**result.output)
        privacy_lower = output.privacy_md.lower()
        assert any(kw in privacy_lower for kw in ["dpdp", "personal data", "data protection"]), \
            "DPDP/data protection reference missing from privacy policy"

    def test_no_insert_placeholders(self, tmp_path, contractforge_ctx):
        agent = LegalAgent()
        result = agent.run(contractforge_ctx, output_dir=str(tmp_path))
        assert result.status == "success"
        output = LegalAgentOutput(**result.output)
        for doc_name, doc in [("terms", output.terms_md), ("privacy", output.privacy_md), ("refund", output.refund_md)]:
            assert "[INSERT" not in doc, f"{doc_name} has [INSERT placeholder"
            assert "[TBD]" not in doc.upper(), f"{doc_name} has [TBD] placeholder"
            assert "PLACEHOLDER" not in doc.upper(), f"{doc_name} has PLACEHOLDER"
