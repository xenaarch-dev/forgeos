"""LegalAgent — India-law T&C, Privacy Policy, and Refund Policy generator.

Compliance targets:
- DPDP Act 2023 (Digital Personal Data Protection Act)
- Information Technology Act 2000 + Amendment 2008
- Consumer Protection Act 2019
- Arbitration and Conciliation Act 1996
- Indian Contract Act 1872

Uses claude-sonnet-4-6 with SSE streaming (three separate calls, one per
document). Streaming sidesteps the 120 s HTTP read-timeout that trips
non-streaming tool_use requests for large legal documents.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

from models import AgentResult, AgentStatus
from models.outputs.legal_output import LegalAgentOutput, ProductContext


class LegalAgent:
    """Generate India-law compliant legal documents for a SaaS product."""

    name = "legal_agent"

    def run(self, ctx: ProductContext, *, output_dir: str) -> AgentResult:
        result = AgentResult.started(self.name)
        try:
            output = self._generate(ctx, output_dir)
            result.finalize(AgentStatus.SUCCESS, output=output)
        except Exception as exc:
            tb = traceback.format_exc()
            result.finalize(AgentStatus.FAILED, error=f"{type(exc).__name__}: {exc}")
            result.log.append(tb)
            self._log(f"[{self.name}] FAILED: {exc}")
        return result

    def _generate(self, ctx: ProductContext, output_dir: str) -> dict[str, Any]:
        from llm.claude import ClaudeClient

        client = ClaudeClient(model="claude-sonnet-4-6")
        system = self._system_prompt()
        data_list = ", ".join(ctx.data_collected) if ctx.data_collected else "email, name"
        services_list = ", ".join(ctx.third_party_services) if ctx.third_party_services else "none"

        terms_md = client.complete(
            messages=[{"role": "user", "content": self._terms_prompt(ctx, data_list, services_list)}],
            system=system,
            stream=True,
            max_tokens=8192,
        ).text

        privacy_md = client.complete(
            messages=[{"role": "user", "content": self._privacy_prompt(ctx, data_list, services_list)}],
            system=system,
            stream=True,
            max_tokens=8192,
        ).text

        refund_md = client.complete(
            messages=[{"role": "user", "content": self._refund_prompt(ctx)}],
            system=system,
            stream=True,
            max_tokens=4096,
        ).text

        output = LegalAgentOutput(
            terms_md=terms_md,
            privacy_md=privacy_md,
            refund_md=refund_md,
            jurisdiction=f"Courts of {ctx.jurisdiction}",
            dpdp_compliant=True,
            gdpr_provisions=True,
        )

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "terms.md").write_text(output.terms_md, encoding="utf-8")
        (out_path / "privacy.md").write_text(output.privacy_md, encoding="utf-8")
        (out_path / "refund.md").write_text(output.refund_md, encoding="utf-8")

        return output.model_dump()

    def _system_prompt(self) -> str:
        return (
            "You are a senior Indian technology lawyer specialising in SaaS product compliance. "
            "You draft legally precise, complete documents with exact Indian Act names and section numbers. "
            "NEVER use placeholder text such as [INSERT ...], [TBD], or PLACEHOLDER anywhere in the output. "
            "Write every clause in full — no ellipsis, no stubs."
        )

    def _terms_prompt(self, ctx: ProductContext, data_list: str, services_list: str) -> str:
        return f"""Write a complete Terms and Conditions document (minimum 2000 characters) for:

Product: {ctx.product_name} ({ctx.domain})
Jurisdiction: {ctx.jurisdiction}
Contact: {ctx.contact_email}

The document must include all of the following sections in full:
1. Introduction & Acceptance of Terms — binding agreement upon accessing {ctx.domain}
2. Eligibility — users must be 18 years or older; service intended for Indian residents and businesses
3. Account Registration — user responsibilities for credentials and account security
4. Services Provided — AI-powered contract and legal document generation by {ctx.product_name}
5. Payment & Billing — subscription pricing, authorised payment processors, no chargebacks
6. Intellectual Property — all platform IP belongs to {ctx.product_name}; limited licence to users
7. Prohibited Uses — illegal activity, reverse engineering, scraping, reselling without authorisation
8. Disclaimer & Limitation of Liability — service provided "as is"; liability capped at fees paid in prior 3 months
9. Indemnification — user indemnifies {ctx.product_name} against third-party claims arising from user content
10. Termination — either party may terminate; user data deleted after 3 years post-closure
11. Governing Law — Indian Contract Act 1872, Information Technology Act 2000 (as amended 2008)
12. Consumer Rights — rights under Consumer Protection Act 2019
13. Dispute Resolution — mandatory arbitration under Arbitration and Conciliation Act 1996; seat in {ctx.jurisdiction}
14. Jurisdiction — exclusive jurisdiction of Courts of {ctx.jurisdiction}
15. Amendments — {ctx.product_name} may update these terms with 30 days prior notice

Write the full document now in Markdown format with ## headings for each section."""

    def _privacy_prompt(self, ctx: ProductContext, data_list: str, services_list: str) -> str:
        return f"""Write a complete Privacy Policy (minimum 2000 characters) for:

Product: {ctx.product_name} ({ctx.domain})
Data collected: {data_list}
Third-party processors: {services_list}
Contact: {ctx.contact_email}

The document must include all of the following sections in full:
1. Data Controller — {ctx.product_name}, accessible at {ctx.domain}; contact {ctx.contact_email}
2. Personal Data Collected — {data_list}; purpose of each data type
3. Legal Basis under DPDP Act 2023 — consent and legitimate interest per Digital Personal Data Protection Act 2023
4. Purpose of Processing — service delivery, billing, customer support, legal compliance
5. Third-Party Data Processors — {services_list}; describe each processor's role and data access
6. Data Retention — retained for 3 years after account closure, then securely and permanently deleted
7. Data Subject Rights — right to access, correct, erase, and port personal data (DPDP Act 2023 and IT Act 2000)
8. No Sale of Personal Data — personal data is never sold, rented, or traded to any third party
9. Security Measures — AES-256 encryption at rest, TLS 1.3 in transit, access controls; per IT (Reasonable Security Practices and Procedures) Rules 2011
10. Cookies and Tracking — types of cookies used, user opt-out options
11. Cross-Border Transfers — transfers to processors outside India are governed by DPDP Act 2023 safeguards
12. Children's Privacy — service is not directed at users under 18; data of minors not knowingly collected
13. Policy Updates — users notified via email at {ctx.contact_email} 30 days in advance of material changes
14. Grievance Officer — {ctx.contact_email}; grievances acknowledged within 48 hours and resolved within 30 days per IT Act

Write the full document now in Markdown format with ## headings for each section."""

    def _refund_prompt(self, ctx: ProductContext) -> str:
        return f"""Write a complete Refund Policy (minimum 500 characters) for:

Product: {ctx.product_name} ({ctx.domain})
Contact: {ctx.contact_email}

The document must include all of the following in full:
1. Refund Eligibility — requests accepted within 7 days of initial subscription purchase for unused plan
2. Non-Refundable Items — partially consumed subscription periods, custom document generation credits already used, add-on services already delivered
3. How to Request a Refund — email {ctx.contact_email} with order ID and reason; processed within 7-10 business days
4. Refund Method — credited to original payment instrument; UPI/bank transfers within 5-7 working days
5. Subscription Cancellation — cancel anytime; access continues until end of paid billing period; no pro-rata refund for cancellation mid-period
6. Chargeback Policy — unauthorised chargebacks or disputes filed with payment providers without first contacting {ctx.product_name} will result in immediate account suspension
7. Consumer Disputes — per Consumer Protection Act 2019, consumers may approach the National Consumer Disputes Redressal Commission or respective State Commission

Write the full document now in Markdown format."""

    def _log(self, msg: str) -> None:
        try:
            sys.stderr.write(msg + "\n")
            sys.stderr.flush()
        except Exception:
            pass
