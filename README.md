# QQ 每日早安推送

通过 GitHub Actions 每天向指定 QQ 接收人发送早安消息，包含杭州天气、恋爱天数、农历生日倒计时、节日提醒和随机文案。每日任务只调用 QQ；原微信脚本和配置可保留用于回退。

操作入口见 [QQ_SETUP.md](QQ_SETUP.md)，升级步骤见 [UPGRADE.md](UPGRADE.md)，变更见 [CHANGELOG.md](CHANGELOG.md)，恢复方法见 [ROLLBACK.md](ROLLBACK.md)。

## 环境与配置

使用 Python 3.12，安装 `requirements-qq.txt`。QQ 机器人由本项目的 Python 程序对接官方接口，无需 AI 模型或全天候运行的 Agent。绑定时临时连接网关，日常发送使用已保存的接收标识。

在仓库 **Settings → Secrets and variables → Actions** 保存：

| Secret | 是否必需 | 用途 |
| --- | --- | --- |
| `QQ_APP_ID` | 是 | QQ 机器人的 AppID |
| `QQ_APP_SECRET` | 是 | QQ 机器人的 AppSecret |
| `QQ_USER_OPENID` | 是 | 由实际接收人通过 QQ 私下取得的绑定标识，不是 QQ 号码 |
| `DEEPSEEK_API_KEY` | 启用 AI 时必需 | DeepSeek 官方 API 密钥；未配置时使用原有文案 |
| `TIANAPI_KEY` | 否 | 天气与彩虹屁接口；缺失时使用天气不可用占位和本地文案 |

原微信的 `APP_ID`、`APP_SECRET`、`OPEN_ID`、`TEMPLATE_ID` 可保留，每日 QQ 任务不读取它们。不要在代码、日志、聊天或截图中公开实际密钥与接收标识。

个人城市、恋爱起始日和农历生日仍在 `wechat_love.py` 顶部配置，QQ 复用同一套内容生成逻辑。该文件的业务代码与个人设置未改。

## DeepSeek 三段问候

保留原 QQ 消息栏目，将开头问候、天气关心和小情话交给 DeepSeek 生成，每段尽量 20～40 字、最多 60 个字符，完整插入 QQ 正文。日期、天气数据、恋爱天数、农历生日和原有节日、节气、隐藏彩蛋规则仍由原程序决定。

在 GitHub Secrets 保存 `DEEPSEEK_API_KEY` 后，真实发送时默认使用官方 `deepseek-flash` 非思考模式，一次请求生成三个 JSON 字段。正常每天调用一次；只有文案重复时最多再生成一次，网络失败或余额不足不自动重试 AI。

- 普通日子按日期轮换 14 个主题，特别日子按原程序提供的状态写专属问候，不将“下个节日倒计时”当成当天过节。
- 三段分别校验。空白、过长、格式异常、明显与已知天气不符的段落会单独使用原文案；天气数据缺失时，天气关心沿用中性备用提醒。
- AI 不重新计算或复述数字，不编造共同经历或她的工作安排。固定称呼和事实栏目保留，三个 AI 段落不再按微信模板切成短字段。
- 不向 AI 提供 QQ 接收标识、微信或 QQ 凭据；公开日志只显示来源计数和通用状态，不记录密钥、模型响应或新生成的文案正文。
- QQ 接口确认接受后才记录日期和文字指纹。通过 Actions 缓存保留最近 14 天用于检查文字重复，不保存正文，不每日提交到仓库；缓存不可用时继续发送。指纹去重不等于语义去重，近似表达仍可能出现。

暂时关闭 AI：在 **Settings → Secrets and variables → Actions → Variables** 新增或修改 `AI_ENABLED` 为 `false`。下次发送使用原来的三段文案，QQ 收件人与定时保持不变。重新启用改为 `true` 即可。

`python qq_push.py --dry-run` 始终只展示原文案，不调用收费 AI，也不写去重记录。真实 AI 试发需在 **每日早安推送** 手动选择 `feat/deepseek-greetings-20261107` 分支运行一次，并在 QQ 私下检查三段效果；它会真实调用 AI 并向当前接收人发信。满意后再启用到 `main`。

接口依据：[DeepSeek JSON 输出](https://api-docs.deepseek.com/guides/json_mode/)、[思考模式开关](https://api-docs.deepseek.com/guides/thinking_mode/)。

## 两个操作入口

| Actions 工作流 | 手动运行的作用 |
| --- | --- |
| 修复验证与消息预览 | 先检查，再等待实际接收人发送“绑定早安”，私下返回该人的接收标识；已有标识也可以换绑 |
| 每日早安推送 | 向当前 `QQ_USER_OPENID` 主动发送一次完整早安；不启动绑定，不发送微信 |

接收人加机器人好友后，还需完成绑定、更新 Secret 和试收。绑定过程不会自动覆盖 GitHub Secret。换绑步骤详见 [QQ_SETUP.md](QQ_SETUP.md)。

常规操作选择 `main`。测试尚未合并的升级时选择对应功能分支；DeepSeek 本次试用分支为 `feat/deepseek-greetings-20261107`，合并前正式每日任务继续运行已启用的 QQ 稳定版。

## 本地安装与验证

Windows PowerShell 在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-qq.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe qq_push.py --dry-run
```

Linux/macOS 使用 `.venv/bin/python`。共 96 项隔离测试，不连接真实 QQ、微信或天气接口。预览不连接 QQ；若环境中设置了 `TIANAPI_KEY`，内容生成仍可查询天气和彩虹屁。

本地真实绑定命令为 `python qq_push.py --mode bind --timeout 300`，真实主动发送命令为 `python qq_push.py --mode test`。两者都会进行真实 QQ 操作；未准备好接收人时只运行预览。

## 定时与排错

每日工作流是 `.github/workflows/morning–send.yml`，文件名保留原来的 Unicode 短横。定时表达式仍为 `37 22 * * *`，即 UTC 22:37、次日北京时间 06:37；没有调整时间或触发方式，实际启动仍可能受 GitHub 调度延迟影响。

每次运行先安装依赖、检查核心逻辑，再执行 **发送 QQ 早安**。配置缺失或 QQ 拒绝请求时以退出码 `1` 结束。缺少接收标识时直接失败，不会等待绑定或改发给其他账号。

- QQ 返回有效消息 ID 才记录接口接受成功；手机实际收件和会话保留需由接收人确认。
- 绑定和主动发送是不同权限与流程；绑定回复成功不能代替主动试收。
- 天气不可用时显示“暂不可用”，不填入固定气温，不生成无依据的温度建议。
- 彩虹屁不可用时使用本地备用文案。
- 凭据获取与读取请求允许有限重试；发消息的 POST 仅执行一次。超时后先看手机，避免重复补发。
- 错误不输出原始 Token、接收标识、请求正文或接口响应正文；AI 失败使用原有文案，不影响 QQ 发送。

PR 检查只运行测试和内容预览，不读取 QQ Secrets。只有手动运行验证工作流才进入绑定任务；每日任务不接收聊天指令。

## 日期规则与兼容脚本

- 日期统一使用北京时间，一条消息共用一个日期快照。
- 农历生日和节日从当天所属农历年查找；农历三十遇到小月按廿九提醒。
- 农历转换沿用 `zhdate` 的 1900—2100 年数据，普通生日按非闰月处理。
- 雨雪和温度提醒可同时出现；节气近似公式、固定假期文案与原有个人配置继续沿用。
- `wechat_love.py` 与 `requirements.txt` 保留微信稳定版内容；恢复微信每日发送按 [回退指南](ROLLBACK.md) 执行，不需要重建原微信模板。
