# Remote access to the always-on device — spec

- **Device:** old iMac, running Linux, has a desktop GUI available.
- **Starting point:** no VPN/mesh tooling set up yet, not currently reachable remotely at all.
- **Scope:** your own devices only (MacBook, phone, iPad) — never a borrowed or public machine. This rules out any public-facing login screen or exposed port entirely; everything here stays on a private network you control.

## Recommended approach: Tailscale mesh + OpenSSH

Tailscale builds a private virtual network (a "tailnet") between devices signed into the same account, each getting a stable private address and hostname, reachable from anywhere there's internet — no router configuration, no port forwarding, no public IP exposure. SSH then rides on top of that private network exactly like it would on a home LAN.

### 1. Install Tailscale everywhere
- On the iMac (Linux): install via the distro's package or Tailscale's install script, then `sudo tailscale up` and sign in.
- On your MacBook, phone, iPad: install the Tailscale app, sign in with the **same account**.
- Once all are up, each device has a stable tailnet hostname (e.g. `imac.your-tailnet.ts.net`) and a `100.x.x.x` address that works the same whether you're on the same Wi-Fi or on the other side of the country.

### 2. Enable SSH on the iMac
- Install and enable the SSH server if it isn't already running: `sudo apt install openssh-server` (or your distro's equivalent), then `sudo systemctl enable --now ssh`.
- Harden it once it's reachable only over the tailnet anyway: set `PasswordAuthentication no` in `/etc/ssh/sshd_config` and use key-based auth (copy your MacBook's public key over once via `ssh-copy-id`, or Tailscale SSH — see below). This is a standard hardening step independent of Tailscale, worth doing regardless.
- No firewall port-opening on your router is needed — Tailscale's traffic doesn't go through the regular exposed ports at all.

### 3. Connect
- From any of your other devices: `ssh you@imac.your-tailnet.ts.net` — works identically whether you're home or out.
- This also means a new Claude Code session on the iMac needs nothing special beyond this: SSH in, run `claude` there like any terminal program. "Reaching Claude Code remotely" is just reaching the machine remotely — there's no separate remote-agent protocol to set up.

### 4. GUI access (since the iMac has a desktop)
- For times you want the full desktop rather than a terminal, add a remote-desktop layer over the same Tailscale connection rather than exposing it separately: the distro's built-in screen-sharing (e.g. GNOME Remote Desktop over RDP) or a VNC server (TigerVNC/x11vnc), bound so it's only reachable via the tailnet interface, same as SSH.
- This is optional and separate from the SSH path — use SSH for quick command/Claude Code work, the GUI session for anything that actually needs a screen (browser testing mydash's UI, say).

### 5. Alternative worth knowing: Tailscale SSH
Tailscale has a built-in SSH feature that uses your Tailscale identity instead of separate SSH keys, with access rules defined in the tailnet's ACL policy. It's simpler to manage (one identity, no key distribution) but less standard than running your own `sshd`. Either is fine at this scale (one person, a handful of devices) — running plain OpenSSH over the Tailscale network is the more conventional setup and what's assumed above; Tailscale SSH is a drop-in swap later if key management gets annoying.

## Explicitly not needed, given "own devices only"
- No port forwarding on the home router.
- No Dynamic DNS.
- No public-facing SSH or any exposed port.
- No VPS/bastion/reverse-proxy layer — that complexity only shows up if a non-enrolled device ever needs access, which is out of scope here.

## Security notes
- Tailscale is gated by the account you sign into it with (Google/GitHub/Microsoft, etc.) — put MFA on that account, since it's now the thing that gates access to the iMac.
- Keep the iMac's OS and SSH daemon patched. It's not internet-exposed, but it is a listening service, and "not exposed" isn't the same as "never needs updates."

## Relationship to doc 3
This doc gets *you* onto the device to develop on it. `03-server-and-sync-discussion.md` covers a separate, later question: once mydash itself runs on this iMac, how do your devices reach the *app* (as end users, via a browser) rather than you reaching the *machine* (as a developer, via SSH). Same Tailscale network can carry both, but they're different layers — don't conflate "I can SSH in" with "the Flask app is safely reachable from my phone's browser."
