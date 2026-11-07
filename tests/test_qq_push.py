import contextlib
import io
import json
import os
from unittest import TestCase
from unittest.mock import Mock, patch

import requests

import qq_push as qq


RECIPIENT = "ABCDEF0123456789ABCDEF0123456789"
TOKEN = "FAKE_QQ_TOKEN_NEVER_LOG"
SECRET = "FAKE_QQ_SECRET_NEVER_LOG"


def response(payload, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode("utf-8")
    return result


def hello(interval=45000):
    return {"op": 10, "d": {"heartbeat_interval": interval}}


def ready():
    return {"op": 0, "s": 1, "t": "READY", "d": {"session_id": "fake-session"}}


def bind_event(**overrides):
    data = {"id": "FAKE_MESSAGE_ID", "author": {"user_openid": RECIPIENT}, "content": "绑定早安"}
    data.update(overrides)
    return {"op": 0, "s": 2, "t": "C2C_MESSAGE_CREATE", "d": data}


class Clock:
    def __init__(self):
        self.now = 0
    def __call__(self):
        return self.now


class FakeConnection:
    def __init__(self, events, clock, on_send=None):
        self.events = list(events)
        self.clock = clock
        self.sent = []
        self.closed = False
        self.on_send = on_send
    def receive(self, timeout):
        if self.events:
            self.clock.now += 0.01
            event = self.events.pop(0)
            if isinstance(event, BaseException):
                raise event
            return event
        self.clock.now += timeout
        raise TimeoutError
    def send(self, payload):
        self.sent.append(payload)
        if self.on_send:
            self.on_send(payload, self)
    def close(self):
        self.closed = True


class QQTests(TestCase):
    def setUp(self):
        # 不允许测试访问真实机器人、真实天气或发送任何消息。
        self.get = self.enterContext(patch.object(qq.requests, "get"))
        self.post = self.enterContext(patch.object(qq.requests, "post"))
        self.get.side_effect = AssertionError("测试禁止真实 GET")
        self.post.side_effect = AssertionError("测试禁止真实 POST")
        self.enterContext(patch.object(qq.time, "sleep"))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch.dict(os.environ, {"QQ_APP_ID": "123456789", "QQ_APP_SECRET": SECRET, "QQ_USER_OPENID": ""}))
        self.client = qq.QQClient("123456789", SECRET)
        self.client.token = TOKEN

    def use_post(self, payload, status=200):
        self.post.side_effect = None
        self.post.return_value = response(payload, status)

    def run_binding(self, events, *, on_send=None):
        clock = Clock()
        connection = FakeConnection(events, clock, on_send)
        client = Mock()
        client.access_token.return_value = TOKEN
        client.gateway_url.return_value = "wss://api.bot.qq.com/websocket/"
        qq.bind_receiver(client, 30, connection_factory=lambda url: connection, clock=clock)
        return client, connection

    def test_missing_secrets_are_reported_before_network(self):
        with patch.dict(os.environ, {"QQ_APP_SECRET": ""}):
            self.assertEqual(qq.main([]), 1)
        self.assertIn("QQ_APP_SECRET", self.output.getvalue())
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_token_business_failure_is_checked_even_on_http_200(self):
        self.use_post({"code": 100016, "message": SECRET})
        with self.assertRaises(qq.QQPushError) as caught:
            self.client.access_token()
        self.assertIn("100016", str(caught.exception))
        self.assertNotIn(SECRET, str(caught.exception))

    def test_token_requires_nonempty_string(self):
        for token in (None, "", "  ", 42):
            with self.subTest(token=token):
                self.use_post({"access_token": token})
                with self.assertRaises(qq.QQPushError):
                    self.client.access_token()

    def test_string_business_error_code_is_not_treated_as_success(self):
        self.use_post({"code": "100016", "access_token": TOKEN})
        with self.assertRaises(qq.QQPushError):
            self.client.access_token()

    def test_active_send_has_no_passive_reply_context(self):
        self.use_post({"id": "sent-message"})
        self.assertEqual(self.client.send_text(RECIPIENT, "早安试收"), "sent-message")
        payload = self.post.call_args.kwargs["json"]
        self.assertEqual(payload, {"msg_type": 0, "content": "早安试收"})
        self.assertEqual(self.post.call_args.kwargs["headers"]["Authorization"], "QQBot " + TOKEN)

    def test_bind_reply_uses_message_context(self):
        self.use_post({"id": "sent-message"})
        self.client.send_text(RECIPIENT, "绑定成功", reply_to="incoming-message")
        payload = self.post.call_args.kwargs["json"]
        self.assertEqual(payload["msg_id"], "incoming-message")
        self.assertEqual(payload["msg_seq"], 1)

    def test_send_timeout_is_not_retried_or_exposed(self):
        self.post.side_effect = requests.Timeout(TOKEN + RECIPIENT)
        with self.assertRaises(qq.QQPushError) as caught:
            self.client.send_text(RECIPIENT, "早安")
        self.post.assert_called_once()
        self.assertIn("避免重复发送", str(caught.exception))
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertNotIn(RECIPIENT, str(caught.exception))

    def test_send_http_error_is_not_retried(self):
        self.use_post({"message": TOKEN}, 503)
        with self.assertRaises(qq.QQPushError):
            self.client.send_text(RECIPIENT, "早安")
        self.post.assert_called_once()

    def test_send_business_error_in_http_200_fails(self):
        self.use_post({"code": 40034105, "message": TOKEN})
        with self.assertRaises(qq.QQPushError) as caught:
            self.client.send_text(RECIPIENT, "早安")
        self.assertIn("40034105", str(caught.exception))
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_send_requires_delivery_confirmation(self):
        for payload in ({}, {"id": ""}, {"id": 1}, []):
            with self.subTest(payload=payload):
                self.use_post(payload)
                with self.assertRaises(qq.QQPushError):
                    self.client.send_text(RECIPIENT, "早安")

    def test_invalid_recipient_is_rejected_before_authentication(self):
        self.client.token = None
        for value in (None, "", "123456789", "../users/example", RECIPIENT + "/x"):
            with self.subTest(value=value), self.assertRaises(qq.QQPushError):
                self.client.send_text(value, "早安")
        self.post.assert_not_called()

    def test_invalid_message_is_not_sent(self):
        for text in ("", "  ", "x" * 2001):
            with self.subTest(text_length=len(text)), self.assertRaises(qq.QQPushError):
                self.client.send_text(RECIPIENT, text)
        self.post.assert_not_called()

    def test_read_timeout_can_recover(self):
        self.get.side_effect = [requests.Timeout(TOKEN), requests.Timeout(TOKEN), response({"url": "wss://api.bot.qq.com/websocket/"})]
        self.assertEqual(self.client.gateway_url(), "wss://api.bot.qq.com/websocket/")
        self.assertEqual(self.get.call_count, 3)
        self.assertNotIn(TOKEN, self.output.getvalue())

    def test_gateway_rejects_unencrypted_or_foreign_addresses(self):
        for url in ("ws://api.bot.qq.com/websocket", "wss://example.com/", "wss://api.bot.qq.com.example.com/", "wss://user@api.bot.qq.com/"):
            with self.subTest(url=url):
                self.get.side_effect = None
                self.get.return_value = response({"url": url})
                with self.assertRaises(qq.QQPushError):
                    self.client.gateway_url()

    def test_binding_returns_identifier_only_to_its_owner(self):
        client, connection = self.run_binding([hello(), ready(), bind_event(), bind_event()])
        client.send_text.assert_called_once()
        args, kwargs = client.send_text.call_args
        self.assertEqual(args[0], RECIPIENT)
        self.assertIn(RECIPIENT, args[1])
        self.assertIn("QQ_USER_OPENID", args[1])
        self.assertEqual(kwargs["reply_to"], "FAKE_MESSAGE_ID")
        self.assertNotIn(RECIPIENT, self.output.getvalue())
        self.assertNotIn(TOKEN, self.output.getvalue())
        self.assertTrue(connection.closed)

    def test_binding_ignores_other_messages_and_bot_messages(self):
        events = [hello(), bind_event(), ready(), bind_event(content="你好"), bind_event(content=None), bind_event(author={"bot": True, "user_openid": RECIPIENT}), {"op": 0, "t": "GROUP_AT_MESSAGE_CREATE", "d": {}}, bind_event()]
        client, connection = self.run_binding(events)
        client.send_text.assert_called_once()
        self.assertTrue(connection.closed)

    def test_binding_heartbeat_uses_latest_sequence(self):
        def heartbeat(payload, connection):
            if payload["op"] == 1:
                connection.events.extend([{"op": 11}, bind_event()])
        client, connection = self.run_binding([hello(1000), ready(), {"op": 0, "s": 7, "t": "IGNORED"}], on_send=heartbeat)
        self.assertIn({"op": 1, "d": 7}, connection.sent)
        client.send_text.assert_called_once()

    def test_missing_heartbeat_ack_closes_connection(self):
        clock = Clock()
        connection = FakeConnection([hello(1000), ready()], clock)
        client = Mock()
        client.access_token.return_value = TOKEN
        with self.assertRaises(qq.QQPushError) as caught:
            qq.bind_receiver(client, 30, connection_factory=lambda url: connection, clock=clock)
        self.assertIn("心跳", str(caught.exception))
        client.send_text.assert_not_called()
        self.assertTrue(connection.closed)

    def test_binding_timeout_does_not_send(self):
        clock = Clock()
        connection = FakeConnection([hello(), ready()], clock)
        client = Mock()
        client.access_token.return_value = TOKEN
        with self.assertRaises(qq.QQPushError) as caught:
            qq.bind_receiver(client, 30, connection_factory=lambda url: connection, clock=clock)
        self.assertIn("等待超时", str(caught.exception))
        client.send_text.assert_not_called()
        self.assertTrue(connection.closed)

    def test_invalid_handshake_is_rejected_and_closed(self):
        for first in ({"op": 9}, hello(0), hello("45000")):
            with self.subTest(first=first):
                clock = Clock()
                connection = FakeConnection([first], clock)
                client = Mock()
                client.access_token.return_value = TOKEN
                with self.assertRaises(qq.QQPushError):
                    qq.bind_receiver(client, 30, connection_factory=lambda url: connection, clock=clock)
                self.assertEqual(connection.sent, [])
                self.assertTrue(connection.closed)

    def test_gateway_reconnect_request_fails_without_reply(self):
        for opcode in (7, 9):
            with self.subTest(opcode=opcode), self.assertRaises(qq.QQPushError):
                self.run_binding([hello(), ready(), {"op": opcode}])

    def test_recipient_must_come_from_c2c_user_openid(self):
        with self.assertRaises(qq.QQPushError):
            self.run_binding([hello(), ready(), bind_event(author={"id": "123456789"})])

    def test_trial_without_recipient_uses_binding_mode(self):
        with patch.object(qq, "bind_receiver") as bind:
            self.assertEqual(qq.main([]), 0)
        bind.assert_called_once()
        self.post.assert_not_called()

    def test_trial_with_recipient_uses_active_send_only(self):
        with patch.dict(os.environ, {"QQ_USER_OPENID": RECIPIENT}), patch.object(qq, "morning_text", return_value="早安试收"), patch.object(qq.QQClient, "send_text", return_value="sent") as send, patch.object(qq, "bind_receiver") as bind, patch.object(qq.wechat_love, "send_message") as wechat:
            self.assertEqual(qq.main([]), 0)
        send.assert_called_once_with(RECIPIENT, "早安试收")
        bind.assert_not_called()
        wechat.assert_not_called()

    def test_preview_does_not_need_credentials_or_connect_qq(self):
        with patch.dict(os.environ, {"QQ_APP_ID": "", "QQ_APP_SECRET": ""}), patch.object(qq, "morning_text", return_value="早安预览"):
            self.assertEqual(qq.main(["--dry-run"]), 0)
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_main_failure_does_not_print_private_request_data(self):
        with patch.dict(os.environ, {"QQ_USER_OPENID": RECIPIENT}), patch.object(qq, "morning_text", return_value="早安"):
            self.post.side_effect = requests.Timeout(TOKEN + RECIPIENT + SECRET)
            self.assertEqual(qq.main([]), 1)
        for value in (TOKEN, RECIPIENT, SECRET):
            self.assertNotIn(value, self.output.getvalue())

    def test_morning_text_reuses_existing_fields(self):
        names = ("top1", "top2", "d", "c", "w", "t", "ld", "bl", "h", "t1", "t2", "t3", "q1", "q2", "q3", "q4")
        fields = {name: {"value": name + "\n"} for name in names}
        with patch.object(qq.wechat_love, "build_message", return_value={"data": fields}):
            text = qq.morning_text()
        for expected in ("top1top2", "q1q2q3q4", "t1t2t3", "第 ld 天", "bl 天"):
            self.assertIn(expected, text)
