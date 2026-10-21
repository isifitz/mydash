# Things to look into — v2 research

mydash v1 is done: capture, confirm, Today/Inbox/Board/Item pages, and MCP all work, and your six Waverley items are live in it. Before building v2 (expanded inbox, graph/link view, kanban board, filtering, Claude-chat linking — see `future_notes.md`), go use these for an hour each and take notes. Don't rebuild any of them; just steal the two or three things that make each one feel good or bad to use.

For each app below, try to answer:
- What's the *one* interaction that makes capture feel instant?
- What breaks down when you have 50+ items vs. 5?
- What would you keep, and what would you actively not want in mydash?

## Kanban / board tools

**Trello**
- Cards-in-columns is the reference point for your Board page. Look at: how drag-and-drop reordering feels, how a card preview shows just enough (due date chip, labels, checklist count) without opening it, how "Power-Ups" bolt extra fields onto a card without cluttering the default view.
- Relevant to: Board page tabs/columns, collapsing Parked.

**Linear**
- Faster and more opinionated than Trello. Look at: keyboard-first navigation (no mouse needed to triage), the "Today/This cycle" style priority view, how status + priority + due date combine into one compact row instead of three separate widgets.
- Relevant to: Today page density, the single-NOW philosophy you already have.

**GitHub Projects / Issues**
- Look at: how an issue links to other issues (blocks/blocked-by), and how a short title + full-body-below pattern works for item detail.
- Relevant to: the "branching problems" idea in future_notes.md — Recoup on Todva with sub-questions underneath.

## Note-taking / linking tools

**Obsidian**
- This is the big one for your graph-view idea. Look at: `[[wikilink]]` auto-linking between notes, the local graph view (one note and its direct connections) vs. the global graph (everything), backlinks panel (what links *to* this note), and how tags vs. folders vs. links each solve a different organizing problem.
- Relevant to: "the whimsical/graph view for seeing links and notes," auto-linking in future_notes.md.

**Notion**
- Look at: how a database (table) and a page can be the same underlying object viewed differently (table view vs. board view vs. calendar view of one dataset), and how a page can contain a bulleted list where each bullet can itself be expanded into a sub-page.
- Relevant to: your bullet-list capture idea (Recoup on Todva with sub-items), and board/table/calendar as views over one items table rather than separate features.

**Roam Research / Logseq** (optional, only if you have time)
- Daily-notes-first instead of folders-first; every bullet is addressable and linkable. More extreme than Obsidian. Worth 15 minutes just to see the daily-log capture pattern.
- Relevant to: fast inbox capture, the "small note working in like father" idea you jotted down.

## Calendar tools

**Google Calendar / Notion Calendar**
- Look at: how an event with a duration differs from a due-date task, how "time blocking" drags a task onto a calendar slot, and all-day vs. timed events.
- Relevant to: "the time should also allow me to change it from est minutes to hours or date ranges," and Phase 2's Google Calendar sync.

## Spreadsheet / lightweight DB tools

**Airtable**
- Look at: custom fields per "table" (like your paths each having slightly different needs), linked records between tables, and filtered/saved views.
- Relevant to: "a way to add in more areas within the 3 pillars" — Airtable's answer is user-defined fields per table.

## Project management (heavier, for contrast)

**Asana or ClickUp**
- Look at: subtasks, dependencies, and how overwhelming a fully-featured tool feels compared to Trello. This is useful mainly as a *cautionary* example — note what you'd never want in mydash.
- Relevant to: knowing where to stop adding features.

---

## How to bring findings back

When you've done this research, come back with a file (or just a conversation) covering, per app:
1. One screenshot or short description of the interaction that stood out.
2. One sentence on whether it fits mydash's "one person, no figuring out" philosophy or fights it.

We'll reverse-engineer the specific pieces you want into a v2 spec, the same way v1 started as a design doc before any code.

---

## Best-use-case advice for building mydash with me

**Keep using the spec-first flow.** v1 worked because `docs/specs/2026-10-20-mydash-mvp-design.md` existed before any code did, and `CLAUDE.md` pointed at it as the source of truth with an explicit "build only what's listed" guardrail. For v2, write (or have me draft from your notes, then you edit) a new dated spec doc before asking for implementation. This is the single biggest lever for keeping scope sane — reread the "Not now" list in the old spec before every v2 session.

**Hand me research, not conclusions, when you want options.** If you want me to compare Obsidian's graph view against Notion's linked databases, paste your raw notes/screenshots and ask "what pattern fits here" rather than pre-deciding and asking me to code it. I'll give you a tradeoff and a recommendation; you redirect.

**For UI work specifically:**
- Since this is vanilla HTML/CSS/JS with no build step, the fastest loop is: describe the interaction → I edit the template/CSS/JS → you reload the browser and react. No compile step to wait on.
- For anything involving layout decisions (tabs vs. horizontal scroll for the Board page, how a graph view should look), a quick Excalidraw or Whimsical sketch (I have tools for both) before I write CSS saves a round-trip of "no, more like this."
- Use the `dataviz` skill if the graph/link view becomes an actual node-link visualization — it has a worked method for this rather than ad hoc D3/SVG.

**For planning v2 itself**, use Plan mode (`EnterPlanMode`) once you've picked 2-3 features from your research to tackle first. Don't try to spec the whole future_notes.md backlog in one pass — it spans board redesign, bullet-list capture, graph view, and cross-app integration, which are four separable specs, not one.

**Experimental things worth trying:**
- **MCP-driven capture from this chat.** The `mydash` MCP server is already registered and connected (`mcp__mydash__*` tools). You can dictate loose ideas to me mid-conversation and I'll call `capture` directly — no need to open the Inbox page for quick thoughts. Try this for a week before building the "give Claude access to notes" feature from future_notes.md; you may find the MCP tools already *are* that feature.
- **Use `today` as a standup.** Start a session with "what's NOW" and let me call the tool instead of you checking the browser — useful for testing whether the MCP layer is actually load-bearing before investing in Hermes/Telegram (Phase 2).
- **Question-click-to-answer.** You noted AI questions on a confirm card are valuable context. Before building UI for "click a question to answer it," try it manually in chat first: paste a card's questions here, answer them in one line each, and see if that's actually faster than a UI widget would be. Cheap way to validate the feature before coding it.
- **Don't let me improvise the pillar/path list.** `rules.md` and `config.py` are the only places path structure should change — if a v2 feature needs new areas under the three pillars, update those files deliberately rather than letting proposals invent paths ad hoc.
