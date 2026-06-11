"""
Shared base class and types for all ForgeOS LLM clients.

The canonical definitions now live in models to avoid circular imports.
This module re-exports them so existing `from .base import ...` within the
llm package continues to work unchanged.
"""

from models import LLMClient, LLMError, LLMResponse

__all__ = ["LLMClient", "LLMResponse", "LLMError"]
