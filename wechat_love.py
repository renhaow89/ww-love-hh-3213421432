# -*- coding: utf-8 -*-
import requests
import os
import random
from datetime import datetime, timedelta, date
from zhdate import ZhDate

# ==========================================
# 环境变量读取与核心常量配置区
# ==========================================
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
OPEN_ID = os.environ.get("OPEN_ID")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")
TIANAPI_KEY = os.environ.get("TIANAPI_KEY")

CITY_NAME = "杭州"
LOVE_DATE = date(2019, 3, 10)
BIRTHDAY_LUNAR = (1998, 8, 18)

HOLIDAY_SOLAR = {
    "01-01": "元旦",
    "02-14": "情人节",
    "03-08": "女神节",
    "05-01": "劳动节",
    "05-20": "520表白日",
    "06-01": "儿童节",
    "10-01": "国庆节",
    "11-01": "万圣节",
    "12-24": "平安夜",
    "12-25": "圣诞节",
    "12-31": "跨年"
}

HOLIDAY_LUNAR = {
    (1, 1): "春节",
    (5, 5): "端午节",
    (7, 7): "七夕节",
    (8, 15): "中秋节",
    (12, 8): "腊八节",
    (12, 24): "南方小年"
}

# 新增：每日随机寄语池
DAILY_GREETINGS = [
    "今天也要记得吃早餐哦 ❤️",
    "工作再忙，也别忘了照顾自己。",
    "希望今天一切顺顺利利。",
    "今天也会是幸运的一天。",
    "不要太累啦，记得按时休息。",
    "希望今天能有很多开心的小事情发生。"
]

# ==========================================
# 基础时间与日期处理模块
# ==========================================
def get_beijing_today():
    utc_now = datetime.utcnow()
    beijing_now = utc_now + timedelta(hours=8)
    return beijing_now.date()

def get_love_days():
    return (get_beijing_today() - LOVE_DATE).days

def get_birthday_left():
    today = get_beijing_today()
    try:
        birthday = ZhDate(today.year, BIRTHDAY_LUNAR[1], BIRTHDAY_LUNAR[2]).to_datetime().date()
    except Exception:
        birthday = date(today.year, 9, 20)
        
    if birthday < today:
        try:
            birthday = ZhDate(today.year + 1, BIRTHDAY_LUNAR[1], BIRTHDAY_LUNAR[2]).to_datetime().date()
        except Exception:
            birthday = date(today.year + 1, 9, 20)
            
    return (birthday - today).days

# ==========================================
# 核心历法与天体测算引擎
# ==========================================
def get_qingming_date(year):
    y = year % 100
    day = int(y * 0.2422 + 4.81) - (y // 4)
    return date(year, 4, day)

def get_next_lunar_date(today, lunar_month, lunar_day):
    try:
        target_date = ZhDate(today.year, lunar_month, lunar_day).to_datetime().date()
    except Exception:
        target_date = date(today.year, 12, 31)
        
    if target_date < today:
        try:
            target_date = ZhDate(today.year + 1, lunar_month, lunar_day).to_datetime().date()
        except Exception:
            pass
    return target_date

def get_next_chuxi(today):
    sf_this_year = ZhDate(today.year, 1, 1).to_datetime().date()
    chuxi_this_year = sf_this_year - timedelta(days=1)
    
    if chuxi_this_year >= today:
        return chuxi_this_year
        
    sf_next_year = ZhDate(today.year + 1, 1, 1).to_datetime().date()
    return sf_next_year - timedelta(days=1)

def get_dynamic_holiday_str(today, birthday_left, love_days):
    candidates = {}
    
    for m_d, name in HOLIDAY_SOLAR.items():
        m, d = map(int, m_d.split("-"))
        try:
            h_date = date(today.year, m, d)
        except ValueError:
            continue
        if h_date >= today:
            candidates[name] = (h_date - today).days
        else:
            candidates[name] = (date(today.year + 1, m, d) - today).days

    qm_this_year = get_qingming_date(today.year)
    if qm_this_year >= today:
        candidates["清明节"] = (qm_this_year - today).days
    else:
        qm_next_year = get_qingming_date(today.year + 1)
        candidates["清明节"] = (qm_next_year - today).days

    for (l_m, l_d), name in HOLIDAY_LUNAR.items():
        h_date = get_next_lunar_date(today, l_m, l_d)
        candidates[name] = (h_date - today).days

    chuxi_date = get_next_chuxi(today)
    candidates["除夕"] = (chuxi_date - today).days

    try:
        anni_this_year = date(today.year, LOVE_DATE.month, LOVE_DATE.day)
    except ValueError:
        anni_this_year = date(today.year, LOVE_DATE.month, LOVE_DATE.day - 1)
        
    if anni_this_year >= today:
        candidates["恋爱纪念日"] = (anni_this_year - today).days
    else:
        candidates["恋爱纪念日"] = (date(today.year + 1, LOVE_DATE.month, LOVE_DATE.day) - today).days

    if birthday_left == 0:
        return "今天是小胡胡的农历生日！🎂"
    if candidates.get("恋爱纪念日") == 0:
        return f"今天是恋爱 {love_days // 365} 周年纪念日！❤️"
        
    for name, days_left in candidates.items():
        if days_left == 0:
            return f"今天是{name}快乐！❤️"
            
    next_name, next_days = min(candidates.items(), key=lambda x: x[1])
    return f"下个节日【{next_name}】还有 {next_days} 天 ⏳"

# ==========================================
# 文本切片与多态预警计算引擎
# ==========================================
def get_segmented_weather_tips(weather_info):
    """
    状态机层级：极端气温 > 降水天气 > 晴/阴常规天气。
    切片规范：保证3个子切片的长度分布，适配微信 UI 排版边界。
    """
    weather_str = weather_info.get("weather", "")
    low_str = weather_info.get("low", "")
    high_str = weather_info.get("high", "")
    
    # 默认保底切片
    lines = ["今天天气不错哦，", "希望你这一天，", "都有好心情相伴 ❤️"]
    
    try:
        clean_low = float(low_str.replace("℃", "").replace("°C", "").strip())
        clean_high = float(high_str.replace("℃", "").replace("°C", "").strip())
        
        # 1. 物理极值预警（最高优先级）
        if clean_high >= 35.0:
            lines = ["今天杭州比较热，", "记得多喝点水，", "空调也不要吹太久哦 ❤️"]
        elif clean_high >= 30.0:
            lines = ["今天气温有点偏高，", "出门注意做好防晒，", "多喝水谨防中暑 ❤️"]
        elif clean_low <= 10.0:
            lines = ["今天有点降温啦，", "记得多穿两件厚衣服，", "千万别感冒了 ❤️"]
        # 2. 降水预警（次高优先级）
        elif "雨" in weather_str:
            lines = ["杭州今天有雨，", "出门记得带伞哦～", "希望一路顺顺利利 ❤️"]
        elif "雪" in weather_str:
            lines = ["今天下雪啦，", "路面可能会打滑，", "走路要注意安全哦 ❤️"]
        # 3. 常规天候提示（常规优先级，新增请求适配）
        elif "晴" in weather_str:
            lines = ["☀ 今天天气很好，", "希望你今天也能，", "拥有一个好心情 ❤️"]
        elif "阴" in weather_str or "多云" in weather_str:
            lines = ["🌤 今天虽然有点阴，", "但希望你的心情，", "一直都是晴天 ❤️"]
    except Exception:
        pass
        
    tip1 = lines[0] + "\n" if len(lines) > 0 else ""
    tip2 = lines[1] + "\n" if len(lines) > 1 else ""
    tip3 = lines[2] if len(lines) > 2 else ""
    
    return tip1, tip2, tip3

# ==========================================
# 外部接口服务模块
# ==========================================
def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    return requests.get(url, timeout=10).json().get("access_token")

def get_weather():
    try:
        url = f"https://apis.tianapi.com/tianqi/index?key={TIANAPI_KEY}&city={CITY_NAME}&type=1"
        res = requests.get(url, timeout=10).json()
        if res.get("code") == 200:
            data = res["result"]
            return {"weather": data["weather"], "low": data["lowest"], "high": data["highest"]}
    except Exception:
        pass
    return {"weather": "多云", "low": "20℃", "high": "25℃"}

def get_caihongpi():
    try:
        url = f"https://apis.tianapi.com/caihongpi/index?key={TIANAPI_KEY}"
        res = requests.get(url, timeout=10).json()
        if res.get("code") == 200:
            content = res["result"]["content"]
            return content.replace("XXX", "小胡胡")
    except Exception:
        pass
    return "今天也超级喜欢你！"

# ==========================================
# 主运行管道与抽象语法树载荷封装
# ==========================================
def send_message():
    access_token = get_access_token()
    if not access_token:
        print("❌ Token 获取阻断")
        return False

    weather = get_weather()
    caihongpi = get_caihongpi()
    love_days = get_love_days()
    birthday_left = get_birthday_left()
    today = get_beijing_today()
    today_str = today.strftime("%Y年%m月%d日")

    holiday_str = get_dynamic_holiday_str(today, birthday_left, love_days)
    tip1, tip2, tip3 = get_segmented_weather_tips(weather)

    q1 = caihongpi[:18]
    q2 = caihongpi[18:36]
    q3 = caihongpi[36:54]
    q4 = caihongpi[54:72]
    
    temp_str = f"{weather['low']} ~ {weather['high']}"
    
    # 构建随机寄语节点并执行强行切片，规避顶层截断机制
    random_greeting = random.choice(DAILY_GREETINGS)
    full_top_str = f"早安，我最爱的宝宝！{random_greeting}"
    top1 = full_top_str[:18]
    top2 = full_top_str[18:36]

    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    data = {
        "touser": OPEN_ID,
        "template_id": TEMPLATE_ID,
        "data": {
            "top1": {"value": top1, "color": "#FF69B4"},
            "top2": {"value": f"{top2}\n", "color": "#FF69B4"},
            "d": {"value": today_str, "color": "#173177"},
            "c": {"value": CITY_NAME, "color": "#173177"},
            "w": {"value": weather["weather"], "color": "#173177"},
            "t": {"value": f"{temp_str}\n", "color": "#FF0000"},
            "ld": {"value": str(love_days), "color": "#FF69B4"},
            "bl": {"value": str(birthday_left), "color": "#FF69B4"},
            "h": {"value": f"{holiday_str}\n", "color": "#FF8C00"},
            "t1": {"value": tip1, "color": "#008000"},
            "t2": {"value": tip2, "color": "#008000"},
            "t3": {"value": f"{tip3}\n", "color": "#008000"},
            "q1": {"value": q1, "color": "#FF1493"},
            "q2": {"value": q2, "color": "#FF1493"},
            "q3": {"value": q3, "color": "#FF1493"},
            "q4": {"value": q4, "color": "#FF1493"},
        }
    }

    res = requests.post(url, json=data, timeout=10).json()
    if res.get("errcode") == 0:
        print("✅ 消息推送与渲染数据下发成功")
        return True
    print(f"❌ 微信网关返回错误: {res}")
    return False

if __name__ == "__main__":
    send_message()
