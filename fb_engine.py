# fb_core_engine.py - Part 1: Base Utils, Cookies, View Count, Date Parser

# 💡 สำหรับ Cython ให้ Build ได้ — Safety Defaults
#collected_reels_list_fb = []
#scroll_pause = 1.0
#initial_scroll_attempts_target = 5
#timeout_seconds = 30

# 📦 Built-in
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'constants')))

import os
import re
import json
import time
import platform
import threading
import datetime
import queue
import concurrent.futures
from urllib.parse import urlparse, parse_qs
# ใช้ Selenium Manager / webdriver-manager สำหรับจัดการ Driver อัตโนมัติ
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import json
from datetime import datetime, timedelta, timezone
from selenium.webdriver.common.by import By
# 🌐 Selenium
from datetime import datetime as dt, timedelta

from selenium.common.exceptions import WebDriverException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
# ⚙️ Constants (config สำหรับ Facebook)
from constants_fb import XPATH_VIEW_COUNT, XPATH_DATE_TEXT, XPATHS_PRIORITY_LIST

# ⬇️⬇️ สวิตช์หลักอยู่ตรงนี้ ⬇️⬇️
# True = โหมดพัฒนา (เห็นอีโมจิ)
# False = โหมดสำหรับสร้าง .exe (เป็นตัวอักษร ปลอดภัย) #f"{get_symbol('wait')}
IS_DEV_MODE = True 

def get_symbol(symbol_type: str) -> str:
    """แปลงชนิดของสัญลักษณ์เป็นอีโมจิ (ตอนพัฒนา) หรือข้อความ (ตอนใช้งานจริง)"""
    if IS_DEV_MODE:
        symbols = {
            "ok": "✅",
            "error": "❌",
            "warn": "⚠️",
            "info": "🔵",
            "scan": "🔍",
            "debug": "⚙️",
            "wait": "⏳",
            "start": "⚡",
            "Cleared": "👍",
            "manual": "🕹️"
                # <--- เพิ่มบรรทัดนี้           
            
        }
    else:
        # ใช้ข้อความที่ปลอดภัยสำหรับไฟล์ .exe
        symbols = {
            "ok": "[OK]",
            "error": "[ERROR]",
            "warn": "[WARN]",
            "info": "[INFO]",
            "scan": "[SCAN]",
            "debug": "[DEBUG]",
            "wait": "[...]",
            "start": "[START]",
            "Cleared": "[Cleared]",
            "manual": "[MANUAL]" # <--- เพิ่มบรรทัดนี้
        }
    return symbols.get(symbol_type, "")

# ================== จบส่วนที่เพิ่ม ==================

def safe_utf8(text):
    try:
        return str(text).encode('utf-8', errors='replace').decode('utf-8')
    except Exception:
        return "[Encode Error]"


# ⚠️ extract_id_from_url สำหรับ Cython compiler ใช้ตอน build
def extract_id_from_url(url):
    # รองรับ URL reels และโพสต์ปกติ
    if "reel/" in url:
        return url.split("reel/")[1].split("/")[0]
    elif "/posts/" in url:
        return url.split("/posts/")[1].split("/")[0]
    return ""
# ⚠️ extract_id_from_url สำหรับ Cython compiler ใช้ตอน build

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)


def check_and_prepare_facebook_language(driver, url, load_cookies_func=None, js_callback=None):
    # สร้างฟังก์ชัน log_func จาก js_callback เพื่อให้เรียกใช้งานง่าย
    def log_func(message):
        if js_callback:
            # รูปแบบ callback ของคุณต้องการ Dictionary
            js_callback({"type": "log", "message": message})

    try:
        if load_cookies_func:
            load_cookies_func(driver)

        driver.get(url)
       
        WebDriverWait(driver, 6).until(
            lambda d: d.find_element(By.TAG_NAME, 'html')
        )

        lang_attr = driver.find_element(By.TAG_NAME, 'html').get_attribute('lang')
        if lang_attr and lang_attr.startswith("th"):
            log_func(safe_utf8("[OK] Facebook เป็นภาษาไทยอยู่แล้ว (html lang=th)"))
            return

        page_text = driver.page_source.lower()
        thai_keywords = ["หน้าหลัก", "วิดีโอ", "ผู้ติดต่อ", "สร้างสตอรี่"]
        if any(word in page_text for word in thai_keywords):
            log_func(safe_utf8("[OK] Facebook เป็นภาษาไทยอยู่แล้ว (ตรวจจากข้อความ)"))
            return

        log_func(safe_utf8(f"[WARN] Facebook ไม่ใช่ภาษาไทย (lang={lang_attr}) → กำลังเปลี่ยนเป็นภาษาไทยอัตโนมัติ..."))

        driver.get("https://www.facebook.com/settings/?tab=language_and_region")

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//span[contains(text(), "Account language")]'))
        )

        # ส่ง log_func ต่อไปให้ฟังก์ชันลูก
        auto_change_language_to_thai(driver, log_func)

        driver.get(url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )

    except Exception as e:
        log_func(safe_utf8(f"[WARN] ตรวจสอบหรือเปลี่ยนภาษาไม่สำเร็จ: {e}"))

def auto_change_language_to_thai(driver, log_func: callable):
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Account language")]'))
        ).click()
        time.sleep(1)

        input_lang = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//div[@role="dialog"]//input[contains(@placeholder, "Search")]'))
        )
        input_lang.clear()
        input_lang.send_keys("thai")
        time.sleep(1)

        thai_radio = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "ภาษาไทย")]/ancestor::div[contains(@role,"radio")]'))
        )
        driver.execute_script("arguments[0].click();", thai_radio)

        save_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@aria-label="Save & refresh"]'))
        )
        driver.execute_script("arguments[0].click();", save_button)
        time.sleep(2)

        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.TAG_NAME, 'html').get_attribute('lang') == 'th'
        )

        log_func(safe_utf8("[OK] เปลี่ยนภาษาไทยสำเร็จ (กด Save ด้วย)"))
        return True

    except Exception as e:
        log_func(safe_utf8(f"[FAIL] เปลี่ยนภาษาไทยไม่สำเร็จ: {e}"))
        return False




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

def get_reel_date_via_json_driver(driver, reel_url):
    driver.get(reel_url)
    driver.refresh()

    max_tries = 3
    for attempt in range(max_tries):
        try:
            time.sleep(1.2 + attempt * 0.8)  # รอเพิ่มขึ้นเรื่อยๆ 1.2 → 2.0 → 2.8

            # ✅ รอให้ <script type="application/json"> ปรากฏก่อน
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "script[type='application/json']"))
            )
            time.sleep(1.2)  # 🔧 เพิ่มเพื่อให้แน่ใจว่า script โหลดครบจริง
            
            # ✅ หา JSON scripts ทั้งหมด
            scripts = driver.find_elements(By.CSS_SELECTOR, "script[type='application/json']")

            # 🔧 รอจนมี scripts ที่ความยาวพอ (เพื่อกันโหลดไม่ครบ)
            valid_scripts = []
            for s in scripts:
                txt = s.get_attribute("innerText") or ""
                if txt.strip().startswith("{") and len(txt) > 300:
                    valid_scripts.append(txt)

            if not valid_scripts:
                raise RuntimeError(f"{get_symbol('error')} JSON script ไม่มีสมบูรณ์ใน {reel_url}")

            creation_ts = None
            fallback_ts = []

            for txt in valid_scripts:
                try:
                    data = json.loads(txt)
                except json.JSONDecodeError:
                    continue

                ts = find_creation_time(data)
                if ts:
                    creation_ts = ts
                    break

                ts2 = find_any_time(data)
                if ts2:
                    fallback_ts.append(ts2)

            ts_use = creation_ts or (max(fallback_ts) if fallback_ts else None)
            if not ts_use:
                raise RuntimeError("No timestamp found")

            if ts_use > 1e12:
                ts_use //= 1000
            dt_utc = datetime.fromtimestamp(ts_use, tz=timezone.utc)
            return dt_utc + timedelta(hours=7)

        except Exception:
            if attempt == max_tries - 1:
                raise  # หมดรอบแล้วโยน error ออกไป
        

def create_chrome_driver(print_to_gui=None, headless=True):
    try:
        if print_to_gui:
            print_to_gui(safe_utf8(f"{get_symbol('info')} Initializing Chrome driver..."))

        options = Options()
        if headless:
            options.add_argument("--headless=new")

        # Stealth & performance flags
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")  # << เพิ่มตรงนี้
        options.add_argument("--log-level=3")  # << เพิ่มตรงนี้
        options.add_argument("--disable-features=VoiceTranscriptionCapability,TranslateUI,AudioServiceOutOfProcess")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1024,600")  # ขนาดเดียวกับ IG
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # WebDriverManager (Primary)
        try:
            if print_to_gui:
                print_to_gui(safe_utf8(f"{get_symbol('info')} เปิด Chrome แบบ WebDriverManager..."))
            service = Service(ChromeDriverManager().install(), log_path=os.devnull)  # << เพิ่มตรงนี้
            driver = webdriver.Chrome(service=service, options=options)
            return driver

        except Exception as e:
            if print_to_gui:
                print_to_gui(safe_utf8(f"{get_symbol('error')} WebDriverManager เจ๊ง: {e}"))

            try:
                chrome_path = [
            r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        ]
                options.binary_location = chrome_path
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                if print_to_gui:
                    print_to_gui(safe_utf8(f"{get_symbol('ok')} สำรองเปิด Chrome ด้วย path ตายตัว"))
                return driver

            except Exception as e2:
                if print_to_gui:
                    print_to_gui(safe_utf8(f"{get_symbol('error')} เปิด Chrome ไม่ได้ทั้งสองทาง: {e2}"))
                return None

    except Exception as outer_e:
        if print_to_gui:
            print_to_gui(safe_utf8(f"{get_symbol('warn')}: create_chrome_driver ล้มเหลว: {outer_e}"))
        return None






# ฟังก์ชันนี้สมบูรณ์แบบครับลูกพี่ ไม่ต้องแก้ไขอะไรเลย เป็น Logic ล้วนๆ
def clean_url(url_raw):
    """
    ทำความสะอาด URL โดยการลบช่องว่าง, อักขระที่มองไม่เห็น, และ query parameters
    """
    if not isinstance(url_raw, str):
        return ""
    url = url_raw.strip()
    url = re.sub(r'[\u200e\u200f\u202a-\u202e\u2066-\u2069]', '', url)
    parts = url.split('?')
    return parts[0]

# <<< ปรับแก้เล็กน้อย
# ฟังก์ชันนี้ดีมากครับ แต่เพื่อให้มันยืดหยุ่นและไม่ผูกติดกับ UI ใดๆ
# เราจะเพิ่ม parameter `print_to_gui` เข้าไป
def extract_reel_id_from_url(reel_url, print_to_gui):
    """
    ดึง Reel ID จาก URL ที่ระบุ โดยใช้ regular expressions หลายรูปแบบ
    """
    if not reel_url:
        return None
    
    cleaned_url = clean_url(reel_url)
    
    patterns = [
        r"/reel/(\d+)",
        r"/(?:videos|watch/(?:\?v=)?|video\.php\?v=)(\d+)",
        r"permalink\.php\?.*v=(\d+)",
        r"pfbid0[^&]*&id=\d+&v=(\d+)",
        r"facebook\.com/[^/]+/videos/(\d+)/?"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned_url)
        if match:
            return match.group(1)
            
    # <<< จุดที่ปรับแก้
    # เราจะใช้ `print_to_gui` ที่รับเข้ามาแทนที่จะเรียกใช้แบบลอยๆ
    # เพื่อให้ฟังก์ชันนี้ไม่จำเป็นต้องรู้ว่า `print_to_gui` มาจากไหน
    print_to_gui(safe_utf8(f"#DEBUG_FB: Could not extract Reel/Video ID from URL: {reel_url} (Cleaned: {cleaned_url})"))
    return None


def get_application_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    try:
        return os.path.dirname(__file__)
    except NameError:
        return os.getcwd()

# กำหนดพาธต่างๆ ของโปรแกรม
application_path = get_application_path()
icon_path = os.path.abspath(os.path.join(application_path, "fb_icon.ico"))
cookie_file = os.path.join(application_path, "fb_cookies.json")

# --- START: Core Logic Functions (Facebook) ---

def save_cookies_fb(driver, path, print_to_gui, callback):
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(driver.get_cookies(), file)
        callback({"type": "save_cookie"})
    except Exception as e:
        print_to_gui(safe_utf8(f"Error saving Facebook cookies: {e}"))


def load_cookies_fb(driver, path, print_to_gui, callback, send_status_update=True):
    try:
        with open(path, "r", encoding="utf-8") as file:
            cookies = json.load(file)
        for cookie in cookies:
            if cookie.get('sameSite') == 'None':
                cookie['sameSite'] = 'Lax'
            try:
                driver.add_cookie(cookie)
            except Exception as e_cookie_add:
                print_to_gui(safe_utf8(f"Warning: Could not add FB cookie {cookie.get('name', 'N/A')}: {e_cookie_add}"))
        time.sleep(1)
        return True
    except FileNotFoundError:
        print_to_gui(safe_utf8(f"{get_symbol('ok')} Logged into Facebook via cookies."))
    except json.JSONDecodeError:
        print_to_gui(safe_utf8(f"{get_symbol('error')}Error decoding JSON from Facebook cookie file: {path}."))
    except Exception as e:
        print_to_gui(safe_utf8(f"{get_symbol('error')}Error loading Facebook cookies: {e}"))
    return False


def handle_generic_popups_fb(driver, print_to_gui, quick_check_timeout=1.0, skip_if_known_clean=False):
    print_to_gui(safe_utf8("# DEBUG_FB: Attempting to handle generic pop-ups..."))

    if skip_if_known_clean:
        print_to_gui(safe_utf8("# DEBUG_FB: Skipped popup check (already handled or not expected here)."))
        return False

    try:
        cookie_xpath = (
            '//button[@role="button" and contains(translate(.,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),' 
            '"allow all cookies")] | '
            '//a[@role="button" and contains(translate(.,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),' 
            '"allow all cookies")]'
        )
        WebDriverWait(driver, quick_check_timeout).until(
            EC.element_to_be_clickable((By.XPATH, cookie_xpath))
        ).click()
        print_to_gui(safe_utf8("Facebook Cookie consent button clicked."))
        time.sleep(1)
        return True
    except:
        pass
    for xpath in [
        '//div[@aria-label="ปิด" or @aria-label="Close"]',
        '//div[@role="button" and (contains(.,"ไม่ใช่ตอนนี้") or contains(.,"Not Now"))]'
    ]:
        try:
            elems = driver.find_elements(By.XPATH, xpath)
            for el in elems:
                if el.is_displayed() and el.is_enabled():
                    WebDriverWait(driver, quick_check_timeout).until(
                        EC.element_to_be_clickable(el)
                    ).click()
                    print_to_gui(safe_utf8(f"Facebook generic close button clicked via: {xpath[:30]}..."))
                    time.sleep(0.5)
                    return True
        except:
            continue
    print_to_gui(safe_utf8("# DEBUG_FB: No Facebook pop-ups found or handled."))
    return False


def fb_login(driver, callback, print_to_gui):
    callback({"type": "wait_login"})
    print_to_gui(safe_utf8("# DEBUG_FB: Starting Facebook login process..."))
    driver.get("https://www.facebook.com/")
    time.sleep(1)
    handle_generic_popups_fb(driver, print_to_gui, quick_check_timeout=0.6, skip_if_known_clean=False)

    # พยายามใช้ Cookies เพื่อ login อัตโนมัติ
    if os.path.exists(cookie_file) and load_cookies_fb(driver, cookie_file, print_to_gui, callback):
        driver.get("https://www.facebook.com/")
        time.sleep(3)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                    '//a[@aria-label="หน้าหลัก" or @aria-label="Home"]'))
            )
            print_to_gui(safe_utf8(f"{get_symbol('wait')} Logged into Facebook via cookies."))
            save_cookies_fb(driver, cookie_file, print_to_gui, callback)

            return True
        except Exception:
            print_to_gui(safe_utf8("Facebook cookies invalid. Proceeding manual login."))

    # Manual login flow
    driver.get("https://www.facebook.com/login/")
    time.sleep(1)
    handle_generic_popups_fb(driver, print_to_gui, quick_check_timeout=0.6)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
    except TimeoutException:
        callback({"type": "error", "title": safe_utf8("Error (Facebook)"), "message": safe_utf8("Facebook login page timeout.")})
        return False

    callback({
        "type": "info", "title": safe_utf8("Login Required (Facebook)"),
        "message": safe_utf8("กรุณาเข้าสู่ระบบ Facebook ในเบราว์เซอร์...")
    })

    start = time.time()
    while time.time() - start < 3000:
        url = driver.current_url.lower()
        if "facebook.com" in url and not any(x in url for x in ["login", "checkpoint"]):
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH,
                        '//a[@aria-label="หน้าหลัก" or @aria-label="Home"]'))
                )
                print_to_gui(safe_utf8("Facebook login confirmed."))
                save_cookies_fb(driver, cookie_file, print_to_gui, callback)

                return True
            except:
                pass
        time.sleep(3)

    callback({"type": "error", "title": safe_utf8("Error (Facebook)"), "message": safe_utf8("รอการล็อกอิน Facebook นานเกินไป")})
    return False





# (สมมติว่าฟังก์ชันอื่นๆ และตัวแปร XPATH_VIEW_COUNT อยู่ในไฟล์เดียวกัน)

def parse_view_count_fb(text_input):
    # <<< ฟังก์ชันนี้สมบูรณ์แบบ ไม่ต้องแก้ไข
    if not text_input or not isinstance(text_input, str): return 0
    text = text_input.strip().lower().replace(',', '')
    unit_multipliers = {'พันล้าน': 10**9, 'ล้าน': 10**6, 'แสน': 10**5, 'หมื่น': 10**4, 'พัน': 10**3, 'b': 10**9, 'm': 10**6, 'k': 10**3}
    multiplier = 1; num_str_to_parse = text
    for unit in sorted(unit_multipliers.keys(), key=len, reverse=True):
        if unit in text:
            match_num = re.search(r'(\d+(?:\.\d)?)' + re.escape(unit), text)
            if match_num: num_str_to_parse = match_num.group(1); multiplier = unit_multipliers[unit]; break
            elif text.startswith(tuple(str(i) for i in range(10))):
                parts = text.split(unit, 1); potential_num = parts[0].strip()
                if potential_num.replace('.', '', 1).isdigit(): num_str_to_parse = potential_num; multiplier = unit_multipliers[unit]; break
    num_str_to_parse = re.sub(r'(?:ครั้งที่ดู|การดู|วิว|views|\s)+', '', num_str_to_parse, flags=re.IGNORECASE).strip()
    match_final = re.search(r'^\s*(\d+(?:\.\d+)?)\s*$', num_str_to_parse)
    if match_final:
        try: return int(float(match_final.group(1)) * multiplier)
        except ValueError: return 0
    return 0

# <<< ปรับแก้: เพิ่ม `print_to_gui` เป็นพารามิเตอร์ และส่งต่อไปยังฟังก์ชันลูก
def count_views_fb(driver, url_reels_tab, max_target_clips, print_to_gui, callback):
    print_to_gui(safe_utf8(f"# DEBUG_FB: Navigating to Facebook Reels Tab: {url_reels_tab}"))
    driver.get(url_reels_tab); time.sleep(2); 
    # <<< ปรับแก้: ส่ง `print_to_gui` เข้าไป
    handle_generic_popups_fb(driver, print_to_gui, skip_if_known_clean=True)
    reels_data_list = []

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//a[@aria-label="พรีวิวไทล์ของคลิป Reels" and starts-with(@href, "/reel/")] | //a[contains(@aria-label, "Reel by") and starts-with(@href, "/reel/")]')))
        print_to_gui(safe_utf8("# DEBUG_FB: Step 1: Initial reel links found on the Reels Tab."))
    except TimeoutException:
        print_to_gui("# DEBUG_FB: Step 1 Failed (Reels Tab): Timeout - No initial reel links found.")
        return 0, 0, []
    except Exception as e_initial_reels_tab:
        print_to_gui(f"# DEBUG_FB: Step 1 Failed (Reels Tab): An unexpected error - {e_initial_reels_tab}.")
        return 0, 0, []

    scroll_pause_time = 3.0
    current_height = driver.execute_script("return document.body.scrollHeight")
    processed_reel_links = set(); scroll_attempts = 0; max_scrolls_total = 30 
    consecutive_scrolls_without_new = 0; max_consecutive_scrolls_without_new = 3
    print_to_gui(safe_utf8("--- Facebook Reels Tab Phase: Collecting Reels and Views ---"))

    while len(reels_data_list) < max_target_clips and scroll_attempts < max_scrolls_total:
        new_reels_found_this_pass = 0
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//a[starts-with(@href, "/reel/")] | //a[starts-with(@href, "/watch/?v=")]')))
            reel_link_elements = driver.find_elements(By.XPATH, '//a[@aria-label="พรีวิวไทล์ของคลิป Reels" and starts-with(@href, "/reel/")] | //a[contains(@aria-label, "Reel by") and starts-with(@href, "/reel/")] | //a[starts-with(@href, "/watch/?v=")]')
            print_to_gui(safe_utf8(f"# DEBUG_FB: Step 2 (Reels Tab): Found {len(reel_link_elements)} potential reel links."))
            for link_element in reel_link_elements:
                if len(reels_data_list) >= max_target_clips: break
                link_href = None
                try:
                    link_href = link_element.get_attribute("href")
                    if link_href: link_href = clean_url(link_href)
                    # <<< ปรับแก้: ส่ง `print_to_gui` เข้าไป
                    current_reel_id = extract_reel_id_from_url(link_href, print_to_gui)
                    if current_reel_id and link_href not in processed_reel_links:
                        view_xpath = XPATH_VIEW_COUNT

                        raw_text = "N/A"; views = 0
                        try:
                            view_els = WebDriverWait(link_element, 0.5).until(EC.presence_of_all_elements_located((By.XPATH, view_xpath)))
                            candidates = [v.text for v in view_els if v.text and 0 < len(v.text.strip()) < 25]
                            aria_candidates = [v.get_attribute("aria-label") for v in view_els if v.get_attribute("aria-label") and 0 < len(v.get_attribute("aria-label").strip()) < 50]
                            js_candidates = []
                            for ve in view_els:
                                try:
                                    js_text = driver.execute_script("""
                                        return arguments[0].innerText || 
                                               arguments[0].textContent || 
                                               arguments[0].getAttribute('aria-label');
                                    """, ve)
                                    if js_text and 0 < len(js_text.strip()) < 50:
                                        js_candidates.append(js_text.strip())
                                except Exception as e_js:
                                    print_to_gui(safe_utf8(f"# DEBUG_FB: JS fallback failed on view element: {e_js}"))
                            all_candidates = [c for c in candidates + aria_candidates + js_candidates if c]
                            if all_candidates:
                                best_v = 0; best_t = all_candidates[0]
                                for c_text in all_candidates:
                                    pv = parse_view_count_fb(c_text)
                                    if pv > best_v: best_v = pv; best_t = c_text
                                    elif best_v == 0 and parse_view_count_fb(best_t) == 0:
                                        if len(c_text) > len(best_t) or any(unit in c_text.lower() for unit in ['k','m','b','พัน','ล้าน']):
                                            best_t = c_text
                                views = best_v; raw_text = best_t
                        except (TimeoutException, NoSuchElementException):
                            raw_text = "N/A (Views Not Found)"; views = 0
                        except Exception as e_vx:
                            print_to_gui(safe_utf8(f"  # DEBUG_FB: Error extracting views for {link_href}: {e_vx}"))
                            raw_text = "N/A (View Error)"; views = 0
                        processed_reel_links.add(link_href)
                        reels_data_list.append({
                            'link': link_href,
                            'views': views,
                            'text': raw_text,
                            'id': current_reel_id,
                            'date_text': ''
                        })
                        #// ★ ส่ง progress พร้อม link และ views ให้ JS/UI ★
                        callback({
                            "type": "view_fetch_progress",
                            "data": {
                                "current": len(reels_data_list),
                                "total": max_target_clips,
                                "link": link_href,
                                "views": views
                            }
                        })
                        print_to_gui(safe_utf8(f"   Collected ... Total: {len(reels_data_list)}/{max_target_clips}"))




                        new_reels_found_this_pass += 1
                        print_to_gui(safe_utf8(f"  Collected (FB Reels Tab): {link_href} | V: {views:,} (Raw: '{raw_text}'). Total: {len(reels_data_list)}/{max_target_clips}"))
                except StaleElementReferenceException:
                    print_to_gui(safe_utf8("# DEBUG_FB: Stale element in Reels Tab, re-finding.")); break 
                except Exception as e_li:
                    print_to_gui(safe_utf8(f"# DEBUG_FB: Error processing link in Reels Tab ({link_href or 'Unknown'}): {e_li}"))
            if len(reels_data_list) >= max_target_clips: break
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"); time.sleep(scroll_pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == current_height:
                consecutive_scrolls_without_new += 1 if new_reels_found_this_pass == 0 else 0
                if consecutive_scrolls_without_new >= max_consecutive_scrolls_without_new: break
            else:
                consecutive_scrolls_without_new = 0
            current_height = new_height; scroll_attempts += 1
        except TimeoutException:
            consecutive_scrolls_without_new += 1
            if consecutive_scrolls_without_new >= max_consecutive_scrolls_without_new: break
        except Exception as e_loop_reels_tab:
            print_to_gui(safe_utf8(f"# DEBUG_FB: Error in Reels Tab scraping loop: {e_loop_reels_tab}"))
            break

    # JS FAST DOM DATE SCAN BOOST (Optimized v2)
    try:
        js_scan_result = driver.execute_script("""
            const results = [];
            const posts = document.querySelectorAll('article, div[role="article"]');
            for (const post of posts) {
                let id = '';
                const links = post.querySelectorAll('a[href*="/reel/"], a[href*="watch/?v="], a[href*="/videos/"], a[href*="video.php"]');
                for (const link of links) {
                    const href = link?.href || '';
                    const match = href.match(/\\/reel\\/(\\d+)/) || href.match(/[?&]v=(\\d+)/) || href.match(/\\/videos\\/(\\d+)/);
                    if (match && match[1]) {
                        id = match[1];
                        break;
                    }
                }
                if (!id) continue;

                const abbr = post.querySelector('abbr[title]');
                if (abbr && abbr.title) {
                    results.push({id, date: abbr.title});
                    continue;
                }
                const spans = post.querySelectorAll('span');
                for (const span of spans) {
                    const t = span.innerText?.trim();
                    if (t && t.match(/\\d{1,2}\\s+(ม\\.ค\\.|ก\\.พ\\.|มี\\.ค\\.|เม\\.ย\\.|พ\\.ค\\.|มิ\\.ย\\.|ก\\.ค\\.|ส\\.ค\\.|ก\\.ย\\.|ต\\.ค\\.|พ\\.ย\\.|ธ\\.ค\\.|[A-Za-z]{3,})/)) {
                        results.push({id, date: t});
                        break;
                    }
                }
            }
            return results;
        """)
        js_date_map = {item['id']: item['date'] for item in js_scan_result if item['id'] and item['date']}
        print_to_gui(safe_utf8(f"# DEBUG_FB: JS-Scan Dates collected: {len(js_date_map)} items."))
        for r in reels_data_list:
            reel_id = r.get('id')
            if reel_id in js_date_map:
                r['date_text'] = js_date_map[reel_id]
    except Exception as e_js_inject:
        print_to_gui(safe_utf8(f"# DEBUG_FB: JS-Scan block error: {e_js_inject}"))

    total_v = sum(r['views'] for r in reels_data_list)
    counted_c = len(reels_data_list)
    print_to_gui(safe_utf8(f"--- Finished FB Reels Tab collecting. Reels: {counted_c}, Views: {total_v:,} ---"))
    if counted_c < max_target_clips and max_target_clips > 0:
        print_to_gui(safe_utf8(f"Warning: FB Collected {counted_c} < target {max_target_clips}."))
    return total_v, counted_c, reels_data_list
   

# Global variables
standby_driver_for_dates = None
manual_date_pending        = False
manual_using_auto_driver   = False

def run_manual_date_fetch(profile_url, reel_url, reel_index, callback):
    global manual_date_pending, standby_driver_for_dates, manual_using_auto_driver
    manual_date_pending = False

    def print_to_gui(m):
        callback({"type":"log","message":str(m)})

    # --- START: ขั้นตอนที่ 1 ---
    # แสดงสถานะเริ่มต้นของโหมดพิเศษ
    initial_message = f"🕹️ [โหมดพิเศษ] กำลังตรวจสอบลิงก์ที่มีปัญหา..."
    print_to_gui(safe_utf8(f"# FB_MANUAL_FETCH: Fetching date for {reel_url} …"))
    callback({"type": "status", "message": safe_utf8(initial_message), "special": True})
    # --- END: ขั้นตอนที่ 1 ---

    # reuse หรือสร้าง driver
    if standby_driver_for_dates:
        driver = standby_driver_for_dates
        manual_using_auto_driver = True
        # --- START: ขั้นตอนที่ 2 ---
        # แสดงสถานะว่ากำลังใช้ Standby Driver
        reuse_message = f"🕹️ [โหมดพิเศษ] กำลังใช้ Standby Driver..."
        print_to_gui(safe_utf8(f"{get_symbol('ok')} Reusing standby driver"))
        callback({"type": "status", "message": safe_utf8(reuse_message), "special": True})
        # --- END: ขั้นตอนที่ 2 ---
    else:
        driver = create_chrome_driver(print_to_gui=print_to_gui, headless=True)
        standby_driver_for_dates = driver
        manual_using_auto_driver = False
        print_to_gui(safe_utf8(f"{get_symbol('debug')} Created new headless driver"))

    try:
        # Plan A: พยายามดึงข้อมูลด้วย JSON
        dt = get_reel_date_via_json_driver(driver, reel_url)
        formatted = f"{dt.day} {TH_MONTHS[dt.month-1]} {dt.year + 543}"
        
        # --- START: ขั้นตอนที่ 3 (สำเร็จ) ---
        # แสดงสถานะว่าดึงข้อมูลสำเร็จ
        success_message = f"🕹️ [โหมดพิเศษ] ✅ ดึงข้อมูลสำเร็จ: {formatted}"
        print_to_gui(safe_utf8(f"{get_symbol('ok')} JSON fetch success: {formatted}"))
        callback({"type": "status", "message": safe_utf8(success_message), "special": True})
        time.sleep(1.5) # หน่วงเวลาเล็กน้อยให้ User เห็นข้อความก่อน
        # --- END: ขั้นตอนที่ 3 ---
        
        callback({"type":"update_date_final","data":{"link":reel_url,"date":formatted}})

    except Exception as e:
        # --- START: ขั้นตอนที่ 3 (ล้มเหลว) ---
        # แสดงสถานะว่าดึงข้อมูลล้มเหลว
        fail_message = f"🕹️ [โหมดพิเศษ] ❌ ดึงข้อมูลล้มเหลว"
        print_to_gui(safe_utf8(f"{get_symbol('error')} JSON fetch for {reel_url} failed: {e}"))
        callback({"type": "status", "message": safe_utf8(fail_message), "special": True})
        time.sleep(1.5) # หน่วงเวลาเล็กน้อยให้ User เห็นข้อความก่อน
        # --- END: ขั้นตอนที่ 3 ---
        
        callback({
            "type": "update_date_final", 
            "data": {
                "link": reel_url, 
                "date": "N/A (JSON Fail)"
            }
        })

    finally:
        manual_date_pending = False
        if not manual_using_auto_driver:
            try:
                driver.quit()
                standby_driver_for_dates = None
                callback({"type": "driver_status", "mode": "none"})
                print_to_gui(safe_utf8(f"{get_symbol('ok')} Manual driver closed."))
            except Exception as e:
                print_to_gui(safe_utf8(f"{get_symbol('warn')} Manual driver close failed: {e}"))
        else:
            print_to_gui(safe_utf8(f"{get_symbol('ok')} Skipped driver close (reused)."))

        # **อย่า** reset manual_using_auto_driver ตรงนี้ ให้ค้างไว้รอบต่อไป



# ✅ เพิ่ม Worker ที่จะใช้ใน Driver Pool
def get_date_with_dedicated_browser_reels(video_url, reel_id, print_to_gui):
    """
    Worker สำหรับ Reels: เปิดเบราว์เซอร์ใหม่, หา JSON, แล้ว return ผลลัพธ์
    """
    driver = None
    try:
        driver = create_chrome_driver(headless=True)
        if not driver:
            raise Exception("สร้างเบราว์เซอร์สำหรับดึงข้อมูลวันที่ไม่สำเร็จ")

        driver.get(video_url)

        creation_timestamp = None
        max_retries = 10
        
        for attempt in range(max_retries):
            time.sleep(0.7)
            scripts = driver.find_elements(By.CSS_SELECTOR, "script[type='application/json']")
            
            for script in scripts:
                try:
                    json_text = script.get_attribute("innerText")
                    if "creation_time" in json_text:
                        data = json.loads(json_text)
                        ts = find_creation_time(data) # ใช้ find_creation_time ที่มีอยู่แล้ว
                        if ts:
                            creation_timestamp = ts
                            print_to_gui(safe_utf8(f"  [Reels Worker ID: {reel_id}] เจอ creation_time ในรอบที่ {attempt + 1}"))
                            break
                except Exception:
                    continue
            
            if creation_timestamp:
                break

        if not creation_timestamp:
            return reel_id, video_url, "N/A"

        if creation_timestamp > 1e12:
            creation_timestamp //= 1000
        
        dt_utc = datetime.fromtimestamp(creation_timestamp, timezone.utc)
        dt_bkk = dt_utc + timedelta(hours=7)
        
        formatted_date = f"{dt_bkk.day} {TH_MONTHS[dt_bkk.month - 1]} {dt_bkk.year + 543}"
        
        print_to_gui(safe_utf8(f"  [Reels Worker ID: {reel_id}] ดึงข้อมูลสำเร็จ: {formatted_date}"))
        return reel_id, video_url, formatted_date

    except Exception as e:
        print_to_gui(safe_utf8(f"  [Reels Worker ID: {reel_id}] ดึงข้อมูลล้มเหลว: {e}"))
        return reel_id, video_url, "N/A"
    finally:
        if driver:
            driver.quit()


# <<< ของใหม่: เปลี่ยนชื่อเป็น run_fb_scan และรับ parameter เฉพาะที่จำเป็น + callback

# fb_engine.py (แทนที่ฟังก์ชัน run_fb_scan เดิมทั้งหมด)

def run_fb_scan(url_reels_tab_from_entry, url_profile_main_from_entry, max_clips_str, callback):
    
    # --- ส่วน Setup เริ่มต้น ---
    def print_to_gui(message):
        callback({"type": "log", "message": str(message)})

    # --- ส่วนที่ 1: จัดการ Standby Driver เก่า ---
    global standby_driver_for_dates
    if standby_driver_for_dates:
        try:
            print_to_gui(safe_utf8(f"{get_symbol('debug')} Closing previous standby driver..."))
            standby_driver_for_dates.quit()
            # ✅ 1. คืนสีแดง: เมื่อเริ่มสแกนใหม่และมีการปิด Driver เก่า
            callback({"type": "driver_status", "mode": "none"})
        except Exception as e:
            print_to_gui(safe_utf8(f"{get_symbol('warn')} Failed to close leftover standby driver: {e}"))
    standby_driver_for_dates = None
    
    driver = None
    collected_reels_list = []

    # --- ✅ START: แก้ไขโดยย้ายโค้ดทั้งหมดมาไว้ใน try...except บล็อกเดียว ---
    try:
        # --- เตรียมค่าและสร้างลิงก์โปรไฟล์อัตโนมัติให้เสร็จก่อน ---
        try:
            max_clips = int(max_clips_str)
            if max_clips <= 0:
                raise ValueError("จำนวนคลิปต้องมากกว่า 0")
        except (ValueError, TypeError):
            raise ValueError(f"จำนวนคลิปไม่ถูกต้อง: '{max_clips_str}'")

        if not url_profile_main_from_entry or "facebook.com" not in url_profile_main_from_entry:
            print_to_gui(safe_utf8("ลิงก์โปรไฟล์ไม่ได้ถูกระบุ, กำลังสร้างลิงก์อัตโนมัติ..."))
            if "/reels" in url_reels_tab_from_entry:
                url_profile_main_from_entry = url_reels_tab_from_entry.split('/reels')[0]
                print_to_gui(safe_utf8(f"✅ ลิงก์โปรไฟล์ที่สร้างขึ้น: {url_profile_main_from_entry}"))
            else:
                url_profile_main_from_entry = url_reels_tab_from_entry
        
        # --- นิยามฟังก์ชัน setup_date_driver (ทำงานเบื้องหลัง) ---
        def setup_date_driver():
            global standby_driver_for_dates
            print_to_gui(safe_utf8("⚙️ Creating new standby driver for Reels mode..."))
            standby_driver_for_dates = create_chrome_driver(headless=True)
            if standby_driver_for_dates:
                fb_login(standby_driver_for_dates, lambda _: None, print_to_gui)
                standby_driver_for_dates.get(url_profile_main_from_entry) 
                print_to_gui(safe_utf8(f"{get_symbol('ok')} Standby browser for Reels mode is ready."))
                # (เอา callback ออกจากตรงนี้เพื่อแก้ปัญหา Race Condition)

        # --- สั่งให้ Thread เบื้องหลังเริ่มทำงาน ---
        threading.Thread(target=setup_date_driver, daemon=True).start()

        # --- เริ่มกระบวนการสแกนหลักด้วย Driver ที่มองเห็น ---
        print_to_gui(safe_utf8("กำลังเริ่มต้น WebDriver หลัก..."))
        driver = create_chrome_driver(print_to_gui=print_to_gui, headless=False)
        if not driver:
             raise Exception("ไม่สามารถสร้าง Chrome Driver หลักได้")
             
        if not fb_login(driver, callback, print_to_gui): 
            return
        
        check_and_prepare_facebook_language(driver, url="https://www.facebook.com/", js_callback=callback)
        
        # ✅ 2. คืนสีส้ม: เมื่อพร้อมเริ่มสแกนจริง
        callback({"type": "driver_status", "mode": "auto"})
        
        callback({"type": "status", "message": safe_utf8(f"{get_symbol('scan')} [FB] กำลังค้นหา Reels และยอดวิว...")})
        total_views, counted_clips, collected_reels_list = count_views_fb(
            driver, url_reels_tab_from_entry, max_clips, print_to_gui, callback
        )

        if not collected_reels_list:
            callback({"type": "status", "message": safe_utf8(f"{get_symbol('warn')} [FB] ไม่พบข้อมูล Reels เลย"), "final": True})
        else:
            if driver:
                driver.quit()
                driver = None
                print_to_gui(safe_utf8("✓ ปิด Driver หลักที่ใช้สแกนวิวแล้ว"))

            # ... (ส่วนดึงวันที่ที่เหลือเหมือนเดิม) ...
            if url_profile_main_from_entry:
                list_len = len(collected_reels_list)
                slice_count = 6
                first_indices = list(range(min(slice_count, list_len)))
                last_indices = list(range(max(0, list_len - slice_count), list_len))
                reels_to_process_indices = sorted(set(first_indices + last_indices))

                callback({"type": "auto_date_fetch_start", "data": { "indices": reels_to_process_indices, "platform": "fb" }})

                urls_to_fetch = [collected_reels_list[i]['link'] for i in reels_to_process_indices]
                ids_to_fetch = [collected_reels_list[i]['id'] for i in reels_to_process_indices]
                
                print_to_gui(safe_utf8(f"▶ เริ่มดึงวันที่ Reels (รอบแรก): รวม {len(reels_to_process_indices)} รายการ"))
                failed_tasks = []

                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                    future_to_data = {
                        executor.submit(get_date_with_dedicated_browser_reels, url, reel_id, print_to_gui): (url, reel_id, original_index)
                        for original_index, (url, reel_id) in zip(reels_to_process_indices, zip(urls_to_fetch, ids_to_fetch))
                    }

                    for future in concurrent.futures.as_completed(future_to_data):
                        url, reel_id, original_index = future_to_data[future]
                        try:
                            _id, _url, date = future.result()
                            if date == "N/A":
                                failed_tasks.append({'link': _url, 'id': _id, 'index': original_index})
                            else:
                                for item in collected_reels_list:
                                    if item['id'] == _id:
                                        item['date_text'] = date
                                        break
                                callback({"type": "update_date_status", "data": {"link": _url, "date": date}})
                        except Exception as e:
                            failed_tasks.append({'link': url, 'id': reel_id, 'index': original_index})
                
                print_to_gui(safe_utf8("✓ ทีมพิเศษ (Reels) ทำงานรอบแรกเสร็จสิ้น, ตรวจสอบงานพลาด..."))

                if failed_tasks:
                    print_to_gui(safe_utf8(f"▶ เริ่มเก็บตกงาน Reels ที่พลาด {len(failed_tasks)} รายการ โดยผู้เชี่ยวชาญ..."))
                    for task in sorted(failed_tasks, key=lambda x: x['index']):
                        run_manual_date_fetch(
                            profile_url=url_profile_main_from_entry,
                            reel_url=task['link'],
                            reel_index=task['index'],
                            callback=callback
                        )
                        time.sleep(1)

        total_views = sum(r['views'] for r in collected_reels_list)
        counted_clips = len(collected_reels_list)
        final_message = safe_utf8(f"✅ [FB] สแกนเสร็จสมบูรณ์: {counted_clips} คลิป | รวม {total_views:,} วิว")
        print_to_gui(final_message)
        callback({"type": "update_date_final", "data": {}})
        callback({"type": "status", "message": final_message, "final": True})

        # ✅ 3. คืนสีเขียว: เมื่องานทั้งหมดเสร็จสิ้น และ Standby Driver ควรจะพร้อมแล้ว
        try:
            if standby_driver_for_dates and standby_driver_for_dates.session_id:
                callback({"type": "driver_status", "mode": "manual-ready"})
            else:
                callback({"type": "driver_status", "mode": "none"})
        except Exception:
            callback({"type": "driver_status", "mode": "none"})

    except Exception as e:
        error_message = f"[FB] เกิดข้อผิดพลาดร้ายแรง: {e}"
        print_to_gui(safe_utf8(error_message))
        callback({"type": "error", "title": safe_utf8("Error (FB)"), "message": str(e)})
        callback({"type": "status", "message": safe_utf8(error_message), "final": True})
        
    finally:
        if driver:
            try:
                driver.quit()
            except Exception: 
                pass