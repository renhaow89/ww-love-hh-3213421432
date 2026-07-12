# -*- coding: utf-8 -*-
import requests
import os
from datetime import date
from zhdate import ZhDate

# 从环境变量读取配置（安全，不会泄露）
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
OPEN_ID = os.environ.get("OPEN_ID")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")
TIANAPI_KEY = os.environ.get("TIANAPI_KEY")

CITY_CODE = "101210101"
CITY_NAME = "杭州"
LOVE_DATE = date(2019, 3, 10)
BIRTHDAY_LUNAR = (1998, 8, 18)


def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    return requests.get(url).json().get("access_token")


def get_weather():
    url = f"http://wthrcdn.etouch.cn/weather_mini?citykey={CITY_CODE}"
    res = requests.get(url).json()
    if res.get("status") == 1000:
        today = res["data"]["forecast"][0]
        return {
            "weather": today["type"],
            "low": today["low"].replace("低温 ", ""),
            "high": today["high"].replace("高温 ", ""),
        }
    return {"weather": "未知", "low": "未知", "high": "未知"}


def get_caihongpi():
    url = f"https://apis.tianapi.com/caihongpi/index?key={TIANAPI_KEY}"
    res = requests.get(url).json()
    if res.get("code") == 200:
        return res["result"]["content"]
    return "今天也超级喜欢你！"


def get_love_days():
    return (date.today() - LOVE_DATE).days


def get_birthday_left():
    today = date.today()
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
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    data = {
        "touser": OPEN_ID,
        "template_id": TEMPLATE_ID,
        "data": {
            "date": {"value": date.today().strftime("%Y年%m月%d日")},
            "city": {"value": CITY_NAME},
            "weather": {"value": weather["weather"]},
            "low": {"value": weather["low"]},
            "high": {"value": weather["high"]},
            "love_days": {"value": str(get_love_days()), "color": "#FF69B4"},
            "birthday_left": {"value": str(get_birthday_left()), "color": "#FF69B4"},
            "caihongpi": {"value": caihongpi, "color": "#FF69B4"},
        }
    }
    
    res = requests.post(url, json=data).json()
    if res.get("errcode") == 0:
        print("✅ 发送成功！")
        return True
    else:
        print(f"❌ 失败：{res}")
        return False


if __name__ == "__main__":
    send_message()
