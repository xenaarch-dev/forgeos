"""
FalClient — stubbed provider client for AI video generation via Fal.ai.

Fal.ai hosts both Pika and Higgsfield endpoints under a single API key,
so one signup covers both provider candidates. The active provider is
controlled by the FAL_VIDEO_PROVIDER env var or the `provider` constructor arg.

Status: STUB — all generate() calls raise NotImplementedError until
FAL_API_KEY is set. is_ready() returns False without the key.

Activation checklist:
  1. Sign up at fal.ai → generate an API key
  2. Set FAL_API_KEY in .env or WSL2 ~/.bashrc
  3. Optionally set FAL_VIDEO_PROVIDER=pika or =higgsfield (default: pika)
  4. Wire the actual fal-client library call inside generate()

Campaign asset types (founder_video is intentionally excluded — filmed
for real, separate decision):
  - build_a_brand   15s brand overview
  - app_screens     20s product walkthrough
  - product_sizzle  30s launch reel

CLI:
  python3 tools/fal_client.py generate --type build_a_brand --prompt '...'
  python3 tools/fal_client.py generate --type app_screens --provider higgsfield --prompt '...'
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


VideoType = Literal["build_a_brand", "app_screens", "product_sizzle"]
Provider  = Literal["pika", "higgsfield"]

_VALID_VIDEO_TYPES: tuple[str, ...] = ("build_a_brand", "app_screens", "product_sizzle")
_VALID_PROVIDERS:   tuple[str, ...] = ("pika", "higgsfield")

# Fal.ai model endpoint slugs — update once provider choice is confirmed.
# These are placeholder slugs; verify at fal.ai/models before activating.
_MODEL_MAP: dict[str, dict[str, str]] = {
    "pika": {
        "build_a_brand":  "fal-ai/pika-v2-2/text-to-video",
        "app_screens":    "fal-ai/pika-v2-2/text-to-video",
        "product_sizzle": "fal-ai/pika-v2-2/text-to-video",
    },
    "higgsfield": {
        "build_a_brand":  "fal-ai/higgsfield-ai/cinematic-1",
        "app_screens":    "fal-ai/higgsfield-ai/cinematic-1",
        "product_sizzle": "fal-ai/higgsfield-ai/cinematic-1",
    },
}

_DEFAULT_DURATIONS: dict[str, int] = {
    "build_a_brand":  15,
    "app_screens":    20,
    "product_sizzle": 30,
}


@dataclass
class VideoResult:
    video_url: str
    asset_type: str
    provider: str
    model: str
    duration_seconds: int


class FalClient:
    """
    Provider-agnostic video generation client via Fal.ai.

    Usage (once FAL_API_KEY is set)::

        client = FalClient()
        result = client.build_a_brand("ContractForge", "AI contracts in 60 seconds")
        print(result.video_url)
    """

    def __init__(
        self,
        api_key: str | None = None,
        provider: Provider = "pika",
    ) -> None:
        self._api_key: str = api_key or os.environ.get("FAL_API_KEY", "")
        env_provider = os.environ.get("FAL_VIDEO_PROVIDER", "")
        self._provider: str = (
            env_provider if env_provider in _VALID_PROVIDERS else provider
        )

    def is_ready(self) -> bool:
        """True when FAL_API_KEY is set and the client can make real calls."""
        return bool(self._api_key)

    def generate(
        self,
        asset_type: VideoType,
        prompt: str,
        *,
        duration: int | None = None,
    ) -> VideoResult:
        """Generate a campaign video asset via Fal.ai.

        Args:
            asset_type: one of "build_a_brand", "app_screens", "product_sizzle"
            prompt:     text description for the video generation model
            duration:   override seconds (defaults per asset type if None)

        Raises:
            ValueError: unknown asset_type
            NotImplementedError: FAL_API_KEY not set, or real API call not yet wired
        """
        if asset_type not in _VALID_VIDEO_TYPES:
            raise ValueError(
                f"Unknown asset_type {asset_type!r}. "
                f"Supported: {list(_VALID_VIDEO_TYPES)}"
            )
        if not self._api_key:
            raise NotImplementedError(
                "FalClient is not yet activated.\n"
                "1. Sign up at fal.ai and generate an API key.\n"
                "2. Set FAL_API_KEY in .env or WSL2 ~/.bashrc.\n"
                "3. Optionally set FAL_VIDEO_PROVIDER=pika or =higgsfield."
            )
        # TODO: replace with real fal-client queue submit + poll once activated.
        # Example (fal-client library):
        #   import fal_client
        #   result = fal_client.subscribe(model, arguments={"prompt": prompt, ...})
        #   return VideoResult(video_url=result["video"]["url"], ...)
        raise NotImplementedError(
            "Real Fal.ai API call not yet wired. "
            "Replace this raise with fal_client queue submit + poll."
        )

    def build_a_brand(self, product_name: str, tagline: str) -> VideoResult:
        """15s brand overview video."""
        prompt = (
            f"Product brand video for {product_name}. "
            f"{tagline}. "
            "Clean, modern, minimal aesthetic. No text overlays. 15 seconds."
        )
        return self.generate("build_a_brand", prompt)

    def app_screens(self, product_name: str, key_features: list[str]) -> VideoResult:
        """20s product walkthrough showing key screens."""
        features_str = ", ".join(key_features[:3])
        prompt = (
            f"App screen walkthrough for {product_name}. "
            f"Key features: {features_str}. "
            "Screen recording style, smooth transitions. 20 seconds."
        )
        return self.generate("app_screens", prompt)

    def product_sizzle(
        self, product_name: str, tagline: str, live_url: str
    ) -> VideoResult:
        """30s launch reel."""
        prompt = (
            f"30-second product launch reel for {product_name}. "
            f"{tagline}. "
            f"Live at {live_url}. "
            "Cinematic, energetic, builder-focused. No stock footage."
        )
        return self.generate("product_sizzle", prompt)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(
        prog="fal_client",
        description="FalClient — AI video generation via Fal.ai",
    )
    sub = parser.add_subparsers(dest="cmd")

    gen = sub.add_parser("generate", help="Generate a campaign video")
    gen.add_argument(
        "--type", dest="asset_type", required=True,
        choices=list(_VALID_VIDEO_TYPES),
        help="Asset type to generate",
    )
    gen.add_argument("--prompt", required=True, help="Generation prompt")
    gen.add_argument(
        "--provider", default="pika", choices=list(_VALID_PROVIDERS),
        help="Video provider (default: pika)",
    )

    args = parser.parse_args()
    if args.cmd == "generate":
        client = FalClient(provider=args.provider)
        if not client.is_ready():
            print("FAL_API_KEY not set. Add it to .env or WSL2 ~/.bashrc.")
            raise SystemExit(1)
        result = client.generate(args.asset_type, args.prompt)
        print(_json.dumps({
            "video_url": result.video_url,
            "model": result.model,
            "duration_seconds": result.duration_seconds,
        }))
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()


__all__ = ["FalClient", "VideoResult", "VideoType", "Provider"]
