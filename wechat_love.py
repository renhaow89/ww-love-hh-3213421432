# -*- coding: utf-8 -*-
import requests
import os
from datetime import date
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


def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    return requests.get(url, timeout=10).json().get("access_token")


def get_weather():
    """获取天气（免费接口，无需注册）"""
    try:
        url = f"https://wttr.in/{CITY_NAME}?format=j1&lang=zh"
        res = requests.get(url, timeout=10).json()
        today = res["weather"][0]
        weather_desc = today["lang_zh"][0]["value"] if "lang_zh" in today else today["weatherDesc"][0]["value"]
        return {
            "weather": weather_desc,
            "low": today["mintempC"] + "℃",
            "high": today["maxtempC"] + "℃",
        }
    except Exception as e:
        print(f"天气获取失败: {e}")
        return {"weather": "晴", "low": "20℃", "high": "30℃"}


def get_caihongpi():
    try:
        url = f"https://apis.tianapi.com/caihongpi/index?key={TIANAPI_KEY}"
        res = requests.get(url, timeout=10).json()
        if res.get("code") == 200:
            return res["result"]["content"]
    except:
        pass
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
    love_days = get_love_days()
    birthday_left = get_birthday_left()
    today_str = date.today().strftime("%Y年%m月%d日")
    
    print("========== 调试开始 ==========")
    print(f"日期: [{today_str}]")
    print(f"城市: [{CITY_NAME}]")
    print(f"天气: [{weather['weather']}]")
    print(f"情话: [{caihongpi}]")
    print(f"恋爱天数: [{love_days}]")
    print(f"距生日: [{birthday_left}]")
    print("========== 调试结束 ==========")
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    data = {
        "touser": OPEN_ID,
        "template_id": TEMPLATE_ID,
        "data": {
            "date": {"value": today_str},
            "city": {"value": CITY_NAME},
            "weather": {"value": weather["weather"]},
            "low": {"value": weather["low"]},
            "high": {"value": weather["high"]},
            "love_days": {"value": str(love_days)},
            "birthday_left": {"value": str(birthday_left)},
            "caihongpi": {"value": caihongpi},
        }
    }
    
    res = requests.post(url, json=data, timeout=10).json()
    print(f"微信返回: {res}")
    return res.get("errcode") == 0
        return False


if __name__ == "__main__":
    send_message()
