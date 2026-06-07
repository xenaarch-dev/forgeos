"""PMAgent — Stage 0 demand validation.

Runs BEFORE any code is written. Validates market demand, identifies competitors,
and recommends build / dont_build / pivot.

A dont_build or pivot recommendation raises RuntimeError which stops the
pipeline (gate=True in hermes._build_pipeline). The human sees the reasoning
before a single line of code is generated.
"""

from __future__ import annotations

from typing import Any

from forge_sdk.agent import ForgeAgent
from models import LLMError, ProjectContext
from models.outputs.pm_output import PMOutput


_SYSTEM_PROMPT = """\
You are the Product Market analyst for ForgeOS.
Before any code is written, you validate market demand for the idea.
Research competitors, identify the target user, size the market, and give a
decisive build / dont_build / pivot recommendation backed by evidence.
Be specific to the Indian SaaS market when relevant. Use real competitor
names and concrete pricing. Never hedge.
"""

_PROMPT = """\
Analyse this product idea and return a validated PMOutput:

IDEA: {idea}

Return all fields:
1. product_name — short, marketable name
2. top_3_competitors — exactly 3 real competitors with their weakness and the opportunity it creates for us
3. target_user_persona — detailed persona (≥100 chars)
4. demand_signals — ≥3 evidence points that real demand exists (communities, search volume, complaints, trends)
5. recommended_price_inr — monthly INR price (integer > 0)
6. recommended_price_usd — monthly USD price (integer > 0)
7. build_recommendation — "build" | "dont_build" | "pivot"
8. reasoning — ≥200 chars explaining recommendation with evidence
9. spec_additions — ≥2 must-have features the architect should add based on market research
10. market_size_estimate — estimated TAM/SAM (e.g. "$50M TAM in Indian SMB segment")
11. biggest_risk — single biggest risk that could kill the product
"""


class PMAgent(ForgeAgent):
    """Validate market demand before a single line of code is written."""

    name = "pm_agent"
    phase = "pm"
    capabilities = ["pm_output"]           # writes context.metadata["pm_output"]
    requires = ["idea"]
    budget_usd = 0.10                      # one Claude structured call ~$0.01-0.05

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        import os
        from llm.claude import ClaudeClient
        from llm.router import _build_system_prompt

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY not set — PMAgent requires Claude structured output")

        client = ClaudeClient()
        system = _build_system_prompt(None, _SYSTEM_PROMPT)
        prompt = _PROMPT.format(idea=context.idea)

        result: PMOutput = client.complete_structured(
            messages=[{"role": "user", "content": prompt}],
            output_model=PMOutput,
            system=system,
            max_tokens=4096,
            stage="pm_agent",
        )

        if result.build_recommendation == "dont_build":
            raise RuntimeError(
                f"dont_build — {result.reasoning[:600]}"
            )
        if result.build_recommendation == "pivot":
            raise RuntimeError(
                f"pivot — {result.reasoning[:600]}\n"
                "Tell me: 'confirmed pivot: <new idea>' to continue."
            )

        context.metadata["pm_output"] = result.model_dump()
        self._log(
            f"[pm_agent] recommendation={result.build_recommendation} "
            f"price_inr={result.recommended_price_inr}"
        )
        return result.model_dump()


__all__ = ["PMAgent"]
