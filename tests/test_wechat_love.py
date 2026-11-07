import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import unittest
from datetime import date, timedelta
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wechat_love as love


def response(payload, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode('utf-8')
    result.url = 'https://example.invalid/mock'
    return result


class LoveTests(unittest.TestCase):
    def setUp(self):
        # 每个测试都封住真实 HTTP，防止误发微信或消耗接口额度。
        self.get = self.enterContext(patch.object(love.requests, 'get'))
        self.post = self.enterContext(patch.object(love.requests, 'post'))
        self.get.side_effect = AssertionError('测试中禁止真实 GET')
        self.post.side_effect = AssertionError('测试中禁止真实 POST')
        self.sleep = self.enterContext(patch.object(love.time, 'sleep'))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        for name in ('APP_ID', 'APP_SECRET', 'OPEN_ID', 'TEMPLATE_ID', 'TIANAPI_KEY'):
            self.enterContext(patch.object(love, name, 'TEST_' + name))

    def mock_get(self, payload, status=200):
        self.get.side_effect = None
        self.get.return_value = response(payload, status)

    def mock_post(self, payload, status=200):
        self.post.side_effect = None
        self.post.return_value = response(payload, status)

    def message(self, weather=None):
        weather = weather or {'weather': '暂不可用', 'low': '', 'high': '', 'available': False}
        with patch.object(love, 'get_weather', return_value=weather), patch.object(love, 'get_caihongpi', return_value='今天也喜欢你！'), patch.object(love, 'get_beijing_today', return_value=date(2026, 11, 4)):
            return love.build_message()

    def test_missing_configuration_exits_before_network(self):
        with patch.object(love, 'APP_SECRET', None):
            self.assertEqual(love.main([]), 1)
        self.assertIn('APP_SECRET', self.output.getvalue())
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_whitespace_configuration_is_rejected(self):
        with patch.object(love, 'OPEN_ID', '  '):
            self.assertEqual(love.main([]), 1)
        self.get.assert_not_called()

    def test_token_rejection_sets_failure_exit_code(self):
        self.mock_get({'errcode': 40013, 'errmsg': 'invalid appid'})
        self.assertEqual(love.main([]), 1)
        self.assertIn('40013', self.output.getvalue())
        self.post.assert_not_called()

    def test_token_value_must_be_nonempty_string(self):
        for token in (None, '', '  ', 123):
            with self.subTest(token=token):
                self.mock_get({'access_token': token})
                with self.assertRaises(love.APIError):
                    love.get_access_token()

    def test_read_request_retries_timeout_three_times(self):
        self.get.side_effect = requests.Timeout('url contains TEST_APP_SECRET')
        with self.assertRaises(love.APIError):
            love.get_access_token()
        self.assertEqual(self.get.call_count, 3)
        self.assertEqual(self.sleep.call_count, 2)
        self.assertNotIn('TEST_APP_SECRET', self.output.getvalue())

    def test_read_request_recovers_from_transient_server_error(self):
        self.get.side_effect = [response({}, 503), response({'access_token': 'mock-token'})]
        self.assertEqual(love.get_access_token(), 'mock-token')
        self.assertEqual(self.get.call_count, 2)

    def test_read_request_retries_rate_limit(self):
        self.get.side_effect = [response({}, 429), response({'access_token': 'mock-token'})]
        self.assertEqual(love.get_access_token(), 'mock-token')
        self.assertEqual(self.get.call_count, 2)

    def test_read_request_does_not_retry_client_error(self):
        self.mock_get({}, 400)
        with self.assertRaises(love.APIError):
            love.get_access_token()
        self.assertEqual(self.get.call_count, 1)
        self.sleep.assert_not_called()

    def test_non_json_response_fails_cleanly(self):
        self.mock_get({})
        self.get.return_value._content = b'<html>unavailable</html>'
        with self.assertRaises(love.APIError):
            love.get_access_token()
        self.assertEqual(self.get.call_count, 3)

    def test_send_rejection_sets_failure_exit_code(self):
        self.mock_get({'access_token': 'mock-token'})
        self.mock_post({'errcode': 40003, 'errmsg': 'invalid openid'})
        with patch.object(love, 'build_message', return_value=self.message()):
            self.assertEqual(love.main([]), 1)
        self.post.assert_called_once()
        self.assertIn('40003', self.output.getvalue())

    def test_send_timeout_is_not_retried_and_does_not_expose_token(self):
        self.mock_get({'access_token': 'mock-token'})
        self.post.side_effect = requests.Timeout('https://example.invalid?access_token=mock-token')
        with patch.object(love, 'build_message', return_value=self.message()):
            self.assertEqual(love.main([]), 1)
        self.post.assert_called_once()
        self.assertIn('发送结果未确认', self.output.getvalue())
        self.assertNotIn('mock-token', self.output.getvalue())

    def test_send_http_error_is_failure_without_retry(self):
        self.mock_get({'access_token': 'mock-token'})
        self.mock_post({}, 503)
        with patch.object(love, 'build_message', return_value=self.message()):
            self.assertEqual(love.main([]), 1)
        self.post.assert_called_once()

    def test_send_invalid_json_is_failure(self):
        self.mock_get({'access_token': 'mock-token'})
        self.mock_post({})
        self.post.return_value._content = b'not json'
        with patch.object(love, 'build_message', return_value=self.message()):
            self.assertEqual(love.main([]), 1)

    def test_send_missing_error_code_is_failure(self):
        self.mock_get({'access_token': 'mock-token'})
        self.mock_post({'msgid': 123})
        with patch.object(love, 'build_message', return_value=self.message()):
            self.assertEqual(love.main([]), 1)

    def test_success_exits_zero_and_keeps_template_fields(self):
        self.mock_get({'access_token': 'mock-token'})
        self.mock_post({'errcode': 0, 'msgid': 123})
        message = self.message()
        with patch.object(love, 'build_message', return_value=message):
            self.assertEqual(love.main([]), 0)
        expected = {'top1', 'top2', 'd', 'c', 'w', 't', 'ld', 'bl', 'h', 't1', 't2', 't3', 'q1', 'q2', 'q3', 'q4'}
        self.assertEqual(set(message['data']), expected)
        self.assertEqual(self.post.call_args.kwargs['json'], message)
        self.assertEqual(self.post.call_args.kwargs['params'], {'access_token': 'mock-token'})

    def test_weather_failure_has_no_fabricated_temperature(self):
        self.get.side_effect = requests.Timeout('mock unavailable')
        weather = love.get_weather()
        self.assertFalse(weather['available'])
        self.assertEqual(weather['low'], '')
        self.assertEqual(weather['high'], '')
        self.assertIn('暂不可用', weather['weather'])

    def test_weather_business_error_degrades_without_retry(self):
        self.mock_get({'code': 230, 'msg': 'quota exhausted'})
        self.assertFalse(love.get_weather()['available'])
        self.assertEqual(self.get.call_count, 1)

    def test_weather_invalid_fields_are_unavailable(self):
        for result in (None, [], {}, {'weather': '', 'lowest': '20℃', 'highest': '25℃'}, {'weather': '晴', 'lowest': 'NaN', 'highest': '25℃'}, {'weather': '晴', 'lowest': '30℃', 'highest': '20℃'}):
            with self.subTest(result=result):
                self.mock_get({'code': 200, 'result': result})
                self.assertFalse(love.get_weather()['available'])

    def test_weather_success_preserves_real_values(self):
        self.mock_get({'code': 200, 'result': {'weather': '小雨', 'lowest': '8℃', 'highest': '14℃'}})
        weather = love.get_weather()
        self.assertTrue(weather['available'])
        self.assertEqual(weather['weather'], '小雨')
        self.assertEqual(weather['low'], '8℃')

    def test_missing_optional_key_makes_no_http_requests(self):
        with patch.object(love, 'TIANAPI_KEY', None):
            self.assertFalse(love.get_weather()['available'])
            self.assertEqual(love.get_caihongpi(), '今天也超级喜欢你！')
        self.get.assert_not_called()

    def test_quote_api_error_uses_local_copy(self):
        self.mock_get({'code': 200, 'result': None})
        self.assertEqual(love.get_caihongpi(), '今天也超级喜欢你！')

    def test_snow_keeps_precipitation_and_cold_reminders(self):
        with patch.object(love.random, 'choice', side_effect=lambda choices: choices[0]):
            tip = ''.join(love.get_segmented_weather_tips({'weather': '大雪', 'low': '-2℃', 'high': '3℃'}))
        self.assertIn('雪', tip)
        self.assertIn('保暖', tip)
        self.assertIn('滑', tip)

    def test_rain_and_temperature_reminders_are_combined(self):
        for low, high, expected in (('8℃', '14℃', '添衣'), ('28℃', '35℃', '喝水')):
            with self.subTest(low=low, high=high), patch.object(love.random, 'choice', side_effect=lambda choices: choices[0]):
                tip = ''.join(love.get_segmented_weather_tips({'weather': '雷阵雨', 'low': low, 'high': high}))
                self.assertIn('雨', tip)
                self.assertIn('伞', tip)
                self.assertIn(expected, tip)

    def test_rain_reminder_survives_missing_temperature(self):
        tip = ''.join(love.get_segmented_weather_tips({'weather': '雨', 'low': None, 'high': '未知'}))
        self.assertIn('伞', tip)

    def test_unavailable_weather_uses_neutral_tips_and_temperature(self):
        message = self.message()
        self.assertEqual(message['data']['t']['value'].strip(), '暂不可用')
        self.assertIn('天气暂时查不到', message['data']['t1']['value'])

    def test_laba_before_spring_festival_is_six_days_away(self):
        today = date(2026, 1, 20)
        self.assertEqual(love.get_next_lunar_date(today, 12, 8), date(2026, 1, 26))
        # 1 月 20 日会优先显示当天节气，次日再检查最近节日文案。
        next_day = today + timedelta(days=1)
        text, _ = love.get_dynamic_holiday_str(next_day, 100, love.get_love_days(next_day))
        self.assertIn('腊八节', text)
        self.assertIn('5 天', text)

    def test_lunar_festival_today_and_rollover(self):
        self.assertEqual(love.get_next_lunar_date(date(2026, 1, 26), 12, 8), date(2026, 1, 26))
        self.assertEqual(love.get_next_lunar_date(date(2026, 1, 27), 12, 8), date(2027, 1, 15))

    def test_lunar_birthday_on_day_and_after_birthday(self):
        birthday = love.ZhDate(2026, 8, 18).to_datetime().date()
        self.assertEqual(love.get_birthday_left(birthday), 0)
        self.assertGreater(love.get_birthday_left(birthday + timedelta(days=1)), 300)

    def test_lunar_birthday_before_spring_festival(self):
        with patch.object(love, 'BIRTHDAY_LUNAR', (1998, 12, 8)):
            self.assertEqual(love.get_birthday_left(date(2026, 1, 20)), 6)

    def test_lunar_small_month_day_30_uses_day_29(self):
        month = next(month for month in range(1, 13) if not love.ZhDate.validate(2026, month, 30, False))
        self.assertEqual(love._get_safe_lunar_date(2026, month, 30), love.ZhDate(2026, month, 29).to_datetime().date())

    def test_invalid_lunar_date_fails_instead_of_returning_january_1(self):
        for args in ((2026, 13, 1), (2026, 1, 0), (2101, 1, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                love._get_safe_lunar_date(*args)

    def test_chuxi_today_and_after_new_year(self):
        self.assertEqual(love.get_next_chuxi(date(2026, 2, 16)), date(2026, 2, 16))
        self.assertEqual(love.get_next_chuxi(date(2026, 2, 17)), date(2027, 2, 5))

    def test_one_message_uses_one_date_snapshot(self):
        with patch.object(love, 'get_beijing_today', return_value=date(2026, 11, 4)) as today, patch.object(love, 'get_weather', return_value={'weather': '暂不可用', 'low': '', 'high': '', 'available': False}), patch.object(love, 'get_caihongpi', return_value='早安'):
            message = love.build_message()
        today.assert_called_once()
        self.assertEqual(message['data']['d']['value'], '2026年11月04日')

    def test_dry_run_does_not_need_wechat_credentials_or_send(self):
        with patch.object(love, 'TIANAPI_KEY', None), patch.object(love, 'APP_ID', None):
            self.assertEqual(love.main(['--dry-run']), 0)
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_script_entry_exits_nonzero_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'argv', ['wechat_love.py']), self.assertRaises(SystemExit) as caught:
            runpy.run_path(str(Path(love.__file__)), run_name='__main__')
        self.assertEqual(caught.exception.code, 1)
        self.get.assert_not_called()

    def test_script_entry_dry_run_exits_zero(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'argv', ['wechat_love.py', '--dry-run']), self.assertRaises(SystemExit) as caught:
            runpy.run_path(str(Path(love.__file__)), run_name='__main__')
        self.assertEqual(caught.exception.code, 0)
        self.post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
