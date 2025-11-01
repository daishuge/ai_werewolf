from openai import OpenAI
import random
import re
import json
with open("env.json","r",encoding="utf-8") as environment:
    env=json.load(environment)
def setup():
    model_list=env.get("model", ["x-ai/grok-4-fast"] * 8)
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
    bold={
        "name":"bold",
        "v1":"大胆发言",
        "v2":"大胆发言",
        "p":"大胆发言",
        "w":"大胆发言",
        "f1":"大胆发言",
        "f2":"大胆发言",
        "f3":"大胆发言",
        "g":"大胆发言"}
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
    plans=[defaultplan,complicated,simple,cautious,bold,crazy]
    v1 = {
            "alive": True,
            "history":[],
            "number": 0,
            "role_name": "村民1",
            "role_instruction": "你是普通村民，没有夜间技能，白天通过发言和投票找出狼人",
            "suggestion":"你可以大胆发言",
            "plan":"",
            "model":"",
            "code":"v1"
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
            "code":"v2"
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
            "code":"p"
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
            "code":"w"
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
            "code":"f1"
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
            "code":"f2"
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
            "code":"f3"
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
            "code":"g"
    }
    player_list = [v1,v2,p,w,f1,f2,f3,g]
    game_state={
        "nights":1,
        "witchtarget":"0",
        "wolftarget":"0",
        "protect":"0",
        "save":False,
        "tonight_dead":[]
    }
    return model_list,game_state,plans,player_list
[model_list,game_state,plans,player_list]=setup()
v1=player_list[0]
v2=player_list[1]
p=player_list[2]
w=player_list[3]
f1=player_list[4]
f2=player_list[5]
f3=player_list[6]
g=player_list[7]
def utilities():
    def table():
        print("Number |Character |Faction |Model")
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
        if sub:
            sepp="-"*20
        else:
            sepp="="*25
            print()
        print(f"{sepp}{input}{sepp}\n")
    def sep(long=False):
        sepp="_"*15
        if long:
            print(sepp+sepp)
        else:
            print(sepp)
        print()
    empty={}
    def index(number):                                       #number:str
        for player in player_list:
            if player['number']==int(number):
                return player
        if number=="0":
            return empty
        else:
            raise ValueError(f"There is no player with number {number}")
    def get_player_by_number(seat):
        for entry in player_list:
            if str(entry['number']) == str(seat):
                return entry
        if seat!=0:
            raise ValueError(f"找不到座位号为 {seat} 的玩家")
    def llm(history, model, ifprint=True):
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
    def assign(role,content,tar=player_list):                #tar:list of dict
        for i in tar:
            i["history"].append({"role":role,"content":content})
    def out(ifprint,ifsep,play,len="short"):                 #play:dict
        res = llm(play["history"],play["model"])
        assign("assistant",res,[play])
        if False:
            print(res)
        if ifsep:
            sep(len)
        return res
    def out_extract(ifprint,ifsep,play,len="short"):         #play:dict
        """从模型回复中提取 [[...]] 内的任意内容（含空格/标点/中文/换行）。"""
        trials=1
        m=[]
        while trials!=3:
            try:
                reply = out(ifprint,ifsep,play,len)
                m = re.search(r"\[\[\s*(.+?)\s*\]\]", reply, flags=re.S)  # DOTALL 非贪婪
                break
            except:
                trials+=1
        if not m and m!=0:
            raise ValueError(f"{play['role_name']}：未在输出中找到[[...]]格式的内容")
        return m.group(1)
    def prompt(input,player,respond=True):                   #player:list of dict
        for p in player:
            assign("user",input,[p])
            if respond:
                targ=out_extract(False,False,p)
            else:
                targ="0"
                assign("assistant","",[p])
        return targ
    def broadcast(input,ifprint=False):
        prompt(input,player_list,False)
        if ifprint:
            print(input)
    return table,title,sep,index,get_player_by_number,llm,assign,out,out_extract,prompt,broadcast
[table,title,sep,index,get_player_by_number,llm,assign,out,out_extract,prompt,broadcast]=utilities()
def initiation():
    api = env["api_key"]
    url = env["base_url"]
    global client
    client = OpenAI(
        base_url=url,
        api_key=api,
    )
    title("初始化",False)
    selectedplan="default"
    selectedplan=input("选择玩家的计划: ")
    if selectedplan=="custom":
        for player in player_list:
            playerplan="default"
            playerplan=input(f"选择{player['role_name']}玩家的计划: ")
            for plan in plans:
                if plan["name"]==playerplan:
                    player["plan"]=plan[player["code"]]
    elif selectedplan=="random":
        for player in player_list:
            player["plan"]=random.choice(plans)[player["code"]]
            print(player["code"],player["plan"])
    else:
        for plan in plans:
            if plan["name"]==selectedplan:
                v1["plan"]=plan["v1"]
                v2["plan"]=plan["v2"]
                p["plan"]=plan["p"]
                w["plan"]=plan["w"]
                f1["plan"]=plan["f1"]
                f2["plan"]=plan["f2"]
                f3["plan"]=plan["f3"]
                g["plan"]=plan["g"]
    print()
    random.shuffle(model_list)
    id=1
    randomlist=player_list
    random.shuffle(randomlist)
    for model in model_list:
        player=randomlist[id-1]
        player["model"]=model
        player["number"]=id
        id+=1
    table()
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
                    你的编号是：{num}
                    你的身份是：{role_name}
                    {role_instruction}
                    建议：{suggestion}
                    你的计划：{plann}
                    你应当每回合输出分析，放在两个大括号中，这里面的内容只会被你自己阅读
                    你的最终的结果（玩家代号或者选择或药水选择或遗言或收到），尤其注意白天发言，以上内容务必放在[[]]像这样的两个中括号中
                    例如
                    [[1]]
                    确保它没有任何其他内容
                    在无需目标的情况下，例如遗言，讨论，你不能输出这个内容
                    你的语言应该不那么专业，保持普通人的能力即可，但是尽量积极发言，可以大胆一点'''
        i["history"].append({"role":"system","content":promptt})
def wolf():
    def rechoose(wolf1,wolf2,wolftarget1,wolftarget2):
        if wolftarget1==wolftarget2:
            wolftarget=wolftarget1
        else:
            sep(True)
            r=random.randint(1,2)
            if r==1:
                wolftarget=prompt(f"你的队友选了{wolftarget2}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号，并放在[[]]里",[wolf1])
            if r==2:
                wolftarget=prompt(f"你的队友选了{wolftarget1}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号，并放在[[]]里",[wolf2])
        return wolftarget
    deadwolf=0
    if game_state["nights"]==1:
        prompt(f"你的另外两个队友的代号：{f2['number']}和{f3['number']}",[f1],False)
        prompt(f"你的另外两个队友的代号：{f1['number']}和{f3['number']}",[f2],False)
        prompt(f"你的另外两个队友的代号：{f1['number']}和{f2['number']}",[f3],False)
    if f1["alive"]:
        target1=prompt("狼人请睁眼，今晚你要刀谁？请回答玩家编号，并放在[[]]里",[f1])
        if f2["alive"] or f3["alive"]:
            sep()
    else:
        target1="0"
        deadwolf+=1
    if f2["alive"]:
        target2=prompt("狼人请睁眼，今晚你要刀谁？请回答玩家编号，并放在[[]]里",[f2])
        if f3["alive"]:
            sep()
    else:
        target2="0"
        deadwolf+=1
    if f3["alive"]:
        target3=prompt("狼人请睁眼，今晚你要刀谁？请回答玩家编号，并放在[[]]里",[f3])
    else:
        target3="0"
        deadwolf+=1
    if deadwolf==0:
        if target1==target2 and target1==target3:
            game_state["wolftarget"]=target1
        else:
            sep(True)
            r=random.randint(1,3)
            if r==1:
                game_state["wolftarget"]=prompt(f"你的队友选了{target2}和{target3}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号，并放在[[]]里",[f1])
            if r==2:
                game_state["wolftarget"]=prompt(f"你的队友选了{target1}和{target3}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号，并放在[[]]里",[f2])
            if r==3:
                game_state["wolftarget"]=prompt(f"你的队友选了{target1}和{target2}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号，并放在[[]]里",[f3])
    elif deadwolf==1:
        if target1=="0":
            game_state["wolftarget"]=rechoose(f2,f3,target2,target3)
        if target2=="0":
            game_state["wolftarget"]=rechoose(f1,f3,target1,target3)
        if target3=="0":
            game_state["wolftarget"]=rechoose(f1,f2,target1,target2)
    elif deadwolf==2:
        if target1!=0:
            game_state["wolftarget"]=target1
        elif target2!=0:
            game_state["wolftarget"]=target2
        elif target3!=0:
            game_state["wolftarget"]=target3
    else:
        game_state["wolftarget"]="0"
    prompt(f"狼人最终选择刀{game_state['wolftarget']}号玩家",[f1,f2,f3],False)
def witch():
    game_state["save"]=False
    action=""
    poison=""
    if w["alive"]:
        prompt("女巫请睁眼",[w],False)
        if not(w["poison"] or w["antidote"]):
            prompt("你没有药了",[w],False)
            print("女巫没有药了")
        if w["antidote"]==True and game_state["wolftarget"]!="0":
            action=prompt(f"今晚{game_state['wolftarget']}死了，你有一瓶解药，你要使用吗？请在回答中说[[0]]或[[1]]（1代表yes，0代表no）",[w])
            if action=="1":
                w["antidote"]=False
                game_state["save"]=True
            else:
                game_state["save"]=False
                if w["poison"]:
                    sep()
        if w["poison"]==True and action!="1":
            poison=prompt("你有一瓶毒药，今晚你要使用吗？请在回答中说[[0]]或[[1]]（1代表yes，0代表no）",[w])
            if poison=="1":
                sep()
                game_state["witchtarget"]=prompt("你要毒谁？请回答玩家编号，并放在[[]]里",[w])
                w["poison"]=False
        prompt("女巫请闭眼",[w],False)
    sep(True)
    if w["alive"]:
        if poison=="1":
            print(f"女巫选择毒{game_state['witchtarget']}号玩家")
            print()
        elif action=="1":
            print("女巫使用了解药")
            print()
        print("女巫回合结束")
    else:
        print("女巫回合跳过")
def prophet():
    if p["alive"]:
        a=prompt("预言家请睁眼，选择你要验的玩家编号，回答编号，放在[[]]里",[p])
        i=index(a)
        sep(True)
        if i==f1 or i==f2 or i==f3:
            assign("user","他是个坏人，预言家请闭眼",[p])
            print(f"{i['number']}号玩家是个坏人")
        else:
            assign("user","他是个好人，预言家请闭眼",[p])
            print(f"{i['number']}号玩家是个好人")
        print()
def guard():
    if g["alive"]:
        game_state["protect"]=prompt("守卫请睁眼，今晚你要守谁？回答编号，放在[[]]里",[g])
        sep(True)
        print(f"守卫守护的对象：{game_state['protect']}")
        print()
        print("守卫回合结束")
    else:
        print("守卫回合跳过")
def night():
    broadcast("天黑请闭眼")
    title(f"夜晚阶段：第{game_state['nights']}夜",False)
    title("守卫回合")
    guard()
    print()
    title("狼人回合")
    wolf()
    sep(True)
    if f1["alive"]or f2["alive"] or f3["alive"]:
        print(f"狼人刀的对象：{game_state['wolftarget']}")
        print()
        print("狼人回合结束")
    else:
        print("狼人回合跳过")
    print()
    title("女巫回合")
    witch()
    print()
    title("预言家回合")
    prophet()
    if p["alive"]:
        print("预言家回合结束")
    else:
        print("预言家回合跳过")
def identify_dead():
    title(f"白天阶段：第{game_state['nights']+1}天",False)
    broadcast("天亮了")
    title("白天公告")
    if game_state["protect"]==game_state["wolftarget"] and game_state["save"]==True:
        game_state["save"]=False
        game_state["protect"]="0"
    for i in player_list:
        if ((i["number"]==int(game_state["wolftarget"]) and not game_state["save"]) or i["number"]==int(game_state["witchtarget"])) and int(game_state["protect"])!=i["number"]:
            i["alive"]=False
            game_state["tonight_dead"].append(i)
    if len(game_state["tonight_dead"])==0:
        broadcast("今晚是个平安夜",True)
    elif len(game_state["tonight_dead"])==1:
        broadcast(f"今晚{game_state['tonight_dead'][0]['number']}号玩家死了",True)
    else:
        broadcast(f"今晚{game_state['tonight_dead'][0]['number']}号玩家和{game_state['tonight_dead'][1]['number']}号玩家死了",True)
    print()
def kill_when_dead():
    try:
        death_kill_target=prompt("你被投票处决死了，你作为狼王可以杀死一名玩家，请回答存活的玩家编号，并放在[[]]中，[[]]中不要放发言",[f3])
        for player in player_list:
            if str(player["number"])==death_kill_target:
                player["alive"]=False
                killed=player
        broadcast(f"{f3['number']}号玩家是狼王，死前把{killed['number']}号玩家杀死了",True)
        print()
    except:
        print(f"something went wrong. kill traget:{death_kill_target}, killed:{killed}, f3:{f3['number']}")
def lastwords(list):
    title("遗言阶段")
    if game_state["nights"]==1:
        broadcast("第一晚没有遗言",True)
    else:
        for i in list:
            words=prompt("你死了，请发表遗言",[i])
            broadcast(f"{i['number']}号玩家的遗言是：{words}")
            if i!=list[len(list)-1]:
                sep()
            else:
                print()
def ifend():
    # 判断游戏是否结束
    bad_alive=0
    good_alive=0
    if not f1["alive"] and not f2["alive"] and not f3["alive"]:
        title("游戏结束",False)
        print("好人阵营胜利")
        print()
        return 1
    else:
        for i in player_list:
            if (i==v1 or i==v2 or i==w or i==p or i==g) and i["alive"]:
                good_alive += 1
            elif i["alive"]:
                bad_alive += 1
        if not(v1["alive"] or v2["alive"]) or not(p["alive"] or g["alive"] or w["alive"]) or (bad_alive>=good_alive+1):
            title("游戏结束",False)
            print("狼人阵营胜利")
            print()
            return 2
    return 0
def day():
    if len(game_state["tonight_dead"])!=0:
        lastwords(game_state["tonight_dead"])
        print()
    game_state["nights"]+=1
    title("发言阶段")
    broadcast("发言阶段，请玩家轮流发言，每天顺序交替，第一次1-8，第二次8-1，以此类推")
    for n in range(1,9):
        if game_state["nights"] % 2 ==1:
            n=9-n
        player_obj = get_player_by_number(n)
        if player_obj["alive"]:
            outn=prompt("请玩家发言，内容放在[[]]中",[player_obj])
            broadcast(f"{n}号玩家的发言：{outn}")
            if (n!=8 and game_state["nights"]%2==0) or (n!=1 and game_state["nights"]%2==1):
                sep()
            else:
                print()
        else:
            broadcast(f"{n}号玩家已死亡，跳过发言。",True)
            if (n!=8 and game_state["nights"]%2==0) or (n!=1 and game_state["nights"]%2==1):
                sep()
            else:
                print()
    # ----------------- 投票阶段 -----------------
    title("投票阶段")
    broadcast("请各位玩家轮流投票，必须回复[[座位号]]，一定要把要投的座位号放在[[]]里，弃票的话必须回复[[0]]，每天投票顺序交替，第一次1-8，第二次8-1，以此类推")
    votes = {}
    for n in range(1, 9):
        if game_state["nights"] % 2 ==1:
            n=9-n
        voter = get_player_by_number(n)
        if voter["alive"]:
            try:
                seat = out_extract(False,False,voter)
            except:
                seat="0"
            sep()
            if seat!="0":
                votes.setdefault(seat, 0)
                votes[seat] += 1
                broadcast(f"{n}号玩家投给了{seat}号",True)
            else:
                broadcast(f"{n}号玩家弃票",True)
        else:
            broadcast(f"{n}号玩家已死亡，跳过投票",True)
        if (n!=8 and game_state["nights"]%2==0) or (n!=1 and game_state["nights"]%2==1):
            sep(True)
    sep(True)
    # 统计票数
    try:
        max_votes = max(votes.values())
        top_targets = [k for k, v in votes.items() if v == max_votes]
        if len(top_targets) > 1:
            voted_out = "0"
            broadcast("平票，无人出局",True)
        else:
            voted_out = top_targets[0]
            out_player = index(voted_out)
            out_player["alive"] = False
            broadcast(f"公投结果：{voted_out}号玩家出局",True)
            print()
            if voted_out==str(f3["number"]):
                kill_when_dead()
            lastwords([index(voted_out)])
    except:
        broadcast("全体玩家弃票",True)
        print()
def game():
    initiation()
    cont=ifend()
    isnight=True
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
game()