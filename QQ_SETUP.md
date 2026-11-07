# QQ 独立聊天会话试收

此功能用于检验 QQ 机器人的独立会话是否满足“读完后仍保留入口、能够回看早安消息”的需求。当前先手动试收，日常微信推送继续沿用已经启用的正式版；不修改 `37 22 * * *` 定时表达式。

QQ 后台提示需要接入 Agent，是指机器人尚未连接处理程序。本项目用 Python 对接官方接口，提供接收人绑定和早安试发，不接入 AI 模型。绑定流程只在手动运行期间连接 QQ，暂不提供全天候聊天问答。

## 准备凭据

在 QQ 开放平台创建机器人，并在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 保存：

| 名称 | 内容 |
| --- | --- |
| `QQ_APP_ID` | QQ 机器人的 AppID |
| `QQ_APP_SECRET` | QQ 机器人的 AppSecret |
| `QQ_USER_OPENID` | 首次绑定后通过 QQ 私下获得的接收标识；不是 QQ 号码 |

`TIANAPI_KEY` 仍使用原有天气凭据。前两个 QQ Secret 配好后即可开始绑定；微信原有的 Secrets 不需要修改。所有凭据与接收标识都不应贴进公开代码、聊天或截图。

## 第一次运行：绑定接收人

1. 打开仓库 **Actions → 修复验证与消息预览**，点击 **Run workflow**。
2. 在 **Branch** 选择 `feat/qq-morning-trial-20261107`，再点 **Run workflow**。
3. 等待 `verify` 检查通过，打开 **QQ 接收人绑定与试发 → QQ 绑定或早安试发**。看到“QQ 连接已就绪”后，在手机 QQ 中给机器人发送四个字：**绑定早安**。
4. 等待窗口为五分钟。机器人会私下回复接收标识及保存说明；只接受精确的绑定口令，不处理其他聊天指令。
5. 把回复中的接收标识整行复制到 GitHub 新增 Secret：`QQ_USER_OPENID`。不要复制标题、空格或说明文字，也不要填 QQ 号码。

绑定标识只通过 QQ 回复给对应发送者，不写入仓库、公开日志、任务摘要或 Artifact。用户手动保存 Secret 后才启用固定接收目标，绑定任务不会自动修改 GitHub Secrets。

如等待超时，重新运行一次流程并及时发送口令即可。未收到 QQ 回复时，先查看工作流错误码，不重复修改凭据或随意重置密钥。

## 第二次运行：主动试发早安

保存 `QQ_USER_OPENID` 后，再次从相同分支手动运行 **修复验证与消息预览**。程序会根据接收标识已存在而切换为主动试发，不再等待绑定口令。

本次发信不携带被动回复上下文，用于检验日后定时主动推送的可行性。若收到拒收或无主动消息权限错误，请检查手机 QQ 中该机器人的“允许主动发送”设置及后台应用权限。

收到后请确认：

- 天气、生日和纪念日内容是否正常。
- 读完返回后，机器人会话是否还在 QQ 消息列表。
- 历史消息能否回看，以及当前客户端是否允许置顶该会话。

此阶段不会把正式每日任务切换成 QQ，也不会同时调用微信发送接口。完成试收后再决定是否将 QQ 用于每日发送，或与微信并行。

## 本地验证

```powershell
python -m pip install -r requirements-qq.txt
python -m pip check
python -m unittest discover -s tests -v
python qq_push.py --dry-run
```

`requirements-qq.txt` 包含原项目依赖及固定版本的 `websocket-client==1.9.2`。WebSocket 仅用于一次性接收 QQ 绑定消息；现有微信环境不需要安装 QQ 额外依赖。单元测试通过假连接隔离真实 QQ、微信和天气接口。

## 错误处理

- 身份验证会检查 HTTP 和业务错误码，失败时进程返回 `1`。
- 凭据获取及连接入口请求允许有限重试；消息发送只尝试一次，超时后先查看手机是否收到，避免重复发送。
- QQ 网关只接受已知官方 `wss` 地址，按官方协议维护心跳并限制绑定等待时间。
- 请求异常不打印原始 Token、接收标识、消息事件或接口响应正文。
- 绑定结束、等待超时或连接异常时，都会关闭临时连接。

## 官方接口依据

- [获取访问凭证](https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/access-token.html)
- [WebSocket 连接与心跳](https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/event-emit/websocket.html)
- [单聊消息事件](https://bot.q.qq.com/wiki/develop/api-v2/autogen/event/c2c_message_create.html)
- [发送单聊消息](https://bot.q.qq.com/wiki/develop/api-v2/autogen/api/v2_users_user_openid_messages.post.html)

试运行基于微信稳定版提交 `6f9a33b6617147198be4902d0d6a19073efbb068`。回退与保留旧版的说明见 [ROLLBACK.md](ROLLBACK.md)。
