# 升级指南

本次修复基于 `main` 提交 `c6f6fd4338762b0ac78b27ebbc00daa8df1619d4`。请同时保留 [ROLLBACK.md](ROLLBACK.md) 和交付的原始快照压缩包。

## 升级前

1. 核对仓库当前代码是否仍以该提交为基准。若之后有改动，先比较差异，保留自己的修改。
2. 若使用本地 Git 工作区，先运行 `git status --short`，保存已有未提交修改；不要直接覆盖或重置工作区。
3. 记录当前模板字段和 Secrets 名称，无需复制或导出密钥。此次不改变模板、密钥名称、个人日期设置及定时表达式。
4. 使用独立分支审查修复，待本地检查通过后再应用到 `main`。尚未合并时，原定时任务继续使用原代码。

## 应用代码

修复包包含更新后的完整项目和单独的 Git 补丁。补丁只适用于上述基准版本；在项目根目录执行：

```powershell
git apply --check <修复补丁的完整路径>
git apply <修复补丁的完整路径>
```

只有 `--check` 通过后才执行第二条。路径含空格时请用引号括起。若检查失败，先处理版本差异，不要强制应用补丁。

需要更新的已有文件是 `wechat_love.py` 和 `.github/workflows/morning–send.yml`；新增文件是 `requirements.txt`、`tests/test_wechat_love.py`、`.gitignore` 及四份 Markdown 文档。请保留 `37 22 * * *` 的定时设置。

11 月 7 日另增 `.github/workflows/verify.yml`，用于 PR 的云端测试和预览，不包含正式发信步骤。使用 11 月 7 日的新修复包和补丁时，该文件也会一起应用或撤销。

## 验证

使用 Python 3.12 创建隔离环境，执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe wechat_love.py --dry-run
```

预期：依赖检查无冲突，36 项测试通过，预览正常且不发送微信。未配置 `TIANAPI_KEY` 时出现天气不可用提示属于预期行为。

工作流升级至 Python 3.12，选择该版本是为了与已完成的本地验证一致。`requirements.txt` 固定了 `requests`、`zhdate` 和间接依赖。后续更新依赖时，应在隔离环境中安装、运行上述检查，再统一更新版本，不建议每天自动安装不确定版本。

## 应用后的观察

在决定正式发送后，可等待下一次定时运行；如果当天没有发送过，也可通过 **Actions → 每日早安推送 → Run workflow** 手动验证。此操作会发送真实消息，超时或界面延迟时先查看微信再决定是否再次运行。

检查 Actions 的依赖安装、测试和发送三个步骤，并确认收件端内容；重点检查天气不可用占位、雨雪提醒和生日倒计时。若出现异常，按 [ROLLBACK.md](ROLLBACK.md) 恢复，保留失败运行的错误码方便排查。
