**一个多模型混战的ai狼人杀原型**

*快速开始*

```
pip install -U openai python-dotenv
```

*.env:*
```
api_key=你的API密钥
base_url=https://openrouter.ai/api/v1
```
（作者用的是openrouter.ai，python代码中的model_list定义的是此网站的模型，使用其他模型/网站请自行修改）

<u>仅用于最早上传的版本：</u>
```
tech_out = True
- True：打印技术化信息（模型调用、抽取结果、内部状态等）
- False：仅打印关键回合信息

DEBUG_展示身份到控制台 = True
- True：起局时在控制台展示“座位 ← 角色 / 模型 / 阵营”
- False：隐藏身份映射（为后续用户参加做准备）
```

*TODO:*

- ui
    
- ~~未使用的plan策略字段~~
    
- 允许用户作为一个角色参加
    
- 接入LinuxDO元宇宙(?


欢迎提交分支！！！

**A multi-model ai werewolf game**

*Quick start*

```
pip install -U openai python-dotenv
```

*.env:*
```
api_key=your api
base_url=https://openrouter.ai/api/v1
```

<u>For the earliest uploaded version only:</u>

```
tech_out = True
- True：Prints everything, easy for debug
- False：Only prints key info

DEBUG_展示身份到控制台 = True
- True：Displays character assignment at the start of the game
- False：No character display
```

*Game rules explained (simplified):*

Two sides/factions:

- Good: villagers and special characters, eg. witch

- Bad: werewolves and special characters, eg. werewolf king

Switches between day and night phases until victory of one side

Night:

- Werewolves choose their target

- Witch choose to use antidote on the target or use poison on someone (both potions can only be used once)

- Prophet checks if a player is good or bad

- Guard decides which person to protect (cannot be same for two consecutive nights)


Day:

- If applicable, the dead ones have their last words spoken

- Players that are alive delivers a short speech

- Players decide who to vote for, and the one who gets the most votes is killed


*Sidenote and backstory:*


The old version (1.5) has only basic functions and is very messy, so we did a reconstruction/refactoring of the code (the oldest uploaded)

This time, there are 8 players instead of 6, and the code is more robust

The output is still a bit messed up but things are generally great

We are preparing to upload another version very soon

It will have a plan section where users can customize the course and style of game (already done)

We are working on a user version where it is possible to play the game with ai (only singleplayer for now)

We hope to create a html version with ui sometime soon, perhaps

-Leonard and Cameron









