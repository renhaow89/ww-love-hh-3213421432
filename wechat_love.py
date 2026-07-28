# -*- coding: utf-8 -*-
import requests
import os
import random
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
DAILY_GREETINGS = [
    "今天也要记得吃早餐哦 ❤️", 
    "工作再忙，也别忘了照顾自己。", 
    "希望今天一切顺顺利利。", 
    "今天也会是幸运的一天。", 
    "不要太累啦，记得按时休息。", 
    "希望今天能有很多开心的小事情发生。"
]
FRIDAY_GREETINGS = [
    "今天是周五啦！马上就能过周末咯 🎉",
    "终于周五了！今晚想想吃点什么好吃的 🍖",
    "打工人的最后一天！周末已经在向你招手 👋",
    "周五早安！提前祝宝宝周末愉快哦 ❤️",
    "美丽的周五，连空气都充满了放假的快乐味道 ✨",
    "坚持一下，今天下班就可以尽情放松啦 🎮",
    "周五到了，本周的疲惫即将清零 🔋",
    "今天是充满希望的周五，要开心度过哦 😊"
]

# ==================== 时间引擎 ====================
def get_beijing_today():
    """获取修正时区后的北京时间"""
    return (datetime.utcnow() + timedelta(hours=8)).date()

def get_love_days():
    """计算恋爱天数"""
    return (get_beijing_today() - LOVE_DATE).days

def _get_safe_lunar_date(year, l_month, l_day):
    """
    农历日期安全解析引擎
    机制：应对农历大小月问题。若目标日（如30日）在当月不存在，自动递减至该月实际最后一天（29日）。
    """
    for day_offset in range(l_day, l_day - 3, -1):
        try:
            return ZhDate(year, l_month, day_offset).to_datetime().date()
        except Exception:
            continue
    # 极端异常兜底，强制转换为该年1月1日，避免返回破坏性魔法数据
    return date(year, 1, 1)

def _get_safe_solar_date(year, month, day):
    """
    公历日期安全解析引擎
    机制：拦截闰年 2月29日 在平年的 ValueError，自动降级为 2月28日。
    """
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, month, day - 1)

def get_birthday_left():
    today = get_beijing_today()
    bday = _get_safe_lunar_date(today.year, BIRTHDAY_LUNAR[1], BIRTHDAY_LUNAR[2])
    
    # 如果今年的生日已经过了，计算明年的生日
    if bday < today:
        bday = _get_safe_lunar_date(today.year + 1, BIRTHDAY_LUNAR[1], BIRTHDAY_LUNAR[2])
        
    return (bday - today).days

def get_qingming_date(year):
    """计算清明节日期（利用世纪常数公式）"""
    y = year % 100
    day = int(y * 0.2422 + 4.81) - (y // 4)
    return date(year, 4, day)

def get_next_lunar_date(today, lunar_month, lunar_day):
    """获取下一个指定的农历日期"""
    t_date = _get_safe_lunar_date(today.year, lunar_month, lunar_day)
    if t_date < today:
        t_date = _get_safe_lunar_date(today.year + 1, lunar_month, lunar_day)
    return t_date

def get_next_chuxi(today):
    """计算下一个除夕日期"""
    sf_this_year = ZhDate(today.year, 1, 1).to_datetime().date()
    chuxi = sf_this_year - timedelta(days=1)
    if chuxi >= today: 
        return chuxi
    return ZhDate(today.year + 1, 1, 1).to_datetime().date() - timedelta(days=1)

def get_dynamic_holiday_str(today, birthday_left, love_days):
    candidates = {}
    
    # 1. 公历节日测算
    for m_d, name in HOLIDAY_SOLAR.items():
        m, d = map(int, m_d.split("-"))
        h_date = _get_safe_solar_date(today.year, m, d)
        if h_date < today:
            h_date = _get_safe_solar_date(today.year + 1, m, d)
        candidates[name] = (h_date - today).days
        
    # 2. 清明节测算
    qm = get_qingming_date(today.year)
    if qm < today:
        qm = get_qingming_date(today.year + 1)
    candidates["清明节"] = (qm - today).days
    
    # 3. 农历节日测算
    for (l_m, l_d), name in HOLIDAY_LUNAR.items():
        candidates[name] = (get_next_lunar_date(today, l_m, l_d) - today).days
    candidates["除夕"] = (get_next_chuxi(today) - today).days

    # 4. 纪念日测算 (引入安全历法引擎防止闰年崩溃)
    anni = _get_safe_solar_date(today.year, LOVE_DATE.month, LOVE_DATE.day)
    if anni < today:
        anni = _get_safe_solar_date(today.year + 1, LOVE_DATE.month, LOVE_DATE.day)
    candidates["恋爱纪念日"] = (anni - today).days

    # 5. 优先级匹配（当天节日直接返回）
    if birthday_left == 0: 
        return "今天是小胡胡的农历生日！🎂"
    if candidates.get("恋爱纪念日") == 0: 
        return f"今天是恋爱 {love_days // 365} 周年纪念日！❤️"
    for name, days in candidates.items():
        if days == 0: 
            return f"今天是{name}快乐！❤️"
        
    # 6. 获取最近的下一个节日
    next_name, next_days = min(candidates.items(), key=lambda x: x[1])
    return f"下个节日【{next_name}】还有 {next_days} 天 ⏳"

# ==================== 文本计算 ====================
def get_segmented_weather_tips(weather_info):
    weather_str = weather_info.get("weather", "")
    low_str = weather_info.get("low", "")
    high_str = weather_info.get("high", "")
    
    # 默认兜底文案池（10个）
    default_tips = [
        ["今天天气不错哦，", "希望你这一天，", "都有好心情相伴 ❤️"],
        ["新的一天开始啦，", "不管天气怎么样，", "都要开开心心的 😊"],
        ["平平淡淡的天气，", "也有小确幸在等你，", "今天也要加油哦 💪"],
        ["早安呀宝宝，", "带着满怀的期待，", "开启充满活力的一天吧 ✨"],
        ["无论外面天气如何，", "你在我心里，", "永远是晴空万里 🌈"],
        ["用心去感受生活，", "每一个平凡的日子，", "都因为你而闪闪发光 💖"],
        ["今天也是元气满满，", "记得保持微笑哦，", "好运会向你奔赴而来 🍀"],
        ["把烦恼留在昨天，", "让快乐装满今天，", "愿你事事顺心顺意 🌟"],
        ["美好的早晨，", "送上我最暖的问候，", "愿你拥有一整天的快乐 🎈"],
        ["又是一个崭新的开始，", "带着好心情出发，", "去遇见更多的美好吧 🌻"]
    ]
    lines = random.choice(default_tips)
    
    try:
        cl = float(low_str.replace("℃","").replace("°C","").strip())
        ch = float(high_str.replace("℃","").replace("°C","").strip())
        
        if ch >= 35.0: 
            lines = random.choice([
                ["今天杭州比较热，", "记得多喝点水，", "空调也不要吹太久哦 ❤️"],
                ["外面太阳超级大！", "出门千万要防晒，", "尽量待在室内哦 🍦"],
                ["高温预警来啦，", "冰镇西瓜准备好，", "别让自己热坏了 🍉"],
                ["今天真的是酷暑，", "多喝绿豆汤解暑，", "心静自然凉呀 🧊"],
                ["热浪滚滚的一天，", "记得带好遮阳伞，", "防晒霜绝对不能忘 ☂️"],
                ["气温飙升啦，", "快把冰淇淋安排上，", "给燥热的心降降温 🍨"],
                ["外面像个大火炉，", "如果没有必要，", "就躲在空调房里吧 🌬️"],
                ["今天太阳很毒，", "墨镜防晒衣穿戴好，", "别让我的宝宝晒黑了 🕶️"],
                ["酷热难耐的天气，", "记得补充电解质水，", "千万小心中暑哦 💦"],
                ["又是汗流浃背的一天，", "回家洗个舒服的澡，", "洗去一天的疲惫吧 🛁"]
            ])
        elif ch >= 30.0: 
            lines = random.choice([
                ["今天气温有点偏高，", "出门注意做好防晒，", "多喝水谨防中暑 ❤️"],
                ["天气开始热起来了，", "记得穿透气一点，", "带把遮阳伞出门 ☂️"],
                ["有点夏天的感觉啦，", "防晒霜记得涂好，", "保持清爽好心情 🍹"],
                ["微热的天气，", "适合喝点冰镇饮料，", "享受夏日的小美好 🥤"],
                ["阳光开始变得刺眼，", "遮阳帽记得戴上，", "保护好自己哦 🧢"],
                ["气温逐渐攀升，", "出门记得带包纸巾，", "擦擦脸上的小汗珠 🧻"],
                ["天气闷热的话，", "可以喷点清凉喷雾，", "让自己舒服一点 ❄️"],
                ["有点小热的日子，", "穿上你最喜欢的夏装，", "美美地出门吧 👗"],
                ["虽然有点热，", "但也要保持好心情，", "像向日葵一样灿烂 🌻"],
                ["夏天的气息越来越浓，", "注意饮食清淡些，", "照顾好自己的胃哦 🥗"]
            ])
        elif cl <= 10.0: 
            lines = random.choice([
                ["今天有点降温啦，", "记得多穿两件厚衣服，", "千万别感冒了 ❤️"],
                ["外面风吹着有点冷，", "出门记得带件外套，", "把自己裹得暖暖的 🧣"],
                ["气温有点低哦，", "可以喝点热茶暖身，", "注意保暖别着凉 🍵"],
                ["冷空气来袭，", "秋裤棉袜快安排上，", "脚部保暖很重要 🧦"],
                ["今天体感比较冷，", "多喝热水多运动，", "别让寒气钻进身体 🏃‍♀️"],
                ["外面冷飕飕的，", "出门记得戴上围巾，", "把脖子捂得严严实实 🧣"],
                ["好冷的一天呀，", "真想把你抱在怀里，", "给你传递我的温度 🫂"],
                ["降温了宝宝，", "晚饭吃点热乎的火锅，", "驱赶一天的寒气吧 🍲"],
                ["气温骤降，", "早晚温差比较大，", "洋葱式穿衣法学起来 🧥"],
                ["天冷更要注意休息，", "晚上早点钻进被窝，", "做一个暖暖的梦 🛌"]
            ])
        elif "雨" in weather_str: 
            lines = random.choice([
                ["杭州今天有雨，", "出门记得带伞哦～", "希望一路顺顺利利 ❤️"],
                ["外面滴滴答答下雨，", "记得穿防滑的鞋子，", "带好雨伞再出门 ☔"],
                ["雨天路有点滑，", "走路开车都要慢点，", "我的心陪你撑伞 🌂"],
                ["又是下雨的一天，", "别让坏天气影响心情，", "听听雨声也很治愈 🌧️"],
                ["雨水冲刷着城市，", "出门记得带好雨具，", "别淋湿了衣服哦 🧥"],
                ["阴雨绵绵的日子，", "适合泡一杯热奶茶，", "享受片刻的宁静 ☕"],
                ["下雨天记得关好门窗，", "出门在外小心水坑，", "别弄脏了漂亮的鞋 🥾"],
                ["虽然天在下雨，", "但一想到你，", "我的世界就放晴了 ☀️"],
                ["淅淅沥沥的小雨，", "带上一把结实的伞，", "为你遮风挡雨 ☂️"],
                ["雨天虽然出行不便，", "但空气很清新，", "深呼吸放松一下吧 🌿"]
            ])
        elif "雪" in weather_str: 
            lines = random.choice([
                ["今天下雪啦，", "路面可能会打滑，", "走路要注意安全哦 ❤️"],
                ["哇，外面飘雪了，", "记得戴上手套帽子，", "别冻坏了小手 🧤"],
                ["雪花飞舞的季节，", "真想和你一起打雪仗，", "堆一个可爱的雪人 ⛄"],
                ["天气极寒有雪，", "出门必须全副武装，", "防寒保暖是第一位 🧣"],
                ["下雪天虽然冷，", "但也超级浪漫，", "注意保暖哦宝宝 ❄️"],
                ["雪后的世界纯洁美丽，", "出行要注意防滑，", "开车的话要减速慢行 🚗"],
                ["飘着雪花的早晨，", "喝杯热豆浆暖暖胃，", "开启美好的一天 🥛"],
                ["今天有降雪，", "出门别忘了带伞，", "防止雪水融化弄湿头发 ☂️"],
                ["白茫茫的雪景真好看，", "多穿点衣服再去赏雪，", "做个温暖的雪精灵 🧚‍♀️"],
                ["雪天寒风刺骨，", "把自己裹成小粽子，", "不让冷风有可乘之机 🧥"]
            ])
        elif "晴" in weather_str: 
            lines = random.choice([
                ["☀ 今天天气很好，", "希望你今天也能，", "拥有一个好心情 ❤️"],
                ["☀ 阳光明媚的一天，", "要把被子拿出来晒晒，", "心情也要晒晒太阳 🌞"],
                ["☀ 天空蓝蓝的，", "是很棒的大晴天，", "出门走走吸吸氧吧 🌿"],
                ["☀ 阳光刚刚好，", "微风不燥，", "很适合出门拥抱自然 🍃"],
                ["☀ 艳阳高照的日子，", "不仅要防晒，", "也要多补充水分哦 💧"],
                ["☀ 看着窗外的大太阳，", "所有的烦恼都被蒸发，", "又是充满干劲的一天 💪"],
                ["☀ 晴朗的好天气，", "连空气里都弥漫着，", "快乐和幸福的味道 🍬"],
                ["☀ 阳光洒在身上暖暖的，", "愿你的笑容，", "比今天的阳光更耀眼 ✨"],
                ["☀ 晴天是最美的滤镜，", "今天无论去哪里，", "都要拍美美的照片哦 📷"],
                ["☀ 这么好的天气，", "真想牵着你的手，", "一起在阳光下漫步 👫"]
            ])
        elif "阴" in weather_str or "多云" in weather_str: 
            lines = random.choice([
                ["🌤 今天虽然有点阴，", "但希望你的心情，", "一直都是晴天 ❤️"],
                ["☁️ 云朵挡住了太阳，", "天气感觉挺凉爽的，", "是个舒服的好日子 🍃"],
                ["🌤 多云转晴的心情，", "哪怕见不到太阳，", "我也在发光陪你 ✨"],
                ["☁️ 阴天虽然没有阳光，", "但紫外线还是有的，", "出门别忘了涂防晒霜 🧴"],
                ["🌤 天色稍微有点暗，", "但不要因此 emo 哦，", "想想开心的事情吧 💭"],
                ["☁️ 云层厚厚的天气，", "很适合在家里宅着，", "看看书追追剧 📖"],
                ["🌤 没有大太阳的暴晒，", "出门感觉微风拂面，", "享受这份惬意吧 🎐"],
                ["☁️ 虽然是阴天，", "但我的爱像太阳一样，", "永远温暖着你 ☀️"],
                ["🌤 灰蒙蒙的天空下，", "也要保持内心的明亮，", "做自己世界里的小太阳 🌻"],
                ["☁️ 阴天可能会让人慵懒，", "喝杯咖啡提提神，", "继续为梦想努力吧 ☕"]
            ])
    except Exception: 
        pass
        
    # 按要求返回并注入 \n 用于撑开视图盒子，绝对不要更改这里的逻辑
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
    
    # 判断今天是否为周五 (0是周一，4是周五)
    if today.weekday() == 4:
        greeting_text = random.choice(FRIDAY_GREETINGS)
    else:
        greeting_text = random.choice(DAILY_GREETINGS)
    
    # 【核心防御】物理截断与折叠防御：切片长度严格控制在18，并注入\n
    full_top = f"早安，我最爱的宝宝！{greeting_text}"
    top1 = full_top[:18]
    top2 = full_top[18:36]
    
    tip1, tip2, tip3 = get_segmented_weather_tips(weather)
    
    q1 = caihongpi[:18]
    q2 = caihongpi[18:36]
    q3 = caihongpi[36:54]
    q4 = caihongpi[54:72]

    # 【核心防御】模板组装时严禁破坏现有数据结构，保留末尾换行
    data = {
        "touser": OPEN_ID, 
        "template_id": TEMPLATE_ID,
        "data": {
            "top1": {"value": top1, "color": "#FF69B4"}, 
            "top2": {"value": f"{top2}\n", "color": "#FF69B4"},
            "d": {"value": today.strftime("%Y年%m月%d日"), "color": "#173177"},
            "c": {"value": CITY_NAME, "color": "#173177"}, 
            "w": {"value": weather["weather"], "color": "#173177"},
            "t": {"value": f"{weather['low']} ~ {weather['high']}\n", "color": "#FF0000"},
            "ld": {"value": str(love_days), "color": "#FF69B4"}, 
            "bl": {"value": str(birthday_left), "color": "#FF69B4"},
            "h": {"value": f"{get_dynamic_holiday_str(today, birthday_left, love_days)}\n", "color": "#FF8C00"},
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
        # 仅提取核心的数据载体(data)部分打印，缩进设为2个空格，确保中文正常显示
        print(json.dumps(data.get("data"), ensure_ascii=False, indent=2))
        return True
        
    print(f"❌ 推送失败，微信接口返回错误: {res}")
    print("准备推送的数据为：")
    print(json.dumps(data.get("data"), ensure_ascii=False, indent=2))
    return False

if __name__ == "__main__":
    send_message()
