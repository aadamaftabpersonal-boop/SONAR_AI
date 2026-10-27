# Browser end-to-end test (Build Map T8.8)

Drives the real web app against the real API in **demo mode** (nobody is phoned). It lives here,
not in `frontend/`, so the app's lockfile and Docker build are not touched.

```powershell
# terminal 1: database, migrations, example shops, API
.\tasks.ps1 db-up
cd backend; .\.venv\Scripts\alembic upgrade head; cd ..
backend\.venv\Scripts\python scripts\seed_businesses.py data\businesses.example.yaml
.\tasks.ps1 run

# terminal 2: web app
npm --prefix frontend run dev

# terminal 3: the test (first time: install the runner and its browser)
npm --prefix e2e install
npx --prefix e2e playwright install chromium
$env:SONAR_ACCESS_KEY="<the key in your .env>"
npm --prefix e2e test
```

`SONAR_WEB_URL` overrides the address (default `http://localhost:5173`). The test runs at desktop
size and at phone size (iPhone 13 viewport). The example shops have calling windows, so run it
during their hours (IST), or the search will say no shops are available.
