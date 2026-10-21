# CLAUDE.md — mydash

## Purpose
mydash is a small local dashboard for one person. It removes the "figuring out." It catches every loose idea, turns each into a dated objective with a clear done-definition, and shows exactly one NOW task.

The full design is in `docs/specs/2026-10-20-mydash-mvp-design.md`. **Read it before writing code. It is the source of truth.**

## Stack
- Python 3.11+
- Flask + Jinja2
- SQLite (`sqlite3` stdlib)
- `anthropic` SDK (model `claude-haiku-5-5`)
- `mcp` SDK (FastMCP)
- `pytest`
- `python-dotenv`
- Vanilla HTML/CSS/JS. No frontend framework, no build step.

## Layout
```
app.py          Flask routes only — thin, no SQL, no validation logic
store.py        schema, validation (ValidationError), every query
ai.py           propose(title, note) -> dict | None
calendar_sync.py  sync_due(item) -> list[str] | None (Google Calendar, Phase 2)
mcp_server.py   MCP tools wrapping store.py (stdio; HTTP later via flag)
config.py       pillars, timezone (Africa/Johannesburg), caps, model name
rules.md        rulebook for the AI and for agents
templates/ static/ tests/ data/ docs/
```

## Commands
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
                                    # .env holds ANTHROPIC_API_KEY (optional, gitignored)
python app.py                      # http://127.0.0.1:5000
pytest -q
claude mcp add mydash -- python mcp_server.py   # verify syntax in current docs
```

## Guardrails
1. **Build only what the spec lists.** If something seems missing, ask. Do not add features from `Future_ideas.md` or the "Not now" list.
2. **`store.py` is the only module that touches the database.** Routes, MCP tools and `ai.py` call its functions.
3. **All validation lives in `store.py`** (rules V1–V10 in the spec). Pages and MCP show its messages; they never re-implement them.
4. **AI only suggests.** Never write proposal values into item fields without an explicit confirm. The app must work fully with no API key.
5. **Bind to 127.0.0.1 only.** No auth in v1, so never expose it on the network.
6. **Dates** are in Africa/Johannesburg via `zoneinfo`. Store ISO 8601 strings.
7. **Keep files small and readable.** The owner is learning Python (CS50P), so prefer clear code over clever code, with short docstrings.
8. **Test first for `store.py`.** Each rule V1–V10 gets an accept test and a reject test. Use a temporary database per test.
9. Never commit `.env` or `data/`.
10. Before using the Anthropic or MCP SDKs, check current docs (structured outputs, FastMCP API) rather than relying on memory.

## Definition of done
The acceptance checks in spec §12 all pass, and the owner can capture, confirm and update their six Waverley items.
