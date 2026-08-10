"""
ContractCapability — the mesh adapter over LegalAgent (ContractForge).

SPEC_AgentMesh.md §4c. LegalAgent is real and working but is not a ForgeAgent:
it has a bespoke `run(ctx: ProductContext, *, output_dir: str)` signature and
handles its own AgentResult. This adapter absorbs that difference so the mesh
sees the same shape it sees everywhere else, and — deliberately — does not edit
`agents/legal_agent.py`. Its India-law prompts are proven; they are reused
verbatim, not reimplemented here.

What the adapter owns:
  - deriving a ProductContext from free-text command + RouteDecision args
  - pointing LegalAgent at a directory inside the command workdir
  - folding its three documents into one reviewable MeshArtifact

The three source documents are written by LegalAgent unchanged and kept on
disk next to the artifact, so nothing is lost in the fold.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agents.legal_agent import LegalAgent
from forge_sdk.agent import ForgeAgent
from mesh.models import ArtifactType, MeshArtifact, mesh_args
from models import AgentStatus, ProjectContext
from models.outputs.legal_output import LegalAgentOutput, ProductContext

#: Relpath of the reviewable artifact, relative to the command workdir.
#: With a workdir of builds/commands/<command_id> this is the §7a path.
ARTIFACT_RELPATH = "artifacts/contract.md"

#: Where LegalAgent's own three documents land, verbatim.
LEGAL_SUBDIR = "artifacts/legal"

_DEFAULTS = {
    "product_name": "ContractForge",
    "domain": "contractforge.in",
    "jurisdiction": "Mumbai, Maharashtra",
    "data_collected": "name, email, PAN, GST number, project scope, payment info",
    "third_party_services": "Supabase, Lemon Squeezy, Resend, Vercel, Render",
}

#: "...for Acme Legal" / "...for a fintech client" — the common phrasing. Any
#: structured value in args beats this; args are what Phase 3's HTTP layer will
#: carry, and they always win.
_FOR_PATTERN = re.compile(r"\bfor\s+(?:(?:a|an|the|my|our)\s+)?([^.,;\n]{2,60})", re.I)


class ContractCapability(ForgeAgent):
    """ContractForge, addressed as a mesh capability."""

    name = "contract_capability"
    phase = "mesh"
    capabilities = [ARTIFACT_RELPATH]
    requires = ["idea"]
    budget_usd = 0.35

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        args = mesh_args(context)
        product = self._product_context(context, args)

        legal_dir = Path(context.workdir) / LEGAL_SUBDIR
        result = LegalAgent().run(product, output_dir=str(legal_dir))
        if result.status != AgentStatus.SUCCESS.value:
            raise RuntimeError(f"LegalAgent failed: {result.error}")

        output = LegalAgentOutput(**result.output)
        body = self._compose(context, product, output)
        path = self._write(context, ARTIFACT_RELPATH, body)

        artifact = MeshArtifact(
            agent=self.name,
            artifact_type=ArtifactType.CONTRACT,
            title=f"{product.product_name} — legal pack",
            body=body,
            slug="contract",
            workdir_path=ARTIFACT_RELPATH,
        )
        self._emit(
            "artifact_ready",
            {
                "agent": self.name,
                "type": artifact.artifact_type.value,
                "title": artifact.title,
                "preview": artifact.preview(),
            },
        )

        return {
            "artifact": artifact.model_dump(mode="json"),
            "artifact_path": str(path),
            "documents": ["terms.md", "privacy.md", "refund.md"],
            "legal_dir": LEGAL_SUBDIR,
            "jurisdiction": output.jurisdiction,
            "dpdp_compliant": output.dpdp_compliant,
        }

    # ------------------------------------------------------------------
    # Normalisation — free text in, ProductContext out
    # ------------------------------------------------------------------

    def _product_context(
        self, context: ProjectContext, args: dict[str, str]
    ) -> ProductContext:
        product_name = args.get("product_name") or self._derive_product_name(context.idea)
        domain = args.get("domain") or _DEFAULTS["domain"]
        return ProductContext(
            product_name=product_name,
            domain=domain,
            data_collected=_split(args.get("data_collected") or _DEFAULTS["data_collected"]),
            third_party_services=_split(
                args.get("third_party_services") or _DEFAULTS["third_party_services"]
            ),
            jurisdiction=args.get("jurisdiction") or _DEFAULTS["jurisdiction"],
            contact_email=args.get("contact_email") or f"legal@{domain}",
        )

    @staticmethod
    def _derive_product_name(idea: str) -> str:
        match = _FOR_PATTERN.search(idea or "")
        if not match:
            return _DEFAULTS["product_name"]
        candidate = match.group(1).strip().strip("\"'")
        return candidate or _DEFAULTS["product_name"]

    # ------------------------------------------------------------------
    # Folding three documents into one reviewable artifact
    # ------------------------------------------------------------------

    @staticmethod
    def _compose(
        context: ProjectContext, product: ProductContext, output: LegalAgentOutput
    ) -> str:
        """Wrap the generated documents. Their text is never modified."""
        header = "\n".join(
            [
                f"# {product.product_name} — legal pack",
                "",
                f"> Command: {context.idea.strip()}",
                f"> Jurisdiction: {output.jurisdiction}",
                f"> DPDP Act 2023 clauses: {'yes' if output.dpdp_compliant else 'no'}",
                f"> Source documents: {LEGAL_SUBDIR}/terms.md, privacy.md, refund.md",
                ">",
                "> Status: pending founder approval. Nothing has been sent, filed or"
                " published.",
                "",
            ]
        )
        parts = [header, output.terms_md, output.privacy_md, output.refund_md]
        return "\n\n---\n\n".join(part.strip() for part in parts) + "\n"


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


__all__ = ["ARTIFACT_RELPATH", "LEGAL_SUBDIR", "ContractCapability"]
