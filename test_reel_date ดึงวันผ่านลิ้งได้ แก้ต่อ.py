# test_reel_date.py
import json
import sys
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# ถ้าต้องการฟอร์แมตชื่อเดือนภาษาไทย
TH_MONTHS = [
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
]

def find_creation_time(obj):
    """
    เดิน tree ของ dict/list 
    แล้วเจอ key 'creation_time' (หรือกุญแจคล้ายๆ กัน) ก็ return ค่านั้นทันที
    """
    if isinstance(obj, dict):
        # ถ้าเจอ key ตรง ๆ
        if "creation_time" in obj and isinstance(obj["creation_time"], (int, float)):
            return int(obj["creation_time"])
        # เดินดูค่าในแต่ละ field
        for v in obj.values():
            res = find_creation_time(v)
            if res is not None:
                return res

    elif isinstance(obj, list):
        for item in obj:
            res = find_creation_time(item)
            if res is not None:
                return res

    return None

def find_any_time(obj):
    """
    เดิน tree ของ dict/list 
    หา key ที่ลงท้ายด้วย 'time' แล้วเก็บเป็น fallback
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower().endswith("time") and isinstance(v, (int, float)):
                return int(v)
            sub = find_any_time(v)
            if sub is not None:
                return sub

    elif isinstance(obj, list):
        for item in obj:
            sub = find_any_time(item)
            if sub is not None:
                return sub

    return None

def get_reel_date_via_json(reel_url: str, headless: bool=False):
    # 1) สร้าง Chrome driver
    opts = Options()
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    if headless:
        opts.add_argument("--headless=new")
    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)

    try:
        print(f"🌐 Loading Reel page: {reel_url}")
        driver.get(reel_url)
        driver.implicitly_wait(5)

        scripts = driver.find_elements("css selector", "script[type='application/json']")

        creation_ts = None
        fallback_ts = []

        for idx, s in enumerate(scripts):
            text = s.get_attribute("innerText") or ""
            if not text.strip().startswith("{") or len(text) < 200:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue

            # 1) ลองหา creation_time ก่อน
            ts_cre = find_creation_time(data)
            if ts_cre:
                creation_ts = ts_cre
                print(f"   → JSON#{idx} has creation_time = {creation_ts}")
                break

            # 2) ถ้าไม่เจอ ก็ fallback หา field อื่นลงท้ายด้วย 'time'
            ts_fb = find_any_time(data)
            if ts_fb:
                fallback_ts.append(ts_fb)
                print(f"   → try JSON#{idx} fallback time = {ts_fb}")

        # ตัดสินใจเลือก timestamp
        if creation_ts:
            ts_use = creation_ts
        elif fallback_ts:
            ts_use = max(fallback_ts)
            print(f"   → use fallback max time = {ts_use}")
        else:
            raise RuntimeError("❌ ไม่พบ timestamp ใดๆ ใน JSON scripts")

        # ถ้าเป็น millisecond ให้แปลง
        if ts_use > 1e12:
            ts_use //= 1000

        # แปลงเป็น UTC → บวก 7 ชั่วโมง
        dt_utc   = datetime.fromtimestamp(ts_use, tz=timezone.utc)
        dt_local = dt_utc + timedelta(hours=7)

        # ฟอร์แมตออกมา: 24 มิ.ย. 2025
        formatted = f"{dt_local.day} {TH_MONTHS[dt_local.month-1]} {dt_local.year}"
        print(f"✅ Post date: {formatted}")

    finally:
        driver.quit()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_reel_date.py <REEL_URL>")
        sys.exit(1)
    get_reel_date_via_json(sys.argv[1])
