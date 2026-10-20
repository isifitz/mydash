# mydash — MVP design

- **Date:** 2026-10-20
- **Status:** Approved for build
- **Owner:** single user (me)
- **Location:** `~/Desktop/mydash` (git repo)

---

## 1. Problem

My drain is not effort. It is *planning and bouncing*. With many open jobs, I work on thing 4 while thing 2 sits unguarded in my head, so I jump, lose my place, and burn out without finishing anything.

My best days (setting up and DJing a friend's event; pressing a 100-shirt order) shared one shape:

- a **clear objective**
- a **deadline**
- **one job in my hands**
- a **definition of done**
- **no "figuring out"**, just action

**mydash removes the figuring-out.** It catches every loose thing so nothing is lost, turns each one into a dated objective with a clear done-definition, and shows me exactly one thing to do now.

## 2. User

One person: me. Three pillars only:

- **Waverley** (Waverley Prints): business system, products, recouping losses
- **Music**: DJing, production, theory
- **FixMe**: routine, household, one bag, work system, replacing social media, learning, decentering

I need:
- capture that is instant and feels safe
- structure handed to me, not designed by me each day
- input that is always correct: the system confirms what it understood, and I fill blanks or correct it

## 3. Success criteria

1. **Capture** takes under 10 seconds: one line, Enter.
2. **Nothing is triaged** without a path, a status, a due date and a done-definition. Parked items need only a path.
3. **Tomorrow test:** I open Today and immediately know what is NOW, what is due, and what got done.
4. **Day-one test:** my six open Waverley items are captured, confirmed and dated.

## 4. Scope

### In scope (v1)
- SQLite store with all validation in one module
- Pages: **Today**, **Inbox** (with confirm cards), **Board**, **Item detail**
- AI proposal on each confirm card (Claude Haiku 5.5)
- Update flow: done / progress / small problem / big problem
- MCP server (local stdio) exposing the same actions to Claude Code
- Tests proving validation accepts correct input and rejects wrong or incomplete input

### Not now
- Anything in `Future_ideas.md` beyond what is listed above
- Importing old notes
- Hermes / Telegram
- Google Calendar sync
- Reminders and the morning message
- Login or auth, access from other devices, mobile layout polish
- Drag-and-drop, recurring tasks, stats or analytics

## 5. Architecture

```
            store.py   (SQLite + ALL validation + ALL queries)
           /        \
   app.py (Flask)    mcp_server.py (stdio now, HTTP later)
   pages on            capture · list · today · propose ·
   127.0.0.1:5000      confirm · update · set_status
        |                     |
     ai.py  ──── reads ──── rules.md ──── also read by Claude Code / Hermes
   (Haiku proposal)
```

**Principles**
- `store.py` is the only code that touches the database. Pages, MCP and AI never write SQL.
- `rules.md` is the single rulebook: the Haiku system prompt and the agent's instructions.
- AI only *suggests*. Nothing becomes triaged until confirm passes validation.
- The app must fully work with no API key. Cards just show blanks.

**Stack**
- Python 3.11+
- Flask + Jinja2
- `sqlite3` (stdlib)
- `anthropic` SDK
- `mcp` SDK (FastMCP)
- `pytest`
- `python-dotenv`
- Vanilla JS only where needed; no build step, no frontend framework

**Layout**
```
mydash/
  app.py              # Flask routes only, thin
  store.py            # DB schema, validation, queries
  ai.py               # propose(title, note) -> dict | None
  mcp_server.py       # MCP tools wrapping store.py
  config.py           # pillars, timezone, caps, model name
  rules.md
  CLAUDE.md
  requirements.txt
  .env                # ANTHROPIC_API_KEY (gitignored)
  .gitignore          # .env, data/, __pycache__/
  data/mydash.db      # gitignored
  templates/  base.html  today.html  inbox.html  board.html  item.html
  static/     style.css  app.js
  tests/      test_store.py
  docs/specs/2026-10-20-mydash-mvp-design.md
```

## 6. Data model

### `items`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT NOT NULL | one line, 1–120 chars, trimmed |
| note | TEXT | optional detail |
| path | TEXT | e.g. `Waverley/Products`; required on confirm |
| status | TEXT NOT NULL | `inbox` · `now` · `next` · `later` · `blocked` · `done` · `parked`; default `inbox` |
| done_def | TEXT | what "done" looks like |
| due | TEXT | ISO 8601, Africa/Johannesburg, date or date+time |
| est_minutes | INTEGER | optional, 5–600 |
| proposal | TEXT | JSON from AI; display only, never trusted |
| calendar_id | TEXT | unused in v1 (Phase 2) |
| created_at, updated_at, done_at | TEXT | ISO timestamps |

### `updates`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| item_id | INTEGER FK → items | |
| at | TEXT | timestamp |
| text | TEXT NOT NULL | my short message |
| outcome | TEXT NOT NULL | `done` · `progress` · `small_problem` · `big_problem` |
| next_step | TEXT | required for problems |
| next_due | TEXT | required for problems |

### Paths
- A path must start with a pillar: `Waverley`, `Music`, `FixMe`, or `Parked`.
- Up to 3 segments. Each segment uses letters, numbers, spaces or hyphens.
- New sub-paths are allowed; seed list in `rules.md`.

## 7. Validation rules (all in `store.py`)

Every violation raises `ValidationError` with a list of plain-language messages (e.g. "Due date is missing", "Pick an area: Waverley, Music, FixMe or Parked"). Every write is one transaction: all or nothing.

| # | Rule |
|---|---|
| V1 | **Capture:** title required (non-empty after trim, ≤120 chars). Saved with status `inbox`. Nothing else required. |
| V2 | **Confirm:** path valid; status one of `now/next/later/blocked/parked`. Unless parked: `done_def` required (≥3 chars) and `due` required. |
| V3 | **Dates:** accept `YYYY-MM-DD` or `YYYY-MM-DD HH:MM`, read as Africa/Johannesburg. New due dates cannot be in the past (today is fine). |
| V4 | **One NOW:** setting `now` while another item is `now` is rejected, naming the current NOW ("'Fix heat press' is NOW. Finish or move it first."). |
| V5 | **NEXT cap:** at most 3 items in `next`. |
| V6 | **Update:** item must exist and not be `done`; `text` required; outcome valid. |
| V7 | **Outcome effects:** `done` → status `done`, `done_at` set. `progress` → log only. `small_problem` → `next_step` + `next_due` required; item `due` = `next_due`. `big_problem` → `next_step` + `next_due` required; status `blocked`, `due` = `next_due` (review date). |
| V8 | **Done is final in v1:** done items cannot be re-triaged or updated. |
| V9 | **Delete:** only `inbox` items can be deleted (discarding a bad capture). |
| V10 | **Proposals are never applied automatically.** Only an explicit confirm writes item fields. |

## 8. AI proposal (`ai.py`)

- `propose(title, note=None) -> dict | None`
- Model: `claude-haiku-5-5` (set in `config.py`)
- System prompt: `rules.md` + today's date and time (Africa/Johannesburg) + existing paths + current NOW title (if any) + NEXT count
- Output: structured JSON, enforced with the SDK's structured-output / tool-use JSON schema (check current Anthropic docs):
  ```json
  {"path": "...", "status": "...", "due": "YYYY-MM-DD[ HH:MM]",
   "done_def": "...", "est_minutes": 90, "questions": ["..."]}
  ```
- Called right after capture, with a 10 s timeout, and from a "Re-propose" button.
- Result stored in `items.proposal`.
- Any failure (no key, timeout, bad JSON) → `None`, logged, and the card shows blanks. Never crash a page.
- Expected cost: about $0.0002 per proposal.

## 9. Pages

### Today — `/`
- **NOW card**
  - Shows title, path, done-definition, and due countdown ("due in 3h", "overdue 1 day").
  - Buttons: **Done**, **Problem**, **Update**.
  - Empty state: "Nothing is NOW. Pick one:" with the NEXT items, each with a *Make NOW* button.
- **Due today & overdue:** includes blocked items whose review date is today or earlier.
- **NEXT:** up to 3 items, each with a *Make NOW* button.
- **Since last time:** items done in the last 24 h.
- **Update forms** (inline, small):
  - **Done:** optional note, then "What's NOW next?" listing NEXT.
  - **Problem:** choose *Small* ("What's the fix?" + "When?") or *Big* ("One step that moves it?" + "When do we look again?").
  - **Update:** text, logged as progress.

### Inbox — `/inbox`
- Capture input with autofocus. Enter saves. No other fields.
- Inbox items listed newest first, each as a **confirm card**:
  - Fields: path (input with datalist of known paths), status (select), due (date + optional time), done-definition, est. minutes.
  - Pre-filled from the AI proposal, with AI-filled fields visibly marked and blanks highlighted.
  - AI questions shown under the card.
  - Buttons: **Confirm**, **Park**, **Re-propose**, **Discard**.
  - Validation errors appear inline on that card, and entered values are kept.

### Board — `/board`
- One section per pillar, with columns **NOW · NEXT · LATER · BLOCKED**.
- Each item shows title, due, and done-definition.
- Parked items are collapsed per pillar.
- Clicking an item opens its detail page.

### Item detail — `/item/<id>`
- All fields, editable through the same validation as confirm.
- Update history, newest first.

## 10. MCP server (`mcp_server.py`)

- **Transport:** stdio for now. Design it so streamable HTTP can be switched on later by a flag (needed for Hermes on another machine).
- **Tools:** all call `store.py`. Validation errors are returned as readable text, not exceptions.

| tool | args | does |
|---|---|---|
| `capture` | title, note? | saves to inbox, runs proposal, returns item + proposal |
| `list_items` | status?, path? | filtered list |
| `today` | — | NOW, due/overdue, NEXT, done in last 24 h |
| `propose` | item_id | re-runs the AI proposal |
| `confirm` | item_id, path, status, due?, done_def?, est_minutes? | triages (V2–V5) |
| `update` | item_id, text, outcome, next_step?, next_due? | logs + applies effects (V6–V7) |
| `set_status` | item_id, status | moves between now/next/later/parked (V4–V5) |

- **Agent rule** (in `rules.md`): never call `confirm` without the user's explicit OK in the conversation.
- **Register with Claude Code:** `claude mcp add mydash -- python mcp_server.py` (check current Claude Code docs for exact syntax).

## 11. Phase 2 (designed for, not built)

1. **Hermes** on the always-on machine. Decide where the store lives, then either switch MCP to HTTP or move the app there. Approach decided from the Hermes docs (skill, script or MCP).
2. **Telegram** capture and updates through Hermes, from phone, PC and iPad.
3. **Google Calendar:** on confirm with a due date, create or update an event (`calendar_id`). Visible in Notion Calendar too.
4. **Reminder** message with the current NOW task. Morning triage later.
5. Future ideas backlog.

## 12. Acceptance checks for v1

- [ ] `pytest` passes: every validation rule V1–V10 has at least one accept and one reject case.
- [ ] Capturing "DJ booth package: gazebo, logo table cloth" shows a pre-filled card under `Waverley/Products`.
- [ ] Confirm with a missing due date shows an inline error, and nothing is saved.
- [ ] A second NOW is rejected with the current NOW named.
- [ ] A fourth NEXT is rejected.
- [ ] Big problem → item shows as BLOCKED with a review date.
- [ ] With no API key, capture still works and the card shows blanks.
- [ ] Claude Code can run `today` and `capture` through MCP.
- [ ] The six Waverley items are confirmed, and Today shows one NOW.

## 13. Risks

- **Store location vs Hermes** on the other machine: deferred to Phase 2. Mitigated by the single DB file and switchable MCP transport.
- **Building the system becomes the restart.** Ship v1 as specified, use it for a few days, then change it. No polish before use.
- **API credit:** load credit before testing the AI. Everything else works without it.
