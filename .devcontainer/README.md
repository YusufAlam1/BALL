# Dev Container — BALL + Claude Code

Runs the project in Docker (Python 3.12) with the **Claude Code CLI preinstalled**
and your **host Claude login reused** (no API key needed).

## Prerequisites
- Docker Desktop (running)
- VS Code with the **Dev Containers** extension (`ms-vscode-remote.remote-containers`)

## Open it
1. Open this folder in VS Code.
2. Command Palette (`Ctrl+Shift+P`) → **Dev Containers: Reopen in Container**.
3. First build installs system deps, `requirements.txt`, and Claude Code (a few minutes).

## Use Claude inside the container
Open a terminal in VS Code (it's already inside the container) and run:
```bash
claude
```
Your login is mounted from `C:\Users\<you>\.claude` on the host, so you should be
authenticated already. If not, run `claude login` once inside the container.

## Run the project
```bash
python connect.py          # quick Supabase connectivity check
jupyter notebook --ip=0.0.0.0 --no-browser   # port 8888 is forwarded
```

## Secrets
Copy `.env.example` → `.env` and fill in your Supabase / Postgres values.
`.env` is gitignored and is read by `connect.py` via `python-dotenv`.

## Notes
- `connect.py` imports `supabase`, which isn't pinned in `requirements.txt`;
  the Dockerfile installs it explicitly. Consider adding `supabase` to
  `requirements.txt` so host venvs match.
- macOS/Linux: edit `devcontainer.json` mounts, changing `USERPROFILE` → `HOME`.
