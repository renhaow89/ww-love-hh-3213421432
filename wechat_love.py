# -*- coding: utf-8 -*-
import requests
import os
from datetime import datetime, timedelta, date
from zhdate import ZhDate

# 从环境变量读取配置
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
OPEN_ID = os.environ.get("OPEN_ID")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")
TIANAPI_KEY = os.environ.get("TIANAPI_KEY")

CITY_NAME = "杭州"
LOVE_DATE = date(2019, 3, 10)
BIRTHDAY_LUNAR = (1998, 8, 18)


def get_beijing_today():
    """获取北京时间的日期（UTC+8）"""
    utc_now = datetime.utcnow()
    beijing_now = utc_now + timedelta(hours=8)
    return beijing_now.date()


def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    return requests.get(url, timeout=10).json().get("access_token")


def get_weather():
    try:
        url = f"https://apis.tianapi.com/tianqi/index?key={TIANAPI_KEY}&city={CITY_NAME}&type=1"
        res = requests.get(url, timeout=10).json()
        if res.get("code") == 200:
            data = res["result"]
            return {
                "weather": data["weather"],
                "low": data["lowest"],
                "high": data["highest"],
            }
    except Exception as e:
        print(f"天气获取异常: {e}")
    return {"weather": "晴", "low": "20℃", "high": "30℃"}


def get_caihongpi():
    try:
        url = f"https://apis.tianapi.com/caihongpi/index?key={TIANAPI_KEY}"
        res = requests.get(url, timeout=10).json()
        if res.get("code") == 200:
            return res["result"]["content"]
    except Exception as e:
        print(f"情话获取异常: {e}")
    return "今天也超级喜欢你！"


def get_love_days():
    return (get_beijing_today() - LOVE_DATE).days


def get_birthday_left():
    today = get_beijing_today()
    try:
        birthday = ZhDate(today.year, BIRTHDAY_LUNAR[1], BIRTHDAY_LUNAR[2]).to_datetime().date()
    except:
        birthday = date(today.year, 9, 20)
    if birthday < today:
        try:
            birthday = ZhDate(today.year + 1, BIRTHDAY_LUNAR[1], BIRTHDAY_LUNAR[2]).to_datetime().date()
        except:
            birthday = date(today.year + 1, 9, 20)
    return (birthday - today).days


def send_message():
    access_token = get_access_token()
    if not access_token:
        print("❌ 获取 token 失败")
        return False

    weather = get_weather()
    caihongpi = get_caihongpi()
    love_days = get_love_days()
    birthday_left = get_birthday_left()
    today_str = get_beijing_today().strftime("%Y年%m月%d日")

    print(f"北京时间日期: {today_str}")
    print(f"天气: {weather}")
    print(f"情话: {caihongpi}")

    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    data = {
        "touser": OPEN_ID,
        "template_id": TEMPLATE_ID,
        "data": {
            "riqi": {"value": today_str, "color": "#333333"},
            "city": {"value": CITY_NAME, "color": "#333333"},
            "weather": {"value": weather["weather"], "color": "#333333"},
            "low": {"value": weather["low"], "color": "#333333"},
            "high": {"value": weather["high"], "color": "#333333"},
            "love_days": {"value": str(love_days), "color": "#FF69B4"},
            "birthday_left": {"value": str(birthday_left), "color": "#FF69B4"},
            "qinghua": {"value": caihongpi, "color": "#FF69B4"},
        }
    }

    res = requests.post(url, json=data, timeout=10).json()
    if res.get("errcode") == 0:
        print("✅ 发送成功！")
        return True
    else:
        print(f"❌ 发送失败: {res}")
        return False


if __name__ == "__main__":
    send_message()
