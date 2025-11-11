const dom = {
  logViewport: document.getElementById("logViewport"),
  promptStatus: document.getElementById("promptStatus"),
  activePromptLabel: document.getElementById("activePromptLabel"),
  playerInput: document.getElementById("playerInput"),
  inputForm: document.getElementById("inputForm"),
  submitButton: document.getElementById("submitButton"),
  startButton: document.getElementById("startButton"),
  statusBadge: document.getElementById("statusBadge"),
  clearLogButton: document.getElementById("clearLog"),
  copyTranscriptButton: document.getElementById("copyTranscript"),
  filterGroup: document.getElementById("filterGroup"),
  autoScroll: document.getElementById("autoScroll"),
  metricLogs: document.getElementById("metricLogs"),
  metricPrompts: document.getElementById("metricPrompts"),
  metricInputs: document.getElementById("metricInputs"),
  gameIdLabel: document.getElementById("gameIdLabel"),
  sessionTimer: document.getElementById("sessionTimer"),
};

const statusCopy = {
  waiting: "等待开局",
  running: "进行中",
  completed: "对局结束",
  failed: "发生错误",
  aborted: "已中止",
};

const badgeClasses = {
  waiting: "badge badge-idle",
  running: "badge badge-running",
  completed: "badge badge-done",
  failed: "badge badge-done",
  aborted: "badge badge-done",
};

const state = {
  socket: null,
  gameId: null,
  activePromptId: null,
  events: [],
  eventQueue: [],
  filters: new Set(["log", "prompt", "user", "status", "error"]),
  autoScroll: true,
  metrics: { logs: 0, prompts: 0, inputsSubmitted: 0 },
  createdAt: null,
  clockHandle: null,
  pacerHandle: null,
  syntheticSeq: 1_000_000,
};

const formatTime = (iso) => {
  if (!iso) return "--:--";
  try {
    const date = new Date(iso);
    return date
      .toLocaleTimeString("zh-CN", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
      .padStart(8, "0");
  } catch (err) {
    return "--:--";
  }
};

const escapeHtml = (text = "") =>
  text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const enhanceNarrative = (text = "") =>
  escapeHtml(text)
    .replace(/\n{2,}/g, "<br><br>")
    .replace(/\n/g, "<br>");

const isDecorativeLine = (text = "") => {
  const trimmed = text.trim();
  if (!trimmed) {
    return true;
  }
  return /^[-_=·•—]{5,}$/.test(trimmed);
};

const renderMetrics = () => {
  dom.metricLogs.textContent = state.metrics.logs ?? 0;
  dom.metricPrompts.textContent = state.metrics.prompts ?? 0;
  dom.metricInputs.textContent = state.metrics.inputsSubmitted ?? 0;
};

const stopClock = () => {
  if (state.clockHandle) {
    clearInterval(state.clockHandle);
    state.clockHandle = null;
  }
};

const startClock = () => {
  stopClock();
  if (!state.createdAt) {
    dom.sessionTimer.textContent = "00:00";
    return;
  }
  const tick = () => {
    const diff = Date.now() - state.createdAt.getTime();
    if (diff <= 0) {
      dom.sessionTimer.textContent = "00:00";
      return;
    }
    const totalSeconds = Math.floor(diff / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    dom.sessionTimer.textContent =
      hours > 0
        ? `${hours.toString().padStart(2, "0")}:${minutes
            .toString()
            .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
        : `${minutes.toString().padStart(2, "0")}:${seconds
            .toString()
            .padStart(2, "0")}`;
  };
  tick();
  state.clockHandle = window.setInterval(tick, 1000);
};

const setStatus = (status) => {
  const label = statusCopy[status] || status;
  dom.statusBadge.textContent = label;
  dom.statusBadge.className = badgeClasses[status] || "badge badge-idle";
};

const resetSessionUI = () => {
  state.events = [];
  state.eventQueue = [];
  state.metrics = { logs: 0, prompts: 0, inputsSubmitted: 0 };
  if (state.pacerHandle) {
    clearTimeout(state.pacerHandle);
    state.pacerHandle = null;
  }
  renderMetrics();
  dom.logViewport.innerHTML = "";
  dom.gameIdLabel.textContent = "——";
  dom.sessionTimer.textContent = "00:00";
  dom.activePromptLabel.textContent = "暂无";
  dom.promptStatus.textContent = "当前无需输入";
  dom.playerInput.placeholder = "等待提示...";
  clearPrompt();
};

const clearPrompt = () => {
  state.activePromptId = null;
  dom.promptStatus.textContent = "当前无需输入";
  dom.activePromptLabel.textContent = "暂无";
  dom.playerInput.value = "";
  dom.playerInput.placeholder = "等待提示...";
  dom.playerInput.disabled = true;
  dom.submitButton.disabled = true;
};

const focusPrompt = (text, promptId) => {
  state.activePromptId = promptId;
  const display = text?.trim() || "请根据提示操作";
  dom.promptStatus.textContent = display;
  dom.activePromptLabel.textContent = display;
  dom.playerInput.placeholder = "输入完按回车发送";
  dom.playerInput.disabled = false;
  dom.submitButton.disabled = false;
  dom.playerInput.focus();
};

const teardownSocket = () => {
  if (state.socket) {
    state.socket.close();
    state.socket = null;
  }
};

const renderTimeline = () => {
  const html = state.events
    .filter((evt) => state.filters.has(evt.variant))
    .map((evt) => {
      const tag = evt.label || evt.channel || evt.variant;
      return `
        <article class="timeline-entry ${evt.variant}">
          <div class="entry-meta">
            <span>${formatTime(evt.timestamp)}</span>
            <span class="entry-tag">${tag}</span>
          </div>
          <div class="entry-body">${enhanceNarrative(evt.body || "")}</div>
        </article>
      `;
    })
    .join("");
  dom.logViewport.innerHTML = html;
  if (state.autoScroll) {
    dom.logViewport.scrollTop = dom.logViewport.scrollHeight;
  }
};

const pushEvent = (event) => {
  state.events.push(event);
  renderTimeline();
};

const estimateDelay = (event) => {
  if (!event) {
    return 0;
  }
  const trimmedLength = (event.body || "")
    .replace(/\s+/g, " ")
    .trim().length;
  const isPromptish =
    event.variant === "prompt" ||
    event.variant === "status" ||
    event.variant === "error";
  const isUserInput = event.variant === "user";
  const base = isPromptish ? 140 : 280;
  const perChar = isPromptish ? 3 : 12;
  const backlog = state.eventQueue.length;
  const backlogFactor = backlog > 12 ? 0.35 : backlog > 6 ? 0.6 : 1;
  const rawDelay = base + trimmedLength * perChar;
  const minDelay = isUserInput ? 80 : 160;
  const maxDelay = isPromptish ? 800 : 2000;
  return Math.max(
    minDelay,
    Math.min(maxDelay, rawDelay * backlogFactor)
  );
};

const drainEventQueue = () => {
  if (!state.eventQueue.length) {
    state.pacerHandle = null;
    return;
  }
  const next = state.eventQueue.shift();
  pushEvent(next);
  if (!state.eventQueue.length) {
    state.pacerHandle = null;
    return;
  }
  const delay = estimateDelay(next);
  state.pacerHandle = window.setTimeout(drainEventQueue, delay);
};

const queueEvent = (event, options = {}) => {
  const { immediate = false } = options;
  if (immediate) {
    pushEvent(event);
    return;
  }
  state.eventQueue.push(event);
  if (!state.pacerHandle) {
    drainEventQueue();
  }
};

const normalizeEvent = (event) => {
  const variant = event.type || "log";
  const channel = event.channel || variant;
  const base = {
    sequence: event.sequence ?? Date.now(),
    timestamp: event.timestamp || new Date().toISOString(),
    variant,
    channel,
    label: channel,
    body: event.text || "",
  };

  switch (variant) {
    case "log":
      base.label = channel.replace(":", " · ");
      state.metrics.logs += 1;
      renderMetrics();
      break;
    case "prompt":
      base.label = "输入请求";
      base.body = event.text || "请根据提示回应";
      focusPrompt(event.text, event.promptId);
      state.metrics.prompts += 1;
      renderMetrics();
      break;
    case "prompt_ack":
      base.variant = "status";
      base.label = "输入已接收";
      base.body = "AI 已收到你的指令";
      clearPrompt();
      break;
    case "status":
      base.label = "状态";
      base.body = statusCopy[event.status] || event.status || "状态更新";
      setStatus(event.status);
      break;
    case "error":
      base.label = "系统异常";
      base.body = event.message || "引擎出现未知错误";
      break;
    default:
      break;
  }

  if (variant === "error") {
    base.variant = "error";
  }

  return base;
};

const handleEvent = (event) => {
  const normalized = normalizeEvent(event);
  if (
    normalized?.variant === "log" &&
    isDecorativeLine(normalized.body || "")
  ) {
    state.metrics.logs = Math.max(0, (state.metrics.logs ?? 0) - 1);
    renderMetrics();
    return;
  }
  queueEvent(normalized);
};

const connectSocket = (gameId) => {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(
    `${protocol}://${window.location.host}/ws/games/${gameId}`
  );
  state.socket = socket;

  socket.onmessage = (message) => {
    const data = JSON.parse(message.data);
    handleEvent(data);
  };

  socket.onclose = (evt) => {
    if (state.socket === socket) {
      state.socket = null;
    }
    const reason =
      evt.code === 1000 ? "对局连接已关闭" : "实时通道断开，请刷新页面重连";
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "status",
      label: "连接",
      body: reason,
    });
  };

  socket.onerror = () => {
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "error",
      label: "网络",
      body: "实时连接出现波动，请稍后重试",
    });
  };
};

const hydrateSession = (payload) => {
  state.gameId = payload.gameId;
  dom.gameIdLabel.textContent = payload.gameId.slice(0, 8);
  state.metrics = payload.metrics ?? state.metrics;
  renderMetrics();
  state.createdAt = payload.createdAt ? new Date(payload.createdAt) : new Date();
  startClock();
  setStatus(payload.status);
};

const startGame = async () => {
  teardownSocket();
  resetSessionUI();
  stopClock();
  setStatus("waiting");
  dom.startButton.disabled = true;
  try {
    const response = await fetch("/api/games", { method: "POST" });
    if (!response.ok) {
      throw new Error("无法创建对局");
    }
    const data = await response.json();
    hydrateSession(data);
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "status",
      label: "系统",
      body: `新的对局已创建，代号 ${data.gameId.slice(0, 8)}`,
    });
    connectSocket(data.gameId);
  } catch (error) {
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "error",
      label: "系统",
      body: error.message,
    });
    setStatus("failed");
  } finally {
    dom.startButton.disabled = false;
  }
};

const submitAnswer = async (value) => {
  if (!state.gameId || !state.activePromptId) {
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "status",
      label: "提示",
      body: "当前没有需要回答的提示",
    }, { immediate: true });
    return;
  }
  const payload = { promptId: state.activePromptId, text: value };
  try {
    const response = await fetch(`/api/games/${state.gameId}/input`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error("提示已失效或对局不存在");
    }
    state.metrics.inputsSubmitted += 1;
    renderMetrics();
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "user",
      label: "玩家",
      body: value,
    }, { immediate: true });
  } catch (error) {
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "error",
      label: "输入",
      body: error.message,
    }, { immediate: true });
  }
};

const handleFilterClick = (event) => {
  const button = event.target.closest("button[data-filter]");
  if (!button) {
    return;
  }
  const filter = button.dataset.filter;
  if (!state.filters.has(filter) && state.filters.size === 0) {
    state.filters.add(filter);
  } else if (state.filters.has(filter) && state.filters.size === 1) {
    return;
  } else if (state.filters.has(filter)) {
    state.filters.delete(filter);
    button.classList.remove("active");
    renderTimeline();
    return;
  } else {
    state.filters.add(filter);
  }
  button.classList.toggle("active");
  renderTimeline();
};

const copyTranscript = async () => {
  if (!state.events.length) {
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "status",
      label: "战报",
      body: "暂无内容可复制",
    }, { immediate: true });
    return;
  }
  if (!navigator.clipboard) {
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "error",
      label: "战报",
      body: "浏览器暂不支持一键复制",
    }, { immediate: true });
    return;
  }
  const text = state.events
    .map(
      (evt) =>
        `[${formatTime(evt.timestamp)}] ${evt.label || evt.variant} ▸ ${
          evt.body
        }`
    )
    .join("\n");
  try {
    await navigator.clipboard.writeText(text);
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "status",
      label: "战报",
      body: "整局战报已复制，可直接分享给玩家",
    }, { immediate: true });
  } catch (error) {
    queueEvent({
      sequence: state.syntheticSeq++,
      timestamp: new Date().toISOString(),
      variant: "error",
      label: "战报",
      body: "浏览器未授予复制权限",
    }, { immediate: true });
  }
};

dom.startButton.addEventListener("click", startGame);
dom.clearLogButton.addEventListener("click", () => {
  state.events = [];
  state.eventQueue = [];
  if (state.pacerHandle) {
    clearTimeout(state.pacerHandle);
    state.pacerHandle = null;
  }
  dom.logViewport.innerHTML = "";
});
dom.copyTranscriptButton.addEventListener("click", copyTranscript);
dom.autoScroll.addEventListener("change", (event) => {
  state.autoScroll = event.target.checked;
});
dom.filterGroup.addEventListener("click", handleFilterClick);

dom.inputForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = dom.playerInput.value.trim();
  if (!value) {
    return;
  }
  dom.submitButton.disabled = true;
  await submitAnswer(value);
  dom.playerInput.value = "";
});

clearPrompt();
setStatus("waiting");
renderMetrics();
