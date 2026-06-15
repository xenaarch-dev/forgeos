"""
GameAgent — ForgeOS game development specialist.

Auto-detects game ideas and generates complete, playable games.

Stack selection:
  Browser 3D / FPS / RPG  → Next.js + React Three Fiber + @react-three/rapier
  Browser 2D / platformer  → Next.js + Phaser.js + Matter.js
  Mobile game              → React Native + Expo + Matter.js
  Serious 3D / simulation  → Babylon.js (standalone HTML)
  Desktop / native         → Godot GDScript scaffold

Auto-skips when the idea is not game-related — returns immediately
without marking itself as failed.

Output structure:
  <workdir>/project/game/
    package.json
    README.md
    src/
      main.tsx | main.ts
      game/   (engine core)
      ui/     (HUD, menus)
      hooks/
      assets/
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from models import ProjectContext
from forge_sdk.agent import ForgeAgent


# ---------------------------------------------------------------------------
# Keyword detection
# ---------------------------------------------------------------------------

_GAME_KEYWORDS = frozenset(
    [
        "game", "fps", "rpg", "shooter", "platformer", "puzzle game",
        "arcade", "3d game", "2d game", "multiplayer game", "indie game",
        "metroidvania", "roguelike", "roguelite", "sandbox game", "mmo",
        "battle royale", "tower defense", "strategy game", "racing game",
        "fighting game", "survival game", "horror game", "open world",
    ]
)

_MOBILE_GAME_KEYWORDS = frozenset(
    ["mobile game", "ios game", "android game", "hyper-casual"]
)

_BABYLON_KEYWORDS = frozenset(
    ["simulation", "vr game", "ar game", "serious 3d", "babylon"]
)


# ---------------------------------------------------------------------------
# Stack detection
# ---------------------------------------------------------------------------

STACK_BROWSER_3D = "browser_3d"    # R3F + Rapier
STACK_BROWSER_2D = "browser_2d"    # Phaser.js
STACK_MOBILE     = "mobile"        # React Native + Expo
STACK_BABYLON    = "babylon"       # Babylon.js
STACK_GODOT      = "godot"         # GDScript scaffold


def _detect_stack(idea: str) -> str:
    low = idea.lower()
    if any(k in low for k in _MOBILE_GAME_KEYWORDS):
        return STACK_MOBILE
    if any(k in low for k in _BABYLON_KEYWORDS):
        return STACK_BABYLON
    if "2d" in low or "phaser" in low or "platformer" in low or "arcade" in low:
        return STACK_BROWSER_2D
    return STACK_BROWSER_3D


def _is_game_idea(idea: str) -> bool:
    low = idea.lower()
    return any(k in low for k in _GAME_KEYWORDS)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM = """\
You are the GameAgent in ForgeOS — a senior game developer.
You produce complete, runnable game code. Every file you write must be:
  - Production quality with full TypeScript types
  - No placeholder comments or TODOs
  - Self-contained and immediately playable after `npm install && npm run dev`

When writing files, use this format — every file in its own fenced block:
```path/to/file.ext
<full file contents>
```
"""

_PLAN_PROMPT = """\
Game idea: {idea}
Target stack: {stack_label}

Write a concise Game Design Document (GDD) in JSON format:
```json
{{
  "title": "...",
  "genre": "...",
  "player_description": "...",
  "core_mechanic": "...",
  "controls": {{"keyboard": {{}}, "mouse": {{}}}},
  "levels": ["..."],
  "enemies": [{{"name": "...", "behavior": "..."}}],
  "win_condition": "...",
  "lose_condition": "...",
  "assets_needed": ["..."]
}}
```
Keep it tight — 1 player, 2–3 enemy types, 1–3 levels. No feature creep.
"""

_CORE_PROMPT_3D = """\
Game: {title}
GDD summary: {gdd_summary}
Stack: Next.js 14 + React Three Fiber + @react-three/rapier (Rapier physics)

Generate ALL of the following files in full. No truncation.

Required files:
```package.json
{{
  "name": "{slug}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }},
  "dependencies": {{
    "next": "14.2.29",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@react-three/fiber": "^8.17.10",
    "@react-three/drei": "^9.109.2",
    "@react-three/rapier": "^1.4.0",
    "@dimforge/rapier3d-compat": "^0.12.0",
    "three": "^0.167.1",
    "zustand": "^4.5.4"
  }},
  "devDependencies": {{
    "typescript": "^5.5.3",
    "@types/node": "^20.14.10",
    "@types/react": "^18.3.3",
    "@types/three": "^0.167.0",
    "tailwindcss": "^3.4.6",
    "postcss": "^8.4.39",
    "autoprefixer": "^10.4.19"
  }}
}}
```

Generate these files:
- src/store/gameStore.ts          (Zustand: health, score, gameState, enemies)
- src/hooks/useInput.ts           (keyboard + mouse + gamepad via event listeners)
- src/hooks/useSaveSystem.ts      (localStorage save/load with versioning)
- src/game/Player.tsx             (R3F mesh + Rapier rigid body + controller)
- src/game/Enemy.tsx              (state machine: idle→patrol→chase→attack; Rapier)
- src/game/Scene.tsx              (level geometry, lighting, fog, skybox)
- src/game/HUD.tsx                (health bar, score, ammo — DOM overlay, not 3D)
- src/game/GameLoop.tsx           (useFrame coordinator, win/lose detection)
- src/ui/MainMenu.tsx             (start screen with title + start/controls buttons)
- src/ui/PauseMenu.tsx            (ESC to pause, resume/quit)
- src/ui/GameOver.tsx             (score display, retry button)
- app/page.tsx                    (game entry: state machine for menu/game/pause/gameover)
- app/layout.tsx                  (dark bg, game canvas fills viewport)
- app/globals.css                 (reset, game canvas styles)
- tailwind.config.ts
- tsconfig.json
- next.config.ts                  (transpilePackages for three/r3f)
"""

_CORE_PROMPT_2D = """\
Game: {title}
GDD summary: {gdd_summary}
Stack: Next.js 14 + Phaser 3 + Matter.js physics

Generate ALL of the following files in full. No truncation.

Required files:
```package.json
{{
  "name": "{slug}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{"dev": "next dev", "build": "next build", "start": "next start"}},
  "dependencies": {{
    "next": "14.2.29",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "phaser": "^3.80.1",
    "zustand": "^4.5.4"
  }},
  "devDependencies": {{
    "typescript": "^5.5.3",
    "@types/node": "^20.14.10",
    "@types/react": "^18.3.3",
    "tailwindcss": "^3.4.6",
    "postcss": "^8.4.39",
    "autoprefixer": "^10.4.19"
  }}
}}
```

Generate these files:
- src/store/gameStore.ts             (Zustand: health, score, lives, gameState)
- src/hooks/useSaveSystem.ts         (localStorage save/load)
- src/phaser/config.ts               (Phaser.Game config — type WEBGL, physics Matter)
- src/phaser/scenes/BootScene.ts     (preload assets, loading bar)
- src/phaser/scenes/MenuScene.ts     (title, start button, high score display)
- src/phaser/scenes/GameScene.ts     (main gameplay: player, platforms, enemies, items)
- src/phaser/scenes/PauseScene.ts    (overlay pause, transparent background)
- src/phaser/scenes/GameOverScene.ts (score, retry)
- src/phaser/entities/Player.ts      (Matter body, sprite, animations, input handler)
- src/phaser/entities/Enemy.ts       (state machine: patrol↔chase, attack, death)
- src/phaser/ui/HUD.ts               (Phaser DOM element: health, score, lives)
- app/page.tsx                       (mounts Phaser canvas; no SSR)
- app/layout.tsx
- app/globals.css
- tailwind.config.ts
- tsconfig.json
- next.config.ts
"""

_CORE_PROMPT_MOBILE = """\
Game: {title}
GDD summary: {gdd_summary}
Stack: React Native 0.74 + Expo 51 + Matter.js physics

Generate ALL of the following files in full. No truncation.

Required files:
```package.json
{{
  "name": "{slug}",
  "version": "0.1.0",
  "main": "expo-router/entry",
  "scripts": {{"start": "expo start", "android": "expo run:android", "ios": "expo run:ios"}},
  "dependencies": {{
    "expo": "^51.0.0",
    "expo-router": "^3.5.0",
    "react": "^18.2.0",
    "react-native": "0.74.5",
    "@shopify/react-native-skia": "^1.3.0",
    "matter-js": "^0.19.0",
    "zustand": "^4.5.4",
    "@react-native-async-storage/async-storage": "^1.23.1",
    "expo-haptics": "^13.0.1"
  }},
  "devDependencies": {{
    "typescript": "^5.5.3",
    "@types/react": "^18.2.79",
    "@types/matter-js": "^0.19.6"
  }}
}}
```

Generate these files:
- src/store/gameStore.ts       (Zustand: health, score, lives, gameState)
- src/hooks/useInput.ts        (touch events, tilt via DeviceMotion)
- src/hooks/useSaveSystem.ts   (AsyncStorage save/load)
- src/game/GameEngine.ts       (Matter.js world, requestAnimationFrame loop)
- src/game/Player.ts           (Matter body, sprite, controller)
- src/game/Enemy.ts            (AI state machine)
- src/game/Renderer.tsx        (Skia Canvas: draws all Matter bodies each frame)
- src/ui/HUD.tsx               (React Native overlay: health, score)
- src/ui/MainMenu.tsx
- src/ui/PauseMenu.tsx
- src/ui/GameOver.tsx
- app/(game)/index.tsx         (entry: menu→game→pause→gameover)
- app/_layout.tsx
- app.json
"""

_GODOT_PROMPT = """\
Game: {title}
GDD summary: {gdd_summary}
Stack: Godot 4.x (GDScript)

Generate these Godot project files in full:

- project.godot                (project settings, renderer, resolution)
- scenes/Main.tscn             (root scene, manages scene transitions)
- scenes/Player.tscn + scenes/Player.gd   (CharacterBody3D, camera, controller)
- scenes/Enemy.tscn + scenes/Enemy.gd     (state machine: idle/patrol/chase/attack)
- scenes/Level1.tscn           (first level geometry, spawn points)
- scenes/HUD.tscn + scenes/HUD.gd         (CanvasLayer: health bar, score label)
- scenes/MainMenu.tscn + scenes/MainMenu.gd
- scripts/GameManager.gd       (autoload singleton: score, lives, transitions)
- scripts/SaveSystem.gd        (ConfigFile-based save/load)
- README.md                    (how to open in Godot, controls, add levels)
"""

_README_PROMPT = """\
Game: {title}
Stack: {stack_label}
GDD: {gdd_json}

Write a complete README.md for this game project with:
1. Description (2–3 sentences from the GDD)
2. Prerequisites & quick start (exact commands)
3. Controls (exact keys from GDD)
4. Project structure (annotated file tree)
5. How to add a new level (step-by-step)
6. How to add a new enemy type (step-by-step)
7. Asset pipeline (what formats, where to put files)
8. Deploy to Vercel (for browser stacks) or build for mobile

Be specific. Use the actual controls from the GDD.
"""


# ---------------------------------------------------------------------------
# Stack labels
# ---------------------------------------------------------------------------

STACK_LABELS = {
    STACK_BROWSER_3D: "React Three Fiber + Rapier physics (browser 3D)",
    STACK_BROWSER_2D: "Phaser.js + Matter.js physics (browser 2D)",
    STACK_MOBILE:     "React Native + Expo + Skia + Matter.js (mobile)",
    STACK_BABYLON:    "Babylon.js (browser serious 3D)",
    STACK_GODOT:      "Godot 4 GDScript (desktop native)",
}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class GameAgent(ForgeAgent):
    name         = "game"
    phase        = "code"
    capabilities = ["project/game/"]
    requires     = ["idea"]
    budget_usd   = 0.0

    # Slug helper
    @staticmethod
    def _slugify(title: str) -> str:
        s = re.sub(r"[^\w\s-]", "", title.lower()).strip()
        return re.sub(r"[\s_-]+", "-", s)[:40] or "my-game"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        idea = context.idea

        # ── Auto-skip if not a game idea ──────────────────────────────────
        if not _is_game_idea(idea):
            self._log(
                "[game] Idea is not game-related — skipping GameAgent. "
                "Add 'game', 'FPS', 'RPG', etc. to trigger this agent."
            )
            return {"skipped": True, "reason": "not a game idea"}

        stack = _detect_stack(idea)
        stack_label = STACK_LABELS[stack]
        self._log(f"[game] Detected stack: {stack_label}")

        # ── Output directory ──────────────────────────────────────────────
        game_dir = Path(context.workdir) / "project" / "game"
        game_dir.mkdir(parents=True, exist_ok=True)

        # ── Phase 1: Game Design Document ────────────────────────────────
        self._log("[game] Phase 1/3 — writing Game Design Document…")
        gdd_resp = self._llm(
            context,
            _PLAN_PROMPT.format(idea=idea, stack_label=stack_label),
            system_extra=_SYSTEM,
            task_complexity="hard",
            task_type="architecture",
            purpose="game-gdd",
            max_tokens=2048,
            stream=True,
        )
        gdd = self._extract_json_block(gdd_resp.text) or {}
        title = gdd.get("title", "Unnamed Game")
        slug = self._slugify(title)
        gdd_json = json.dumps(gdd, indent=2)
        gdd_summary = (
            f"Title: {title} | Genre: {gdd.get('genre', '?')} | "
            f"Mechanic: {gdd.get('core_mechanic', '?')} | "
            f"Enemies: {[e.get('name') for e in gdd.get('enemies', [])]} | "
            f"Win: {gdd.get('win_condition', '?')}"
        )
        # Write GDD artifact
        (game_dir / "GDD.json").write_text(gdd_json, encoding="utf-8")
        self._log(f"[game] GDD: {title} ({gdd.get('genre', '?')})")

        # ── Phase 2: Core game files ──────────────────────────────────────
        self._log("[game] Phase 2/3 — generating game engine + UI files…")
        prompt_map = {
            STACK_BROWSER_3D: _CORE_PROMPT_3D,
            STACK_BROWSER_2D: _CORE_PROMPT_2D,
            STACK_MOBILE:     _CORE_PROMPT_MOBILE,
            STACK_BABYLON:    _CORE_PROMPT_3D,   # reuse 3D prompt; LLM adapts
            STACK_GODOT:      _GODOT_PROMPT,
        }
        core_prompt = prompt_map[stack].format(
            title=title,
            slug=slug,
            gdd_summary=gdd_summary,
        )
        core_resp = self._llm(
            context,
            core_prompt,
            system_extra=_SYSTEM,
            task_complexity="hard",
            task_type="code",
            purpose="game-core",
            max_tokens=8192,
            stream=True,
        )
        core_files = self._split_files(core_resp.text)
        written = 0
        for rel_path, content in core_files.items():
            dest = game_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            written += 1
        self._log(f"[game] Wrote {written} core game files")

        # ── Phase 3: README ───────────────────────────────────────────────
        self._log("[game] Phase 3/3 — writing README…")
        readme_resp = self._llm(
            context,
            _README_PROMPT.format(
                title=title,
                stack_label=stack_label,
                gdd_json=gdd_json,
            ),
            system_extra=_SYSTEM,
            task_complexity="medium",
            task_type="code",
            purpose="game-readme",
            max_tokens=2048,
            stream=False,
        )
        readme_text = readme_resp.text.strip()
        # Strip outer markdown fence if present
        if readme_text.startswith("```"):
            readme_text = re.sub(r"^```[^\n]*\n?", "", readme_text)
            readme_text = re.sub(r"\n?```\s*$", "", readme_text)
        (game_dir / "README.md").write_text(readme_text, encoding="utf-8")

        # ── Summary ───────────────────────────────────────────────────────
        summary_lines = [
            f"# {title}",
            f"",
            f"Stack: {stack_label}",
            f"Files written: {written}",
            f"Output: {game_dir}",
            f"",
            f"## Quick start",
            f"```bash",
            f"cd {game_dir}",
            f"npm install",
            f"npm run dev",
            f"```",
        ]
        (game_dir / "SUMMARY.md").write_text("\n".join(summary_lines), encoding="utf-8")

        self._log(f"[game] Done — {title} at {game_dir}")
        return {
            "game_title": title,
            "stack": stack,
            "stack_label": stack_label,
            "files_written": written,
            "game_dir": str(game_dir),
        }


__all__ = ["GameAgent"]
