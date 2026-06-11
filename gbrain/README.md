# GBrain — ForgeOS Knowledge Directory

GBrain is the persistent, structured knowledge store that ForgeOS agents read
before each build and write to after each successful run.

## Purpose

Every build teaches ForgeOS something. GBrain captures those learnings as
reusable patterns so future builds start smarter — not from zero.

- `knowledge.json` — index of all pattern files and store metadata
- `patterns/technical.json` — engineering patterns (stack decisions, bug fixes,
  library quirks, infra gotchas)
- `patterns/legal.json` — jurisdiction-specific regulatory knowledge (India first;
  expand per-region as builds accumulate)

## How it feeds into builds

1. `ArchitectAgent` loads `gbrain/patterns/technical.json` before producing
   `ARCH.md` — relevant patterns are injected as constraints into the LLM prompt.
2. `LegalAgent` loads `gbrain/patterns/legal.json` before generating contracts —
   jurisdiction rules are applied automatically.
3. `ForgeBrain` (post-build) distils new learnings from `ARCH.md`, `SECURITY.md`,
   and `context.json` and appends them back to the appropriate pattern file.

## Schema

Both pattern files share a common entry schema:

```json
{
  "id":          "kebab-case-unique-id",
  "title":       "Short human-readable name",
  "tags":        ["tag1", "tag2"],
  "source":      "build-id or project name that originated this pattern",
  "learned_at":  "ISO 8601 date",
  "pattern":     "What the rule is (1-3 sentences)",
  "when_to_use": "Context or trigger condition",
  "example":     "Code snippet or concrete illustration",
  "related":     ["other-pattern-id"]
}
```

## Adding patterns manually

Edit the relevant `patterns/*.json` file directly. Keep `knowledge.json`
`total_patterns` count in sync. CI runs `PYTHONPATH=. python3 -c
"import json, pathlib; [json.loads(p.read_text()) for p in
pathlib.Path('gbrain/patterns').glob('*.json')]"` to validate JSON on push.

## Roadmap

- [ ] Auto-ingest from `GBrainLogger` session summaries after each build
- [ ] Vector-search index (pgvector in Supabase) for semantic pattern retrieval
- [ ] Per-region legal pattern files (`patterns/legal_us.json`, etc.)
- [ ] Conflict detection when a new pattern contradicts an existing one
