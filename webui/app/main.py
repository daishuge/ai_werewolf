from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from .game_session import SessionStore

app = FastAPI(title="AI Werewolf WebUI", version="1.0.0")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
static_dir = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

sessions = SessionStore()


class SessionMetrics(BaseModel):
    logs: int
    prompts: int
    inputsSubmitted: int


class SessionEnvelope(BaseModel):
    gameId: str
    status: str
    error: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    metrics: SessionMetrics


class InputPayload(BaseModel):
    promptId: str
    text: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/games", response_model=SessionEnvelope)
def create_game() -> SessionEnvelope:
    session = sessions.create()
    return SessionEnvelope(**session.to_dict())


@app.get("/api/games/{game_id}", response_model=SessionEnvelope)
def fetch_game(game_id: str) -> SessionEnvelope:
    try:
        session = sessions.get(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc
    return SessionEnvelope(**session.to_dict())


@app.post("/api/games/{game_id}/input")
def push_input(game_id: str, payload: InputPayload) -> dict:
    try:
        session = sessions.get(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc
    try:
        session.submit_input(payload.promptId, payload.text)
    except KeyError as exc:
        raise HTTPException(status_code=409, detail="Prompt is no longer active") from exc
    return {"status": "accepted"}


@app.get("/api/games/{game_id}/events")
def list_events(game_id: str, since: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
    try:
        session = sessions.get(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc
    return {"events": session.export_history(since)}


@app.websocket("/ws/games/{game_id}")
async def game_stream(websocket: WebSocket, game_id: str) -> None:
    await websocket.accept()
    try:
        session = sessions.get(game_id)
    except KeyError:
        await websocket.send_json({"type": "error", "message": "Game not found"})
        await websocket.close(code=4404)
        return

    subscriber, snapshot = session.subscribe()
    try:
        for event in snapshot:
            await websocket.send_json(event)

        while True:
            event = await _queue_get_async(subscriber)
            await websocket.send_json(event)
            if (
                event.get("type") == "status"
                and event.get("status") in {"completed", "failed", "aborted"}
            ):
                break
    except WebSocketDisconnect:
        pass
    finally:
        session.unsubscribe(subscriber)
if hasattr(asyncio, "to_thread"):

    async def _queue_get_async(q):
        return await asyncio.to_thread(q.get)

else:

    async def _queue_get_async(q):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, q.get)
