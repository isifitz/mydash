# Making the always-on device the application server — discussion doc

This is a discussion document for future reading, not a spec or a decision. It exists so that when multi-device access actually gets built, the tradeoffs are already laid out instead of being figured out from scratch.

## Reframing: this isn't "sync," it's "one server, many clients"

mydash's data model is a single SQLite file read and written by one Flask process. If the always-on device runs that one process and every other device (MacBook, phone, iPad) just opens a browser tab pointed at it, there is no multi-device sync problem to solve — there's exactly one copy of the data, and every device is a thin client looking at the same page. Multi-master sync, where each device holds its own DB that reconciles later, was never designed for here and would be a much bigger rebuild (conflict resolution, merge rules, etc.). Avoid that path entirely — it solves a problem mydash doesn't have.

## What changes vs. v1's guardrails

`CLAUDE.md` guardrail #5 currently reads: "Bind to 127.0.0.1 only. No auth in v1, so never expose it on the network." That was correct for "one person, one laptop." Turning the always-on device into a real server for other devices means directly revisiting that guardrail — any future spec for this has to explicitly replace it, not quietly ignore it.

## Options, roughly least to most exposure

1. **Private VPN mesh (Tailscale / WireGuard), bind to the mesh IP, no auth added.** The app is reachable only from devices enrolled in your own private network, never the public internet. Smallest change to the app itself — arguably just binding to the mesh-assigned IP instead of 127.0.0.1 — but every device that wants access needs the VPN client installed and signed in.
2. **VPN mesh + basic auth in front of Flask (or a reverse proxy doing it).** Same network-level protection as (1), plus a login so a lost or compromised device already on the mesh still can't open mydash without a password. A modest addition — a login page and session cookie.
3. **Reverse proxy (Caddy / nginx) with real auth, exposed to the public internet over HTTPS.** Needed only if you want access from a device that can't run the VPN client — a borrowed computer, a locked-down work machine. The biggest jump in both effort and risk: now it's a public-facing login screen needing rate limiting, real password/session handling, and TLS certs, none of which exist in mydash today.

**Direction for whenever this gets built (not a decision now):** start with option 1. It needs almost no code change, matches "one person's own devices only," and upgrades to option 2 later without redoing anything.

## The Flask dev server caveat

`python app.py` today runs Flask's built-in development server. That's fine bound to 127.0.0.1 for one user, but it isn't meant to carry an always-on, multi-client load — single-threaded by default, no production hardening. If the always-on device becomes the real server, swapping in a small production WSGI server (`waitress` is simple to drop in; `gunicorn` is the common Linux choice) is a prerequisite, independent of the auth/network question above.

## Hermes in this picture

Hermes here means Nous Research's Hermes agent. Nous's Hermes models are typically run as a locally-hosted open-weight model (via something like llama.cpp, vLLM, or Ollama) rather than called through a hosted API, which means the always-on device needs enough RAM/GPU headroom to hold that model *in addition to* running mydash and whatever VPN/proxy layer gets added later. Worth sizing that before assuming mydash's Flask process and Hermes's own inference belong on the same box. If the device turns out to be resource-constrained, the fallback is the same fork the original spec already named in its risks section ("store location vs Hermes... deferred to Phase 2"): Hermes could call mydash's MCP server over the network rather than everything being co-located on one machine.

## Open questions for later

- Does every device need write access (confirming items, logging updates), or do some only need read access (checking Today)?
- If the always-on device also runs Hermes's own inference, is there resource contention with mydash's Flask app?
- At what point does "no auth" stop being acceptable — is a private home network trusted on its own, or does even that need a login?

No action needed on this doc now. Revisit once the remote-access spec (see `02-remote-access-spec.md`, once written) is settled and mydash is actually running on the always-on device.
