# Deploy NovelClaw

This repository ships a GitHub-safe public bundle where `NovelClaw` is the main product route, while `Portal` and `MultiAgent` remain support layers around it.

## Main Route Model

- `/` -> `Portal` public entry
- `/multiagent/` -> optional `MultiAgent` support workspace
- `/claw/` -> main `NovelClaw` writing workspace

If you are deploying this stack for actual use, `/claw/` should be treated as the main application route.

## Deployment References Included

- `infra/nginx/novelclaw.current.conf`
- `infra/systemd/novelclaw-portal.service`
- `infra/systemd/novelclaw-multiagent.service`
- `infra/systemd/novelclaw.service`
- `infra/env/auth-portal.env.template`
- `infra/env/multiagent.env.template`
- `infra/env/novelclaw.env.template`

## Suggested Server Layout

```text
/opt/novelclaw/
|-- .venv/
`-- apps/
    |-- auth-portal/
    |-- multiagent/
    `-- novelclaw/

/etc/novelclaw/
|-- auth-portal.env
|-- multiagent.env
`-- novelclaw.env
```

The provided `systemd` units already expect:

- code under `/opt/novelclaw`
- env files under `/etc/novelclaw`
- the Python environment at `/opt/novelclaw/.venv`

## Suggested Deployment Flow

### 1. Upload the public-safe project files

At minimum, upload:

- `apps/`
- `infra/`
- `scripts/` if you want the helper scripts available on the server
- `README.md`, `RUN_LOCAL_WEB.md`, and `DEPLOYMENT.md` if you want operator docs on the host

Do not upload restored runtime data, local `.env` files, or private snapshots.

### 2. Create the Python environment

```bash
cd /opt/novelclaw
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip setuptools wheel
./.venv/bin/pip install -r apps/auth-portal/requirements.txt
./.venv/bin/pip install -r apps/multiagent/requirements.txt
./.venv/bin/pip install -r apps/multiagent/local_web_portal/requirements.txt
./.venv/bin/pip install -r apps/novelclaw/requirements.txt
./.venv/bin/pip install -r apps/novelclaw/local_web_portal/requirements.txt
```

### 3. Prepare real environment files

```bash
sudo mkdir -p /etc/novelclaw
sudo cp infra/env/auth-portal.env.template /etc/novelclaw/auth-portal.env
sudo cp infra/env/multiagent.env.template /etc/novelclaw/multiagent.env
sudo cp infra/env/novelclaw.env.template /etc/novelclaw/novelclaw.env
```

Then edit the copied files and fill in:

- real domain and public URLs
- session secret and encryption key
- database URLs
- API keys or provider settings
- `APP_BASE_PATH` values that match your deployed routes

### 4. Install the systemd units

```bash
sudo cp infra/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable novelclaw-portal.service
sudo systemctl enable novelclaw-multiagent.service
sudo systemctl enable novelclaw.service
sudo systemctl restart novelclaw-portal.service
sudo systemctl restart novelclaw-multiagent.service
sudo systemctl restart novelclaw.service
```

### 5. Install and adjust the Nginx route configuration

Copy `infra/nginx/novelclaw.current.conf`, then edit:

- `server_name`
- TLS certificate paths if HTTPS is enabled
- any upstream or reverse-proxy details required by your host

The provided route model already maps:

- `/` to port `8010`
- `/multiagent/` to port `8011`
- `/claw/` to port `8012`

### 6. Reload Nginx

```bash
sudo systemctl restart nginx
```

## Post-Deploy Checks

After deployment, verify:

1. `/` opens the public entry page.
2. `/claw/` opens the main NovelClaw workspace.
3. `/multiagent/` opens only if you intend to expose the support workspace.
4. API key saving, chat session creation, and run creation all work inside NovelClaw.
5. run artifacts are being written to the configured directories.

## Important Safety Notes

- Keep secrets outside the repository.
- Do not commit or upload local `.env` files created during preview.
- Do not publish runtime databases, snapshot restores, or local key material.
- Treat the repository templates as placeholders only; they do not contain production-ready values.
