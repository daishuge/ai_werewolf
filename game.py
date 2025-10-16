# -*- coding: utf-8 -*-
# 狼人杀第二版 · 回合循环 + 夜后判定 + 遗言公开 + 预言家仅验活人（从 .env 读取 API）

from openai import OpenAI
import random
import re
import datetime
from collections import defaultdict
import os
from dotenv import load_dotenv

# ============================================================
# 全局配置
# ============================================================
tech_out = True
DEBUG_展示身份到控制台 = True

RULES = {
    "last_words": {
        "enabled": True,
        "audience": "alive",
        "night_dead_can_speak": True,
        "day_dead_can_speak": True,
    },
    "prophet": {
        "must_check_alive": True
    }
}

# ============================================================
# 控制台输出工具（去除时间日志）
# ============================================================

def log(msg, *, force=False):
    if not tech_out and not force:
        return
    print(str(msg))

def big_header(title: str):
    print("=" * 25 + f" {title} " + "=" * 25)

def small_header(title: str):
    print("-" * 25 + f" {title} " + "-" * 25)

def thin_rule():
    print("-" * 25)

def draw_table(headers, rows):
    widths = [len(str(h)) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(str(cell)))
    def fmt_row(row):
        return " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
    sep = "-+-".join("-" * w for w in widths)
    print(fmt_row(headers))
    print(sep)
    for r in rows:
        print(fmt_row(r))
    print()

# ============================================================
# 从 .env 读取 API Key 和 Base URL
# ============================================================
load_dotenv()
api_key = os.getenv("api_key")
base_url = os.getenv("base_url", "https://openrouter.ai/api/v1")

if not api_key:
    raise RuntimeError("未在 .env 中找到 api_key，请添加 api_key 和 base_url。")

client = OpenAI(base_url=base_url, api_key=api_key)

# ============================================================
# 模型列表
# ============================================================
model_list = [
    "openai/gpt-5",
    "google/gemini-2.5-pro",
    "x-ai/grok-4-fast",
    "anthropic/claude-sonnet-4.5",
    "deepseek/deepseek-r1-0528",
    "z-ai/glm-4.6",
    "moonshotai/kimi-k2-0905",
    "qwen/qwen3-vl-235b-a22b-thinking",
]
random.shuffle(model_list)

# ============================================================
# 玩家信息初始化
# ============================================================
villager_1 = {"nick_name": "村民一号", "describe": "你是村民一号，找出并处决所有狼人。", "good": True}
villager_2 = {"nick_name": "村民二号", "describe": "你是村民二号，找出并处决所有狼人。", "good": True}
witch = {"nick_name": "女巫", "describe": "你是女巫，用药物拯救或制裁他人。", "good": True, "poison": True, "antidote": True}
prophet = {"nick_name": "预言家", "describe": "你是预言家，查验身份协助好人。", "good": True}
guard = {"nick_name": "守卫", "describe": "你是守卫，每晚可守护一名玩家。", "good": True}
wolf_1 = {"nick_name": "狼人一号", "describe": "你是狼人一号，消灭所有好人。", "good": False}
wolf_2 = {"nick_name": "狼人二号", "describe": "你是狼人二号，消灭所有好人。", "good": False}
wolf_king = {"nick_name": "狼王", "describe": "你是狼王，出局后可带走一名玩家。", "good": False, "gun_used": False}

player_list = [villager_1, villager_2, witch, prophet, guard, wolf_1, wolf_2, wolf_king]
for p in player_list:
    p.update({"model": "", "number": 0, "history": [], "alive": True, "plan": "自由发挥"})

game_state = {"night_num": 0, "time": "", "die": [], "alive": [], "guard_prev": None, "guard_target": None}

# ============================================================
# 工具函数
# ============================================================
def get_player_by_number(seat):
    for entry in player_list:
        if entry["number"] == seat:
            return entry
    raise ValueError(f"找不到座位号为 {seat} 的玩家")

def get_alive_players():
    return [p for p in player_list if p["alive"]]

def broadcast(role, content, target=player_list):
    for i in target:
        i["history"].append({"role": role, "content": content})

# ============================================================
# LLM调用与提取
# ============================================================
def llm(history, model, ifprint=False):
    log(f"LLM调用 → model={model} | 消息数={len(history)}")
    response = client.chat.completions.create(model=model, messages=history, stream=True)
    chunks = []
    for chunk in response:
        delta = chunk.choices[0].delta
        piece = getattr(delta, "content", None)
        if piece:
            chunks.append(piece)
            if ifprint:
                print(piece, end="", flush=True)
    if ifprint:
        print()
    text = "".join(chunks)
    log(f"LLM完成 → 输出长度={len(text)}")
    return text

RE_SQ = re.compile(r"\[\[(.*?)\]\]", re.S)
RE_DQ = re.compile(r"\{\{(.*?)\}\}", re.S)

def extract(text: str):
    m = RE_SQ.search(text)
    return m.group(1) if m else None

def parse_dual(text: str):
    m1 = RE_DQ.search(text)
    m2 = RE_SQ.search(text)
    return (m1.group(1) if m1 else ""), (m2.group(1) if m2 else "")

def push_and_extract(player, ifprint=False):
    output = llm(player["history"], player["model"], ifprint)
    val = extract(output)
    broadcast("assistant", output, [player])
    return val, output

# ============================================================
# 初始化玩家
# ============================================================
def init_player():
    seats = list(range(1, len(player_list) + 1))
    random.shuffle(seats)
    models = list(model_list)
    for p in player_list:
        p["number"] = seats.pop()
        model = random.choice(models)
        models.remove(model)
        p["model"] = model
        camp = "好人" if p["good"] else "坏人"
        prompt = f"""你是一名狼人杀玩家。
你的输出必须严格包含两部分：
1. {{分析}} 内为你的思考；
2. [[目标]] 内为结论。

身份：
- 角色：{p['nick_name']}
- 阵营：{camp}
- 目标：{p['describe']}
"""
        broadcast("system", prompt, [p])
    small_header("初始化")
    for p in sorted(player_list, key=lambda x: x["number"]):
        log(f"{p['number']}号 ← {p['nick_name']} ({'好人' if p['good'] else '坏人'}) | 模型={p['model']}")

# ============================================================
# 核心流程（夜/昼回合）
# ============================================================

def check_victory():
    alive = get_alive_players()
    wolves = [p for p in alive if not p["good"]]
    goods = [p for p in alive if p["good"]]
    if not wolves:
        log("🏆 好人阵营获胜！")
        return "good"
    if len(wolves) >= len(goods):
        log("💀 狼人阵营获胜！")
        return "wolf"
    return None

def night():
    big_header(f"第{game_state['night_num']+1}夜")
    game_state["night_num"] += 1
    game_state["die"].clear()
    # 示例：这里只展示流程框架
    log("夜幕降临...（此处应调用狼人/守卫/女巫/预言家等行动）")
    return check_victory()

def day():
    small_header(f"第{game_state['night_num']}天 白天阶段")
    log("白天发言与投票阶段...")
    return check_victory()

def run_game():
    init_player()
    while True:
        if night(): break
        if day(): break

# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    run_game()
