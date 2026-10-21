# Google Calendar setup for mydash

One-time setup to let `calendar_sync.py` create/update/delete events on your calendar. Do this once per machine that runs mydash (so again later on the always-on iMac).

## 1. Create a Google Cloud project
1. Go to console.cloud.google.com and create a new project (any name, e.g. "mydash").
2. In the left menu, **APIs & Services → Library**, search "Google Calendar API", and enable it.

## 2. Configure the OAuth consent screen
1. **APIs & Services → OAuth consent screen**.
2. User type: **External** (fine for a personal single-user app).
3. Fill in the required app name/contact fields. Scopes: you don't need to add anything here manually — the app requests `.../auth/calendar` at runtime.
4. Add your own Google account under **Test users**.
5. **Important:** once set up, open the consent screen's publishing status and set it to **"In production"** (not "Testing"). You'll still see an "unverified app" warning when you sign in — that's expected and fine to click through for a personal project — but it avoids a real gotcha: apps left in "Testing" status get refresh tokens that expire after 7 days, which would silently break the sync a week after setup.

## 3. Create OAuth credentials
1. **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Desktop app**.
3. Download the resulting JSON file.
4. Rename it to `google_client_secret.json` and put it in `data/` in this repo (i.e. `data/google_client_secret.json`). That path is already gitignored (the whole `data/` folder is), same as the database.

## 4. First run
The first time `calendar_sync.py` needs the calendar (i.e. the first time you confirm an item with a due date), it will open a browser window for you to sign in and grant access, then save a `data/google_token.json` alongside the credentials — also gitignored. After that it refreshes automatically; no further sign-in needed until you revoke access or change scopes.

This step needs a real browser on the machine running mydash (it opens `localhost` to catch the redirect), so it has to happen on the Mac or the iMac itself, not purely from a phone.

## Moving to the always-on device later
Per `docs/moving/01-migration-guide.md`, `data/` moves by hand, not through git. `google_client_secret.json` and `google_token.json` can move the same way as `mydash.db` — same rules apply (copy out of band, never commit, never paste into chat).
