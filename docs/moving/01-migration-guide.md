# Moving mydash to the always-on device — migration guide

Goal: get the exact same mydash — code, the 11 real items in `data/mydash.db`, and your `.env` key — running on the always-on device, with nothing lost and a way to confirm that before you shut the old copy down.

## What "everything" means, piece by piece

| piece | tracked in git? | how it moves |
|---|---|---|
| `app.py`, `store.py`, `ai.py`, `mcp_server.py`, `config.py`, `templates/`, `static/`, `tests/`, `docs/`, `rules.md`, `CLAUDE.md`, `requirements.txt`, `pytest.ini` | yes | `git clone` / `git pull` on the new machine |
| `.venv/` | no (gitignored) | do **not** copy — rebuild fresh, it's tied to this machine's Python build/architecture |
| `data/mydash.db` | no (gitignored) | copy by hand (see below) — this is your only copy of the 11 real items, irreplaceable |
| `.env` (`ANTHROPIC_API_KEY`) | no (gitignored) | copy by hand, never through git, never pasted into chat or a gist |
| Claude Code's MCP registration (`claude mcp add mydash ...`) | no — it's local Claude Code config on this machine | re-run on the new machine, pointing at its own `.venv` python |
| `__pycache__/`, `.pytest_cache/` | no | ignore, regenerated automatically |

## Before you touch anything
1. `git status` clean here, and push anything pending to `origin` (there's already a GitHub remote set up) so the new machine can clone the latest code.
2. Run `pytest -q` here and confirm it's green (it was 28/28 as of this write-up) — that's your baseline proof the code works before the move.
3. **Back up `data/mydash.db`** to a second location (another drive, cloud storage, wherever) before transferring it anywhere. This step exists only because that file can't be regenerated from git.
4. Note the current `today` output — NOW title and NEXT titles — so you have something concrete to compare against after the copy.

## Steps
1. On the new device, `git clone https://github.com/isifitz/mydash.git`.
2. Build a fresh venv there: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
3. Copy `data/mydash.db` and `.env` over a channel that is neither git nor a public URL — `scp` directly between the two machines over SSH, or an encrypted transfer if both are Macs. Not email, not a shared doc, not pasted into this chat.
4. Check `ls -la data/` on the new machine for sane permissions, and confirm the new clone's `.gitignore` still lists `.env` and `data/` (it will — that file is checked in).
5. Run `pytest -q` on the new machine. 28/28 passing is the signal the code arrived intact.
6. Start the app (`python app.py`) and open Today in a browser on the new machine. Compare NOW/NEXT against what you noted in step 4 of "before."
7. Register MCP fresh there: `claude mcp add mydash -- /path/to/new/.venv/bin/python /path/to/new/mcp_server.py`, then `claude mcp list` and confirm it shows Connected, same as it does on this machine now.
8. Only once 5–7 all check out, stop running the app on this machine. Keep this machine's last DB backup and git history around for a week or two before deleting anything, in case something was missed.

## Rollback
The git-tracked code is never actually at risk — it lives on `origin` regardless of what happens on either machine. The one real risk is `data/mydash.db`, which is why step 3 says *copy*, not *move*: the original stays untouched on this machine until step 8 confirms the new copy is good.

## What not to do
- Don't commit `data/mydash.db` or `.env` to git "just to move them," even briefly, even on a private repo.
- Don't copy `.venv/` — always rebuild it on the target machine.
- Don't skip the pytest / Today comparison in steps 5–6 — that's the only thing standing between "it moved" and "it moved and is correct."
