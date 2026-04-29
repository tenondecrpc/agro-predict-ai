# 06 - Export and Versioning

Once the app builds correctly in APEX, export it to commit the result
to this repository.

## Pre-export checklist

- [ ] Pages 1, 2, 4, 6 work end-to-end (mandatory for the demo).
- [ ] Pages 3 and 5 work or are gracefully degraded with a Static
      Content explaining the path.
- [ ] All REST Data Sources resolve (no 404s in the page debug).
- [ ] The `BACKEND_URL` substitution is set to `&G_BACKEND_URL.` (a
      session variable) instead of a hardcoded ngrok URL, so the
      exported app does not lock to one tunnel.
- [ ] Pages tested with a freshly seeded database.
- [ ] Markdown rendering on page 6 works (marked.js loaded).

## How to export

1. Open **App Builder** -> your application.
2. Click **Export** in the toolbar.
3. Format: **SQL Script (Default)**.
4. Build Status: **Run and Build Application**.
5. Click **Export Application**.
6. APEX downloads `f<APP_ID>.sql` (a few thousand lines).
7. Rename it `agrobuy_app.sql` and save it under
   `operations/apex/agrobuy_app.sql` in this repository.

## How to re-import (clean clone)

For a teammate or a fresh APEX workspace:

1. Open **App Builder** -> **Import**.
2. Select `agrobuy_app.sql`, type **Database Application Export**.
3. Run the script.
4. Set the application ID. Optionally rename the workspace.
5. Set the application items / substitution strings:
   - `BACKEND_URL` to the current ngrok URL.
   - `TENANT_ID`, `TEAM_ID` defaults.
6. Run the app.

## Things NOT to commit

- `.env.local`, ngrok auth tokens.
- The user's personal APEX workspace credentials.
- Application items containing real session data (the export does
  not include session state, so this is automatic).

## Demo-day version

For the actual hackathon judging, prefer a fresh export taken **right
after** the final dry-run. That guarantees the export matches what the
judges see.

After the demo, push a tag:

```bash
git tag -a hackathon-final -m "AgroBuy demo final state"
git push origin hackathon-final
```
