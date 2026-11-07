# QQ 接收人绑定、换绑与每日发送

QQ 机器人已经加为好友，不代表 GitHub 知道该向谁发送。每日任务只读取一个 `QQ_USER_OPENID`；换接收人时，应让新的接收人亲自发绑定口令，再更新这个 Secret。

## 准备

仓库 **Settings → Secrets and variables → Actions** 中保留 `QQ_APP_ID`、`QQ_APP_SECRET`，天气继续使用 `TIANAPI_KEY`。新接收人先用自己的 QQ 添加同一个机器人。

现有测试账号的 `QQ_USER_OPENID` 暂时保留。绑定任务不会自动修改 GitHub Secrets，也不会给旧接收人发送早安。

## 第一步：让实际接收人绑定

1. 打开 **Actions → 修复验证与消息预览 → Run workflow**。
2. 尚未合并 QQ 升级时，Branch 选择 `feat/qq-morning-trial-20261107`；合并后选 `main`。
3. 运行后等待 `verify` 成功，打开 **QQ 接收人绑定 → 绑定或更换 QQ 接收人**。
4. 看到“QQ 连接已就绪”后，让实际接收人在自己的 QQ 中给机器人发送：**绑定早安**。五分钟内发送；此时其他测试账号先不要发送相同口令。
5. 机器人会在该人的 QQ 私下回复接收标识。即使 GitHub 已存有旧标识，也能完成这次绑定；旧 Secret 此时尚未改变。
6. 编辑现有 GitHub Secret `QQ_USER_OPENID`，用新接收人回复中的那一整行标识替换旧值。不要填 QQ 号码、标题或说明文字。标识不要发到聊天或公开日志。

绑定标识只发回给对应发信人，公开日志、任务摘要和 Artifact 均不包含它。机器人提示需要接入 Agent，是因为当前没有聊天程序连接；绑定时由本项目临时连接，平时不提供聊天问答。

## 第二步：向新接收人主动试发

更新 Secret 后，打开 **Actions → 每日早安推送 → Run workflow**，升级未合并时仍选择上述功能分支。

该入口只向当前 `QQ_USER_OPENID` 发送一次 QQ 早安，不发送微信。它不等待“绑定早安”，缺少标识时直接失败。请让实际接收人确认：

- 收到完整的天气、生日和纪念日内容。
- 读完返回消息列表后，机器人会话仍保留。
- 消息可回看；如客户端支持，可自行置顶会话。

如果有错误，先看 **发送 QQ 早安** 步骤的 HTTP 状态和错误码。绑定回复成功不能证明主动推送权限可用。QQ 客户端的机器人接收权限及账号保护规则可能影响主动消息，应按 QQ 官方支持处理；无需反复重置密钥或重新绑定。

## 第三步：启用每日 QQ

正式接收人主动试收成功后，才合并对应 QQ 升级 PR 到 `main`。合并后原有每日工作流只发送 QQ，不再发送微信；`37 22 * * *` 定时表达式保持不变。

尚未合并时，功能分支上的手动试发不改变 `main` 的每日微信任务。保留原微信 Secrets 和备份分支，恢复方法见 [ROLLBACK.md](ROLLBACK.md)。

## 本地验证与依赖

```powershell
python -m pip install -r requirements-qq.txt
python -m pip check
python -m unittest discover -s tests -v
python qq_push.py --dry-run
```

`requirements-qq.txt` 包含原依赖和 `websocket-client==1.9.2`。WebSocket 只用于手动绑定；日常主动消息无需维持聊天网关连接。所有测试隔离真实接口，消息发送不自动重试，临时绑定连接在成功、超时或异常时关闭。

## 官方接口依据

- [获取访问凭证](https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/access-token.html)
- [WebSocket 连接与心跳](https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/event-emit/websocket.html)
- [单聊消息事件](https://bot.q.qq.com/wiki/develop/api-v2/autogen/event/c2c_message_create.html)
- [发送单聊消息](https://bot.q.qq.com/wiki/develop/api-v2/autogen/api/v2_users_user_openid_messages.post.html)
