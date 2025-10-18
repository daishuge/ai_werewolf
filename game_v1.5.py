from openai import OpenAI
import random
global re
import re
api = "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"
url = "https://openrouter.ai/api/v1"
global client
client = OpenAI(
    base_url=url,
    api_key=api,
)
"google/gemini-2.5-flash-preview-09-2025"
"x-ai/grok-4-fast"
"deepseek/deepseek-chat-v3.1:free"
global default
default = "x-ai/grok-4-fast"
global set
num_list=[]
set = ["v1","v2","p","w","f1","f2"]
for i in range(1,7,1):
    num_list.append(i)
random.shuffle(num_list)
print(num_list)
global vote
vote = {
        "v1":0,
        "v2":0,
        "p":0,
        "w":0,
        "f1":0,
        "f2":0,
}
global v1
v1 = {
        "alive": True,
        "history":[],
        "number": num_list[0],
        "role_name": "村民1",
        "role_instruction": "你是普通村民，没有夜间技能，白天通过发言和投票找出狼人，可以大胆发言。",
}
global v2
v2 = {
        "alive": True,
        "history":[],
        "number": num_list[1],
        "role_name": "村民2",
        "role_instruction": "你是普通村民，没有夜间技能，白天通过发言和投票找出狼人，可以大胆发言。",
}
global p
p = {
        "alive": True,
        "target": "",
        "history":[],
        "number": num_list[2],
        "role_name": "预言家",
        "role_instruction": "你每晚可以随机查验一名玩家阵营，在白天合理分享信息，第一夜建议随机选择要验的玩家，可以大胆发言透露身份，便于神职和平民的合作。",
}
global w
w = {
        "alive": True,
        "d": True,
        "j": True,
        "target": "0",
        "history":[],
        "number": num_list[3],
        "role_name": "女巫",
        "role_instruction": "你拥有一瓶解药和一瓶毒药每种，最多使用一次，建议第一晚使用解药，有必要的时候大胆使用毒药，可以大胆发言透露身份，便于神职和平民的合作。女巫是可以自救的。",
}
global f1
f1 = {
        "alive": True,
        "target": "",
        "history":[],
        "number": num_list[4],
        "role_name": "狼人1",
        "role_instruction": "你与另一名狼人协同作战，夜间选择击杀目标，白天需要隐藏身份，建议选择自刀或者刀队友作为策略，第一夜建议随机选择，发言阶段可以伪装成预言家来骗玩家，尽量配合队友欺骗平民票出神职，也建议自刀来骗女巫和平民，别忘了发言顺序是1到6，可别乱说没发言的玩家发言很怪。",
}
global f2
f2 = {
        "alive": True,
        "target": "",
        "history":[],
        "number": num_list[5],
        "role_name": "狼人2",
        "role_instruction": "你与另一名狼人协同作战，夜间选择击杀目标，白天需要隐藏身份，建议选择自刀或者刀队友作为策略，第一夜建议随机选择，发言阶段可以伪装成预言家来骗玩家，尽量配合队友欺骗平民票出神职，也建议自刀来骗女巫和平民，别忘了发言顺序是1到6，可别乱说没发言的玩家发言很怪。",
}
global target
global player
target = ""
player = [v1,v2,p,w,f1,f2]
def llm(history, model=default, ifprint=True):
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

    return "".join(chunks)
def assign(role,content,tar=player):
    for i in tar:
        i["history"].append({"role":role,"content":content})
for i in player:
    num = i["number"]
    role_name = i.get("role_name", "未知身份")
    role_instruction = i.get("role_instruction", "")
    prompt = f'''你是一个狼人杀玩家，你将参与一场狼人杀对局，想尽一切办法获胜
                我们标准配置有六名玩家：两名村民，一名预言家，一名女巫
                总共有六位玩家，请使用玩家编号互相称呼
                编号和角色的对应顺序将会打乱，不按照任何规律
                你的编号是：{num}
                你的身份是：{role_name}
                {role_instruction}
                你应当每回合输出分析，放在两个大括号中，这里面的内容只会被你自己阅读
                你的最终的结果（玩家代号或者选择或药水选择或遗言或收到），尤其注意白天发言，以上内容务必放在[[]]像这样的两个中括号中
                例如
                [[1]]
                确保它没有任何其他内容
                在无需目标的情况下，例如遗言，讨论，你不能输出这个内容
                你的语言应该不那么专业，保持普通人的能力即可，但是尽量积极发言，可以大胆一点
    '''
    i["history"].append({"role":"system","content":prompt})
def out(ifprint,ifsep,play,len="short"):
    res = llm(play["history"])
    assign("assistant",res,[play])
    if False:
        print(res)
    if ifsep:
        print_separator(len)
    return res
def identify(inp):
    res=re.findall(r"\[+\s*(\d+)\s*\]+", inp)[0]
    return res
def out_extract(ifprint,ifsep,play,len="short"):
    """从模型回复中提取 [[...]] 内的任意内容（含空格/标点/中文/换行）。"""
    reply = out(ifprint,ifsep,play,len)
    m = re.search(r"\[\[\s*(.+?)\s*\]\]", reply, flags=re.S)  # DOTALL 非贪婪
    if not m and m!=0:
        raise ValueError("未在输出中找到[[...]]格式的内容")
    return m.group(1)
def wolf():
    global target
    target="0"
    if f1["alive"] and f2["alive"]:
        f1_assign = ""
        f2_assign = ""
        if first_night:
            f1_assign += f"另一个狼人的玩家代号：{f2['number']}, "
            f2_assign += f"另一个狼人的玩家代号：{f1['number']}, "
        f1_assign += "狼人请睁眼，今晚你要杀谁？回答编号，放在[[]]里"
        f2_assign += "狼人请睁眼，今晚你要杀谁？回答编号，放在[[]]里"
        assign("user",f1_assign,[f1])
        assign("user",f2_assign,[f2])
        f1["target"] = out_extract(True,False,f1)
        print_separator("short")
        f2["target"] = out_extract(True,False,f2,)
        print_separator("short")
        if f1["target"]==f2["target"]:
            target=f1["target"]
        else:
            if nights%2==0:
                assign("user","你的队友选了"+f2["target"]+"号玩家，请重新选一次，可以和之前的重复，你的队友将知道你的选择并决定目标，回答编号，放在[[]]里",[f1])
                res=out_extract(True,True,f1)
                assign("user","你的队友重新选了"+res+"号玩家，由你决定目标，回答编号，放在[[]]里",[f2])
                res=out_extract(True,True,f2)
            elif nights%2==1:
                assign("user","你的队友选了"+f1["target"]+"号玩家，请重新选一次，可以和之前的重复，你的队友将知道你的选择并决定目标，回答编号，放在[[]]里",[f2])
                res=out_extract(True,True,f2)
                assign("user","你的队友重新选了"+res+"号玩家，由你决定目标，回答编号，放在[[]]里",[f1])
                res=out_extract(True,True,f1)
            target=res
    elif f1["alive"]:
        f1_assign = "狼人请睁眼，今晚你要杀谁？回答编号，放在[[]]里"
        assign("user",f1_assign,[f1])
        target = out_extract(True,True,f1)
    elif f2["alive"]:
        f2_assign = "狼人请睁眼，今晚你要杀谁？回答编号，放在[[]]里"
        assign("user",f2_assign,[f2])
        target = out_extract(True,True,f2)
    else:
        target="0"
    return target
def witch(target):
    global save
    save=False
    wi=""
    action=""
    if w["alive"]:
        wi+="女巫请睁眼,"
        if w["j"] and target!="0":
            wi+=f"今晚{target}死了，你有一瓶解药，你要使用吗？请在回答中说[[0]]或[[1]]（1代表yes，0代表no）"
            assign("user",wi,[w])
            action=out_extract(True,True,w)
            if action=="1":
                target="0"
                w["j"]==False
                save=True
            else:
                save=False
        if w["d"] and action!="1":
            if action=="":
                wi+="你还有一瓶毒药，今晚你要使用吗？请在回答中说[[0]]或[[1]]（1代表yes，0代表no）"
                assign("user",wi,[w])
                action=out_extract(True,True,w)
            else:
                assign("user","你有一瓶毒药，今晚你要使用吗？请在回答中说[[0]]或[[1]]（1代表yes，0代表no）")
                action=out_extract(True,True,w)
            if action=="1":
                assign("user","你要毒谁？")
                w["target"]=out_extract(True,True,w)
                w["d"]=False
        if not(w["d"] or w["j"]):
            wi+="你没有药了"
            assign("user",wi,[w])
        assign("user","女巫请闭眼",[w])
def prophet():
    if p["alive"]:
        assign("user","预言家请睁眼，选择你要验的玩家编号，回答编号，放在[[]]里",[p])
        a=out_extract(True,True,p)
        for i in player:
            if i["number"]==int(a):
                if i==f1 or i==f2:
                    assign("user","他是个坏人，预言家请闭眼",[p])
                    print(f"{i['number']}号玩家是个坏人")
                else:
                    assign("user","他是个好人，预言家请闭眼",[p])
                    print(f"{i['number']}号玩家是个好人")
def pt(i):
    u="-"
    res=u*15+" "+i+" "+u*15
    print()
    print(res)
def night():
    assign("user","天黑请闭眼")
    global nights
    print()
    print_separator("",f"夜晚阶段：第{nights}夜",True)
    global target
    nights += 1
    global first_night
    if nights != 1:
        first_night = False
    else:
        first_night =True
    print_separator("","狼人回合")
    wolf()
    if f1["alive"]or f2["alive"]:
        print(f"狼人刀的对象：{target}")
        print()
        print("狼人回合结束")
    else:
        print("狼人回合跳过")
    print_separator("","女巫回合")
    witch(target)
    if w["alive"]:
        print("女巫回合结束")
    else:
        print("女巫回合跳过")
    print_separator("","预言家回合")
    prophet()
    if p["alive"]:
        print("预言家回合结束")
    else:
        print("预言家回合跳过")
def id():
    print_separator("",f"白天阶段：第{nights+1}天",True)
    assign("user","天亮了")
    global tonight
    tonight=[]
    print()
    for i in player:
        if (i["number"]==int(target) and not save) or i["number"]==int(w["target"]):
            i["alive"]=False
            dead.append(i)
            tonight.append(i)
    if len(tonight)==0:
        assign("user","今晚是个平安夜")
        print("今晚是个平安夜")
    elif len(tonight)==1:
        assign("user",f"今晚{tonight[0]['number']}号玩家死了")
        print(f"今晚{tonight[0]['number']}号玩家死了")
    else:
        assign("user",f"今晚{tonight[0]['number']}号玩家和{tonight[1]['number']}号玩家死了")
        print(f"今晚{tonight[0]['number']}号玩家和{tonight[1]['number']}号玩家死了")
    print_separator("")
def lastwords():
    if first_night:
        assign("user","第一晚没有遗言")
    else:
        for i in tonight:
            assign("user","你死了，请发表遗言",[i])
            words=out_extract(True,True,i,"")
            assign("user",f"{i}的遗言是：{words}")
def print_separator(len,label=None,title=False):
    SECTION_LINE = "-" * 25
    mmm="="*25
    oooof="-"*20
    """Print a reusable separator line for clearer console output."""
    if label:
        if title:
            print(f"\n{mmm} {label} {mmm}")
        else:
            print(f"\n{SECTION_LINE} {label} {SECTION_LINE}")
            print()
    elif len=="short":
        print(f"\n{SECTION_LINE}")
    else:
        print(f"\n{oooof*2}")
def get_player_by_number(seat):
    """根据座位号查找对应的玩家字典。"""
    for entry in player:
        if str(entry["number"]) == str(seat):
            return entry
    if seat!=0:
        raise ValueError(f"找不到座位号为 {seat} 的玩家")
def out_extract(ifprint,ifsep,play,len="short"):
    """从模型回复中提取 [[...]] 内的任意内容（含空格/标点/中文/换行）。"""
    reply = out(ifprint,ifsep,play,len)
    m = re.search(r"\[\[\s*(.+?)\s*\]\]", reply, flags=re.S)  # DOTALL 非贪婪
    if not m and m!=0:
        raise ValueError("未在输出中找到[[...]]格式的内容")
    return m.group(1)
def ifend():
    # 判断游戏是否结束
    if not f1["alive"] and not f2["alive"]:
        print()
        print()
        print("好人阵营胜利")
        print()
        return 1
    else:
        good_alive = 0
        bad_alive = 0
        for i in player:
            if "狼人" not in i["role_name"] and i["alive"]:
                good_alive += 1
            elif i["alive"]:
                bad_alive += 1
        if (bad_alive==2 and good_alive<=1)or(bad_alive==1 and (good_alive==1 or good_alive==0)):
            print()
            print()
            print("狼人阵营胜利")
            print()
            return 2
    return 0
def day():
    assign("user", "请各位玩家轮流发言，放在两个方括号中 [[...]]")
    for n in range(1, 7):
        player_obj = get_player_by_number(n)
        if player_obj["alive"]:
            if n!=6:
                outn = out_extract(True,True,player_obj)
                assign("user", f"{n}号玩家：{outn}")
            else:
                outn = out_extract(True,False,player_obj)
                assign("user", f"{n}号玩家：{outn}")
        else:
            print(f"{n}号玩家已死亡，跳过发言。")
            if n!=6:
                print_separator("short")

    # ----------------- 投票阶段 -----------------
    print_separator("","投票阶段")
    assign("user", "请各位玩家轮流投票（回复[[座位号]]）")
    votes = {}
    for n in range(1, 7):
        voter = get_player_by_number(n)
        if voter["alive"]:
            seat = out_extract(True,False,voter)
            votes.setdefault(seat, 0)
            votes[seat] += 1
            print(f"{n}号玩家投给了{seat}号")
            assign("user",f"{n}号玩家投给了{seat}号")
            if n!=6:
                print_separator("short")
    print_separator("")
    # 统计票数
    max_votes = max(votes.values())
    top_targets = [k for k, v in votes.items() if v == max_votes]
    if len(top_targets) > 1:
        voted_out = "0"
        print("平票，无人出局")
        assign("user","平票，无人出局")
    else:
        voted_out = top_targets[0]

        out_player = get_player_by_number(voted_out)
        out_player["alive"] = False
        assign("user", f"公投结果：{voted_out}号玩家出局")
        print(f"公投结果：{voted_out}号玩家出局")
        print_separator("","遗言阶段")
        assign("user", "请出局玩家发表遗言（务必，务必放在[[...]]中，其中的内容会被广播给所有人）", [out_player])
        last_word = out_extract(True,False,out_player)
        assign("user", f"{voted_out}号玩家的遗言：{last_word}")

global nights
nights = 0
global dead
dead = []
cont=ifend()
while cont==0:
    night()
    id()
    if len(tonight)!=0:
        lastwords()
    day()
    cont=ifend()
