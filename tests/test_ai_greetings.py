import contextlib
from datetime import date, timedelta
import io
import json
import os
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

import requests

import ai_greetings as ai
import qq_push as qq


SECRET = "FAKE_DEEPSEEK_KEY_NEVER_LOG"
RECIPIENT = "ABCDEF0123456789ABCDEF0123456789"
COPY = {
    "greeting": "新的一天慢慢来，愿你忙里也能找到属于自己的小开心。",
    "weather_care": "出门记得带上雨伞，外套也别落下，路上慢慢走。",
    "love_note": "平凡日子里最确定的小事，就是醒来又多喜欢你一点。",
}
ALTERNATIVE = {
    "greeting": "愿清晨把温柔留给你，今天也可以按自己的节奏向前走。",
    "weather_care": "雨天出门把伞带好，照顾好自己，也记得给自己留点休息。",
    "love_note": "想把生活里遇见的小美好，都慢慢攒成送给你的喜欢。",
}


def fields():
    values = {
        "top1": "🌸早安，我最爱的宝宝！", "top2": "原来的开场问候。",
        "d": "2026年11月09日", "c": "杭州", "w": "小雨", "t": "8℃ ~ 15℃",
        "ld": "2801", "bl": "313", "h": "下个节日【平安夜】还有 45 天 ⏳",
        "t1": "原来的天气提醒，", "t2": "注意带伞，", "t3": "照顾好自己。",
        "q1": "原来的情话，", "q2": "今天喜欢你，", "q3": "明天也喜欢，", "q4": "一直喜欢你。",
    }
    return {name: {"value": text} for name, text in values.items()}


def response(segments=None, *, status=200, finish="stop", content=None):
    result = requests.Response()
    result.status_code = status
    body = {"choices": [{"finish_reason": finish, "message": {"content": (
        json.dumps(COPY if segments is None else segments, ensure_ascii=False) if content is None else content
    )}}]}
    result._content = json.dumps(body).encode("utf-8")
    return result


class AITests(TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.directory) / "state/history.json"
        self.post = self.enterContext(patch.object(ai.requests, "post", side_effect=AssertionError("禁止真实 AI POST")))
        self.get = self.enterContext(patch.object(ai.requests, "get", side_effect=AssertionError("禁止真实 GET")))
        self.enterContext(patch.dict(os.environ, {"DEEPSEEK_API_KEY": SECRET, "AI_ENABLED": "true", "QQ_APP_ID": "123456789", "QQ_APP_SECRET": "FAKE_QQ_SECRET", "QQ_USER_OPENID": RECIPIENT}))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def generate(self):
        return ai.generate(fields(), history_path=self.path)

    def use(self, *responses):
        self.post.side_effect = list(responses)

    def history(self, items):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")

    def test_no_key_or_disabled_does_not_call_or_write(self):
        for changes in ({"DEEPSEEK_API_KEY": ""}, {"AI_ENABLED": "false"}, {"AI_ENABLED": "OFF"}):
            with self.subTest(changes=changes), patch.dict(os.environ, changes):
                self.assertEqual(self.generate().segments, {})
        self.post.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_one_request_produces_three_fields_without_history_write(self):
        self.use(response())
        result = self.generate()
        self.assertEqual(result.segments, COPY)
        self.post.assert_called_once()
        self.assertFalse(self.path.exists())

    def test_official_request_is_bounded_and_excludes_delivery_secrets(self):
        self.use(response())
        self.generate()
        self.assertEqual(self.post.call_args.args, ("https://api.deepseek.com/chat/completions",))
        options = self.post.call_args.kwargs
        self.assertEqual(options["headers"]["Authorization"], "Bearer " + SECRET)
        self.assertFalse(options["allow_redirects"])
        self.assertEqual(options["timeout"], (5, 18))
        payload = options["json"]
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["max_tokens"], 512)
        text = json.dumps(payload, ensure_ascii=False)
        self.assertIn("2026-11-09", text)
        self.assertIn("星期一", text)
        self.assertNotIn(RECIPIENT, text)
        self.assertNotIn(SECRET, text)
        self.assertNotIn("FAKE_QQ_SECRET", text)

    def test_partial_invalid_field_keeps_other_two(self):
        self.use(response({**COPY, "love_note": "长" * 61}))
        self.assertEqual(self.generate().segments, {k: v for k, v in COPY.items() if k != "love_note"})
        self.post.assert_called_once()

    def test_network_error_falls_back_once_without_private_exception(self):
        self.use(requests.Timeout(SECRET + RECIPIENT))
        self.assertEqual(self.generate().segments, {})
        self.post.assert_called_once()
        self.assertNotIn(SECRET, self.output.getvalue())
        self.assertNotIn(RECIPIENT, self.output.getvalue())

    def test_http_failure_or_redirect_does_not_retry_or_expose_response(self):
        for status in (301, 401, 402, 429, 500):
            with self.subTest(status=status):
                self.post.reset_mock()
                self.use(response(status=status, content=SECRET))
                self.assertEqual(self.generate().segments, {})
                self.post.assert_called_once()
                self.assertIn(f"HTTP {status}", self.output.getvalue())
        self.assertNotIn(SECRET, self.output.getvalue())

    def test_blank_invalid_json_or_nonobject_content_falls_back(self):
        for content in (" ", "[1,2]", "not-json", "null", "{}"):
            with self.subTest(content=content):
                self.use(response(content=content))
                self.assertEqual(self.generate().segments, {})

    def test_incomplete_generation_is_not_used(self):
        self.use(response(finish="length"))
        self.assertEqual(self.generate().segments, {})

    def test_unexpected_envelope_is_not_used(self):
        for payload in ([], {}, {"choices": []}, {"choices": [None]}, {"choices": [{"finish_reason": "stop", "message": {"content": 123}}]}):
            with self.subTest(payload=payload):
                result = requests.Response()
                result.status_code = 200
                result._content = json.dumps(payload).encode()
                self.use(result)
                self.assertEqual(self.generate().segments, {})

    def test_invalid_segments_do_not_enter_message(self):
        _, context = ai.build_context(fields())
        for value in (None, 42, [], "", "太短", "好" * 61, "今天是第2801天，继续好好喜欢你。", "今天天气很好\n记得照顾自己呀。", "看这里https://example.com宝贝", "<think>今天也要开开心心</think>", "🌸" * 12):
            with self.subTest(value=value):
                self.assertFalse(ai.valid_segment("greeting", value, context))

    def test_unknown_weather_only_falls_back_for_weather_care(self):
        values = fields()
        values["w"]["value"] = "暂不可用"
        values["t"]["value"] = "暂不可用"
        self.use(response())
        result = ai.generate(values, history_path=self.path)
        self.assertEqual(set(result.segments), {"greeting", "love_note"})

    def test_weather_without_evidence_is_rejected(self):
        values = fields()
        values["w"]["value"] = "晴"
        _, context = ai.build_context(values)
        for text in (COPY["weather_care"], "今天下雪记得做好保暖，出门慢慢走。", "今天降温记得穿厚一点，别让冷风吹到自己。", "今天暴雨出门多注意，记得把雨伞带好。", "今天高温记得防中暑，好好照顾自己呀。"):
            with self.subTest(text=text):
                self.assertFalse(ai.valid_segment("weather_care", text, context))

    def test_mild_rain_does_not_allow_heavy_rain_claim(self):
        _, context = ai.build_context(fields())
        self.assertFalse(ai.valid_segment("weather_care", "今天暴雨出门别着急，记得把雨伞带上。", context))
        self.assertTrue(ai.valid_segment("weather_care", COPY["weather_care"], context))

    def test_daily_themes_rotate_and_preserve_special_day(self):
        themes = set()
        values = fields()
        for offset in range(14):
            values["d"]["value"] = (date(2026, 11, 9) + timedelta(days=offset)).strftime("%Y年%m月%d日")
            _, context = ai.build_context(values)
            themes.add(context["theme"])
            self.assertFalse(context["occasion_is_today"])
        self.assertEqual(len(themes), 14)
        values["h"]["value"] = "✨ 隐藏彩蛋：今天是相爱的第 2800 天！❤️"
        _, context = ai.build_context(values)
        self.assertTrue(context["occasion_is_today"])
        self.assertEqual(context["theme"], "特别日子专属问候")

    def test_invalid_date_skips_ai_without_network(self):
        values = fields()
        values["d"]["value"] = "not-a-date"
        self.assertEqual(ai.generate(values, history_path=self.path).segments, {})
        self.post.assert_not_called()

    def test_corrupt_history_does_not_block_generation(self):
        self.path.parent.mkdir()
        self.path.write_text("broken-json", encoding="utf-8")
        self.use(response())
        self.assertEqual(self.generate().segments, COPY)

    def test_history_only_keeps_recent_valid_fingerprints(self):
        digest = ai.fingerprint(COPY["greeting"])
        self.history([
            {"date": "2026-10-26", "hashes": {"greeting": digest}},
            {"date": "2026-10-27", "hashes": {"greeting": digest, "secret": SECRET}},
            {"date": "2026-11-10", "hashes": {"greeting": digest}},
            {"date": "invalid", "hashes": {"greeting": digest}},
        ])
        self.assertEqual(ai.read_history(self.path, date(2026, 11, 9)), [{"date": "2026-10-27", "hashes": {"greeting": digest}}])

    def test_repeat_rewrites_once_and_keeps_nonrepeated_fields(self):
        self.history([{"date": "2026-11-08", "hashes": {"greeting": ai.fingerprint(COPY["greeting"])}}])
        self.use(response(), response(ALTERNATIVE))
        result = self.generate()
        self.assertEqual(self.post.call_count, 2)
        self.assertEqual(result.segments["greeting"], ALTERNATIVE["greeting"])
        self.assertEqual(result.segments["weather_care"], COPY["weather_care"])
        self.assertIn("重复", self.post.call_args.kwargs["json"]["messages"][1]["content"])

    def test_repeated_second_response_falls_back_only_for_repeated_field(self):
        self.history([{"date": "2026-11-08", "hashes": {"greeting": ai.fingerprint(COPY["greeting"])}}])
        self.use(response(), response())
        result = self.generate()
        self.assertEqual(set(result.segments), {"weather_care", "love_note"})
        self.assertEqual(self.post.call_count, 2)

    def test_failed_rewrite_keeps_first_response_good_fields(self):
        self.history([{"date": "2026-11-08", "hashes": {"greeting": ai.fingerprint(COPY["greeting"])}}])
        self.use(response(), requests.Timeout(SECRET))
        self.assertEqual(set(self.generate().segments), {"weather_care", "love_note"})
        self.assertEqual(self.post.call_count, 2)

    def test_same_text_in_two_columns_is_not_used_twice(self):
        self.use(response({**COPY, "love_note": COPY["greeting"]}), response(ALTERNATIVE))
        result = self.generate()
        self.assertEqual(result.segments["greeting"], COPY["greeting"])
        self.assertEqual(result.segments["love_note"], ALTERNATIVE["love_note"])

    def test_history_contains_hashes_only_and_generation_does_not_write(self):
        self.use(response())
        result = self.generate()
        self.assertFalse(self.path.exists())
        ai.record_sent(result)
        raw = self.path.read_text(encoding="utf-8")
        for private in (*COPY.values(), SECRET, RECIPIENT, "杭州"):
            self.assertNotIn(private, raw)
        records = json.loads(raw)
        self.assertEqual(set(records[0]), {"date", "hashes"})
        self.assertEqual(records[0]["hashes"]["greeting"], ai.fingerprint(COPY["greeting"]))

    def test_empty_generation_does_not_save_history(self):
        ai.record_sent(ai.GeneratedCopy(history_path=self.path))
        self.assertFalse(self.path.exists())

    def test_history_save_failure_does_not_raise_or_log_exception_data(self):
        result = ai.GeneratedCopy(dict(COPY), date(2026, 11, 9), history_path=self.path)
        with patch.object(Path, "mkdir", side_effect=OSError(SECRET)):
            ai.record_sent(result)
        self.assertNotIn(SECRET, self.output.getvalue())

    def test_fingerprints_ignore_punctuation_whitespace_and_emoji(self):
        self.assertEqual(ai.fingerprint("今天也喜欢你！🌷"), ai.fingerprint("今天 也喜欢你。"))

    def test_composition_keeps_facts_and_entire_ai_sentences(self):
        generated = ai.GeneratedCopy(dict(COPY))
        with patch.object(qq.wechat_love, "build_message", return_value={"data": fields()}), patch.object(ai, "generate", return_value=generated):
            message = qq.compose_morning_message()
        for value in (*COPY.values(), "2026年11月09日", "杭州 | 小雨", "8℃ ~ 15℃", "第 2801 天", "313 天", "下个节日【平安夜】还有 45 天"):
            self.assertIn(value, message.text)
        self.assertIn("🌸早安，我最爱的宝宝！" + COPY["greeting"], message.text)
        self.assertNotIn("原来的", message.text)
        self.assertNotIn(COPY["love_note"], self.output.getvalue())

    def test_missing_ai_column_uses_its_own_fallback(self):
        generated = ai.GeneratedCopy({"greeting": COPY["greeting"], "love_note": COPY["love_note"]})
        with patch.object(qq.wechat_love, "build_message", return_value={"data": fields()}), patch.object(ai, "generate", return_value=generated):
            message = qq.compose_morning_message()
        self.assertIn("原来的天气提醒，注意带伞，照顾好自己。", message.text)
        self.assertIn(COPY["greeting"], message.text)

    def test_dry_preview_never_calls_paid_ai_or_writes_history(self):
        with patch.object(qq.wechat_love, "build_message", return_value={"data": fields()}), patch.object(ai, "generate") as generate, patch.object(ai, "record_sent") as save:
            self.assertEqual(qq.main(["--dry-run"]), 0)
        generate.assert_not_called()
        save.assert_not_called()
        self.post.assert_not_called()

    def test_successful_qq_send_records_history_after_acceptance(self):
        generated = ai.GeneratedCopy(dict(COPY))
        parent = Mock()
        with patch.object(qq, "compose_morning_message", return_value=qq.MorningMessage("测试早安", generated)), patch.object(qq.QQClient, "access_token", return_value="fake-token"), patch.object(qq.QQClient, "send_text", return_value="accepted") as send, patch.object(ai, "record_sent") as save:
            parent.attach_mock(send, "send")
            parent.attach_mock(save, "save")
            self.assertEqual(qq.main([]), 0)
        self.assertEqual([call[0] for call in parent.mock_calls], ["send", "save"])
        save.assert_called_once_with(generated)

    def test_rejected_qq_send_does_not_record_generated_text(self):
        generated = ai.GeneratedCopy(dict(COPY))
        with patch.object(qq, "compose_morning_message", return_value=qq.MorningMessage("测试早安", generated)), patch.object(qq.QQClient, "access_token", return_value="fake-token"), patch.object(qq.QQClient, "send_text", side_effect=qq.QQPushError("QQ 拒绝")), patch.object(ai, "record_sent") as save:
            self.assertEqual(qq.main([]), 1)
        save.assert_not_called()

    def test_qq_auth_failure_stops_before_paid_ai_and_history(self):
        with patch.object(qq.QQClient, "access_token", side_effect=qq.QQPushError("QQ 凭据无效")), patch.object(qq, "compose_morning_message") as compose, patch.object(ai, "record_sent") as save:
            self.assertEqual(qq.main([]), 1)
        compose.assert_not_called()
        save.assert_not_called()
        self.post.assert_not_called()

    def test_binding_does_not_generate_ai_copy(self):
        with patch.object(qq, "bind_receiver"), patch.object(ai, "generate") as generate:
            self.assertEqual(qq.main(["--mode", "bind"]), 0)
        generate.assert_not_called()
        self.post.assert_not_called()
