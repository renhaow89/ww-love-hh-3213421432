# -*- coding: utf-8 -*-
import requests
import os
import random
import json
from datetime import datetime, timedelta, date
from zhdate import ZhDate

# ==================== 配置区 ====================
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
OPEN_ID = os.environ.get("OPEN_ID")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")
TIANAPI_KEY = os.environ.get("TIANAPI_KEY")

CITY_NAME = "杭州"
LOVE_DATE = date(2019, 3, 10)
BIRTHDAY_LUNAR = (1998, 8, 18)

HOLIDAY_SOLAR = {
    "01-01": "元旦", "02-14": "情人节", "03-08": "女神节", 
    "05-01": "劳动节", "05-20": "520表白日", "06-01": "儿童节", 
    "10-01": "国庆节", "11-01": "万圣节", "12-24": "平安夜", 
    "12-25": "圣诞节", "12-31": "跨年"
}
HOLIDAY_LUNAR = {
    (1, 1): "春节", (5, 5): "端午节", (7, 7): "七夕节", 
    (8, 15): "中秋节", (12, 8): "腊八节", (12, 24): "南方小年"
}

# 节日专属 Emoji 映射字典
HOLIDAY_EMOJI_MAP = {
    "春节": "🧨", "情人节": "🌹", "圣诞节": "🎄", "跨年": "🎉", 
    "元旦": "🎆", "女神节": "👑", "520表白日": "💖", "七夕节": "💕", 
    "儿童节": "🍭", "中秋节": "🥮", "恋爱纪念日": "🥂", "生日": "🎂",
    "恋爱里程碑": "✨"
}

# 二十四节气 C 值字典 (21世纪算法参数)
SOLAR_TERMS_C_VALUES = {
    "小寒": (1, 5.4055), "大寒": (1, 20.12), "立春": (2, 3.87), "雨水": (2, 18.73),
    "惊蛰": (3, 5.63), "春分": (3, 20.646), "清明": (4, 4.81), "谷雨": (4, 20.1),
    "立夏": (5, 5.52), "小满": (5, 21.04), "芒种": (6, 5.678), "夏至": (6, 21.37),
    "小暑": (7, 7.108), "大暑": (7, 22.83), "立秋": (8, 7.5), "处暑": (8, 23.13),
    "白露": (9, 7.646), "秋分": (9, 23.042), "寒露": (10, 8.318), "霜降": (10, 23.438),
    "立冬": (11, 7.438), "小雪": (11, 22.36), "大雪": (12, 7.18), "冬至": (12, 21.94)
}

# 星期情绪引擎：特定工作日语录 (每种 8 条)
MONDAY_GREETINGS = [
    "周一综合征发作啦？喝杯咖啡，新的一周也要元气满满哦 ☕",
    "新的一周开始啦，把周末的慵懒收一收，准备大干一场吧 💪",
    "周一早安！不管今天多忙，都要记得按时吃饭哦 🍱",
    "又是全新的周一，愿你拥有一个闪闪发光的开始 ✨",
    "周一早上好！喝杯热牛奶，开启元气满满的一周吧 🥛",
    "不管周末多开心，周一也要好好吃饭好好工作哦 💻",
    "新的一周，新的想你！今天也要做个开心的小朋友 🎈",
    "周一可能会有点忙，别忘了按时休息多喝水哦 🍵"
]
WEDNESDAY_GREETINGS = [
    "星期三啦！本周工作进度条已过半，坚持就是胜利 🔋",
    "周三早安，美好的小长假已经在向我们招手了，冲鸭 🦆",
    "熬过周三，哪怕是翻山！今天也要保持好心情哦 ⛰️",
    "进度条 50%！给自己加个油，剩下的两天也会顺顺利利 🎈",
    "周三啦！距离周末只有两天了，今天也要开心度过 🌻",
    "小周末快乐！今天下班要去吃点好吃的犒劳自己 🍰",
    "打工人撑住！美好的周末已经在向我们招手啦 👋",
    "周三早安！不管发生什么，我都在你身后支持你 ❤️"
]
THURSDAY_GREETINGS = [
    "疯狂星期四！马上就要熬出头啦，今天也要开心鸭 🍗",
    "周四到了，周末还会远吗？打起精神迎接美好的早晨 🌅",
    "曙光就在眼前！坚持过今天，明天就是快乐周五啦 🎉",
    "今天是充满希望的周四，记得对我多笑一笑哦 😊",
    "再坚持一下！熬过今天就是快乐周五啦，冲冲冲 🚀",
    "周四到了，连空气里都飘着快要放假的快乐气息 🍃",
    "快看，周末在前方探出头了！今天也要顺顺利利 🌟",
    "星期四早安！今天也要元气满满，准备迎接周末啦 🌈"
]
FRIDAY_GREETINGS = [
    "今天是周五啦！马上就能过周末咯 🎉", 
    "终于周五了！今晚想想吃点什么好吃的 🍖",
    "打工人的最后一天！周末已经在向你招手 👋", 
    "美丽的周五，连空气都充满了放假的快乐味道 ✨",
    "耶！终于周五了，今晚有什么开心的计划吗？ 🥂",
    "快乐周五！放假倒计时开始，今天的心情是彩色的 🎨",
    "周五早安！忙完今天就可以好好赖床啦，超开心 🛌",
    "熬过今天就是周末！下班后去吃顿大餐放松一下吧 🍔"
]
DAILY_GREETINGS = [
    "今天也要记得吃早餐哦 ❤️", "工作再忙，也别忘了照顾自己。", 
    "希望今天一切顺顺利利。", "今天也会是幸运的一天。", 
    "不要太累啦，记得按时休息。", "希望今天能有很多开心的小事情发生。",
    "早安呀！今天也要把好心情装进口袋里带出门哦 👜", "新的一天开始了，愿你遇到的一切都如你般可爱 🌸"
]

# ==================== 时间引擎 ====================
def get_beijing_today():
    return (datetime.utcnow() + timedelta(hours=8)).date()

def get_love_days():
    return (get_beijing_today() - LOVE_DATE).days

def _get_safe_lunar_date(year, l_month, l_day):
    for day_offset in range(l_day, l_day - 3, -1):
        try:
            return ZhDate(year, l_month, day_offset).to_datetime().date()
        except Exception:
            continue
    return date(year, 1, 1)

def _get_safe_solar_date(year, month, day):
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, month, day - 1)

def get_birthday_left():
    today = get_beijing_today()
    bday = _get_safe_lunar_date(today.year, BIRTHDAY_LUNAR[1], BIRTHDAY_LUNAR[2])
    if bday < today:
        bday = _get_safe_lunar_date(today.year + 1, BIRTHDAY_LUNAR[1], BIRTHDAY_LUNAR[2])
    return (bday - today).days

def get_qingming_date(year):
    y = year % 100
    day = int(y * 0.2422 + 4.81) - (y // 4)
    return date(year, 4, day)

def get_next_lunar_date(today, lunar_month, lunar_day):
    t_date = _get_safe_lunar_date(today.year, lunar_month, lunar_day)
    if t_date < today:
        t_date = _get_safe_lunar_date(today.year + 1, lunar_month, lunar_day)
    return t_date

def get_next_chuxi(today):
    sf_this_year = ZhDate(today.year, 1, 1).to_datetime().date()
    chuxi = sf_this_year - timedelta(days=1)
    if chuxi >= today: return chuxi
    return ZhDate(today.year + 1, 1, 1).to_datetime().date() - timedelta(days=1)

def get_dynamic_holiday_str(today, birthday_left, love_days):
    # 🌟 方案一：隐藏彩蛋最高优先级拦截
    if love_days in [520, 1314] or (love_days >= 100 and love_days % 100 == 0):
        return f"✨ 隐藏彩蛋：今天是相爱的第 {love_days} 天！❤️", "恋爱里程碑"

    candidates = {}
    for m_d, name in HOLIDAY_SOLAR.items():
        m, d = map(int, m_d.split("-"))
        h_date = _get_safe_solar_date(today.year, m, d)
        if h_date < today:
            h_date = _get_safe_solar_date(today.year + 1, m, d)
        candidates[name] = (h_date - today).days
        
    candidates["清明节"] = (get_qingming_date(today.year) - today).days if get_qingming_date(today.year) >= today else (get_qingming_date(today.year + 1) - today).days
    
    for (l_m, l_d), name in HOLIDAY_LUNAR.items():
        candidates[name] = (get_next_lunar_date(today, l_m, l_d) - today).days
    candidates["除夕"] = (get_next_chuxi(today) - today).days

    anni = _get_safe_solar_date(today.year, LOVE_DATE.month, LOVE_DATE.day)
    if anni < today:
        anni = _get_safe_solar_date(today.year + 1, LOVE_DATE.month, LOVE_DATE.day)
    candidates["恋爱纪念日"] = (anni - today).days

    # 常规生日与纪念日拦截
    if birthday_left == 0: 
        return "今天是小胡胡的农历生日！🎂", "生日"
    if candidates.get("恋爱纪念日") == 0: 
        return f"今天是恋爱 {love_days // 365} 周年纪念日！❤️", "恋爱纪念日"
    
    for name, days in candidates.items():
        if days == 0: 
            return f"今天是{name}快乐！❤️", name
            
    # 🌸 方案三：二十四节气次级拦截（如果今天没有大节，判断是否是节气）
    for term_name, (month, c) in SOLAR_TERMS_C_VALUES.items():
        if today.month == month:
            y = today.year % 100
            day = int(y * 0.2422 + c) - (y // 4)
            if today.day == day:
                return f"今天是【{term_name}】，感受中式浪漫 🌸", term_name
        
    # 如果什么节日和节气都没有，正常显示下个节日
    next_name, next_days = min(candidates.items(), key=lambda x: x[1])
    return f"下个节日【{next_name}】还有 {next_days} 天 ⏳", None

# ==================== 文本计算 ====================
def get_segmented_weather_tips(weather_info):
    weather_str = weather_info.get("weather", "")
    low_str = weather_info.get("low", "")
    high_str = weather_info.get("high", "")
    
    default_tips = [
        ["今天天气不错哦，", "希望你这一天，", "都有好心情相伴 ❤️"],
        ["无论外面天气如何，", "你在我心里，", "永远是晴空万里 🌈"],
        ["把烦恼留在昨天，", "让快乐装满今天，", "愿你事事顺心顺意 🌟"]
    ]
    lines = random.choice(default_tips)
    
    try:
        cl = float(low_str.replace("℃","").replace("°C","").strip())
        ch = float(high_str.replace("℃","").replace("°C","").strip())
        
        if ch >= 35.0: 
            lines = random.choice([
                ["今天杭州比较热，", "记得多喝点水，", "空调也不要吹太久哦 ❤️"],
                ["外面太阳超级大！", "出门千万要防晒，", "尽量待在室内哦 🍦"],
                ["高温预警来啦，", "冰镇西瓜准备好，", "别让自己热坏了 🍉"]
            ])
        elif ch >= 30.0: 
            lines = random.choice([
                ["今天气温有点偏高，", "出门注意做好防晒，", "多喝水谨防中暑 ❤️"],
                ["微热的天气，", "适合喝点冰镇饮料，", "享受夏日的小美好 🥤"]
            ])
        elif cl <= 10.0: 
            lines = random.choice([
                ["今天有点降温啦，", "记得多穿两件厚衣服，", "千万别感冒了 ❤️"],
                ["外面风吹着有点冷，", "出门记得带件外套，", "把自己裹得暖暖的 🧣"]
            ])
        elif "雨" in weather_str: 
            lines = random.choice([
                ["杭州今天有雨，", "出门记得带伞哦～", "希望一路顺顺利利 ❤️"],
                ["阴雨绵绵的日子，", "适合泡一杯热奶茶，", "享受片刻的宁静 ☕"]
            ])
        elif "雪" in weather_str: 
            lines = random.choice([
                ["今天下雪啦，", "路面可能会打滑，", "走路要注意安全哦 ❤️"],
                ["哇，外面飘雪了，", "记得戴上手套帽子，", "别冻坏了小手 🧤"]
            ])
        elif "晴" in weather_str: 
            lines = random.choice([
                ["☀ 今天天气很好，", "希望你今天也能，", "拥有一个好心情 ❤️"],
                ["☀ 阳光刚刚好，", "微风不燥，", "很适合出门拥抱自然 🍃"]
            ])
        elif "阴" in weather_str or "多云" in weather_str: 
            lines = random.choice([
                ["🌤 今天虽然有点阴，", "但希望你的心情，", "一直都是晴天 ❤️"],
                ["☁️ 云朵挡住了太阳，", "天气感觉挺凉爽的，", "是个舒服的好日子 🍃"]
            ])
    except Exception: 
        pass
        
    return (
        lines[0] + "\n" if len(lines) > 0 else "", 
        lines[1] + "\n" if len(lines) > 1 else "", 
        lines[2] if len(lines) > 2 else ""
    )

# ==================== API 请求 ====================
def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    return requests.get(url, timeout=10).json().get("access_token")

def get_weather():
    try:
        url = f"https://apis.tianapi.com/tianqi/index?key={TIANAPI_KEY}&city={CITY_NAME}&type=1"
        res = requests.get(url, timeout=10).json()
        if res.get("code") == 200: 
            return {
                "weather": res["result"]["weather"], 
                "low": res["result"]["lowest"], 
                "high": res["result"]["highest"]
            }
    except: 
        pass
    return {"weather": "多云", "low": "20℃", "high": "25℃"}

def get_caihongpi():
    try:
        url = f"https://apis.tianapi.com/caihongpi/index?key={TIANAPI_KEY}"
        res = requests.get(url, timeout=10).json()
        if res.get("code") == 200: 
            return res["result"]["content"].replace("XXX", "小胡胡")
    except: 
        pass
    return "今天也超级喜欢你！"

# ==================== 主发信管道 ====================
def send_message():
    access_token = get_access_token()
    if not access_token: 
        print("❌ 获取 Access Token 失败")
        return False

    weather = get_weather()
    caihongpi = get_caihongpi()
    love_days = get_love_days()
    birthday_left = get_birthday_left()
    today = get_beijing_today()
    
    # 动态匹配节日文案与名称
    holiday_text, today_holiday_name = get_dynamic_holiday_str(today, birthday_left, love_days)
    
    # 获取专属 Emoji (节气统一用 🌸 兜底，其他走字典)
    if today_holiday_name in SOLAR_TERMS_C_VALUES:
        holiday_emoji = "🌸"
    else:
        holiday_emoji = HOLIDAY_EMOJI_MAP.get(today_holiday_name, "")
    
    # 🏖️ 假期情绪拦截引擎 (优先级高于普通星期)
    is_holiday_half = False
    is_holiday_end = False
    
    # 1. 公历长假判断 (五一、国庆)
    if (today.month == 10 and today.day == 4) or (today.month == 5 and today.day == 3):
        is_holiday_half = True
    elif (today.month == 10 and today.day == 7) or (today.month == 5 and today.day == 5):
        is_holiday_end = True
        
    # 2. 农历长假判断 (春节 正月初四、初七)
    if today == _get_safe_lunar_date(today.year, 1, 4):
        is_holiday_half = True
    elif today == _get_safe_lunar_date(today.year, 1, 7):
        is_holiday_end = True

    # 📅 组合状态：全自动“假期拦截”与“星期情绪”判断
    if is_holiday_half:
        greeting_text = random.choice(HOLIDAY_HALF_GREETINGS)
    elif is_holiday_end:
        greeting_text = random.choice(HOLIDAY_END_GREETINGS)
    else:
        weekday = today.weekday()
        if weekday == 0:
            greeting_text = random.choice(MONDAY_GREETINGS)
        elif weekday == 2:
            greeting_text = random.choice(WEDNESDAY_GREETINGS)
        elif weekday == 3:
            greeting_text = random.choice(THURSDAY_GREETINGS)
        elif weekday == 4:
            greeting_text = random.choice(FRIDAY_GREETINGS)
        else:
            greeting_text = random.choice(DAILY_GREETINGS)
    
    # 将彩蛋 Emoji 与情绪语录无缝拼接 (总计切片36字符)
    full_top = f"{holiday_emoji}早安，我最爱的宝宝！{greeting_text}"
    top1 = full_top[:18]
    top2 = full_top[18:36]
    
    tip1, tip2, tip3 = get_segmented_weather_tips(weather)
    
    q1 = caihongpi[:18]
    q2 = caihongpi[18:36]
    q3 = caihongpi[36:54]
    q4 = caihongpi[54:72]

    # 动态计算气温颜色
    try:
        high_temp = float(weather["high"].replace("℃","").replace("°C","").strip())
        if high_temp >= 30.0:
            temp_color = "#FF0000"  # 红色
        elif high_temp <= 15.0:
            temp_color = "#1E90FF"  # 蓝色
        else:
            temp_color = "#008000"  # 绿色
    except:
        temp_color = "#FF0000"

    data = {
        "touser": OPEN_ID, 
        "template_id": TEMPLATE_ID,
        "data": {
            "top1": {"value": top1, "color": "#FF69B4"}, 
            "top2": {"value": f"{top2}\n", "color": "#FF69B4"},
            "d": {"value": today.strftime("%Y年%m月%d日"), "color": "#173177"},
            "c": {"value": CITY_NAME, "color": "#173177"}, 
            "w": {"value": weather["weather"], "color": "#173177"},
            "t": {"value": f"{weather['low']} ~ {weather['high']}\n", "color": temp_color},
            "ld": {"value": str(love_days), "color": "#FF69B4"}, 
            "bl": {"value": str(birthday_left), "color": "#FF69B4"},
            "h": {"value": f"{holiday_text}\n", "color": "#FF8C00"},
            "t1": {"value": tip1, "color": "#008000"}, 
            "t2": {"value": tip2, "color": "#008000"}, 
            "t3": {"value": f"{tip3}\n", "color": "#008000"},
            "q1": {"value": q1, "color": "#FF1493"}, 
            "q2": {"value": q2, "color": "#FF1493"}, 
            "q3": {"value": q3, "color": "#FF1493"}, 
            "q4": {"value": q4, "color": "#FF1493"},
        }
    }
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    res = requests.post(url, json=data, timeout=10).json()
    
    if res.get("errcode") == 0:
        print("✅ 推送成功！本次推送的具体文案数据如下：")
        print(json.dumps(data.get("data"), ensure_ascii=False, indent=2))
        return True
        
    print(f"❌ 推送失败，微信接口返回错误: {res}")
    print("准备推送的数据为：")
    print(json.dumps(data.get("data"), ensure_ascii=False, indent=2))
    return False

if __name__ == "__main__":
    send_message()
