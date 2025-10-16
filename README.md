一个多模型混战的ai狼人杀原型

快速开始

```
pip install -U openai python-dotenv
```

.env:
```
api_key=你的API密钥
base_url=https://openrouter.ai/api/v1
```
（作者用的是openrouter.ai，python代码中的model_list定义的是此网站的模型，使用其他模型/网站请自行修改）

tech_out = True

- True：打印技术化信息（模型调用、抽取结果、内部状态等）

- False：仅打印关键回合信息

DEBUG_展示身份到控制台 = True

- True：起局时在控制台展示“座位 ← 角色 / 模型 / 阵营”

- False：隐藏身份映射（为后续用户参加做准备）

TODO:
    - ui
    - 未使用的plan策略字段
    - 允许用户作为一个角色参加
    - 接入LinuxDO元宇宙(?

欢迎提交分支！！！