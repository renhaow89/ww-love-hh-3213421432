# 微信每日早安推送

通过 GitHub Actions 每天运行 Python 脚本，向指定微信用户发送早安模板消息，包含杭州天气、恋爱天数、农历生日倒计时、节日提醒和随机文案。

本次稳定性修复的升级步骤见 [UPGRADE.md](UPGRADE.md)，变更记录见 [CHANGELOG.md](CHANGELOG.md)，恢复方法见 [ROLLBACK.md](ROLLBACK.md)。

QQ 独立会话接入目前处于手动试收阶段。机器人提示需要接入 Agent 时，按 [QQ 接收人绑定与试发指南](QQ_SETUP.md) 操作，由本项目的 Python 程序完成对接。日常微信推送与时间设置继续保留。

## 环境与配置

- Python 3.12，与工作流及本地验证环境一致。
- 依赖固定在 `requirements.txt`；不需要额外安装测试框架。
- 微信端需要可用的 AppID、AppSecret、接收者 OpenID 和模板 ID。

在仓库的 **Settings → Secrets and variables → Actions → New repository secret** 中配置：

| Secret | 是否必需 | 用途 |
| --- | --- | --- |
| `APP_ID` | 是 | 微信 AppID |
| `APP_SECRET` | 是 | 微信 AppSecret |
| `OPEN_ID` | 是 | 消息接收者 |
| `TEMPLATE_ID` | 是 | 微信模板 ID |
| `TIANAPI_KEY` | 否 | 天行天气和彩虹屁接口；缺失或不可用时降级推送 |

脚本启动时检查四个微信必需配置；缺失时以非零退出码结束，不调用微信接口。不要将实际密钥写进代码、提交记录或聊天。

`wechat_love.py` 顶部保留原有城市、恋爱起始日和农历生日配置。本次没有改变这些个人设置，也没有改变现有模板字段。

## 微信模板字段

已有模板可以继续使用；字段名必须与代码一致：

| 字段 | 内容 |
| --- | --- |
| `top1`、`top2` | 早安问候 |
| `d`、`c` | 日期、城市 |
| `w`、`t` | 天气、温度范围 |
| `ld`、`bl` | 恋爱天数、农历生日倒计时 |
| `h` | 节日或节气文案 |
| `t1`、`t2`、`t3` | 天气提醒 |
| `q1`、`q2`、`q3`、`q4` | 彩虹屁文案 |

微信模板中的变量形式为 `{{top1.DATA}}`，其余字段同理。现有分段长度和配色继续沿用，长文案仍可能被截断，手机端最终排版需实际查看。

## 本地安装、测试和预览

先确认 `python --version` 为 3.12。Windows PowerShell 在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe wechat_love.py --dry-run
```

Linux/macOS 将上面的 `.\.venv\Scripts\python.exe` 替换为 `.venv/bin/python`。

`--dry-run` 只生成消息预览，不获取微信 Token、不发送消息，不需要微信凭据。如果设置了 `TIANAPI_KEY`，预览仍会读取天气和彩虹屁；未设置时使用中性的天气占位和本地文案。测试用例全部隔离 HTTP，不会真实发信。

真实推送命令为 `python wechat_love.py`，仅在准备好正式发送时执行。

## 定时运行与排错

新增 `.github/workflows/verify.yml`：PR 创建或更新时，在 GitHub 的 Ubuntu 环境运行依赖检查、回归测试与消息预览。该验证工作流不注入微信或天气密钥，不发送消息；实际发送仍使用下述每日推送工作流。

工作流文件是 `.github/workflows/morning–send.yml`，其中短横为原有的 Unicode 字符。当前定时表达式保持为 `37 22 * * *`：UTC 22:37，即次日北京时间 06:37。没有变更定时、时区或触发方式；实际启动时间仍可能受 GitHub 调度延迟影响。

每次工作流先安装依赖、运行回归测试，再读取 Secrets 并推送。查看结果的路径：仓库 → **Actions → 每日早安推送 → 某次运行 → 发送消息**。点击 **Run workflow** 会真实发送消息，请留意当天是否已经发送。

- 成功：微信接口返回 `errcode=0`，进程退出码为 `0`。这表示接口已接受请求，手机是否最终展示仍应查看微信。
- 必需配置缺失、Token 获取失败或发送失败：退出码为 `1`，Actions 可将任务标为失败；可在个人 GitHub 通知设置中开启 Actions 失败通知。
- 天气失败：显示“暂不可用”，不填入固定气温，也不据此生成具体温度建议；消息仍可发送。
- 彩虹屁失败：使用本地备用文案，不阻断消息。
- 读取请求遇到超时、HTTP 429 或 5xx 时最多尝试三次；普通 HTTP 4xx 不重试。
- 发送 POST 不自动重试。超时可能发生在微信已经接收请求之后，请先查看收件端，再决定是否补发。

日志只输出配置名称和错误码，不输出实际密钥、Token URL 或失败请求的完整载荷。成功日志保留原有消息预览，因此公开仓库的 Actions 日志仍可能展示个人文案。

## 日期规则与当前范围

- 日期统一按北京时间生成，一条消息使用同一个日期快照。
- 农历生日及节日从当天所属农历年开始查找，修复春节前腊八、小年等跨年计算错误。
- 农历三十遇到小月时按廿九提醒；不支持的日期直接报错，不再假定为元旦。
- 农历转换沿用 `zhdate` 的 1900—2100 年数据；普通生日按非闰月处理。
- 雨雪与温度提醒可以同时出现，例如雨天带伞添衣、雪天保暖防滑。
- 节气近似公式、固定假期文案、原有问候语长度策略仍沿用；没有接入每年调休表，也没有新增节气算法。
