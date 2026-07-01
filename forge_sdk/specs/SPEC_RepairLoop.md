# RepairLoop — Specification

> Status: SPEC ONLY — no implementation
> Spec date: 2026-07-01 (Day 173)
> Author: Padmaja Kotoky + Claude Sonnet 4.6
> Context: Two independent external reviews converged on this as the largest
> single quality gap in the pipeline. Implementation deferred — scoped and
> specced today so it can be built in one focused session.

---

## 1. Purpose

RepairLoop closes the most impactful quality gap in ForgeOS: the pipeline
currently has no attempt→test→patch cycle. Code is generated once, then
evaluated by LLM opinion. When the LLM-produced code has bugs, the pipeline
either ships broken code or halts at a gate. Neither outcome is acceptable.

The mechanic that correlates most with real coding-agent quality is:
**generate → run real tests → read the actual failure → patch → re-run**.

RepairLoop makes this explicit: after MissionWorkerLoop produces code, and
before ScoreGate sees it, ForgeOS runs the generated test suite, reads any
failures, calls an LLM to patch the specific file(s), and re-runs — up to a
bounded attempt count.

---

## 2. Pipeline Position

| Attribute | Value |
|-----------|-------|
| Stage number | Between 9 (MissionWorkerLoop) and 10 (ReviewGate) |
| Name key | `"repair"` |
| Class | `RepairLoopAgent` |
| Gate | `False` during repair iterations; final attempt failure surfaces to founder |
| Left neighbor | MissionWorkerLoop (stage 9) |
| Right neighbor | ReviewGate (stage 10) |

### Placement in `hermes.py._build_pipeline()`

```python
# After MissionWorkerLoop:
{"name": "worker",     "cls": MissionWorkerLoop, "gate": False},
# Insert:
{"name": "repair",     "cls": RepairLoopAgent,   "gate": False},
# Before ReviewGate:
{"name": "review",     "cls": ReviewGate,         "gate": True},
```

RepairLoopAgent is `gate=False` but its final-attempt behaviour is
effectively blocking: when all attempts are exhausted with failures
remaining, it sets `context.metadata["repair_failed"] = True` and raises
`RuntimeError`, which HermesOrchestrator surfaces as a pipeline halt.

---

## 3. What "Real Test Suite" Means

### Pre-condition: test scaffold must exist
ScaffoldAgent already writes a `project/` directory. RepairLoopAgent requires
that the generated project includes a runnable test suite. This is NOT
guaranteed today — it depends on whether ScaffoldAgent or MissionWorkerLoop
generated test files.

**Decision required before implementation (Open Question 1):** Does ForgeOS
scaffold always include a test scaffold, or does RepairLoop need a new
mini-stage that generates tests first?

Recommended path: add a `TestScaffoldStep` (light weight, ~20 lines of LLM
call) that runs between ScaffoldAgent and MissionWorkerLoop to generate at
minimum one test file per generated module. This is a prerequisite for
RepairLoop to be meaningful.

### Test runner selection
RepairLoopAgent should detect the test framework automatically:

| Framework | Detection | Run command |
|-----------|-----------|-------------|
| pytest | `pyproject.toml` contains `[tool.pytest...]` or `requirements.txt` contains `pytest` | `python -m pytest --tb=short --no-header -q` |
| jest | `package.json` contains `"jest"` in devDependencies | `npx jest --bail --forceExit` |
| vitest | `package.json` contains `"vitest"` | `npx vitest run` |
| go test | `go.mod` present | `go test ./...` |
| unknown | fallback | log warning, skip loop — do not hard-fail the pipeline |

The runner must:
1. Run in `project/` as the working directory
2. Capture stdout + stderr combined
3. Enforce a per-run timeout (recommendation: 120s, configurable via env var
   `FORGEOS_REPAIR_TIMEOUT`)
4. Return: `(exit_code: int, output: str)`

---

## 4. Attempt Loop Design

```
for attempt in range(1, max_attempts + 1):
    exit_code, output = run_tests(project_root)
    if exit_code == 0:
        log "all tests passed on attempt {attempt}"
        break
    if attempt == max_attempts:
        raise RuntimeError("RepairLoop exhausted {max_attempts} attempts — tests still failing")
    failures = parse_failures(output)
    patch = call_llm(failures, project_root)
    apply_patch(patch, project_root)
```

### Attempt count
Recommendation: **3 attempts** (configurable via `FORGEOS_REPAIR_ATTEMPTS` env var).

Rationale:
- Attempt 1: catches obvious compilation errors and import failures (LLM almost
  always fixes these in one shot).
- Attempt 2: catches logic errors that become visible after imports are fixed.
- Attempt 3: catches regressions introduced by attempt-2 patches.
- Attempt 4+: diminishing returns. Cost grows linearly; quality improvement
  flattens. Log and surface to founder instead of burning more tokens.

Open Question 2: Should `max_attempts` be configurable per agent, or is a
global env var sufficient?

### Exhaustion behaviour
When all attempts are used with tests still failing:
1. Write `REPAIR_SUMMARY.md` to workdir with: attempt count, final test
   output (truncated to 2000 chars), list of files that were patched.
2. Set `context.metadata["repair_failed"] = True`.
3. `context.metadata["repair_attempts"] = max_attempts`.
4. Raise `RuntimeError("RepairLoop exhausted")` — pipeline halts, founder
   sees the error in the SSE stream and can inspect REPAIR_SUMMARY.md.
5. Do NOT silently pass — a broken test suite that reaches ScoreGate is
   worse than an honest halt.

---

## 5. Failure Feedback Format

### What to send to the LLM for each patch attempt

```
FAILING TESTS (attempt {N}/{max}):

{test_output[:3000]}

PROJECT FILES:
{list of modified files with their current content}

Task: Patch the minimum number of files to make the failing tests pass.
Output ONLY file patches in this format:

--- FILE: <relative/path/to/file.py> ---
<complete new file content>
--- END FILE ---

Repeat for each file that needs changes. Do not invent new tests.
```

Sending full test output (not a summary) is deliberate — LLM patch quality
degrades significantly when it cannot read the exact assertion failure and
traceback.

### Truncation
If `test_output` exceeds 3000 chars, truncate to the last 3000 chars (tail,
not head) — the most recent failures are at the bottom of pytest/jest output.

### File context window
Send only the files that the failing test imports or references (parsed from
the traceback). Do not send the entire project directory — context pollution
degrades patch quality.

---

## 6. LLM Tier for Patch Calls

Each patch attempt is an LLM call. Cost is the primary concern.

| Scenario | Model |
|----------|-------|
| Attempt 1, 2 | GLM-5.2 (Tier 1) — most bugs are straightforward fixes |
| Attempt 3 | claude-sonnet-4-6 (Tier 2) — escalate to higher quality for the final chance |
| Attempt 3 with `FORGEOS_FRONTIER_TIER=true` | claude-fable-5 (Tier 3) |

Rationale: cheap models handle simple import/syntax fixes well. Escalating on
the last attempt is cheaper than using frontier for all three.

Task type for router: `task_type="repair"`. This is a new task_type not yet
in `_select_chain()`. Implementation must add it.

---

## 7. Cost Implications

Each repair loop multiplies LLM calls. At max 3 attempts:
- Best case: 1 test run + 0 LLM calls (tests pass immediately) = no extra cost
- Typical: 2 test runs + 1 patch call (GLM-5.2, ~$0.002/run) = negligible
- Worst case: 4 test runs + 2 GLM patch calls + 1 Sonnet patch call = ~$0.05 extra per build

The worst-case cost is acceptable for pre-revenue builds where quality matters.
At scale (many concurrent builds), add `RepairLoopAgent.budget_usd` to cap
spend per build — recommendation: `0.20` (matches ArchitectAgent precedent).

---

## 8. ForgeAgent Declaration

```python
class RepairLoopAgent(ForgeAgent):
    name         = "repair_loop"
    phase        = "repair"
    capabilities = ["REPAIR_SUMMARY.md"]
    requires     = ["project/", "tasks"]
    budget_usd   = 0.20
```

---

## 9. Implementation Checklist (for the build session)

- [ ] `agents/repair.py` — `RepairLoopAgent(ForgeAgent)` with `_execute`,
      `_run_tests`, `_parse_failures`, `_patch`, `_render_summary`
- [ ] `llm/router.py` — add `"repair"` to `_select_chain` (Tier 1 for attempt
      1-2, Tier 2 for attempt 3)
- [ ] `agents/hermes.py` — insert repair stage between worker and review
- [ ] `agents/__init__.py` — add `RepairLoopAgent` to `_LAZY`
- [ ] `tests/test_repair_loop.py` — unit tests for each method + integration
      test with a real broken fixture
- [ ] **Prerequisite first**: `TestScaffoldStep` or verify ScaffoldAgent
      generates test files — RepairLoop is meaningless without a test suite
      to run

---

## 10. Open Questions

| # | Question | Priority | Notes |
|---|----------|----------|-------|
| 1 | Does ScaffoldAgent always produce a test file? If not, is TestScaffoldStep a prerequisite? | HIGH — blocks implementation | Need to run a test build and inspect output before implementing |
| 2 | Should `max_attempts` be configurable per agent via `ForgeAgent.repair_attempts` class var, or global env only? | LOW | Global env is simpler; per-agent lets security-critical services run more attempts |
| 3 | What if the test runner isn't detected? Hard-fail or skip? | MEDIUM | Current recommendation: skip loop (log warning) — don't block on missing test toolchain |
| 4 | Does RepairLoop need to handle multi-process test runners (jest --workers)? | LOW | Defer; single-process run is sufficient for MVP |
| 5 | How does RepairLoop interact with the cost ledger (`context.record_tokens`)? | LOW | Each patch LLM call must be recorded — handled automatically by `ForgeAgent._llm()` |
