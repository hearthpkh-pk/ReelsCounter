# test_reel_date.py
import json
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def find_creation_time(obj):
    """
    เดิน tree ของ dict/list 
    แล้วเจอ key 'creation_time' ก็ return ค่านั้นทันที
    """
    if isinstance(obj, dict):
        # ถ้าเจอ key ตรง ๆ
        if "creation_time" in obj and isinstance(obj["creation_time"], (int, float)):
            return obj["creation_time"]
        # เดินเข้าไปดูค่าตัวอื่นๆ
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

def get_reel_date_via_json(reel_url):
    # 1) เตรียม ChromeDriver
    opts = Options()
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    # หากต้องการซ่อนเบราเซอร์ ให้เปิด headless
    # opts.add_argument("--headless=new")

    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)

    try:
        print(f"🌐 Loading Reel page: {reel_url}")
        driver.get(reel_url)

        # 2) รอให้ script โหลดเสร็จ (ถ้าจำเป็นอาจเพิ่ม WebDriverWait)
        driver.implicitly_wait(5)

        # 3) ดึงทุก <script type="application/json">
        scripts = driver.find_elements("css selector", "script[type='application/json']")

        # 4) ไล่หา JSON ที่มี creation_time
        for idx, s in enumerate(scripts):
            text = s.get_attribute("innerText").strip()
            # ข้อควรระวัง: สคริปต์บางตัวอาจไม่ใช่ JSON จึงข้าม
            if not text.startswith("{") or len(text) < 200:
                continue

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue

            ts = find_creation_time(data)
            if ts:
                dt = datetime.fromtimestamp(ts)
                print(f"✅ Post date (from JSON#{idx}): {dt.isoformat()}")
                break
        else:
            print("❌ ไม่พบ creation_time ใน JSON ใด ๆ")

    finally:
        driver.quit()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_reel_date.py <REEL_URL>")
        sys.exit(1)

    url = sys.argv[1]
    get_reel_date_via_json(url)
