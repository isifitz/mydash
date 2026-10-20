"""AI triage proposal. It only suggests; nothing here confirms an item."""
import logging
import os

from dotenv import load_dotenv

import config
import store

load_dotenv(config.BASE_DIR / ".env")
log = logging.getLogger(__name__)

PROPOSAL_TOOL = {
    "name": "propose_triage",
    "description": "Propose how to triage a captured item.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "status": {"type": "string", "enum": config.CONFIRM_STATUSES},
            "due": {"type": "string",
                    "description": "YYYY-MM-DD or YYYY-MM-DD HH:MM; empty if parked"},
            "done_def": {"type": "string"},
            "est_minutes": {"type": "integer"},
            "questions": {"type": "array", "items": {"type": "string"},
                          "maxItems": 2},
        },
        "required": ["path", "status", "done_def", "questions"],
    },
}


def _system_prompt():
    """rules.md plus today's date and the current state of NOW and NEXT."""
    t = store.today()
    now = store.now_ts()
    now_title = t["now"]["title"] if t["now"] else "none"
    return (config.RULES_PATH.read_text()
            + f"\n\n## Current state\n- Now: {now} ({config.TIMEZONE})\n"
            + f"- Known paths: {', '.join(store.known_paths())}\n"
            + f"- Current NOW: {now_title}\n"
            + f"- NEXT count: {len(t['next'])} of {config.NEXT_CAP}\n")


def propose(title, note=None):
    """Return a proposal dict, or None on any failure (never raises)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.info("No ANTHROPIC_API_KEY; skipping proposal")
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(timeout=config.AI_TIMEOUT_SECONDS,
                                     max_retries=0)
        text = title + (f"\n\nNote: {note}" if note else "")
        message = client.messages.create(
            model=config.MODEL,
            max_tokens=500,
            system=_system_prompt(),
            messages=[{"role": "user", "content": text}],
            tools=[PROPOSAL_TOOL],
            tool_choice={"type": "tool", "name": PROPOSAL_TOOL["name"]},
        )
        for block in message.content:
            if block.type == "tool_use" and isinstance(block.input, dict):
                return dict(block.input)
        log.warning("Proposal had no tool_use block")
    except Exception:  # any failure just means blank card
        log.exception("Proposal failed")
    return None


def propose_and_save(item_id):
    """Run propose() for a stored item and save the result for display."""
    item = store.get_item(item_id)
    if item is None:
        return None
    proposal = propose(item["title"], item["note"])
    store.save_proposal(item_id, proposal)
    return proposal
