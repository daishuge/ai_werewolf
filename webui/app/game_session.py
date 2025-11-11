from __future__ import annotations

import importlib
import queue
import sys
import threading
import uuid
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Ensure the repository root is importable when the web server is launched
# from subdirectories so relative files (env.json, etc.) are still reachable.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GAME_MODULE = "webui.app.engine.game_engine"


class WerewolfSession:
    """Runs a single game_user session with redirected IO."""

    def __init__(self) -> None:
        self.id: str = uuid.uuid4().hex
        self.status: str = "waiting"
        self.error: Optional[str] = None
        self.history: List[Dict[str, Any]] = []
        self.created_at = self._now()
        self.updated_at = self.created_at
        self.metrics: Dict[str, int] = {
            "logs": 0,
            "prompts": 0,
            "inputsSubmitted": 0,
        }
        self._pending_inputs: Dict[str, "queue.Queue[Optional[str]]"] = {}
        self._subscribers: List["queue.Queue[Dict[str, Any]]"] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._sequence = count()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_game, daemon=True)
        self._thread.start()

    def submit_input(self, prompt_id: str, text: str) -> None:
        normalized = text.strip()
        with self._lock:
            waiter = self._pending_inputs.get(prompt_id)
        if waiter is None:
            raise KeyError(f"Prompt {prompt_id} is no longer active")
        waiter.put(normalized or "")
        self.metrics["inputsSubmitted"] += 1

    def stop(self) -> None:
        self._stop_event.set()
        self.status = "aborted"
        with self._lock:
            pending = list(self._pending_inputs.values())
            self._pending_inputs.clear()
        for waiter in pending:
            waiter.put(None)
        self._publish({"type": "status", "status": "aborted"})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gameId": self.id,
            "status": self.status,
            "error": self.error,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "metrics": dict(self.metrics),
        }

    def export_history(
        self, since_sequence: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        with self._lock:
            if since_sequence is None:
                return list(self.history)
            return [evt for evt in self.history if evt["sequence"] > since_sequence]

    def _run_game(self) -> None:
        try:
            module = importlib.reload(importlib.import_module(GAME_MODULE))
        except ModuleNotFoundError as exc:
            self.error = "找不到内置的狼人杀引擎"
            self.status = "failed"
            self._publish({"type": "error", "message": self.error})
            self._publish({"type": "status", "status": self.status})
            raise RuntimeError("game_engine 模块未找到") from exc

        runner = getattr(module, "run", None)
        if not callable(runner):
            self.error = "内置引擎缺少 run(io) 接口"
            self.status = "failed"
            self._publish({"type": "error", "message": self.error})
            self._publish({"type": "status", "status": self.status})
            return

        session = self

        class SessionIO:
            """Bridges engine IO events to the web UI session."""

            def __init__(self) -> None:
                self._buffer = ""

            def write(self, text: str) -> None:
                if text is None:
                    return
                self._buffer += str(text)
                self._drain()

            def _drain(self) -> None:
                while "\n" in self._buffer:
                    line, self._buffer = self._buffer.split("\n", 1)
                    self._emit(line)

            def _emit(self, raw: str) -> None:
                if raw is None:
                    return
                text = raw.rstrip("\r")
                trimmed = text.strip()
                if not trimmed:
                    return
                if self._is_decorative(trimmed):
                    return
                session._publish({"type": "log", "text": text})

            def flush(self) -> None:
                if self._buffer:
                    self._emit(self._buffer)
                    self._buffer = ""

            def ask(self, prompt_text: str = "") -> str:
                if session._stop_event.is_set():
                    raise RuntimeError("Session aborted")
                prompt_id = uuid.uuid4().hex
                waiter: "queue.Queue[Optional[str]]" = queue.Queue(maxsize=1)
                with session._lock:
                    session._pending_inputs[prompt_id] = waiter
                session._publish(
                    {"type": "prompt", "promptId": prompt_id, "text": prompt_text or ""}
                )
                answer = waiter.get()
                if answer is None:
                    raise RuntimeError("Session aborted")
                with session._lock:
                    session._pending_inputs.pop(prompt_id, None)
                session._publish({"type": "prompt_ack", "promptId": prompt_id})
                return answer

            @staticmethod
            def _is_decorative(text: str) -> bool:
                if len(text) < 4:
                    return False
                return set(text) <= set("_-=·•—")

        session_io = SessionIO()

        self.status = "running"
        self._publish({"type": "status", "status": self.status})

        try:
            runner(session_io)
            if self.status != "aborted":
                self.status = "completed"
                self._publish({"type": "status", "status": self.status})
        except Exception as exc:  # pylint: disable=broad-except
            if self.status != "aborted":
                self.error = str(exc)
                self.status = "failed"
                self._publish({"type": "error", "message": self.error})
                self._publish({"type": "status", "status": self.status})
        finally:
            session_io.flush()
            with self._lock:
                pending = list(self._pending_inputs.values())
                self._pending_inputs.clear()
            for waiter in pending:
                waiter.put(None)

    def _publish(self, payload: Dict[str, Any]) -> None:
        event = self._decorate_event(payload)
        with self._lock:
            self.history.append(event)
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)

    def subscribe(self) -> tuple["queue.Queue[Dict[str, Any]]", List[Dict[str, Any]]]:
        channel: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        with self._lock:
            snapshot = list(self.history)
            self._subscribers.append(channel)
        return channel, snapshot

    def unsubscribe(self, subscriber: "queue.Queue[Dict[str, Any]]") -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def _decorate_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        event = dict(payload)
        event.setdefault("timestamp", now.isoformat())
        event["sequence"] = next(self._sequence)
        event.setdefault("type", "log")
        if event["type"] == "log":
            event["channel"] = self._classify_log(event.get("text", ""))
            self.metrics["logs"] += 1
        elif event["type"] == "prompt":
            event["channel"] = self._classify_prompt(event.get("text", ""))
            self.metrics["prompts"] += 1
        elif event["type"] == "status":
            event["channel"] = f"status:{event.get('status', 'unknown')}"
        elif event["type"] == "error":
            event["channel"] = "system:error"
        self.updated_at = now
        return event

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _classify_prompt(text: str) -> str:
        lowered = text.lower()
        mapping = [
            ("计划", "prompt:plan"),
            ("plan", "prompt:plan"),
            ("default", "prompt:plan"),
            ("random", "prompt:plan"),
            ("发言", "prompt:speech"),
            ("speech", "prompt:speech"),
            ("投票", "prompt:vote"),
            ("vote", "prompt:vote"),
            ("守卫", "prompt:guard"),
            ("女巫", "prompt:witch"),
            ("毒药", "prompt:witch"),
            ("解药", "prompt:witch"),
            ("技能", "prompt:skill"),
            ("行动", "prompt:skill"),
        ]
        for keyword, channel in mapping:
            if keyword in text or keyword in lowered:
                return channel
        return "prompt:generic"

    @staticmethod
    def _classify_log(text: str) -> str:
        candidates: Iterable[tuple[str, str]] = (
            ("天亮", "phase:daybreak"),
            ("夜晚", "phase:nightfall"),
            ("夜幕", "phase:nightfall"),
            ("白天", "phase:day"),
            ("发言", "stage:speech"),
            ("遗言", "stage:last-words"),
            ("投票", "stage:vote"),
            ("公投", "stage:vote"),
            ("女巫", "skill:witch"),
            ("守卫", "skill:guard"),
            ("猎人", "skill:hunter"),
            ("狼人", "faction:wolves"),
            ("预言家", "faction:seer"),
            ("平民", "faction:villager"),
            ("胜利", "result:win"),
            ("失败", "result:loss"),
            ("存活", "status:alive"),
            ("出局", "status:dead"),
        )
        for keyword, channel in candidates:
            if keyword in text:
                return channel
        return "stage:generic"


class SessionStore:
    """Thread-safe in-memory registry for active sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, WerewolfSession] = {}
        self._lock = threading.Lock()

    def create(self) -> WerewolfSession:
        session = WerewolfSession()
        with self._lock:
            self._sessions[session.id] = session
        session.start()
        return session

    def get(self, game_id: str) -> WerewolfSession:
        with self._lock:
            session = self._sessions.get(game_id)
        if session is None:
            raise KeyError(f"Game {game_id} not found")
        return session

    def remove(self, game_id: str) -> None:
        with self._lock:
            self._sessions.pop(game_id, None)
