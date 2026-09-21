# Shipped JSON contracts

Every `*.schema.json` here is part of the plugin's distribution surface: it is
validated by `scripts/validate_distribution.py`, exercised by
`tests/test_contracts.py` and `tests/test_visual_contracts.py`, and consumed by
downstream hosts, guards and Skills.

## Authoring rules

- JSON Schema **draft 2020-12** (`$schema` must name that dialect).
- `$id` must live under `dreamina-canvas/schemas/`.
- `additionalProperties: false` at every object level. A contract that stops
  being closed is a false green for every consumer, so this is enforced by the
  distribution validator rather than by review.
- Canonical identifiers: lowercase UUIDs (`^[0-9a-f-]{36}$`), lowercase SHA-256
  (`^[0-9a-f]{64}$`), UTC RFC 3339 timestamps (`...T..:..:..Z`, no offset).
- Never declare a field whose name is a secret shape (`access_token`,
  `refresh_token`, `cookie`, `signed_url`, `creditConfirmationToken`, …). The
  contracts scan for those names, and `scripts/artifact_guard.py` scans for
  those names at the payload boundary.

## Version fields and the back-compatibility policy

New contracts carry an explicit version constant, e.g.
`"schemaVersion": {"const": "judge_receipt/1"}`. The seven contracts released
with the `0.1.x` line (`approval_receipt`, `artifact_receipt`, `canvas_request`,
`capability_snapshot`, `command_result`, `operation_receipt`, `quote_receipt`)
predate that convention and keep their current shape; retrofitting a required
version field onto a released contract is itself a breaking change and is
deferred until a real consumer needs it.

Because closure is mandatory, compatibility is **negotiated through the version
constant, not through unknown-field tolerance**. Adding an optional field is not
free: an older consumer validating a newer document will reject it.

| Change | Class | Reasoning |
|---|---|---|
| Add a required field | **major** | Existing producers stop validating |
| Add an optional field | **major** for readers | Closed contracts make old readers reject new documents; bump the version constant so readers can branch |
| Remove or rename a field | **major** | Existing documents stop validating |
| Tighten a `pattern`, `enum`, or bound | **major** | Previously valid documents may become invalid |
| Widen a bound, add an `enum` member | **minor** | Old documents stay valid |
| `title` / `description` / `$comment` wording | **patch** | No machine effect |

A `major` change means a new version constant (`judge_receipt/2`) alongside the
old one for at least one release; consumers must not silently accept both.
