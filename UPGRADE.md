# 升级到每日 QQ 早安

## 本次 DeepSeek 升级

本轮基于已启用的 QQ 稳定版 `1642c26e1244dc7888722494f25b31905108a40c`，备份为 `backup/before-deepseek-ai-20261107`。以下“升级到每日 QQ”是前一轮渠道升级说明；本次仍只发 QQ，不改收件人、个人日期设置或定时。

1. 在 GitHub Secrets 保存 `DEEPSEEK_API_KEY`，不提供或公开密钥值。
2. 本地运行测试、依赖检查和 `python qq_push.py --dry-run`；现在共 97 项测试。离线预览不调用 AI，不能代替实际 AI 验证。
3. 从 `feat/deepseek-greetings-20261107` 分支手动运行“每日早安推送”一次，在 QQ 私下检查三段文案。日志显示 `AI 3/3 栏` 表示三段均通过校验；较小计数表示部分或全部使用了原文案。
4. 实收和风格验收后再合并对应 AI PR。合并前 `main` 的 QQ 正式任务保持原版；不要重跑固定在旧提交的任务来验证新代码。
5. 不满意时设置仓库变量 `AI_ENABLED=false` 暂停 AI，或按回退指南撤销本次 AI 升级，保留 QQ 渠道。

本次升级基于已启用的微信稳定版 `6f9a33b6617147198be4902d0d6a19073efbb068`。每日发送渠道改为只发 QQ，定时表达式、个人日期配置和内容生成逻辑保持不变。原微信 Secrets 和稳定版备份继续保留。

## 升级前

1. 保留 [ROLLBACK.md](ROLLBACK.md) 和 `backup/before-qq-trial-20261107` 备份分支，不导出实际密钥。
2. QQ AppID 和 AppSecret 已存入 GitHub Secrets。正式接收人需添加机器人、完成绑定，并将 `QQ_USER_OPENID` 更新为该人的标识；原测试账号成功不代表正式接收人已经绑定。
3. 按 [QQ_SETUP.md](QQ_SETUP.md) 从功能分支手动运行“每日早安推送”，由正式接收人确认完整消息与读后会话保留。
4. 正式接收人试收成功前，不合并到 `main`。此时 `main` 的微信每日任务继续使用原配置。

## 改动范围

- 新增 QQ 客户端、接收人绑定、主动消息及对应隔离测试。
- 验证工作流的手动 QQ 任务固定执行绑定；已有接收标识也可换绑，不会误向旧接收人发早安。
- 每日工作流改用 `requirements-qq.txt`，执行 `python -u qq_push.py --mode test`，仅注入 QQ 与天气 Secrets。
- 每日缺少接收标识时退出失败，不会进入五分钟绑定等待。
- `wechat_love.py` 和 `requirements.txt` 与微信稳定版逐字节一致；定时保持 `37 22 * * *`。
- README、QQ 操作、变更与回退说明同步更新。

## 验证

使用 Python 3.12：

```powershell
python -m pip install -r requirements-qq.txt
python -m pip check
python -m unittest discover -s tests -v
python qq_push.py --dry-run
python wechat_love.py --dry-run
```

预期为 65 项隔离测试通过，依赖无冲突，预览正常。单元测试与预览不替代正式接收人的真实试收；若设置天气凭据，预览仍可能查询天气。

交付补丁以微信稳定版 `6f9a33b...` 为基准。在干净的相应版本上，先执行 `git apply --check <补丁完整路径>`，通过后再 `git apply <补丁完整路径>`。路径有空格时加引号。已有后续修改时先比较，不强行覆盖。

## 启用与观察

正式接收人验收后，合并 QQ 升级 PR 到 `main`。后续 **每日早安推送** 只发送 QQ；北京时间计划仍为 06:37，GitHub 实际调度延迟不在本次修改范围。

合并本身不手动补发。若需要补发，先查看当天是否已经收到，再决定是否运行一次，避免重复。查看 **Actions → 每日早安推送 → 发送 QQ 早安** 和接收人的手机结果。

异常时按 [ROLLBACK.md](ROLLBACK.md) 撤销 QQ 升级，恢复微信稳定版；不要撤销更早的微信稳定性修复。
