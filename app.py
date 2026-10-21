"""Flask routes only. All rules and queries live in store.py."""
from datetime import datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, url_for

import ai
import calendar_sync
import config
import store

app = Flask(__name__)
app.secret_key = "local-only"  # only used for flash messages; no auth in v1
store.init_db()


# ---------- helpers ----------

@app.template_filter("countdown")
def countdown(due):
    """'due in 3h', 'due today', 'overdue 1 day' from a stored due value."""
    if not due:
        return ""
    has_time = "T" in due
    when = datetime.fromisoformat(due)
    if not has_time:
        when = datetime.fromisoformat(due + "T23:59")
    if when.tzinfo is None:
        when = when.replace(tzinfo=store.TZ)
    delta = when - datetime.now(store.TZ)
    secs = int(delta.total_seconds())
    if secs >= 0:
        if not has_time and when.date() == datetime.now(store.TZ).date():
            return "due today"
        hours = secs // 3600
        return f"due in {hours}h" if hours < 24 else f"due in {hours // 24}d"
    secs = -secs
    if secs < 3600 * 24:
        return f"overdue {max(secs // 3600, 1)}h"
    days = secs // (3600 * 24)
    return f"overdue {days} day{'s' if days != 1 else ''}"


app.jinja_env.globals.update(due_for_input=store.due_for_input,
                             statuses=config.CONFIRM_STATUSES)


def form_fields():
    """Read the triage card fields from the posted form."""
    f = request.form
    date, time = f.get("due_date", "").strip(), f.get("due_time", "").strip()
    return dict(path=f.get("path", ""), status=f.get("status", ""),
                due=(f"{date} {time}" if date and time else date),
                done_def=f.get("done_def", ""),
                est_minutes=f.get("est_minutes", ""))


def card(item, posted=None):
    """Build the values shown on a confirm card: posted, else AI, else blank.

    Each field is (value, source) where source is 'you', 'ai' or 'blank'.
    """
    if posted is not None:
        due = posted["due"]
        values = dict(posted, due_date=due[:10], due_time=due[11:16])
        return {k: (values.get(k, ""), "you")
                for k in ("path", "status", "due_date", "due_time",
                          "done_def", "est_minutes")}
    prop = item.get("proposal") or {}
    due = store.due_for_input(prop.get("due"))
    values = dict(path=prop.get("path", ""), status=prop.get("status", ""),
                  due_date=due[:10], due_time=due[11:16],
                  done_def=prop.get("done_def", ""),
                  est_minutes=prop.get("est_minutes") or "")
    return {k: (v, "ai" if v != "" else "blank") for k, v in values.items()}


def render_inbox(errors=None, posted=None):
    """Render the inbox; `errors`/`posted` are {item_id: ...} for one card."""
    items = store.list_items(status="inbox")
    cards = [dict(item=i, fields=card(i, (posted or {}).get(i["id"])),
                  errors=(errors or {}).get(i["id"], []))
             for i in items]
    return render_template("inbox.html", cards=cards,
                           paths=store.known_paths())


def flash_errors(e):
    for m in e.messages:
        flash(m)


def sync_calendar(item_id):
    """Mirror an item's due date to Google Calendar; flash any clashes."""
    clashes = calendar_sync.sync_due(store.get_item(item_id))
    if clashes:
        flash("Clashes with: " + ", ".join(clashes))


# ---------- pages ----------

@app.get("/")
def today():
    return render_template("today.html", t=store.today())


@app.route("/inbox", methods=["GET", "POST"])
def inbox():
    if request.method == "POST":
        try:
            item = store.capture(request.form.get("title", ""))
        except store.ValidationError as e:
            flash_errors(e)
        else:
            ai.propose_and_save(item["id"])
        return redirect(url_for("inbox"))
    return render_inbox()


@app.get("/board")
def board():
    return render_template("board.html", board=store.board(),
                           pillars=config.PILLARS)


@app.route("/item/<int:item_id>", methods=["GET", "POST"])
def item_detail(item_id):
    item = store.get_item(item_id)
    if item is None:
        return "No such item", 404
    errors, posted = [], None
    if request.method == "POST":
        posted = form_fields()
        try:
            store.confirm(item_id, **posted)
            sync_calendar(item_id)
            return redirect(url_for("item_detail", item_id=item_id))
        except store.ValidationError as e:
            errors = e.messages
    return render_template("item.html", item=item,
                           fields=card(item, posted) if posted else
                           card({"proposal": {
                               "path": item["path"], "status": item["status"],
                               "due": item["due"], "done_def": item["done_def"],
                               "est_minutes": item["est_minutes"]}}),
                           errors=errors, updates=store.get_updates(item_id),
                           paths=store.known_paths())


# ---------- actions ----------

@app.post("/item/<int:item_id>/confirm")
def confirm(item_id):
    posted = form_fields()
    try:
        store.confirm(item_id, **posted)
        sync_calendar(item_id)
    except store.ValidationError as e:
        return render_inbox({item_id: e.messages}, {item_id: posted})
    return redirect(url_for("inbox"))


@app.post("/item/<int:item_id>/park")
def park(item_id):
    posted = form_fields()
    try:
        store.confirm(item_id, posted["path"] or "Parked", "parked",
                      done_def=posted["done_def"],
                      est_minutes=posted["est_minutes"])
        sync_calendar(item_id)
    except store.ValidationError as e:
        return render_inbox({item_id: e.messages}, {item_id: posted})
    return redirect(url_for("inbox"))


@app.post("/item/<int:item_id>/repropose")
def repropose(item_id):
    ai.propose_and_save(item_id)
    return redirect(url_for("inbox"))


@app.post("/item/<int:item_id>/discard")
def discard(item_id):
    try:
        store.discard(item_id)
    except store.ValidationError as e:
        flash_errors(e)
    return redirect(url_for("inbox"))


@app.post("/item/<int:item_id>/make-now")
def make_now(item_id):
    try:
        store.set_status(item_id, "now")
    except store.ValidationError as e:
        flash_errors(e)
    return redirect(url_for("today"))


@app.post("/item/<int:item_id>/update")
def update(item_id):
    """Done / progress / small problem / big problem from the Today forms."""
    f = request.form
    kind = f.get("kind", "")
    try:
        if kind == "done":
            store.add_update(item_id, f.get("text") or "Done", "done")
            sync_calendar(item_id)
        elif kind == "progress":
            store.add_update(item_id, f.get("text", ""), "progress")
        elif kind in ("small_problem", "big_problem"):
            store.add_update(item_id, f.get("text") or "Problem", kind,
                             next_step=f.get("next_step"),
                             next_due=f.get("next_due"))
            sync_calendar(item_id)
        else:
            raise store.ValidationError("Pick an update type")
    except store.ValidationError as e:
        flash_errors(e)
    return redirect(request.referrer or url_for("today"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
