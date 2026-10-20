"""MCP tools for Claude Code. Thin wrappers over store.py and ai.py.

Run over stdio:        python mcp_server.py
Run over HTTP (later): python mcp_server.py --http
Agents must follow the hard rules in rules.md (e.g. never confirm without
the user's explicit OK).
"""
import json
import sys

from mcp.server import MCPServer

import ai
import store

mcp = MCPServer("mydash")
store.init_db()


def show(data):
    """Format a result as readable JSON text."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def safe(action):
    """Run an action; validation errors come back as plain text."""
    try:
        return show(action())
    except store.ValidationError as e:
        return "Not saved: " + "; ".join(e.messages)


@mcp.tool()
def capture(title: str, note: str | None = None) -> str:
    """Save a loose item to the inbox and return it with the AI proposal."""
    def run():
        item = store.capture(title, note)
        ai.propose_and_save(item["id"])
        return store.get_item(item["id"])
    return safe(run)


@mcp.tool()
def list_items(status: str | None = None, path: str | None = None) -> str:
    """List items, optionally filtered by status and/or path."""
    return safe(lambda: store.list_items(status, path))


@mcp.tool()
def today() -> str:
    """Show NOW, due/overdue, NEXT and what was done in the last 24 hours."""
    return safe(store.today)


@mcp.tool()
def propose(item_id: int) -> str:
    """Re-run the AI triage proposal for an item (suggestion only)."""
    def run():
        ai.propose_and_save(item_id)
        return store.get_item(item_id)
    return safe(run)


@mcp.tool()
def confirm(item_id: int, path: str, status: str, due: str | None = None,
            done_def: str | None = None,
            est_minutes: int | None = None) -> str:
    """Triage an item. Only call after the user explicitly says OK."""
    return safe(lambda: store.confirm(item_id, path, status, due, done_def,
                                      est_minutes))


@mcp.tool()
def update(item_id: int, text: str, outcome: str,
           next_step: str | None = None, next_due: str | None = None) -> str:
    """Log an update. outcome: done, progress, small_problem, big_problem.

    Problems need next_step and next_due. Only call with the user's OK.
    """
    return safe(lambda: store.add_update(item_id, text, outcome, next_step,
                                         next_due))


@mcp.tool()
def set_status(item_id: int, status: str) -> str:
    """Move an item to now, next, later or parked. Needs the user's OK."""
    return safe(lambda: store.set_status(item_id, status))


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
    else:
        mcp.run()
