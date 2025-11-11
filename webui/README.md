# AI Werewolf WebUI

Self-contained FastAPI experience; all gameplay logic now lives under `webui/app/engine/game_engine.py`, so the WebUI never imports modules outside `webui/`.

## Highlights
- Real-time log stream for every night/day narration, vote, and skill resolution.
- Prompt queue clearly shows when the engine expects human input (plan selection, witch actions, speeches, votes, etc.).
- WebSocket transport delivers low-latency updates without polling.
- Dedicated session runner hot-reloads the internal engine, intercepts only that module's `print`/`input`, and multicasts events to connected browsers.

## Getting Started
1. Install dependencies from the repo root:
   ```powershell
   pip install -r webui/requirements.txt
   ```
2. Start the dev server:
   ```powershell
   uvicorn webui.app.main:app --reload
   ```
3. Visit <http://localhost:8000> and click "Start Match" to launch a game.
4. Answer prompts exactly as in the CLI (`default`, seat numbers, `0` for skip, etc.).

## Architecture
- `webui/app/engine/game_engine.py`: full Werewolf ruleset copied locally; tweak this file to change behaviors.
- `webui/app/game_session.py`: spins up engine sessions, captures logs, manages prompt/input queues, and publishes events over WebSockets.
- `webui/app/main.py`: FastAPI surface serving the REST/WebSocket APIs plus the immersive front-end located in `templates` and `static`.

## Requirements
- `env.json` (API credentials) is still read from the repository root; ensure it contains valid `base_url` and `api_key` before starting the server.
