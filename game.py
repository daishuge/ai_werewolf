# -*- coding: utf-8 -*-
# 狼人杀第二版 · 回合循环 + 夜后判定 + 遗言公开 + 预言家仅验活人（精简输出·去除时间日志）
# 读取 .env 中的 api_key / base_url（小写），不在代码里硬编码密钥。

from openai import OpenAI
import random
import re
import datetime
from collections import defaultdict
import os
from dotenv import load_dotenv

# ------------------------------
# 全局配置
# ------------------------------
# 是否显示技术化输出（模型调用、抽取结果、内部状态等）
tech_out = True

# 调试：是否在初始化时把身份/模型打印到控制台
DEBUG_展示身份到控制台 = True

# 规则：遗言与查验约束
RULES = {
    "last_words": {
        "enabled": True,              # 开启遗言
        "audience": "alive",          # "alive"=仅在世公开，"public"=所有玩家（含已死）广播
        "night_dead_can_speak": True, # 夜死可留遗言
        "day_dead_can_speak": True,   # 白天处决可留遗言
    },
    "prophet": {
        "must_check_alive": True      # 预言家只能查验在世玩家
    }
}

# ------------------------------
# 控制台输出工具（去除时间日志）
# ------------------------------
def log(msg, *, force=False):
    if not tech_out and not force:
        return
    print(str(msg))

def big_header(title: str):
    line = "=" * 25
    print(f"{line} {title} {line}")

def small_header(title: str):
    line = "-" * 25
    print(f"{line} {title} {line}")

def thin_rule():
    print("-" * 25)

# 文本表格渲染（简洁）
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

# ------------------------------
# OpenAI 客户端初始化（从 .env 读取）
# ------------------------------
load_dotenv()
api_key = os.getenv("api_key")
base_url = os.getenv("base_url", "https://openrouter.ai/api/v1")  # 可自行更换为你的服务端地址

if not api_key:
    raise RuntimeError("未在 .env 中找到 api_key。请在项目根目录创建 .env 并添加 api_key=... 以及 base_url=...")

client = OpenAI(base_url=base_url, api_key=api_key)

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

# ------------------------------
# 玩家信息区域
# ------------------------------
villager_1 = {
    "model": "",
    "number": 0,            # 玩家座位号
    "history": [],          # 玩家上下文
    "alive": True,          # 是否存活
    "nick_name": "村民一号",
    "describe": "你是村民一号，找出并处决所有狼人。",
    "plan": "自由发挥",
    "good": True
}

villager_2 = {
    "model": "",
    "number": 0,
    "history": [],
    "alive": True,
    "nick_name": "村民二号",
    "describe": "你是村民二号，找出并处决所有狼人。",
    "plan": "自由发挥",
    "good": True
}

witch = {
    "model": "",
    "number": 0,
    "history": [],
    "alive": True,
    "nick_name": "女巫",
    "describe": "你是女巫，用药物拯救或制裁他人，助好人阵营获胜。(使用解药：save,使用毒药：kill,不行动：none)",
    "plan": "自由发挥，第一晚使用解药",
    "poison": True,     # 毒药
    "antidote": True,   # 解药
    "good": True
}

prophet = {
    "model": "",
    "number": 0,
    "history": [],
    "alive": True,
    "nick_name": "预言家",
    "describe": "你是预言家，查验身份，协助好人阵营获胜。",
    "plan": "自由发挥",
    "good": True
}

guard = {
    "model": "",
    "number": 0,
    "history": [],
    "alive": True,
    "nick_name": "守卫",
    "describe": "你是守卫。每晚可守护一名玩家（可守自己），免受狼人刀杀；不可连续两晚守同一人；可选择不守（填0）。若你守护的人同时被女巫解药救治，将发生冲突并导致该玩家死亡。",
    "plan": "自由发挥",
    "good": True
}

wolf_1 = {
    "model": "",
    "number": 0,
    "history": [],
    "alive": True,
    "nick_name": "狼人一号",
    "describe": "你是狼人一号，消灭所有好人。",
    "plan": "自由发挥",
    "good": False
}

wolf_2 = {
    "model": "",
    "number": 0,
    "history": [],
    "alive": True,
    "nick_name": "狼人二号",
    "describe": "你是狼人二号，消灭所有好人。",
    "plan": "自由发挥",
    "good": False
}

wolf_king = {
    "model": "",
    "number": 0,
    "history": [],
    "alive": True,
    "nick_name": "狼王",
    "describe": "你是狼王。你在自身出局后，可以强制带走场上一名玩家（[[座位号]]；放弃则[[0]]）。",
    "plan": "自由发挥",
    "good": False,
    "gun_used": False,  # 是否已开枪
}

player_list = [villager_1, villager_2, witch, prophet, guard, wolf_1, wolf_2, wolf_king]

# 游戏状态
game_state = {
    "night_num": 0,
    "time": "",   # "night" 或 "day"
    "die": [],
    "alive": [],
    # 守卫状态
    "guard_prev": None,     # 上一晚守护的座位号（或 None/0）
    "guard_target": None,   # 本晚守护的座位号（或 0/None）
}

# ------------------------------
# 基础功能
# ------------------------------
def get_player_by_number(seat):
    for entry in player_list:
        if str(entry["number"]) == str(seat):
            return entry
    raise ValueError(f"找不到座位号为 {seat} 的玩家")

def get_alive_players():
    return [p for p in player_list if p["alive"]]

def broadcast(role, content, target=player_list):
    for i in target:
        i["history"].append({"role": role, "content": content})

def llm(history, model, ifprint=False):
    # 精简输出：默认不打印时间，仅在 tech_out 时打印关键信息
    log(f"LLM调用 → model={model} | 消息数={len(history)}")
    response = client.chat.completions.create(
        model=model,
        messages=history,
        stream=True,
    )
    chunks = []
    try:
        for chunk in response:
            delta = chunk.choices[0].delta
            piece = getattr(delta, "content", None)
            if not piece:
                continue
            chunks.append(piece)
            if ifprint:
                print(piece, end="", flush=True)
    finally:
        if ifprint:
            print()
    text = "".join(chunks)
    log(f"LLM完成 → 输出长度={len(text)}")
    return text

# 预编译抽取正则（优化）
RE_SQ = re.compile(r"\[\[(.*?)\]\]", re.S)    # [[...]]
RE_DQ = re.compile(r"\{\{(.*?)\}\}", re.S)    # {{...}}
RE_AMP = re.compile(r"&&(.+?)&&", re.S)       # &&...&&（备用，占位）

def extract(text: str, symbol="["):
    if symbol == "[":
        pat = RE_SQ
    elif symbol == "{":
        pat = RE_DQ
    elif symbol == "&":
        pat = RE_AMP
    else:
        raise ValueError("Unsupported symbol. Use one of: '[', '{', '&'.")
    m = pat.search(text)
    return m.group(1) if m else None

def parse_dual(text: str):
    """返回 (analysis_text, target_text)（均为去壳后的内容）"""
    return extract(text, "{"), extract(text, "[")

def push(player, ifprint=False):
    model = player["model"]
    history = player["history"]
    log(f"→ 推送到 {player['number']}号（{player['nick_name']}）")
    output = llm(history, model, ifprint=ifprint)
    broadcast("assistant", output, [player])
    return output

def push_and_extract(player, ifprint=False):
    model = player["model"]
    history = player["history"]
    log(f"→ 推送并抽取到 {player['number']}号（{player['nick_name']}）")
    output = llm(history, model, ifprint=ifprint)
    broadcast("assistant", output, [player])
    val = extract(output)
    if val is None:
        log("抽取失败：未发现成对括号内容")
    else:
        log(f"抽取成功：[[{val}]]")
    return val, output

# ------------------------------
# 状态展示（无时间戳）
# ------------------------------
def print_alive_list():
    alive_seats = sorted([p["number"] for p in player_list if p["alive"]])
    log(f"在世座位：{alive_seats if alive_seats else '（全灭）'}")

def print_dead_list():
    if game_state["die"]:
        log(f"当夜死亡：{sorted(game_state['die'])}")
    else:
        log("当夜死亡：无（平安夜）")

def print_player_mapping(debug_show_role=True):
    pub = sorted([(p["number"], p["nick_name"]) for p in player_list], key=lambda x: x[0])
    for seat, nick in pub:
        log(f"{seat}号 ← {nick}")
    if debug_show_role:
        log("（DEBUG）身份/模型：")
        for p in sorted(player_list, key=lambda x: x["number"]):
            camp = "好人" if p["good"] else "坏人"
            log(f"{p['number']}号 {p['nick_name']} | 阵营={camp} | 模型={p['model']}")
    print_alive_list()

    rows = []
    for p in sorted(player_list, key=lambda x: x["number"]):
        camp = "好人" if p["good"] else "坏人"
        rows.append([p["number"], p["nick_name"], camp, p["model"]])
    print()
    draw_table(["座位", "角色", "阵营", "模型"], rows)

# ------------------------------
# 构建每个玩家的个性化prompt与座位号和模型
# ------------------------------
def init_player():
    game_state["alive"] = []
    one_to_n = list(range(1, len(player_list) + 1))
    random.shuffle(one_to_n)

    models = list(model_list)
    for i in player_list:
        seat_num = one_to_n.pop()
        i["number"] = seat_num
        game_state["alive"].append(seat_num)

        model = random.choice(models)
        models.remove(model)
        i["model"] = model

        camp = "好人" if i["good"] else "坏人"

        global_prompt = f"""
你是一名狼人杀玩家。
你的输出必须严格遵守以下规则：

1. 每次输出必须包含两部分：
    - 分析部分：放在一对大括号内，例如：{{{{分析内容}}}}
    - 目标部分：放在一对中括号内，例如：[[目标内容]]

2. 输出中 **只能** 包含这两种括号的内容，不能输出任何其他文字或符号，不得使用markdown。

3. 分析和发言必须使用自然、日常的语言表达。
   不要使用狼人杀术语（如“边缘位”“倒钩”“身份逻辑”“警徽流”等），
   也不要用逻辑推理类表达（如“根据信息量”“推断概率”“行为学分析”等）。
   说话方式要像真实玩家在聊天，不要像解说员或分析师。

【目标部分说明】
目标可能是：
- 座位号：[[1]]
- 遗言：[[我前一晚死掉了，我认为五号玩家嫌疑很大...]]
- 发言：[[我认为三号玩家是狼，因为他之前一直污蔑我这个好人]]
- 女巫用药：[[save]]
- 收到信息：[[收到]]

【身份信息】
- 你的玩家编号：{seat_num}
- 你的角色：{i["nick_name"]}
- 你的阵营：{camp}
- 你的目标：{i["describe"]}
- 你的策略：{i["plan"]}
"""
        broadcast("system", global_prompt, [i])

    small_header("初始化")
    print_player_mapping(DEBUG_展示身份到控制台)

# ------------------------------
# 胜负判定
# ------------------------------
def check_victory():
    alive = get_alive_players()
    wolves = [p for p in alive if not p["good"]]
    goods = [p for p in alive if p["good"]]
    if len(wolves) == 0:
        small_header("游戏结束")
        log("胜负 → 好人阵营获胜！")
        broadcast("user", "游戏结束：好人阵营获胜！")
        return "good"
    if len(wolves) >= len(goods):
        small_header("游戏结束")
        log("胜负 → 狼人阵营获胜！")
        broadcast("user", "游戏结束：狼人阵营获胜！")
        return "wolf"
    return None

# ------------------------------
# 公共：遗言
# ------------------------------
def last_words(dead_players, audience="alive"):
    if not RULES["last_words"]["enabled"]:
        return
    if not dead_players:
        return

    small_header("遗言环节")
    recips = get_alive_players() if audience == "alive" else player_list
    for p in dead_players:
        broadcast("user", "你已死亡，请在目标部分 [[遗言]] 中发表简短遗言给大家。", [p])
        val, _out = push_and_extract(p)
        text = (val or "").strip() or "（无遗言）"
        msg = f"{p['number']}号 的遗言：{text}"
        broadcast("user", msg, recips)
        log(f"遗言 → {msg}")

# ------------------------------
# 守卫行动
# ------------------------------
def guard_play():
    small_header("守卫行动")
    guard_p = next((p for p in player_list if p["nick_name"] == "守卫"), None)
    if (guard_p is None) or (not guard_p["alive"]):
        log("守卫不在场或已死亡，跳过守卫阶段。")
        game_state["guard_target"] = None
        return None

    alive_seats = [x["number"] for x in get_alive_players()]
    prev = game_state["guard_prev"]
    hint_prev = f"{prev}号" if prev else "无"
    msg = (
        f"请选择本晚守护对象（在世：{sorted(alive_seats)}）。可守自己；"
        f"不可连续两晚守同一人（上一晚：{hint_prev}）。不守请输入 [[0]]。"
        f"在目标部分仅填 [[座位号]] 或 [[0]]。"
    )
    broadcast("user", msg, [guard_p])
    s, _ = push_and_extract(guard_p)

    def _parse(s):
        try:
            return int((s or "").strip())
        except:
            return None

    pick = _parse(s)
    if pick == 0:
        log("守卫选择：不守护")
        game_state["guard_target"] = 0
        game_state["guard_prev"] = None
        return 0

    if (pick in alive_seats) and (pick != (prev or -1)):
        game_state["guard_target"] = pick
        game_state["guard_prev"] = pick
        log(f"守卫守护 → {pick}号")
        return pick

    log(f"守卫提交非法目标({s})，视为不守护。")
    game_state["guard_target"] = 0
    game_state["guard_prev"] = None
    return 0

# ------------------------------
# 狼人行动（定制化输出 + 表格）
# ------------------------------
def wolf_play():
    """
    流程：
      1) 在世狼人各自给出建议（{{分析}} + [[座位号]])
      2) 随机选一名狼人作为最终决策者（若无人提交有效目标，则在在世狼人中任意选择）
      3) 决策者基于简报给出最终 [[座位号]]
    返回：被刀的玩家字典或 None
    """
    small_header("狼人回合")
    wolves = [p for p in player_list if ("狼" in p["nick_name"]) and p["alive"]]
    if not wolves:
        log("无在世狼人，跳过狼人阶段。")
        return None

    seats_text = "、".join(f'{p["number"]}号' for p in wolves)
    alive_nums_sorted = sorted([p["number"] for p in get_alive_players()])
    log(f"提示 → 狼人玩家：{seats_text}，请先分别给出建议刀口（在世可选：{alive_nums_sorted}）。")
    broadcast("user",
              f"狼人玩家：{seats_text}，今晚先各自给出建议刀口（请用{{分析}}与[[座位号]]；必须从在世座位中选择：{alive_nums_sorted}）。",
              wolves)

    proposals = []  # [{wolf_seat, role, model, target, analysis}]
    alive_nums = set(alive_nums_sorted)

    first_block = True
    for w in wolves:
        seat_str_output = push(w, ifprint=False)
        analysis, seat_str = parse_dual(seat_str_output)

        if not first_block:
            thin_rule()
        first_block = False

        # 展示 LLM 原始两段
        print(f"{{{analysis or ''}}}\n")
        print(f"[[{seat_str or ''}]]\n")

        try:
            pick = int((seat_str or "").strip())
        except:
            pick = None

        if pick in alive_nums:
            proposals.append({
                "wolf_seat": w["number"],
                "role": w["nick_name"],
                "model": w["model"],
                "target": pick,
                "analysis": (analysis or "").strip().replace("\n", " "),
            })
            log(f"狼人 {w['number']}号 建议 → {pick}号")
        else:
            proposals.append({
                "wolf_seat": w["number"],
                "role": w["nick_name"],
                "model": w["model"],
                "target": "非法/空",
                "analysis": (analysis or "").strip().replace("\n", " "),
            })
            log(f"警告：狼人 {w['number']}号 提交了非法建议({seat_str})")

    rows = []
    for item in proposals:
        rows.append([
            item["wolf_seat"],
            item["role"],
            item["model"],
            item["target"],
            (item["analysis"][:60] + "…") if len(item["analysis"]) > 60 else item["analysis"]
        ])
    draw_table(["狼座位", "角色", "模型", "建议目标", "分析(截断)"], rows)

    valid_deciders = [get_player_by_number(i["wolf_seat"]) for i in proposals if isinstance(i["target"], int)]
    if not valid_deciders:
        valid_deciders = list(wolves)  # 兜底：若无人给出有效目标，任意狼人做最终决策
    decider = random.choice(valid_deciders)

    log(f"最终决策者 → {decider['number']}号（{decider['nick_name']}）")
    summary = "; ".join([f"{i['wolf_seat']}→{i['target']}" for i in proposals if isinstance(i['target'], (int, str))])
    if not summary:
        summary = "无队友建议"

    broadcast(
        "user",
        f"队友建议汇总：{summary}。请你作为最终决策者，选择今晚的最终刀口（在世座位：{alive_nums_sorted}），目标部分仅填 [[座位号]]；若放弃则填 [[0]]。",
        [decider],
    )
    final_pick_str_output = push(decider, ifprint=False)
    decider_analysis, final_pick_str = parse_dual(final_pick_str_output)

    thin_rule()
    print(f"{{{decider_analysis or ''}}}\n")
    print(f"[[{final_pick_str or ''}]]\n")

    try:
        final_pick = int((final_pick_str or "").strip())
    except:
        final_pick = 0

    if final_pick == 0:
        log("狼队选择本夜放弃击杀。")
        rows2 = []
        for item in proposals:
            rows2.append([
                item["wolf_seat"],
                item["role"],
                item["model"],
                item["target"],
                ""
            ])
        draw_table(["狼座位", "角色", "模型", "建议目标", "最终刀口"], rows2)
        return None

    if final_pick not in alive_nums:
        log(f"最终刀口非法（{final_pick}不在在世列表），视为放弃。")
        rows2 = []
        for item in proposals:
            rows2.append([
                item["wolf_seat"],
                item["role"],
                item["model"],
                item["target"],
                "非法"
            ])
        draw_table(["狼座位", "角色", "模型", "建议目标", "最终刀口"], rows2)
        return None

    chosen_player = get_player_by_number(final_pick)
    log(f"狼队最终刀口确定 → {chosen_player['number']}号（由 {decider['number']}号 决定）")

    rows2 = []
    for item in proposals:
        rows2.append([
            item["wolf_seat"],
            item["role"],
            item["model"],
            item["target"],
            f"{chosen_player['number']}号" if isinstance(item["target"], int) and item["wolf_seat"] == decider["number"] else ""
        ])
    draw_table(["狼座位", "角色", "模型", "建议目标", "最终刀口"], rows2)

    return chosen_player

# ------------------------------
# 女巫行动（毒杀解析健壮化）
# ------------------------------
def witch_play(wolves_target):
    small_header("女巫行动")
    witch_player = next((p for p in player_list if p["nick_name"] == "女巫"), None)
    if (witch_player is None) or (not witch_player["alive"]):
        log("女巫不在场或已死亡，跳过女巫阶段。")
        return "none"

    if wolves_target and wolves_target["alive"]:
        log(f"女巫看到刀口：{wolves_target['number']}号")
        if witch_player.get("antidote", False):
            log("女巫拥有解药。可选：save / kill / none")
            broadcast("user", f"狼人打算击杀 {wolves_target['number']}号。请选择是否用药（save/kill/none）", [witch_player])
            choice, _ = push_and_extract(witch_player)
        else:
            log("女巫无解药，仅可考虑毒/放弃。可选：kill / none")
            broadcast("user", "你没有解药。是否使用毒药？（kill/none）", [witch_player])
            choice, _ = push_and_extract(witch_player)
    else:
        log("本夜无刀口信息或目标已不在存活，女巫可考虑毒/放弃。可选：kill / none")
        broadcast("user", "今晚无人可救。是否使用毒药？（kill/none）", [witch_player])
        choice, _ = push_and_extract(witch_player)

    c = (choice or "").strip().lower()
    log(f"女巫选择 → {c if c else '（空）'}")

    if c == "save" and wolves_target and witch_player.get("antidote", False) and wolves_target["alive"]:
        witch_player["antidote"] = False
        log(f"女巫使用解药拯救 {wolves_target['number']}号")
        return "saved"

    if c == "kill" and witch_player.get("poison", False):
        broadcast("user", "请选择用毒药对象（输入座位号）", [witch_player])
        pos_str, _ = push_and_extract(witch_player)
        try:
            pos_int = int((pos_str or "").strip())
        except:
            pos_int = None
        if pos_int is not None:
            try:
                t = get_player_by_number(pos_int)
            except Exception:
                t = None
            if t and t["alive"]:
                t["alive"] = False
                game_state["die"].append(t["number"])
                witch_player["poison"] = False
                log(f"女巫使用毒药处决 {t['number']}号")
                return "killed"
            else:
                log("女巫选中的目标无效或已死亡，毒药未生效。")
        else:
            log("女巫未提供有效毒杀目标。")

    return "none"

# ------------------------------
# 预言家行动
# ------------------------------
def prophet_play():
    small_header("预言家行动")
    prophet_p = next((p for p in player_list if p["nick_name"] == "预言家"), None)
    if (prophet_p is None) or (not prophet_p["alive"]):
        log("预言家不在场或已死亡，跳过预言家阶段。")
        return

    alive_seats = [x["number"] for x in get_alive_players()]
    broadcast("user", f"请选择预言对象（输入座位号，必须为在世玩家：{sorted(alive_seats)}）", [prophet_p])
    pos_str, _ = push_and_extract(prophet_p)
    if not pos_str:
        log("预言家未给出有效目标。")
        return

    def _parse_target(s):
        try:
            return int(s.strip())
        except:
            return None

    target_seat = _parse_target(pos_str)
    if RULES["prophet"]["must_check_alive"] and (target_seat not in alive_seats):
        log(f"预言家首选目标非法或不在世：{pos_str}")
        broadcast("user", f"该目标不在在世列表，请重新选择在世座位（{sorted(alive_seats)}）", [prophet_p])
        pos_str2, _ = push_and_extract(prophet_p)
        target_seat = _parse_target(pos_str2)
        if target_seat not in alive_seats:
            log("预言家二次仍未给出有效在世目标，跳过本夜查验。")
            return

    t = get_player_by_number(target_seat)
    camp = "好人" if t["good"] else "坏人"
    log(f"预言家查验结果 → {t['number']}号 为 {camp}")
    broadcast("user", f"对方是：{camp}，请你回复收到", [prophet_p])
    _ack, _ = push_and_extract(prophet_p)

# ------------------------------
# 狼王开枪（链式触发）
# ------------------------------
def wolf_king_chain_shoot(initial_dead_objs, phase="night"):
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

