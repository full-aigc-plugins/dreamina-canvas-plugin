# Contributing

## Development setup

Use Python 3.11 or newer in an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

Do not commit the virtual environment, credentials, generated media, operation
journals, or approval tokens.

## Verification

Run the complete non-charging gate before opening a pull request:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s tests/scenarios -v
.venv/bin/python scripts/verify_dreamina_canvas_skills.py
.venv/bin/python scripts/validate_distribution.py
git diff --check
```

The packaged `skills/dreamina-canvas-*` files are a pinned upstream snapshot.
Do not patch them locally. Publish corrections in
`full-aigc-skills/dreamina-skills`, update the lock, and re-run the deterministic
sync.

## Runtime acceptance

CLI installation, login, account inspection, and paid generation are outside
normal CI. Each requires the authorization documented by the relevant Skill.
A timeout or ambiguous submission must be resumed by the existing identifier;
never mint a replacement `submitId` automatically.
