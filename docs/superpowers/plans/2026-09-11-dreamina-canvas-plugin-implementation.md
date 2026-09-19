# Codex Dreamina Canvas Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and distribute a public Codex plugin that safely operates the user-installed `dreamina-canvas` CLI and packages the thirteen Canvas Skills from a pinned `full-aigc-skills/dreamina-skills` commit.

**Architecture:** The plugin uses a strict argv-only adapter and closed receipt schemas for capability, quote, approval, operation, and artifact state. Skill prose remains owned by `dreamina-skills`; a deterministic sync process copies and verifies exact bytes. Foundation and atomic Skills are packaged before domain Skills, with `compose` and `use` last.

**Tech Stack:** Codex plugin manifest, Agent Skills, Python 3, JSON Schema, `unittest`/`pytest`, `dreamina-canvas` CLI, GitHub public repository.

**Spec:** `docs/superpowers/specs/2026-09-11-partme-dreamina-canvas-design.md`

## Global Constraints

- Plugin repository and directory remain `partme-dreamina-canvas`; manifest ID is `codex-dreamina-canvas`.
- Source-of-truth repository is `https://github.com/full-aigc-skills/dreamina-skills`.
- Packaging begins only after the Canvas Skill source plan publishes a verified SHA containing all 13 Canvas Skills.
- The plugin packages exactly 13 Canvas Skills and records their upstream SHA and file hashes.
- Only `dreamina-canvas-use` permits implicit invocation; all lower-level Skills are explicit.
- Runtime `version`, `schema`, `model`, and `voice` output is authoritative.
- Saving a node is not generation. Paid commands require quote-bound action-time approval.
- Ambiguous submission and exit code 20 are recovered by the same `projectId` and `submitId`; never resubmit automatically.
- Normal CI is offline and non-charging. CLI installation, authentication, account checks, and paid canaries are separate approval boundaries.
- Secrets and ephemeral credit tokens are excluded from logs, schemas, fixtures, journals, and artifacts.
- Every task follows RED → GREEN → regression → review → commit.

## Foundation baseline completed 2026-09-12

Task 1's compatibility foundation is now materially present as `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, Apache-2.0/legal files, three transparent PNG assets, implementation directories, `scripts/validate_distribution.py`, and `tests/test_distribution.py`. Tasks 2–10 are implemented and their evidence is recorded under `docs/verification/`. Production hardening adds a reproducible development dependency set, an offline CI matrix, and security/contribution guidance.

---

### Task 1: Convert the documentation-only repository into a valid plugin scaffold

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `.agents/plugins/marketplace.json`
- Create: `tests/test_plugin_manifest.py` — **delivered as `tests/test_distribution.py`**; the same identity assertions now live there alongside the full distribution gate (see Step 1 note below)
- Create: `assets/icon.svg` — **delivered as `assets/logo.svg` plus the manifest-referenced PNGs** (`assets/logo.png`, `assets/logo-dark.png`, `assets/composer-icon.png`), which is what `interface.composerIcon` / `logo` / `logoDark` actually point at
- Modify: `README.md`
- Modify: `README.zh-CN.md`

**Interfaces:**
- Consumes: repository identity `partme-ai/partme-dreamina-canvas` and the existing bilingual architecture/spec documents.
- Produces: a validator-compatible plugin manifest and repo-local marketplace entry.

- [x] **Step 1: Write the failing manifest test**

```python
def test_manifest_identity_and_skill_root():
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    assert manifest["name"] == "codex-dreamina-canvas"
    assert manifest["skills"] == "./skills/"
    assert manifest["repository"] == "https://github.com/partme-ai/partme-dreamina-canvas"
```

These three assertions are asserted verbatim in `tests/test_distribution.py`
(`PLUGIN_ID`, `manifest["skills"]`, `REPOSITORY`), which absorbed the
standalone manifest test when the distribution gate was added in Task 9.

- [x] **Step 2: Run RED**

Run: `python3 -m unittest tests.test_distribution -v`

Expected: FAIL because `.codex-plugin/plugin.json` is absent.

- [x] **Step 3: Scaffold the manifest without placeholders**

Use the system `plugin-creator` scaffold rules. The manifest must include strict semver, author, repository, Apache-2.0 license, `skills: "./skills/"`, and an interface block with display name “Dreamina Canvas”. Do not declare apps or MCP servers until companion files exist.

- [x] **Step 4: Add the repository marketplace entry**

```json
{
  "name": "codex-dreamina-canvas",
  "source": {
    "source": "url",
    "url": "https://github.com/partme-ai/partme-dreamina-canvas.git",
    "ref": "main"
  },
  "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
  "category": "Creativity"
}
```

Validate the URL source and resolved `main` commit before relying on the marketplace entry. Installation evidence must record the resolved commit rather than treating a moving branch name as immutable proof.

- [x] **Step 5: Run validator and commit**

```bash
python3 -m unittest tests.test_distribution -v
python3 /Users/wandl/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
git add .codex-plugin .agents assets tests README.md README.zh-CN.md
git commit -m "feat: scaffold Dreamina Canvas Codex plugin"
```

### Task 2: Define closed runtime contracts

**Files:**
- Create: `schemas/capability_snapshot.schema.json`
- Create: `schemas/command_result.schema.json`
- Create: `schemas/canvas_request.schema.json`
- Create: `schemas/quote_receipt.schema.json`
- Create: `schemas/approval_receipt.schema.json`
- Create: `schemas/operation_receipt.schema.json`
- Create: `schemas/artifact_receipt.schema.json`
- Create: `tests/test_contracts.py`

**Interfaces:**
- Consumes: the CLI guide's identifiers, exit codes, required actions, per-item batch behavior, and secret exclusions.
- Produces: closed JSON contracts consumed by the adapter, guards, ledger, downloader, and packaged Skill scenarios.

- [x] **Step 1: Write failing schema tests**

```python
def test_all_contracts_are_closed_and_reject_secrets():
    for path in (ROOT / "schemas").glob("*.schema.json"):
        schema = json.loads(path.read_text())
        assert schema["additionalProperties"] is False
        serialized = json.dumps(schema).lower()
        for forbidden in ("access_token", "cookie", "signed_url", "creditconfirmationtoken"):
            assert forbidden not in serialized
```

- [x] **Step 2: Run RED**

Expected: FAIL because the schemas are missing.

- [x] **Step 3: Define exact receipt relationships**

`CapabilitySnapshot` includes CLI version/commit/edition/distribution, schema hash, profile/region/environment, and fetched-at time. `ApprovalReceipt` binds quote ID, project ID, ordered node IDs, ceiling, currency/unit, expiry, and request fingerprint but never stores the confirmation token. `OperationReceipt` contains project/node/submit IDs, last known submission state, resubmittable fact, required action, and timestamps. `ArtifactReceipt` contains resource ID, canonical local path, byte count, SHA-256, and media metadata.

- [x] **Step 4: Validate positive and negative fixtures**

Tests must reject additional properties, uppercase/noncanonical UUIDs where the contract requires lowercase UUIDs, empty submit IDs, approval for a different ordered node set, and artifact receipts without checksum evidence.

- [x] **Step 5: Commit**

```bash
git add schemas tests/test_contracts.py
git commit -m "feat: define Dreamina Canvas runtime contracts"
```

### Task 3: Implement the strict CLI adapter and error router

**Files:**
- Create: `scripts/dreamina_canvas_adapter.py`
- Create: `scripts/error_router.py`
- Create: `tests/fixtures/cli/success.json`
- Create: `tests/fixtures/cli/confirm-required.json`
- Create: `tests/fixtures/cli/resume-required.json`
- Create: `tests/fixtures/cli/upgrade-required.json`
- Create: `tests/test_dreamina_canvas_adapter.py`
- Create: `tests/test_error_router.py`

**Interfaces:**
- Consumes: argv list, timeout, environment/profile selection, stdout, stderr, and process exit code.
- Produces: `CommandResult(exit_code, payload, error, required_action, partial_data)` and a typed next-action decision.

- [x] **Step 1: Write failing argv and stream tests**

```python
def test_adapter_uses_argv_and_json_mode():
    result = run_dreamina_canvas(["schema", "node create image"], timeout_seconds=5)
    assert captured_argv[:3] == ["dreamina-canvas", "--format", "json"]
    assert captured_argv[3:] == ["schema", "node create image"]
```

Also baseline missing executable, malformed JSON, output-size limit, timeout, stdout-on-error contamination, and stderr-on-success diagnostics.

- [x] **Step 2: Run RED**

Run: `python3 -m unittest tests/test_dreamina_canvas_adapter.py tests/test_error_router.py -v`

Expected: FAIL because adapter functions are undefined.

- [x] **Step 3: Implement argv-only execution**

Never invoke a shell or interpolate user content. Force `--format json`, cap stdout/stderr, parse a single error object from stderr when nonzero, and retain the original numeric exit code.

- [x] **Step 4: Implement stable error routing**

Map 2 to caller correction, 10 to approval pause, 11 to login, 12 to permission stop, 13 to upgrade, 20 to resume, 21 to bounded backoff, and 22 to human intervention. Localized `message` is display-only; branching uses exit code and `error.requiredAction`.

- [x] **Step 5: Run tests and commit**

```bash
python3 -m unittest tests/test_dreamina_canvas_adapter.py tests/test_error_router.py -v
git add scripts tests
git commit -m "feat: add strict Dreamina Canvas CLI adapter"
```

### Task 4: Pin and synchronize the upstream Canvas Skill source

**Files:**
- Create: `upstream/dreamina-skills.lock.json`
- Create: `scripts/sync_dreamina_canvas_skills.py`
- Create: `scripts/verify_dreamina_canvas_skills.py`
- Create: `tests/test_skill_sync.py`
- Create: `skills/.gitkeep`

**Interfaces:**
- Consumes: a published `full-aigc-skills/dreamina-skills` SHA that passed its 13-Skill source plan.
- Produces: thirteen byte-identical packaged Skill directories plus a per-file SHA-256 ledger.

- [x] **Step 1: Write the failing lock and parity test**

```python
def test_packaged_skills_match_locked_source():
    lock = load_lock()
    assert lock["repository"] == "https://github.com/full-aigc-skills/dreamina-skills"
    assert len(lock["skills"]) == 13
    assert verify_locked_files(lock) == []
```

- [x] **Step 2: Run RED**

Expected: FAIL because the lock, sync script, and packaged Skills are absent.

- [x] **Step 3: Implement deterministic sync**

Require an explicit 40-character commit SHA; fetch that commit into an isolated temporary directory; copy only the declared `dreamina-canvas-*` directories; reject symlinks, caches, hidden credential files, and undeclared Skill identities; record sorted relative paths and SHA-256 values.

- [x] **Step 4: Pin the verified source commit**

Do not pin `main`, a tag without resolved commit evidence, or the pre-Canvas migration SHA `b9d11ac`. Record the new published SHA produced by the source plan's final task.

- [x] **Step 5: Verify and commit**

```bash
python3 scripts/sync_dreamina_canvas_skills.py --lock upstream/dreamina-skills.lock.json
python3 scripts/verify_dreamina_canvas_skills.py
python3 -m unittest tests/test_skill_sync.py -v
git add upstream scripts skills tests
git commit -m "build: pin Dreamina Canvas Skill source"
```

### Task 5: Package and validate the foundation and atomic Skills

**Files:**
- Package: `skills/dreamina-canvas-cli/`
- Package: `skills/dreamina-canvas-auth/`
- Package: `skills/dreamina-canvas-discover-models/`
- Package: `skills/dreamina-canvas-create/`
- Package: `skills/dreamina-canvas-quote-and-run/`
- Package: `skills/dreamina-canvas-resume-operation/`
- Package: `skills/dreamina-canvas-download-assets/`
- Create: `tests/scenarios/test_atomic_skills.py`

**Interfaces:**
- Consumes: the pinned source snapshot and adapter fixture API.
- Produces: seven independently validated atomic Skill entries.

- [x] **Step 1: Baseline atomic routing failures**

```python
def test_exit_20_routes_to_resume_not_run():
    response = evaluate_skill("dreamina-canvas-resume-operation", fixture="resume-required.json")
    assert "operation wait" in response.commands
    assert all("node run" not in command for command in response.commands)
```

Add separate scenarios for local status versus account identity, out-of-catalog models, concurrent canvas creation, exit-10 approval pause, and verified download receipts.

- [x] **Step 2: Run RED against an empty/unpackaged snapshot**

Expected: FAIL because the seven Skill entries are not yet packaged.

- [x] **Step 3: Sync the exact upstream files**

Do not edit packaged Skill prose. Any issue found during validation must be fixed and published in `dreamina-skills`, followed by updating the lock SHA and re-syncing.

- [x] **Step 4: Validate each Skill independently**

Run quick validation, strict TRACE, and its own retrieval/application scenario for each of the seven names. Preserve seven separate results in `docs/verification/atomic-skills.md`.

- [x] **Step 5: Commit**

```bash
git add skills upstream docs/verification tests/scenarios
git commit -m "feat: package atomic Dreamina Canvas Skills"
```

### Task 6: Implement quote, approval, operation, and artifact guards

**Files:**
- Create: `scripts/approval_guard.py`
- Create: `scripts/operation_ledger.py`
- Create: `scripts/artifact_guard.py`
- Create: `tests/test_approval_guard.py`
- Create: `tests/test_operation_ledger.py`
- Create: `tests/test_artifact_guard.py`

**Interfaces:**
- Consumes: closed receipts and `CommandResult` from Task 3.
- Produces: request fingerprints, one-use approval decisions, atomic non-secret journals, conservative recovery decisions, and verified artifact receipts.

- [x] **Step 1: Write failing approval-scope tests**

Test no quote, `confirmable=false`, ceiling below total, changed project/ordered node set, expiry, replay, and a latest quote above the approved ceiling.

- [x] **Step 2: Write failing recovery tests**

Test process restart, empty submit ID, `in_progress`, `completed`, `absent + resubmittable=true`, missing submission fact, batch partial data, and exit-code 21 bounded retry. No test may accept generation of a new submit ID during recovery.

- [x] **Step 3: Write failing artifact tests**

Test approved path containment, atomic-write evidence, byte-count mismatch, SHA-256 mismatch, missing media metadata, and secret-field rejection.

- [x] **Step 4: Implement the guards**

Use canonical sorted-key JSON for lowercase SHA-256 fingerprints. Persist operation receipts through temporary-file plus atomic replacement with restrictive permissions. Keep credit confirmation tokens in process memory only.

- [x] **Step 5: Run tests and commit**

```bash
python3 -m unittest tests/test_approval_guard.py tests/test_operation_ledger.py tests/test_artifact_guard.py -v
git add scripts tests
git commit -m "feat: enforce Canvas approval recovery and artifact guards"
```

### Task 7: Package image, video, audio, and timeline Skills

**Files:**
- Package: `skills/dreamina-canvas-generate-image/`
- Package: `skills/dreamina-canvas-generate-video/`
- Package: `skills/dreamina-canvas-generate-audio/`
- Package: `skills/dreamina-canvas-manage-timeline/`
- Create: `tests/scenarios/test_domain_skills.py`
- Create: `docs/verification/domain-skills.md`

**Interfaces:**
- Consumes: atomic Skills, adapter fixtures, approval/recovery/artifact guards, and the pinned source lock.
- Produces: four independently verified media/timeline Skill entries.

- [x] **Step 1: Baseline domain failures**

```python
def test_video_rejects_nonexistent_i2v_mode():
    response = evaluate_skill("dreamina-canvas-generate-video", request="单图生成视频，mode=i2v")
    assert response.selected_mode == "m2v"
    assert "i2v" not in response.argv
```

Also test image generation replacement versus sparse metadata edit, TTS/music exclusivity, timeline full-track replacement warning, out-of-catalog values, and draft-only default behavior.

- [x] **Step 2: Run RED, then sync the four Skills**

No packaged file may be patched locally. Upstream corrections require a new source commit and lock update.

- [x] **Step 3: Validate each Skill independently**

Run four quick validations, four strict TRACE evaluations, and four separate forward scenarios. Record exact upstream SHA and scenario result in `docs/verification/domain-skills.md`.

- [x] **Step 4: Commit**

```bash
git add skills upstream docs/verification tests/scenarios
git commit -m "feat: package Dreamina Canvas media Skills"
```

### Task 8: Package composition and top-level orchestration last

**Files:**
- Package: `skills/dreamina-canvas-compose/`
- Package: `skills/dreamina-canvas-use/`
- Create: `tests/scenarios/test_orchestration_skills.py`
- Create: `docs/verification/orchestration-skills.md`

**Interfaces:**
- Consumes: all eleven previously packaged Skills and runtime guards.
- Produces: non-charging graph composition and the only implicitly invoked end-to-end Canvas workflow.

- [x] **Step 1: Write failing orchestration tests**

```python
def test_use_is_the_only_implicit_canvas_skill():
    policies = load_canvas_skill_policies()
    assert policies["dreamina-canvas-use"] is True
    assert all(not value for name, value in policies.items() if name != "dreamina-canvas-use")
```

Add scenarios for building a graph without spending, explicit topological run batches, quote rejection, resumed video, per-item batch reporting, timeline replacement warning, and downloaded artifact verification.

- [x] **Step 2: Run RED, then sync `compose` and `use`**

The `use` Skill must route to lower-level Skills and must not duplicate global flags, exit-code tables, model catalogs, or node schemas.

- [x] **Step 3: Validate and commit**

Run both quick validators, strict TRACE checks, orchestration scenarios, and the upstream parity verifier.

```bash
git add skills upstream docs/verification tests/scenarios
git commit -m "feat: package Dreamina Canvas orchestration Skills"
```

### Task 9: Add plugin-wide distribution and security gates

**Files:**
- Create: `scripts/validate_distribution.py`
- Create: `tests/test_distribution.py`
- Create: `docs/verification/offline.md`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.agents/plugins/marketplace.json`
- Modify: `README.md`
- Modify: `README.zh-CN.md`

**Interfaces:**
- Consumes: all manifests, schemas, scripts, tests, assets, 13 packaged Skills, and the upstream lock.
- Produces: a distributable plugin archive with reproducible offline evidence.

- [x] **Step 1: Write failing distribution tests**

Assert repository URL, plugin ID, strict semver, exact 13-Skill inventory, source SHA, byte parity, explicit/implicit policies, executable bits, license presence, valid local links, no symlinks/caches, and zero secret-pattern matches.

- [x] **Step 2: Run RED and fix only evidenced failures**

Do not add apps/MCP fields, screenshots, or runtime claims unless corresponding files and verification exist.

- [x] **Step 3: Run the complete offline gate**

```bash
python3 -m unittest discover -s tests -v
python3 scripts/verify_dreamina_canvas_skills.py
python3 scripts/validate_distribution.py
python3 /Users/wandl/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
git diff --check
```

- [x] **Step 4: Record evidence and commit**

`docs/verification/offline.md` must include command, timestamp, exit status, test count, plugin validator result, source SHA, and explicit `cli_runtime=NOT_RUN` / `paid_canary=NOT_RUN` when those checks were not authorized.

```bash
git add scripts tests docs/verification .codex-plugin .agents README.md README.zh-CN.md
git commit -m "test: verify Dreamina Canvas plugin distribution"
```

### Task 10: Perform separately authorized runtime and installation acceptance

**Files:**
- Create: `docs/verification/dreamina-canvas-runtime.md`
- Create: `docs/verification/codex-installation.md`
- Modify: `upstream/dreamina-skills.lock.json` only if the verified source changed.

**Interfaces:**
- Consumes: a separately authorized CLI installation/authentication state and the completed plugin package.
- Produces: read-only CLI contract evidence and a fresh Codex task discovery result; paid canary remains independent.

- [x] **Step 1: Stop for installation authorization when CLI is absent**

Present the reviewed installation source `https://jimeng.jianying.com/canvas-cli`, expected install directory, files it may modify, and verification commands. Do not execute the installer based only on this plan.

- [x] **Step 2: Capture read-only runtime evidence after authorization**

```bash
dreamina-canvas --format json version
dreamina-canvas --format json schema
dreamina-canvas --format json auth status
dreamina-canvas --format json model search --type image --detail full
dreamina-canvas --format json voice list --language zh-CN --offset 0 --count 50
```

Run `auth account` only when authentication/account access was also authorized. Redact user identifiers from committed evidence.

- [x] **Step 3: Install from the public repository marketplace**

Follow the current plugin-creator cachebuster/reinstall flow. Open a fresh Codex task and verify discovery of exactly thirteen names, with only `dreamina-canvas-use` available for implicit invocation.

- [x] **Step 4: Keep paid canary independent**

Without a separate action-time approval, write `paid_canary=NOT_RUN`. If approved, create one low-cost draft, quote it, show the exact maximum credits, obtain approval again, run once with a persisted submit ID, wait to terminal state, and verify the downloaded artifact.

- [x] **Step 5: Commit, push, and prove remote equality**

```bash
git add docs/verification upstream/dreamina-skills.lock.json
git commit -m "test: record Dreamina Canvas runtime acceptance"
git push origin main
```

Compare local, upstream-tracking, and remote `main` SHAs. Report runtime, installation, authentication, and paid-canary gates separately.

## Completion Gate

```text
upstream_canvas_skill_count = 13
packaged_canvas_skill_count = 13
upstream_snapshot_parity = PASS
only_use_allows_implicit_invocation = PASS
plugin_manifest_validation = PASS
contract_and_adapter_tests = PASS
approval_recovery_artifact_tests = PASS
atomic_skill_scenarios = 7/7 PASS
domain_skill_scenarios = 4/4 PASS
orchestration_skill_scenarios = 2/2 PASS
skill_quick_validation = 13/13 PASS
skill_trace = 13/13 PASS
distribution_and_secret_scan = PASS
read_only_cli_runtime = PASS or explicitly NOT_RUN
fresh_codex_installation = PASS
paid_canary = separately approved PASS or NOT_RUN
local_tracking_remote_sha = identical
```
