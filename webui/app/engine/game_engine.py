from openai import OpenAI
import random
import re
import json
import builtins
from contextlib import contextmanager
from typing import Optional
with open("env.json","r",encoding="utf-8") as environment:
    env=json.load(environment)  # 读取环境配置，包含模型列表与鉴权信息

_builtin_print = builtins.print
_builtin_input = builtins.input


class EngineIO:
    """Minimal IO abstraction so the engine can target console or the web UI."""

    def write(self, text: str) -> None:
        _builtin_print(text, end="")

    def ask(self, prompt_text: str = "") -> str:
        return _builtin_input(prompt_text)


class StdoutIO(EngineIO):
    """Default IO implementation that proxies to stdout/stdin."""


_current_io: EngineIO = StdoutIO()


@contextmanager
def use_io(io: Optional["EngineIO"] = None):
    """Temporarily switch the IO target for the engine."""
    global _current_io
    previous = _current_io
    if io is not None:
        _current_io = io
    try:
        yield _current_io
    finally:
        _current_io = previous


def configure_io(io: "EngineIO") -> None:
    """Permanently set the IO target (mainly for tests)."""
    global _current_io
    _current_io = io


def _io_print(*args, **kwargs):
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    if sep is None:
        sep = " "
    if end is None:
        end = ""
    text = sep.join(str(arg) for arg in args)
    payload = f"{text}{end}"
    _current_io.write(payload)


def _io_input(prompt_text: str = "") -> str:
    return _current_io.ask(prompt_text)


# Override module-level print/input so existing game logic stays untouched.
print = _io_print  # type: ignore
input = _io_input  # type: ignore
def setup():
    """初始化全部角色信息、策略模板以及全局状态。"""
    # 读取 env.json 中可用模型列表，缺省时回退到 8 个默认模型
    model_list=env.get("model", ["x-ai/grok-4-fast"] * 8)
    # 默认模板：不给额外限制，适合自由发挥
    defaultplan={
        "name":"default",
        "v1":"自由发挥",
        "v2":"自由发挥",
        "p":"自由发挥",
        "w":"自由发挥",
        "f1":"自由发挥",
        "f2":"自由发挥",
        "f3":"自由发挥",
        "g":"自由发挥"}
    # 深度推理模板：强调思考过程与输出思维链
    complicated={
        "name":"complicated",
        "v1":"仔细研究玩家的发言，尝试找出狼的蛛丝马迹，必须深度思考，输出思考内容",
        "v2":"仔细研究玩家的发言，尝试找出狼的蛛丝马迹，必须深度思考，输出思考内容",
        "p":"仔细研究玩家的发言，尝试找出狼的蛛丝马迹，晚上运用技能找到潜在狼人，白天保持谨慎，必须深度思考，输出思考内容",
        "w":"仔细研究玩家的发言，尝试找出狼的蛛丝马迹，发挥技能解药救人，觉得是狼人之后使用毒药毒死玩家，必须深度思考，输出思考内容",
        "f1":"使用诡计，第一晚自刀骗药，与队友配合欺骗平民，杀死和票出关键玩家，混淆视听，必须深度思考，输出思考内容",
        "f2":"使用诡计，第一晚最好配合刀队友一号骗药，与队友配合欺骗平民，杀死和票出关键玩家，必须深度思考，输出思考内容",
        "f3":"使用诡计，第一晚最好配合刀队友一号骗药，与队友配合欺骗平民，杀死和票出关键玩家，被投票处决时杀死关键玩家，必须深度思考，输出思考内容",
        "g":"仔细研究玩家的发言，尝试找出狼的蛛丝马迹，守护关键玩家，白天保持谨慎，必须深度思考，输出思考内容"}
    # 轻量模板：尽量减少措辞与思考成本
    simple={
        "name":"simple",
        "v1":"自由发挥，尽量简化发言和思考",
        "v2":"自由发挥，尽量简化发言和思考",
        "p":"自由发挥，尽量简化发言和思考",
        "w":"自由发挥，尽量简化发言和思考",
        "f1":"自由发挥，尽量简化发言和思考",
        "f2":"自由发挥，尽量简化发言和思考",
        "f3":"自由发挥，尽量简化发言和思考",
        "g":"自由发挥，尽量简化发言和思考"}
    # 谨慎模板：适合保守玩家
    cautious={
        "name":"cautious",
        "v1":"谨慎发言",
        "v2":"谨慎发言",
        "p":"谨慎发言",
        "w":"谨慎发言",
        "f1":"谨慎发言",
        "f2":"谨慎发言",
        "f3":"谨慎发言",
        "g":"谨慎发言"}
    # 激进模板：鼓励主动发言（仍需注意伪装）
    bold={
        "name":"bold",
        "v1":"大胆发言",
        "v2":"大胆发言",
        "p":"大胆发言",
        "w":"大胆发言",
        "f1":"大胆发言，不过不要显得带节奏",
        "f2":"大胆发言，不过不要显得带节奏",
        "f3":"大胆发言，不过不要显得带节奏",
        "g":"大胆发言"}
    # 迷惑模板：通过伪装不同身份扰乱视角
    crazy={
        "name":"crazy",
        "v1":"混淆视听，伪装成女巫，防止狼人把女巫刀掉",
        "v2":"混淆视听，伪装成守卫，防止狼人把真守卫刀掉",
        "p":"混淆视听，伪装成平民，防止被狼人刀掉",
        "w":"混淆视听，伪装成预言家，防止被狼人刀掉",
        "f1":"混淆视听，伪装成女巫，防止被好人阵营识破并票出局",
        "f2":"混淆视听，伪装成预言家，防止被好人阵营识破并票出局",
        "f3":"混淆视听，伪装成守卫，防止被好人阵营识破并票出局",
        "g":"混淆视听，伪装成平民，防止被狼人刀掉"}
    # 汇总所有策略模板，按名称或随机进行分配
    plans=[defaultplan,complicated,simple,cautious,bold,crazy]
    # 以下定义 8 名角色的初始信息与个性提示
    v1 = {
            "alive": True,
            "history":[],
            "number": 0,
            "role_name": "村民1",
            "role_instruction": "你是普通村民，没有夜间技能，白天通过发言和投票找出狼人",
            "suggestion":"你可以大胆发言",
            "plan":"",
            "model":"",
            "code":"v1",
            "isuser":False
    }
    v2 = {
            "alive": True,
            "history":[],
            "number": 0,
            "role_name": "村民2",
            "role_instruction": "你是普通村民，没有夜间技能，白天通过发言和投票找出狼人",
            "suggestion":"你可以大胆发言",
            "plan":"",
            "model":"",
            "code":"v2",
            "isuser":False
    }
    p = {
            "alive": True,
            "history":[],
            "number": 0,
            "role_name": "预言家",
            "role_instruction": "你每晚可以随机查验一名玩家阵营，在白天合理分享信息，通过投票打败狼人",
            "suggestion":"你可以发言透露身份，便于神职和平民的合作。第一夜建议随机选择要验的玩家",
            "plan":"",
            "model":"",
            "code":"p",
            "isuser":False
    }
    w = {
            "alive": True,
            "poison": True,
            "antidote": True,
            "history":[],
            "number": 0,
            "role_name": "女巫",
            "role_instruction": "你拥有一瓶解药和一瓶毒药每种，最多使用一次",
            "suggestion":"你可以发言透露身份，便于神职和平民的合作。女巫是可以用解药自救的。确认身份后可以大胆使用毒药。第一夜不太可能是狼人自刀",
            "plan":"",
            "model":"",
            "code":"w",
            "isuser":False
    }
    f1 = {
            "alive": True,
            "history":[],
            "number": 0,
            "role_name": "狼人1",
            "role_instruction": "你与另一名狼人和一名狼王协同作战，夜间选择击杀目标，白天需要隐藏身份",
            "suggestion":"第一夜建议随机选择或自刀和刀队友。发言阶段可以伪装成预言家来骗玩家，尽量配合队友欺骗平民票出神职，也建议自刀来骗女巫和平民。别忘了发言顺序，不要乱说没发言的玩家发言很怪",
            "plan":"",
            "model":"",
            "code":"f1",
            "isuser":False
    }
    f2 = {
            "alive": True,
            "history":[],
            "number": 0,
            "role_name": "狼人2",
            "role_instruction": "你与另一名狼人和一名狼王协同作战，夜间选择击杀目标，白天需要隐藏身份",
            "suggestion":"第一夜建议随机选择或自刀和刀队友。发言阶段可以伪装成预言家来骗玩家，尽量配合队友欺骗平民票出神职，也建议自刀来骗女巫和平民。别忘了发言顺序，不要乱说没发言的玩家发言很怪",
            "plan":"",
            "model":"",
            "code":"f2",
            "isuser":False
    }
    f3 = {
            "alive": True,
            "history":[],
            "number": 0,
            "role_name": "狼王",
            "role_instruction": "你与两名狼人协同作战，夜间选择击杀目标，白天需要隐藏身份。当你在白天被票出局时，杀死一位玩家。",
            "suggestion":"第一夜建议随机选择或自刀和刀队友。发言阶段可以伪装成预言家来骗玩家，尽量配合队友欺骗平民票出神职，也建议自刀来骗女巫和平民。别忘了发言顺序，不要乱说没发言的玩家发言很怪",
            "plan":"",
            "model":"",
            "code":"f3",
            "isuser":False
    }
    g = {
            "alive": True,
            "history":[],
            "number": 0,
            "role_name": "守卫",
            "role_instruction": "你每晚可以守卫一位玩家，连续两晚守卫的玩家不能重复。假如守卫和女巫同时守/救狼人刀的对象，目标仍旧死亡",
            "suggestion":"第一晚建议守自己。你可以发言透露身份，便于神职和平民的合作",
            "plan":"",
            "model":"",
            "code":"g",
            "isuser":False
    }
    player_list = [v1,v2,p,w,f1,f2,f3,g]
    # game_state 记录夜间行动及能量冷却等信息，贯穿整局游戏
    game_state={
        "nights":1,
        "witchtarget":"0",
        "wolftarget":"0",
        "protect":"0",
        "save":False,
        "tonight_dead":[],
        "prev":"0"
    }
    return model_list,game_state,plans,player_list
# 解包 setup 结果，方便全局函数直接引用共享状态
# 解包 setup 结果，方便全局函数直接引用共享状态
[model_list,game_state,plans,player_list]=setup()
# 建立按身份命名的引用，减少后续查找成本
v1=player_list[0]
v2=player_list[1]
p=player_list[2]
w=player_list[3]
f1=player_list[4]
f2=player_list[5]
f3=player_list[6]
g=player_list[7]
def utilities():
    """封装界面输出与通用工具函数，便于后续调用。"""
    def table():
        """打印当前编号与阵营对照表。"""
        print("Number |Character |Faction |Model")
        # 逐号遍历，确保输出顺序与座位一致
        for i in range(1,9,1):
            for player in player_list:
                if player["number"]==i:
                    if player==f1 or player==f2:
                        Role="Wolf      "
                        Faction="Bad     "
                    elif player==f3:
                        Role="Wolf king "
                        Faction="Bad     "
                    elif player==v1 or player==v2:
                        Role="Villager  "
                        Faction="Good    "
                    elif player==g:
                        Role="Guard     "
                        Faction="Good    "
                    elif player==p:
                        Role="Prophet   "
                        Faction="Good    "
                    elif player==w:
                        Role="Witch     "
                        Faction="Good    "
                    print(f"{player['number']}      |{Role}|{Faction}|{player['model']}")
    def title(input,sub=True):
        """输出统一格式的标题，sub=False 表示一级标题。"""
        if sub:
            sepp="-"*20
        else:
            sepp="="*25
            print()
        print(f"{sepp}{input}{sepp}\n")
    def sep(long=False):
        """输出空行间隔，避免在 Web UI 中出现冗余的下划线分割线。"""
        flag = long
        if isinstance(long, str):
            flag = long.lower() in {"long", "full", "double"}
        else:
            flag = bool(long)
        print()
        if flag:
            print()
    # empty 作为 prompt 接口返回的占位玩家，编号 0 对应该对象
    empty={}
    def index(number):                                       #number:str
        """根据座位号获取玩家对象，当 number 为 0 时返回 empty。"""
        # 顺序遍历列表以找到对应编号
        # individual 模式：逐个玩家选择计划
        for player in player_list:
            if player['number']==int(number):
                return player
        # 约定输入 0 表示不选择任何玩家
        if number=="0":
            return empty
        else:
            raise ValueError(f"There is no player with number {number}")
    def get_player_by_number(seat):
        """按编号查询玩家，若不存在则抛出异常。"""
        # 允许 seat 传入字符串或整数
        for entry in player_list:
            if str(entry['number']) == str(seat):
                return entry
        if seat!=0:
            raise ValueError(f"找不到座位号为 {seat} 的玩家")
    def llm(history, model, ifprint=True):
        """统一封装 LLM 调用流程，支持是否回显输出。"""
        response = client.chat.completions.create(
            model=model,
            messages=history,
            stream=True,
        )
        # 收集流式返回的内容片段，便于统一写入历史记录
        chunks = []
        try:
            for chunk in response:
                delta = chunk.choices[0].delta
                piece = getattr(delta, "content", None)
                if not piece:
                    continue
                chunks.append(piece)
                # 如需调试，可打开 ifprint 以实时查看输出
                if ifprint:
                    print(piece, end="", flush=True)
        finally:
            if ifprint:
                print()
        return "".join(chunks)
    def assign(role,content,tar=player_list):                #tar:list of dict
        """批量写入历史消息，方便上下文持续积累。"""
        # tar 允许传入任意子集，便于只向特定玩家广播
        for i in tar:
            i["history"].append({"role":role,"content":content})
    def out(ifprint,ifsep,play,spacing="short"):                 #play:dict
        """触发模型输出，并在需要时追加分隔线。"""
        # 模型调用统一走 llm，保证历史上下文一致
        res = llm(play["history"],play["model"],False)
        assign("assistant",res,[play])
        if False:
            print(res)
        if ifsep:
            sep(spacing)
        return res
    def out_extract(ifprint,ifsep,play,spacing="short"):         #play:dict
        """从模型回复中提取 [[...]] 内的任意内容（含空格/标点/中文/换行）。"""
        trials=1
        m=[]
        while trials!=3:
            try:
                reply = out(ifprint,ifsep,play,spacing)
                # ??? [[...]] ??????????????????
                m = re.search(r"\[\[\s*(.+?)\s*\]\]", reply, flags=re.S)  # DOTALL 非贪婪
                break
            except:
                trials+=1
        if not m and m!=0:
            raise ValueError(f"{play['role_name']}：未在输出中找到[[...]]格式的内容")
        return m.group(1)
    def prompt(inputt,player,respond=True,ifsep=False,sepifuser=False):                   #player:list of dict
        """统一的人机/模型交互入口，负责提示与结果收集。"""
        for p in player:
            # 区分真人与 AI，真人走命令行交互，AI 追加到 prompt 历史
            if p["isuser"]==True:
                if sepifuser:
                    sep()
                if respond:
                    targ=input(f"{inputt}：")
                else:
                    targ="0"
                    print(inputt)
            else:
                # 对于 AI 玩家，将输入描述写入历史并要求 [[...]] 输出格式
                assign("user",f"{inputt}，回答的内容一定要放在[[]]中：",[p])
                if respond:
                    targ=out_extract(False,False,p)
                else:
                    targ="0"
                    assign("assistant","",[p])
        if ifsep:
            sep()
        return targ
    def broadcast(input,ifprint=False):
        """面向所有玩家的公告通道，默认不回显。"""
        # 默认静默广播给所有玩家，除非外部要求回显
        prompt(input,player_list,False,False,False)
        if False:
            print(input)
    return table,title,sep,index,get_player_by_number,llm,assign,out,out_extract,prompt,broadcast
[table,title,sep,index,get_player_by_number,llm,assign,out,out_extract,prompt,broadcast]=utilities()
def initiation():
    """初始化客户端、分配计划并注入角色提示词。"""
    api = env["api_key"]
    url = env["base_url"]
    global client
    client = OpenAI(
        base_url=url,
        api_key=api,
    )
    title("初始化",False)
    selectedplan=input("选择玩家的计划: ")
    # 根据输入的模式分支，决定如何为各角色配置计划
    if selectedplan=="individual":
        for player in player_list:
            playerplan=input(f"选择{player['role_name']}玩家的计划: ")
            canfind=False
            for plan in plans:
                if plan["name"]==playerplan:
                    canfind=True
                    player["plan"]=plan[player["code"]]
            if not canfind:
                player["plan"]=plans[0][player["code"]]
    elif selectedplan=="random":
        # 每位玩家随机抽取一个模板，便于快速开局
        for player in player_list:
            player["plan"]=random.choice(plans)[player["code"]]
            print(player["code"],player["plan"])
    elif selectedplan=="custom":
        # 完全自定义文本，允许在运行期快速调参
        for player in player_list:
            player["plan"]=input(f"选择{player['role_name']}玩家的计划: ")
    else:
        # 兜底分支：若输入名称无效，则统一使用 default 计划
        canfind=False
        for plan in plans:
            if plan["name"]==selectedplan:
                canfind=True
                for player in player_list:
                    player["plan"]=plan[player["code"]]
        if not canfind:
            for player in player_list:
                player["plan"]=plans[0][player["code"]]
    print()
    # 将模型顺序打乱，避免固定映射导致策略固化
    random.shuffle(model_list)
    id=1
    randomlist=player_list
    # 再对玩家列表洗牌，从而随机绑定模型
    random.shuffle(randomlist)
    for model in model_list:
        player=randomlist[id-1]
        player["model"]=model
        player["number"]=id
        id+=1
    # 随机指定真人玩家的座位编号
    usernumber=random.randint(1,8)
    for player in player_list:
        if player["number"]==usernumber:
            player["isuser"]=True
            prompt(f"你的身份是：{player['role_name']}",[player],False)
    print(f"你的代号：{usernumber}")
    print()
    # 初始化每名角色的 system prompt，保证开局共识一致
    for i in player_list:
        num = i["number"]
        role_name = i.get("role_name", "未知身份")
        role_instruction = i.get("role_instruction", "")
        suggestion=i.get("suggestion","")
        plann=i.get("plan","自由发挥")
        promptt = f'''你是一个狼人杀玩家，你将参与一场狼人杀对局，想尽一切办法获胜
                    我们标准配置有8名玩家：两名村民，一名预言家，一名女巫，两个狼人，一个狼王，一个守卫
                    总共有8位玩家，请使用玩家编号互相称呼
                    编号和角色的对应顺序将会打乱，不按照任何规律
                    特别注意：一晚上守卫和女巫同时守和就一位玩家则玩家仍旧死亡
                    你的编号是：{num}
                    你的身份是：{role_name}
                    {role_instruction}
                    建议：{suggestion}
                    你的计划：{plann}
                    你应当每回合输出分析，放在两个大括号'''+"{{}}"+'''中，这里面的内容只会被你自己阅读
                    你的最终的结果（玩家代号或者选择或药水选择或遗言或收到），尤其注意白天发言，以上内容务必放在[[]]像这样的两个中括号中
                    例如
                    [[1]]
                    确保它没有任何其他内容
                    在无需目标的情况下，例如遗言，讨论，你不能输出这个内容
                    你的语言应该不那么专业，保持普通人的能力即可，可以结合计划展现一定程度的个性，不要过于格式化。不要盲目认为发言谨慎的玩家就是狼人
                    白天发言不要过于格式化，尽量不要以“大家好，我是……号玩家”开头，可以自由一点'''
        i["history"].append({"role":"system","content":promptt})
def wolf():
    """处理狼人阵营夜间的击杀目标协商逻辑。"""
    def rechoose(wolf1,wolf2,wolftarget1,wolftarget2):
        """在仅剩两名狼人时重新确认最终刀人。"""
        if wolftarget1==wolftarget2:
            wolftarget=wolftarget1
        else:
            r=random.randint(1,2)
            if r==1:
                wolftarget=prompt(f"你的队友选了{wolftarget2}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号",[wolf1],True,False,True)
            if r==2:
                wolftarget=prompt(f"你的队友选了{wolftarget1}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号",[wolf2],True,False,True)
        return wolftarget
    # 统计当前仍可参与决策的狼人数量
    deadwolf=0
    if game_state["nights"]==1:
        # 第一个夜晚互相报号，帮助 AI 建立阵营共识
        prompt(f"你的另外两个队友的代号：{f2['number']}和{f3['number']}\n",[f1],False)
        prompt(f"你的另外两个队友的代号：{f1['number']}和{f3['number']}\n",[f2],False)
        prompt(f"你的另外两个队友的代号：{f1['number']}和{f2['number']}\n",[f3],False)
    # 依次询问每名狼人今晚的刀人选择
    if f1["alive"]:
        target1=prompt("狼人请睁眼，今晚你要刀谁？请回答玩家编号",[f1])
    else:
        target1="0"
        deadwolf+=1
    if f2["alive"]:
        target2=prompt("狼人请睁眼，今晚你要刀谁？请回答玩家编号",[f2])
    else:
        target2="0"
        deadwolf+=1
    if f3["alive"]:
        target3=prompt("狼人请睁眼，今晚你要刀谁？请回答玩家编号",[f3])
    else:
        target3="0"
        deadwolf+=1
    # 根据存活狼人数量，决定如何得出最终刀人
    if deadwolf==0:
        if target1==target2 and target1==target3:
            game_state["wolftarget"]=target1
        else:
            r=random.randint(1,3)
            if r==1:
                game_state["wolftarget"]=prompt(f"你的队友选了{target2}和{target3}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号",[f1],True,False,True)
            if r==2:
                game_state["wolftarget"]=prompt(f"你的队友选了{target1}和{target3}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号",[f2],True,False,True)
            if r==3:
                game_state["wolftarget"]=prompt(f"你的队友选了{target1}和{target2}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号",[f3],True,False,True)
    elif deadwolf==1:
        if target1=="0":
            game_state["wolftarget"]=rechoose(f2,f3,target2,target3)
        if target2=="0":
            game_state["wolftarget"]=rechoose(f1,f3,target1,target3)
        if target3=="0":
            game_state["wolftarget"]=rechoose(f1,f2,target1,target2)
    elif deadwolf==2:
        if target1!="0":
            game_state["wolftarget"]=target1
        elif target2!="0":
            game_state["wolftarget"]=target2
        elif target3!="0":
            game_state["wolftarget"]=target3
    else:
        game_state["wolftarget"]="0"
    # 将最终决定同步给仍存活的狼人，方便后续行动串联
    prompt(f"\n狼人最终选择刀{game_state['wolftarget']}号玩家",[f1,f2,f3],False)
def witch():
    """执行女巫夜间的解药与下毒决策。"""
    # 每个夜晚都需要重置女巫技能的临时状态
    # 每晚开始前重置状态，以免上一晚遗留干扰
    game_state["save"]=False
    action=""
    poison=""
    if w["alive"]:
        prompt("女巫请睁眼",[w],False)
        if not(w["poison"] or w["antidote"]):
            prompt("你没有药了",[w],False)
        if w["antidote"]==True and game_state["wolftarget"]!="0":
            # 女巫优先判断是否救人，save 标记会影响日间结算
            action=prompt(f"今晚{game_state['wolftarget']}死了，你有一瓶解药，你要使用吗？请在回答中说0或1（1代表yes，0代表no）",[w])
            if action=="1":
                w["antidote"]=False
                game_state["save"]=True
            else:
                game_state["save"]=False
                if w["poison"] and w["isuser"]:
                    sep()
        if w["poison"]==True and action!="1":
            # 只有在未使用解药的情况下才允许考虑毒杀目标
            poison=prompt("你有一瓶毒药，今晚你要使用吗？请在回答中说0或1（1代表yes，0代表no）",[w])
            if poison=="1":
                if w["isuser"]:
                    sep()
                game_state["witchtarget"]=prompt("你要毒谁？请回答玩家编号",[w])
                w["poison"]=False
        prompt("女巫请闭眼",[w],False)
def prophet():
    """预言家夜间验人流程。"""
    if p["alive"]:
        # 只要还活着，就允许输入要验的座位号
        a=prompt("预言家请睁眼，选择你要验的玩家编号，回答编号",[p])
        try:
            i=index(a)
            if p["isuser"]:
                sep()
            if i==f1 or i==f2 or i==f3:
                prompt("他是个坏人，预言家请闭眼",[p],False)
            else:
                prompt("他是个好人，预言家请闭眼",[p],False)
        except:
            prompt("预言家玩家选择错误，跳过回合",[p],False)
def guard():
    """守卫夜间守护流程，避免连续守护同一玩家。"""
    if g["alive"]:
        # 守卫需要记忆上一晚目标，不能连续守同一人
        game_state["protect"]=prompt("守卫请睁眼，今晚你要守谁？回答编号",[g])
        if game_state["protect"]==game_state["prev"]:
            # 违反规则时将守护目标置 0，等价于未守护
            game_state["protect"]="0"
        game_state["prev"]=game_state["protect"]
def night():
    """夜晚阶段主流程，依次触发守卫、狼人、女巫与预言家。"""
    game_state["save"]=False
    game_state["wolftarget"]="0"
    game_state["witchtarget"]="0"
    game_state["protect"]="0"
    game_state["tonight_dead"]=[]
    broadcast("天黑请闭眼")
    title(f"夜晚阶段：第{game_state['nights']}夜",False)
    guard()
    wolf()
    witch()
    prophet()
def identify_dead():
    """根据夜间行动结果结算死亡名单并播报。"""
    title(f"白天阶段：第{game_state['nights']+1}天",False)
    broadcast("天亮了")
    print()
    title("白天公告")
    if game_state["protect"]==game_state["wolftarget"] and game_state["save"]==True:
        # 守卫与女巫同时保护同一人，按照游戏规则仍旧视为死亡
        game_state["save"]=False
        game_state["protect"]="0"
    # 将夜间决策统一转换为整数，减少循环内的重复转换
    wolftarget_int=int(game_state["wolftarget"])
    witchtarget_int=int(game_state["witchtarget"])
    protect_int=int(game_state["protect"])  # 统一转为整数，避免在循环内重复计算
    for i in player_list:
        # 狼刀成功且未被解药救，或中了毒且未被守卫，则加入今晚死亡名单
        if ((i["number"]==wolftarget_int and not game_state["save"]) or i["number"]==witchtarget_int) and protect_int!=i["number"]:
            i["alive"]=False
            game_state["tonight_dead"].append(i)
    if len(game_state["tonight_dead"])==0:
        broadcast("今晚是个平安夜")
    elif len(game_state["tonight_dead"])==1:
        broadcast(f"今晚{game_state['tonight_dead'][0]['number']}号玩家死了")
    else:
        broadcast(f"今晚{game_state['tonight_dead'][0]['number']}号玩家和{game_state['tonight_dead'][1]['number']}号玩家死了")
    print()
def kill_when_dead():
    """狼王在被处决时，允许额外带走一名玩家。"""
    death_kill_target="0"  # 预设默认值，避免异常时变量未定义
    try:
        death_kill_target=prompt("你被投票处决死了，你作为狼王可以杀死一名玩家，请回答存活的玩家编号，不刀人并隐藏身份请回答0，不要回答发言",[f3])
        for player in player_list:
            # 验证输入是否存在并立即执行带走效果
            if str(player["number"])==death_kill_target:
                player["alive"]=False
                broadcast(f"{f3['number']}号玩家是狼王，死前把{player['number']}号玩家杀死了",True)
        print()
    except:
        print(f"something went wrong. kill traget:{death_kill_target}, f3:{f3['number']}")
def lastwords(list):
    """处理遗言阶段，首夜直接跳过。"""
    title("遗言阶段")
    if game_state["nights"]==1:
        # 按照常规规则，首夜死亡不留遗言
        broadcast("第一晚没有遗言")
        print()
    else:
        for i in list:
            # 依次给予今晚死亡的玩家遗言机会
            words=prompt("你死了，请发表遗言",[i])
            if i["isuser"]:
                print()
            broadcast(f"{i['number']}号玩家的遗言是：{words}")
            if i!=list[len(list)-1]:
                sep()
            else:
                print()
def ifend():
    """判断游戏是否结束，并返回 0/1/2 表示状态。"""
    # 判断游戏是否结束
    bad_alive=0
    good_alive=0
    if not f1["alive"] and not f2["alive"] and not f3["alive"]:
        # 三狼全部阵亡，直接宣布好人胜利
        title("游戏结束",False)
        print("好人阵营胜利")
        print()
        return 1
    else:
        # 统计当前双方阵营存活人数，用于另一种胜利条件
        for i in player_list:
            if (i==v1 or i==v2 or i==w or i==p or i==g) and i["alive"]:
                good_alive += 1
            elif i["alive"]:
                bad_alive += 1
        if not(v1["alive"] or v2["alive"]) or not(p["alive"] or g["alive"] or w["alive"]) or (bad_alive>=good_alive+1):
            # 当关键好人角色倒光或狼人数量领先时，视作狼人获胜
            title("游戏结束",False)
            print("狼人阵营胜利")
            print()
            return 2
    return 0
def day():
    """白天阶段流程，先发言再投票。"""
    if len(game_state["tonight_dead"])!=0:
        # 白天开始时先让夜间遇害者依次发表遗言
        lastwords(game_state["tonight_dead"])
    game_state["nights"]+=1
    title("发言阶段")
    broadcast("发言阶段，请玩家轮流发言，每天顺序交替，第一次1-8，第二次8-1，以此类推")
    print()
    for n in range(1,9):
        # 奇偶日交替发言顺序，形成 1-8 与 8-1 的蛇形流程
        if game_state["nights"] % 2 ==1:
            n=9-n
        player_obj = get_player_by_number(n)
        if player_obj["alive"]:
            # 捕获模型输出异常，保证流程继续
            try:
                outn=prompt("请玩家发言",[player_obj])
                if player_obj["isuser"]:
                    print()
                broadcast(f"{n}号玩家的发言：{outn}")
            except:
                broadcast(f"{n}号发言有格式错误，跳过发言")
        else:
            broadcast(f"{n}号玩家已死亡，跳过发言。")
        if (n!=8 and game_state["nights"]%2==0) or (n!=1 and game_state["nights"]%2==1):
            sep()
    print()
    # ----------------- 投票阶段 -----------------
    title("投票阶段")
    broadcast("投票阶段，请各位玩家轮流投票，每天投票顺序交替，第一次1-8，第二次8-1，以此类推")
    print()
    # votes 使用座位号作为 key 统计当日票型
    votes = {}
    for n in range(1, 9):
        if game_state["nights"] % 2 ==1:
            n=9-n
        voter = get_player_by_number(n)
        if voter["alive"]:
            try:
                seat = prompt("请玩家投票，必须回复座位号，弃票的话必须回复0",[voter])
                if voter["isuser"]:
                    print()
            except:
                seat="0"
            if seat!="0":
                # 只统计非弃票，0 代表弃权
                votes.setdefault(seat, 0)
                votes[seat] += 1
                broadcast(f"{n}号玩家投给了{seat}号")
            else:
                broadcast(f"{n}号玩家弃票")
        else:
            broadcast(f"{n}号玩家已死亡，跳过投票")
        if (n!=8 and game_state["nights"]%2==0) or (n!=1 and game_state["nights"]%2==1):
            sep()
    sep(True)
    # 统计票数
    try:
        # 票型统计完毕后，找出票数最高的候选人
        max_votes = max(votes.values())
        top_targets = [k for k, v in votes.items() if v == max_votes]
        if len(top_targets) > 1:
            # 并列最高票直接平票，无需进入处决或 PK
            voted_out = "0"
            broadcast("平票，无人出局")
        else:
            voted_out = top_targets[0]
            out_player = index(voted_out)
            out_player["alive"] = False
            broadcast(f"公投结果：{voted_out}号玩家出局")
            print()
            if voted_out==str(f3["number"]):
                kill_when_dead()
            lastwords([index(voted_out)])
    except:
        broadcast("全体玩家弃票")
        print()
def game():
    """整体游戏主循环，交替推进昼夜直至结束。"""
    initiation()
    cont=ifend()
    isnight=True
    # 主循环：交替执行夜晚与白天，直到 ifend 判定结果
    while cont==0:
        if isnight:
            night()
            identify_dead()
            cont=ifend()
            isnight=False
        else:
            day()
            cont=ifend()
            isnight=True
    # 对局结束后输出角色与模型的完整对照表
    table()
    print()


def run(io: Optional["EngineIO"] = None) -> None:
    """Convenience wrapper so callers can supply a custom IO adapter."""
    with use_io(io):
        game()
