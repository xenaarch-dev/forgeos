"""
GStack gate registry.

Maps pipeline stage names to skill commands.
gate=True means the pipeline blocks on failure.
"""

from __future__ import annotations

from typing import Any


GATE_REGISTRY: list[dict[str, Any]] = [
    # Planning gates
    {"name": "office_hours",   "skill": "/office-hours",     "gate": True},
    {"name": "ceo_review",     "skill": "/plan-ceo-review",  "gate": True},
    # Design gates
    {"name": "eng_review",     "skill": "/plan-eng-review",  "gate": True},
    {"name": "design_shotgun", "skill": "/design-shotgun",   "gate": True},
    # Review gates
    {"name": "review",         "skill": "/review",           "gate": True},
    {"name": "adversarial",    "skill": "/adversarial",      "gate": True},
    {"name": "score",          "skill": "/score",            "gate": True,  "min_score": 7},
    # Security gates
    {"name": "cso",            "skill": "/cso",              "gate": True},
    # QA gate
    {"name": "qa",             "skill": "/qa",               "gate": True},
]


__all__ = ["GATE_REGISTRY"]
