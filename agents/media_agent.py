"""
MediaAgent — media pipeline: optimisation, transcoding, and CDN delivery.

Sits in the pipeline after CoderAgent has generated upload/storage code:

    CoderAgent  →  MediaAgent  →  SecurityAgent

Consumes:
  context.workdir / project/   — the generated codebase
  context.stack                — chosen storage and CDN providers
  context.metadata["tasks"]    — finds tasks tagged "media" to determine scope

Produces:
  MEDIA.md                     — asset pipeline spec and CDN configuration
  project/media/               — processed sample assets (resized images,
                                 transcoded videos) for integration testing
  context.metadata["media_output"]  — structured MediaOutput

Tool registry
-------------
Each tool entry is a dict with:
  name        — short identifier (matches the tool class / CLI name)
  description — what it does in the ForgeOS context
  requires    — env vars or binaries needed to activate it
  optional    — True if the agent degrades gracefully when unavailable
"""

from __future__ import annotations

from typing import Any

from forge_sdk.agent import ForgeAgent
from models import ProjectContext


TOOLS: list[dict[str, Any]] = [
    {
        "name": "ffmpeg",
        "description": (
            "Transcodes video to HLS + DASH adaptive-bitrate streams, extracts "
            "poster frames, and generates WebM/MP4 dual-format outputs. Also "
            "extracts audio waveforms for waveform-visualisation features. "
            "Requires ffmpeg 6+ on PATH."
        ),
        "requires": ["ffmpeg>=6"],
        "optional": True,
    },
    {
        "name": "pillow",
        "description": (
            "Batch-resizes images to responsive breakpoints (320 / 640 / 1024 / "
            "1920 px), converts to AVIF + WebP + JPEG fallback, strips EXIF "
            "metadata, and generates blurhash placeholders for progressive loading."
        ),
        "requires": ["Pillow>=10"],
        "optional": False,
    },
    {
        "name": "cloudinary",
        "description": (
            "Uploads processed assets to Cloudinary, applies on-the-fly "
            "transformation URLs, and returns signed delivery URLs. Used when "
            "context.stack.extras contains 'cdn: cloudinary'."
        ),
        "requires": ["CLOUDINARY_URL"],
        "optional": True,
    },
    {
        "name": "bunny_cdn",
        "description": (
            "Uploads assets to Bunny.net storage zone via the Edge Storage API, "
            "purges CDN cache after upload, and generates pull-zone delivery URLs. "
            "Preferred for cost-sensitive builds (cheaper than Cloudinary at scale)."
        ),
        "requires": ["BUNNY_STORAGE_API_KEY", "BUNNY_STORAGE_ZONE", "BUNNY_PULL_ZONE"],
        "optional": True,
    },
    {
        "name": "supabase_storage",
        "description": (
            "Uploads assets to a Supabase Storage bucket with public or "
            "signed-URL access. Default media backend when no dedicated CDN "
            "tokens are configured — uses the existing SUPABASE_* env vars."
        ),
        "requires": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"],
        "optional": False,
    },
    {
        "name": "stable_diffusion_placeholder",
        "description": (
            "Generates placeholder hero images and product thumbnails via the "
            "Stability AI API (or a local SDXL server). Avoids shipping "
            "placeholder.com boxes in the generated project screenshots."
        ),
        "requires": ["STABILITY_API_KEY"],
        "optional": True,
    },
    {
        "name": "sharp_cli",
        "description": (
            "Node-based alternative to Pillow for projects with a Next.js "
            "frontend — uses sharp (libvips) to produce optimised images that "
            "match Next.js <Image> component expectations exactly."
        ),
        "requires": ["node>=20", "sharp"],
        "optional": True,
    },
    {
        "name": "lighthouse_media_audit",
        "description": (
            "Runs a Lighthouse media audit against the generated app to score "
            "image sizing, video autoplay policy, font subsetting, and LCP "
            "candidate optimisation. Findings are written to MEDIA.md."
        ),
        "requires": ["node>=20", "lighthouse>=12"],
        "optional": True,
    },
]


class MediaAgent(ForgeAgent):
    """
    Process, optimise, and upload all media assets for the generated project.

    Pipeline position: CoderAgent → **MediaAgent** → SecurityAgent

    This agent is not yet implemented. When implemented it will:

    1. Walk project/static/ and project/public/ for raw image and video assets
       seeded by CoderAgent or explicitly listed in TASKS.json.
    2. Run Pillow (or sharp when the frontend is Next.js) to resize images to
       responsive breakpoints and convert to AVIF + WebP + JPEG.
    3. Run ffmpeg (when available) to transcode any sample videos to HLS with
       poster frames.
    4. Generate blurhash placeholders for every image and inject them into the
       component props file (project/src/lib/media.ts or equivalent).
    5. Upload processed assets to the configured CDN (Cloudinary → Bunny →
       Supabase Storage, in preference order by available env vars).
    6. If STABILITY_API_KEY is set, generate hero and thumbnail placeholder
       images so the shipped project looks complete, not lorem-ipsum'd.
    7. Write MEDIA.md with the full asset pipeline spec, CDN configuration,
       and Lighthouse media-audit results.
    8. Write media_output to context.metadata for downstream agents.

    Raises NotImplementedError until implementation is complete — the
    pipeline degrades gracefully (stage marked as degraded, build continues
    to SecurityAgent with raw/unoptimised assets in place).
    """

    name = "media_agent"
    phase = "media"
    capabilities = [
        "MEDIA.md",             # asset pipeline spec, CDN config, Lighthouse scores
        "project/media/",       # processed sample assets
        "media_output",         # context.metadata key with structured output
    ]
    requires = [
        "idea",
        "stack",                # context.stack — determines CDN and frontend targets
        "project_workdir",      # project/ directory written by ScaffoldAgent
    ]
    budget_usd = 0.05           # minimal LLM use; cost is dominated by CDN API calls

    #: Tool registry — read by agent-organizer to decide activation order.
    tools: list[dict[str, Any]] = TOOLS

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        raise NotImplementedError(
            "MediaAgent._execute() is not yet implemented. "
            "Implement the steps described in the class docstring, "
            "then remove this raise."
        )


__all__ = ["MediaAgent", "TOOLS"]
