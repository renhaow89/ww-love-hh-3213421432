# -*- coding: utf-8 -*-
"""QQ 早安推送：接收人绑定与主动发送。"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

import wechat_love
import ai_greetings


API_BASE = "https://api.bot.qq.com"
BIND_MESSAGE = "绑定早安"
C2C_INTENT = 1 << 25


class QQPushError(RuntimeError):
    pass


def _error_code(payload):
    code = payload.get("code")
    return code if type(code) is int else None


def _validate_recipient(openid):
    if not isinstance(openid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", openid):
        raise QQPushError("QQ_USER_OPENID 无效，请使用绑定消息中的接收标识，不要填 QQ 号码")
    return openid


class QQClient:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self.token = None

    @classmethod
    def from_env(cls):
        names = ("QQ_APP_ID", "QQ_APP_SECRET")
        values = {name: os.environ.get(name, "").strip() for name in names}
        missing = [name for name in names if not values[name]]
        if missing:
            raise QQPushError("缺少必要配置：" + ", ".join(missing))
        return cls(values["QQ_APP_ID"], values["QQ_APP_SECRET"])

    def _request(self, method, path, label, *, payload=None, authenticate=True, read_only=False):
        if authenticate and self.token is None:
            self.access_token()
        headers = {"Authorization": f"QQBot {self.token}"} if authenticate else {}
        attempts = 3 if read_only else 1
        for attempt in range(attempts):
            try:
                if method == "GET":
                    response = requests.get(API_BASE + path, headers=headers, timeout=10)
                else:
                    response = requests.post(API_BASE + path, headers=headers, json=payload, timeout=10)
                result = response.json()
            except (requests.RequestException, ValueError):
                if attempt + 1 < attempts:
                    time.sleep(attempt + 1)
                    continue
                # 不输出原始异常，避免其中的 Token、接收标识或请求正文进入日志。
                suffix = "；请先检查 QQ 是否收到，避免重复发送" if not read_only else ""
                raise QQPushError(f"{label}结果未确认{suffix}") from None
            if not isinstance(result, dict):
                raise QQPushError(f"{label}返回格式异常")
            code = _error_code(result)
            if "code" in result and type(result["code"]) is not int:
                raise QQPushError(f"{label}错误码格式异常")
            if response.status_code >= 400 or code not in (None, 0):
                if response.status_code in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
                    time.sleep(attempt + 1)
                    continue
                detail = f"，错误码 {code}" if code is not None else ""
                raise QQPushError(f"{label}失败：HTTP {response.status_code}{detail}")
            return result
        raise QQPushError(f"{label}失败")

    def access_token(self):
        result = self._request(
            "POST", "/app/getAppAccessToken", "QQ 身份验证",
            payload={"appId": self.app_id, "clientSecret": self.app_secret},
            authenticate=False, read_only=True,
        )
        token = result.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise QQPushError("QQ 身份验证未返回有效凭据，请检查两个 QQ Secret")
        self.token = token
        return token

    def gateway_url(self):
        result = self._request("GET", "/gateway/bot", "QQ 连接入口", read_only=True)
        url = result.get("url")
        if not isinstance(url, str):
            raise QQPushError("QQ 连接入口缺失")
        parsed = urlparse(url)
        if parsed.scheme != "wss" or parsed.hostname not in {
            "api.bot.qq.com", "api.sgroup.qq.com", "sandbox.api.sgroup.qq.com"
        } or parsed.username is not None or parsed.password is not None:
            raise QQPushError("QQ 连接入口不属于已知的官方加密网关")
        return url

    def send_text(self, openid, text, *, reply_to=None):
        recipient = _validate_recipient(openid)
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            raise QQPushError("QQ 文本为空或过长")
        payload = {"msg_type": 0, "content": text}
        if reply_to is not None:
            if not isinstance(reply_to, str) or not reply_to:
                raise QQPushError("QQ 绑定消息缺少有效的消息标识")
            payload.update(msg_id=reply_to, msg_seq=1)
        # 发信 POST 仅执行一次；普通试发不携带回复上下文，用于验证主动发送能力。
        result = self._request("POST", f"/v2/users/{recipient}/messages", "QQ 消息发送", payload=payload)
        if not isinstance(result.get("id"), str) or not result["id"]:
            raise QQPushError("QQ 未返回发送确认，请检查手机后再决定是否重试")
        return result["id"]


class GatewayConnection:
    def __init__(self, url):
        # 微信日常任务无需安装这个依赖；只有 QQ 首次绑定时才加载。
        try:
            import websocket
        except ImportError:
            raise QQPushError("缺少 QQ 绑定依赖，请安装 requirements-qq.txt") from None
        self.library = websocket
        try:
            self.socket = websocket.create_connection(url, timeout=10)
        except (websocket.WebSocketException, OSError):
            raise QQPushError("无法建立 QQ 连接，请检查网络及机器人后台设置") from None

    def receive(self, timeout):
        try:
            self.socket.settimeout(timeout)
            raw = self.socket.recv()
        except self.library.WebSocketTimeoutException:
            raise TimeoutError from None
        except (self.library.WebSocketException, OSError):
            raise QQPushError("QQ 连接已中断，请重新运行绑定流程") from None
        if not raw:
            raise QQPushError("QQ 连接已关闭，请重新运行绑定流程")
        try:
            result = json.loads(raw)
        except (TypeError, ValueError):
            raise QQPushError("QQ 网关返回格式异常") from None
        if not isinstance(result, dict):
            raise QQPushError("QQ 网关返回格式异常")
        return result

    def send(self, payload):
        try:
            self.socket.send(json.dumps(payload, ensure_ascii=False))
        except (self.library.WebSocketException, OSError):
            raise QQPushError("无法向 QQ 网关发送连接信息") from None

    def close(self):
        try:
            self.socket.close()
        except (self.library.WebSocketException, OSError):
            pass


def bind_receiver(client, timeout_seconds=300, *, connection_factory=GatewayConnection, clock=time.monotonic):
    token = client.access_token()
    connection = connection_factory(client.gateway_url())
    try:
        try:
            hello = connection.receive(10)
        except TimeoutError:
            raise QQPushError("QQ 网关握手超时，请重新运行绑定流程") from None
        interval = hello.get("d", {}).get("heartbeat_interval") if isinstance(hello.get("d"), dict) else None
        if hello.get("op") != 10 or type(interval) is not int or interval <= 0:
            raise QQPushError("QQ 网关握手格式异常")
        connection.send({"op": 2, "d": {"token": f"QQBot {token}", "intents": C2C_INTENT, "shard": [0, 1]}})
        deadline = clock() + timeout_seconds
        heartbeat_interval = interval / 1000 * 0.8
        next_heartbeat = clock() + heartbeat_interval
        waiting_ack = False
        sequence = None
        ready = False
        print(f"正在连接 QQ；连接就绪后，请在 {timeout_seconds} 秒内给机器人发送：{BIND_MESSAGE}", flush=True)
        while clock() < deadline:
            now = clock()
            if now >= next_heartbeat:
                if waiting_ack:
                    raise QQPushError("QQ 心跳确认超时，请重新运行绑定流程")
                connection.send({"op": 1, "d": sequence})
                waiting_ack = True
                next_heartbeat = now + heartbeat_interval
            wait = max(0.01, min(5, next_heartbeat - clock(), deadline - clock()))
            try:
                event = connection.receive(wait)
            except TimeoutError:
                continue
            if type(event.get("s")) is int:
                sequence = event["s"]
            opcode = event.get("op")
            if opcode == 11:
                waiting_ack = False
                continue
            if opcode == 1:
                connection.send({"op": 1, "d": sequence})
                waiting_ack = True
                next_heartbeat = clock() + heartbeat_interval
                continue
            if opcode in (7, 9):
                raise QQPushError("QQ 要求重新建立连接，请检查权限后重新运行绑定流程")
            if opcode != 0:
                continue
            if event.get("t") == "READY":
                ready = True
                print(f"✅ QQ 连接已就绪，现在请在手机 QQ 给机器人发送：{BIND_MESSAGE}", flush=True)
                continue
            if not ready or event.get("t") != "C2C_MESSAGE_CREATE":
                continue
            data = event.get("d")
            if not isinstance(data, dict):
                continue
            content = data.get("content")
            if not isinstance(content, str) or content.strip() != BIND_MESSAGE:
                continue
            author = data.get("author")
            if not isinstance(author, dict) or author.get("bot") is True:
                continue
            recipient = _validate_recipient(author.get("user_openid"))
            confirmation = (
                "✅ QQ 早安接入测试成功！\n\n"
                "你的接收标识（不是 QQ 号码）：\n" + recipient + "\n\n"
                "请把上面这一行完整保存到 GitHub 项目的 Secret：QQ_USER_OPENID。"
                "然后告诉助手已保存，再进行早安消息试发。"
            )
            client.send_text(recipient, confirmation, reply_to=data.get("id"))
            print("✅ 接收标识已通过 QQ 私下回传，请保存为 QQ_USER_OPENID；日志不会显示该标识", flush=True)
            return
        raise QQPushError("绑定等待超时；重新运行后，请在五分钟内向机器人发送“绑定早安”")
    finally:
        connection.close()


@dataclass
class MorningMessage:
    text: str
    ai_copy: ai_greetings.GeneratedCopy


def compose_morning_message(*, use_ai=True):
    fields = wechat_love.build_message()["data"]
    def value(name):
        return fields[name]["value"].strip()
    generated = ai_greetings.generate(fields) if use_ai else ai_greetings.GeneratedCopy()
    greeting = value("top1") + value("top2")
    if "greeting" in generated.segments:
        salutation = "早安，我最爱的宝宝！"
        before, marker, _ = greeting.partition(salutation)
        greeting = (before + marker if marker else salutation) + generated.segments["greeting"]
    care = generated.segments.get("weather_care", value("t1") + value("t2") + value("t3"))
    love = generated.segments.get("love_note", "".join(value(name) for name in ("q1", "q2", "q3", "q4")))
    text = "\n".join([
        "💕 早安",
        greeting,
        "📅 日期：" + value("d"),
        "📍 城市：" + value("c") + " | " + value("w"),
        "🌡️ 气温：" + value("t"),
        "💖 恋爱打卡：第 " + value("ld") + " 天",
        "🎂 生日倒数：" + value("bl") + " 天",
        "⭐ " + value("h"),
        "🔔 " + care,
        "💌 " + love,
    ])
    if use_ai:
        print(f"文案来源：AI {len(generated.segments)}/3 栏，其余使用原有文案", flush=True)
    return MorningMessage(text, generated)


def morning_text():
    # 预览与 PR 检查始终不调用收费 AI 接口，也不写去重记录。
    return compose_morning_message(use_ai=False).text


def main(argv=None):
    parser = argparse.ArgumentParser(description="QQ 接收人绑定与早安试发")
    parser.add_argument("--mode", choices=("trial", "bind", "test"), default="trial")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true", help="仅显示早安正文，不连接 QQ")
    args = parser.parse_args(argv)
    try:
        if args.dry_run:
            print(morning_text())
            return 0
        if not 30 <= args.timeout <= 600:
            raise QQPushError("绑定等待时间应为 30～600 秒")
        client = QQClient.from_env()
        recipient = os.environ.get("QQ_USER_OPENID", "").strip()
        if args.mode == "bind" or (args.mode == "trial" and not recipient):
            bind_receiver(client, args.timeout)
        else:
            _validate_recipient(recipient)
            message = compose_morning_message()
            client.send_text(recipient, message.text)
            ai_greetings.record_sent(message.ai_copy)
            print("✅ QQ 接口已接受早安消息，请在手机上确认消息与会话是否保留")
        return 0
    except (QQPushError, ValueError) as exc:
        # ValueError 可能来自日期配置；不记录包含请求数据的原始异常。
        detail = str(exc) if isinstance(exc, QQPushError) else "无法生成早安内容，请检查日期配置"
        print("❌ " + detail, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
