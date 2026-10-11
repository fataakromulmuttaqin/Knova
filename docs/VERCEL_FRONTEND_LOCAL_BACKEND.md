# Vercel frontend with a local backend

Run the React frontend on Vercel while the FastAPI backend keeps running on your
own machine. Vercel proxies every `/api` request to the machine, so the browser
only ever sees one origin.

## Why the proxy is required

The backend issues the `knova_session` cookie. If the Vercel page called the
machine directly, that cookie would be a third-party cookie: Safari blocks those
outright and Chrome blocks them in more cases each release. With the `/api`
rewrite the browser sees a single origin, the cookie stays first-party, and no
CORS preflight is needed.

The proxy also keeps the backend free of TLS setup: Cloudflare terminates HTTPS
at the tunnel.

## 1. Run the backend

```powershell
cd "C:\path\to\Knova\Ragkno"
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## 2. Expose the backend permanently with Tailscale Funnel

The backend is reachable for free, permanently, and with a trusted HTTPS
certificate through Tailscale Funnel. No account-less quick tunnel, no changing
hostname.

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" funnel --bg 8000
```

Output:

```
Available on the internet:
https://<machine>.<tailnet>.ts.net/
|-- proxy http://127.0.0.1:8000
```

`--bg` stores the configuration in the Tailscale service, so the Funnel returns
after a reboot without a login. Confirm it with:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" funnel status
```

Notes:

- The hostname is stable for the life of the tailnet. It changes only if the
  machine is renamed or removed from the tailnet.
- Funnel is available on every Tailscale plan, including the free Personal plan.
- Funnel exposes only the one proxied port to the internet. The rest of the
  tailnet stays private.
- The public DNS name resolves to the machine's `100.x.y.z` tailnet address.
  Browsers on the tailnet resolve it locally; everyone else resolves it through
  public DNS. An occasional public-DNS hiccup can make the first request fail,
  so the frontend retries failed `GET` requests (`frontend/src/api.js:25`).
- Account-less `cloudflared` quick tunnels are kept in
  `C:\path\to\tools\cloudflared.exe` as a fallback. Their hostname
  changes on every restart, so each change requires a `frontend/vercel.json`
  edit and a redeploy. Use them only for a temporary test.

## 3. Point the rewrite at the tunnel

In `frontend/vercel.json`, set the `/api/:path*` destination to your tunnel host:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://<machine>.<tailnet>.ts.net/:path*"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

Order matters. The API rewrite must come before the single-page fallback,
otherwise `/api` requests are answered with `index.html`.

## 4. Create the Vercel project

- Import the repository. Set **Root Directory** to `frontend`.
- Framework preset: Vite. Build command `npm run build`, output directory `dist`.
- Environment variable, for Production and Preview:
  `VITE_API_URL=/api`
  Vite inlines it at build time, so a redeploy is required after changing it.

Without `VITE_API_URL`, the frontend calls its own origin and receives
`index.html` instead of JSON; login and chat will fail with parse errors.

## 5. Configure the backend

Add to `Ragkno/.env` and restart the backend:

```
FRONTEND_URL=https://your-project.vercel.app
CORS_ORIGINS=https://your-project.vercel.app
GOOGLE_APP_REDIRECT_URI=https://your-project.vercel.app/api/login/google/callback
GOOGLE_REDIRECT_URI=https://your-project.vercel.app/api/auth/callback
```

`FRONTEND_URL` is added to the allowed origins automatically
(`backend/main.py:142`). Mutating requests are rejected with
`403 Origin is not allowed.` when the browser origin is absent from that list
(`backend/main.py:292`), so this step is mandatory.

Register both redirect URIs in the Google Cloud console under **Authorized
redirect URIs**. They must use the Vercel domain, not the tunnel host: the
browser has to return to the Vercel origin so the session cookie is stored
there. Redirecting through the tunnel host leaves the user logged out on the
Vercel page.

## 6. Verify

1. `https://your-project.vercel.app` renders the landing page.
2. `https://your-project.vercel.app/api/health/ready` returns
   `{"status":"ready",...}`.
3. Google or password login returns to the Vercel domain and stays logged in
   after a reload.
4. A chat question streams the answer token by token rather than appearing all
   at once.
5. Upload a small file first. See the limits below before uploading anything
   large.

## Known limits

- **Upload size.** Vercel Functions cap request and response bodies at 4.5 MB.
  A rewrite to an external origin is not a Function, and a 20 MB POST through
  the Funnel returned `422` (validation) rather than `413`, so large bodies do
  pass through in testing. Verify each large upload once; if it fails with
  `413 FUNCTION_PAYLOAD_TOO_LARGE`, send uploads straight to the Funnel host or
  serve the frontend from the Funnel host instead of Vercel.

- **Streaming.** `/query` replies with `text/event-stream`, and the frontend
  reads the body with a stream reader (`frontend/src/api.js:289`). If the proxy
  buffers the response, answers arrive in one chunk after the model finishes.
- **Availability.** The Vercel site stays online when the machine is off, but
  every `/api` request fails until the backend and the Funnel are running again.
  The Vercel Function buffers proxied responses, so a request that is queued
  while the backend is down holds the connection for up to 300 seconds before
  the frontend sees the error.

## Keeping it running on Windows

- Start the backend and cloudflared as a scheduled task (trigger: at logon, and
  restart on failure) or with a service wrapper.
- Keep the machine awake: disable sleep in the power plan, or the tunnel and the
  backend stop responding.
- Back up `KNOVA_DATA_DIR` (default `Ragkno/data`) and the Obsidian vault
  directory. All state lives on this machine.
