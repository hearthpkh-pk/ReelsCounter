# fb_core_engine.py - Part 1: Base Utils, Cookies, View Count, Date Parser

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
    """
    ใช้ driver ที่เตรียม cookies+login+popup handling แล้ว
    เปิดเพจ reel_url, สแกน <script type="application/json"> 
    แล้วคืนค่า datetime (UTC+7) กลับไป (ยังไม่ปิด driver)
    """
    # เปิดหน้า Reel
    driver.get(reel_url)
    driver.implicitly_wait(5)
    
    # หา JSON scripts ทั้งหมด
    scripts = driver.find_elements(By.CSS_SELECTOR, "script[type='application/json']")
    
    creation_ts = None
    fallback_ts = []
    
    for idx, s in enumerate(scripts):
        txt = s.get_attribute("innerText") or ""
        if not txt.strip().startswith("{") or len(txt) < 200:
            continue
        try:
            data = json.loads(txt)
        except json.JSONDecodeError:
            continue
        
        # 1) หา creation_time ก่อน
        ts = find_creation_time(data)
        if ts:
            creation_ts = ts
            break
        
        # 2) ถ้าไม่เจอ ก็เก็บ any_time ไว้ fallback
        ts2 = find_any_time(data)
        if ts2:
            fallback_ts.append(ts2)
    
    # เลือก timestamp
    if creation_ts:
        ts_use = creation_ts
    elif fallback_ts:
        ts_use = max(fallback_ts)
    else:
        raise RuntimeError("❌ ไม่พบ timestamp ใดๆ ใน JSON scripts")
    
    # แปลง ms→s ถ้าจำเป็น
    if ts_use > 1e12:
        ts_use //= 1000
    
    # สร้าง datetime (UTC) แล้วบวก 7 ชั่วโมง
    dt_utc   = datetime.fromtimestamp(ts_use, tz=timezone.utc)
    dt_local = dt_utc + timedelta(hours=7)
    return dt_local
        

def create_chrome_driver(print_to_gui=None, headless=True):
    try:
        if print_to_gui:
            print_to_gui("🌀 Initializing Chrome driver...")

        options = Options()
        if headless:
            options.add_argument("--headless=new")

        # Stealth & performance flags
        options.add_argument("--disable-gpu")
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
                print_to_gui("🔵 เปิด Chrome แบบ WebDriverManager...",)
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver

        except Exception as e:
            if print_to_gui:
                print_to_gui(f"❌ WebDriverManager เจ๊ง: {e}",)

            try:
                chrome_path = [
            r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        ]
                options.binary_location = chrome_path
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                if print_to_gui:
                    print_to_gui("✅ สำรองเปิด Chrome ด้วย path ตายตัว",)
                return driver

            except Exception as e2:
                if print_to_gui:
                    print_to_gui(f"❌ เปิด Chrome ไม่ได้ทั้งสองทาง: {e2}")
                return None

    except Exception as outer_e:
        if print_to_gui:
            print_to_gui(f"🔥 ERROR: create_chrome_driver ล้มเหลว: {outer_e}",)
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
    print_to_gui(f"#DEBUG_FB: Could not extract Reel/Video ID from URL: {reel_url} (Cleaned: {cleaned_url})")
    return None


# ---- START: Paths Configuration (FB Version) ----
# <<< ปรับแก้: ส่วนนี้สมบูรณ์ดีอยู่แล้วครับลูกพี่ เก็บไว้เหมือนเดิมได้เลย



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
        print_to_gui(f"Error saving Facebook cookies: {e}")


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
                print_to_gui(f"Warning: Could not add FB cookie {cookie.get('name', 'N/A')}: {e_cookie_add}")
        time.sleep(1)
        return True
    except FileNotFoundError:
        print_to_gui("Facebook cookie file not found.")
    except json.JSONDecodeError:
        print_to_gui(f"Error decoding JSON from Facebook cookie file: {path}.")
    except Exception as e:
        print_to_gui(f"Error loading Facebook cookies: {e}")
    return False


def handle_generic_popups_fb(driver, print_to_gui, quick_check_timeout=1.0, skip_if_known_clean=False):
    print_to_gui("# DEBUG_FB: Attempting to handle generic pop-ups...")

    if skip_if_known_clean:
        print_to_gui("# DEBUG_FB: Skipped popup check (already handled or not expected here).")
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
        print_to_gui("Facebook Cookie consent button clicked.")
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
                    print_to_gui(f"Facebook generic close button clicked via: {xpath[:30]}...")
                    time.sleep(0.5)
                    return True
        except:
            continue
    print_to_gui("# DEBUG_FB: No Facebook pop-ups found or handled.")
    return False


def fb_login(driver, callback, print_to_gui):
    callback({"type": "wait_login"})
    print_to_gui("# DEBUG_FB: Starting Facebook login process...")
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
            print_to_gui("Logged into Facebook via cookies.")
            save_cookies_fb(driver, cookie_file, print_to_gui, callback)
            return True
        except Exception:
            print_to_gui("Facebook cookies invalid. Proceeding manual login.")

    # Manual login flow
    driver.get("https://www.facebook.com/login/")
    time.sleep(1)
    handle_generic_popups_fb(driver, print_to_gui, quick_check_timeout=0.6)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
    except TimeoutException:
        callback({"type": "error", "title": "Error (Facebook)", "message": "Facebook login page timeout."})
        return False
    callback({
        "type": "info", "title": "Login Required (Facebook)",
        "message": "กรุณาเข้าสู่ระบบ Facebook ในเบราว์เซอร์..."
    })

    start = time.time()
    while time.time() - start < 300:
        url = driver.current_url.lower()
        if "facebook.com" in url and not any(x in url for x in ["login","checkpoint"]):
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH,
                        '//a[@aria-label="หน้าหลัก" or @aria-label="Home"]'))
                )
                print_to_gui("Facebook login confirmed.")
                save_cookies_fb(driver, cookie_file, print_to_gui, callback)
                return True
            except:
                pass
        time.sleep(3)
    callback({"type": "error", "title": "Error (Facebook)", "message": "รอการล็อกอิน Facebook นานเกินไป"})
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
    print_to_gui(f"# DEBUG_FB: Navigating to Facebook Reels Tab: {url_reels_tab}")
    driver.get(url_reels_tab); time.sleep(2); 
    # <<< ปรับแก้: ส่ง `print_to_gui` เข้าไป
    handle_generic_popups_fb(driver, print_to_gui, skip_if_known_clean=True)
    reels_data_list = []

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//a[@aria-label="พรีวิวไทล์ของคลิป Reels" and starts-with(@href, "/reel/")] | //a[contains(@aria-label, "Reel by") and starts-with(@href, "/reel/")]')))
        print_to_gui("# DEBUG_FB: Step 1: Initial reel links found on the Reels Tab.")
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
    print_to_gui("--- Facebook Reels Tab Phase: Collecting Reels and Views ---")

    while len(reels_data_list) < max_target_clips and scroll_attempts < max_scrolls_total:
        new_reels_found_this_pass = 0
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//a[starts-with(@href, "/reel/")] | //a[starts-with(@href, "/watch/?v=")]')))
            reel_link_elements = driver.find_elements(By.XPATH, '//a[@aria-label="พรีวิวไทล์ของคลิป Reels" and starts-with(@href, "/reel/")] | //a[contains(@aria-label, "Reel by") and starts-with(@href, "/reel/")] | //a[starts-with(@href, "/watch/?v=")]')
            print_to_gui(f"# DEBUG_FB: Step 2 (Reels Tab): Found {len(reel_link_elements)} potential reel links.")
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
                                    print_to_gui(f"# DEBUG_FB: JS fallback failed on view element: {e_js}")
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
                            print_to_gui(f"  # DEBUG_FB: Error extracting views for {link_href}: {e_vx}")
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
                        print_to_gui(f"   Collected ... Total: {len(reels_data_list)}/{max_target_clips}")




                        new_reels_found_this_pass += 1
                        print_to_gui(f"  Collected (FB Reels Tab): {link_href} | V: {views:,} (Raw: '{raw_text}'). Total: {len(reels_data_list)}/{max_target_clips}")
                except StaleElementReferenceException:
                    print_to_gui("# DEBUG_FB: Stale element in Reels Tab, re-finding."); break 
                except Exception as e_li:
                    print_to_gui(f"# DEBUG_FB: Error processing link in Reels Tab ({link_href or 'Unknown'}): {e_li}")
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
            print_to_gui(f"# DEBUG_FB: Error in Reels Tab scraping loop: {e_loop_reels_tab}")
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
        print_to_gui(f"# DEBUG_FB: JS-Scan Dates collected: {len(js_date_map)} items.")
        for r in reels_data_list:
            reel_id = r.get('id')
            if reel_id in js_date_map:
                r['date_text'] = js_date_map[reel_id]
    except Exception as e_js_inject:
        print_to_gui(f"# DEBUG_FB: JS-Scan block error: {e_js_inject}")

    total_v = sum(r['views'] for r in reels_data_list)
    counted_c = len(reels_data_list)
    print_to_gui(f"--- Finished FB Reels Tab collecting. Reels: {counted_c}, Views: {total_v:,} ---")
    if counted_c < max_target_clips and max_target_clips > 0:
        print_to_gui(f"Warning: FB Collected {counted_c} < target {max_target_clips}.")
    return total_v, counted_c, reels_data_list

def parse_thai_date_text(date_text_input, print_to_gui):
    """
    แปลงข้อความวันที่/เวลาในรูปแบบต่างๆ (ไทย, อังกฤษ, สัมพัทธ์, ISO)
    ให้เป็นรูปแบบ "วัน เดือน(ย่อ) ปี(พ.ศ.)" ที่มาตรฐาน
    """
    if not date_text_input or not isinstance(date_text_input, str):
        print_to_gui(f"DEBUG_DATE_PARSE_INPUT_ERROR: Input was None or not a string: '{date_text_input}'")
        return "N/A"
    
    date_text = date_text_input.strip()
    now = dt.now()
    date_obj = None
    result_to_return = "N/A" 

    print_to_gui(f"DEBUG_DATE_PARSE_START: Parsing input '{date_text}'")

    try:
        if 'T' in date_text and ('Z' in date_text or ('+' in date_text.split('T')[1] if 'T' in date_text and len(date_text.split('T')) > 1 else False)):
            try:
                date_obj = dt.fromisoformat(date_text.replace("Z", "+00:00"))
                print_to_gui(f"DEBUG_DATE_PARSE_ISO: Parsed as ISO datetime: {date_obj}")
            except ValueError:
                print_to_gui(f"DEBUG_DATE_PARSE_ISO_ERROR: Failed to parse as ISO: '{date_text}'")
    except Exception as e_iso_check:
        print_to_gui(f"DEBUG_DATE_PARSE_ISO_PRECHECK_ERROR: Error during ISO check for '{date_text}': {e_iso_check}")

    if not date_obj:
        relative_patterns = {
            r"(\d+)\s*(?:วินาที|วิ)(?:ที่แล้ว)?": lambda m: (now - timedelta(seconds=int(m.group(1)))),
            r"(\d+)\s*(?:นาที|น\.?)(?:ที่แล้ว)?": lambda m: (now - timedelta(minutes=int(m.group(1)))),
            r"(\d+)\s*(?:ชั่วโมง|ชม\.?)(?:ที่แล้ว)?": lambda m: (now - timedelta(hours=int(m.group(1)))),
            r"(\d+)\s*(?:วัน(?:ที่ผ่านมา|ที่แล้ว)?|days\sago)": lambda m: (now - timedelta(days=int(m.group(1)))),
            r"(\d+)\s*(?:สัปดาห์(?:ที่ผ่านมา|ที่แล้ว)?|อาทิตย์(?:ที่ผ่านมา|ที่แล้ว)?)": lambda m: (now - timedelta(weeks=int(m.group(1)))),
            r"เมื่อวานนี้?(?:เวลา\s+\d{1,2}:\d{2})?|yesterday": lambda m: (now - timedelta(days=1)),
            r"วันนี้|ขณะนี้|just\s?now|now|เพิ่งเสร็จ": lambda m: now,
        }
        for pattern, handler in relative_patterns.items():
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                try:
                    date_obj = handler(match)
                    print_to_gui(f"DEBUG_DATE_PARSE_RELATIVE: Matched relative pattern '{pattern}' -> {date_obj}")
                    break 
                except Exception as e_rel_handler:
                    print_to_gui(f"DEBUG_DATE_PARSE_RELATIVE_ERROR: Handler error for pattern '{pattern}': {e_rel_handler}")
    
    if not date_obj:
        month_map_th_to_en_std_short = {'ม.ค.':'Jan','ก.พ.':'Feb','มี.ค.':'Mar','เม.ย.':'Apr','พ.ค.':'May','มิ.ย.':'Jun','ก.ค.':'Jul','ส.ค.':'Aug','ก.ย.':'Sep','ต.ค.':'Oct','พ.ย.':'Nov','ธ.ค.':'Dec'}
        month_map_th_to_en_std_long = {'มกราคม':'Jan','กุมภาพันธ์':'Feb','มีนาคม':'Mar','เมษายน':'Apr','พฤษภาคม':'May','มิถุนายน':'Jun','กรกฎาคม':'Jul','สิงหาคม':'Aug','กันยายน':'Sep','ตุลาคม':'Oct','พฤศจิกายน':'Nov','ธันวาคม':'Dec'}
        month_map_en_to_std_full = {'january':'Jan', 'february':'Feb', 'march':'Mar', 'april':'Apr', 'may':'May', 'june':'Jun', 'july':'Jul', 'august':'Aug', 'september':'Sep', 'october':'Oct', 'november':'Nov', 'december':'Dec'}
        month_map_en_to_std_short = {name[:3]:std for name, std in month_map_en_to_std_full.items()}
        all_month_maps_for_regex = {**month_map_th_to_en_std_short, **month_map_th_to_en_std_long, **month_map_en_to_std_full, **month_map_en_to_std_short}
        date_text_cleaned = re.sub(r"\s+(?:at|เวลา)\s+\d{1,2}:\d{2}(?:\s*(?:AM|PM|น\.))?","", date_text, flags=re.IGNORECASE).strip()
        if date_text_cleaned != date_text: print_to_gui(f"DEBUG_DATE_PARSE_CLEANED: Cleaned time: '{date_text_cleaned}' from '{date_text}'")

        month_regex_parts = sorted([re.escape(m) for m in all_month_maps_for_regex.keys()], key=len, reverse=True)
        month_pattern_str = "|".join(month_regex_parts)
        abs_date_pattern_1 = r"(\d{1,2})\s+(" + month_pattern_str + r")(?:\s*,?\s*(\d{4}|\d{2}))?" 
        abs_date_pattern_2 = r"(" + month_pattern_str + r")\s+(\d{1,2})(?:,?\s*(\d{4}|\d{2}))?"   
        m_abs = None; day_str, month_text_matched, year_str = None, None, None
        m1 = re.search(abs_date_pattern_1, date_text_cleaned, re.IGNORECASE)
        if m1: m_abs = m1; day_str, month_text_matched, year_str = m_abs.groups(); print_to_gui(f"DEBUG_DATE_PARSE_ABS_P1: Matched '{date_text_cleaned}'")
        else:
            m2 = re.search(abs_date_pattern_2, date_text_cleaned, re.IGNORECASE)
            if m2: m_abs = m2; month_text_matched, day_str, year_str = m_abs.groups(); print_to_gui(f"DEBUG_DATE_PARSE_ABS_P2: Matched '{date_text_cleaned}'")

        if day_str and month_text_matched:
            year_val = int(year_str) if year_str and year_str.isdigit() else now.year
            if year_str and len(year_str) == 2 and year_str.isdigit(): year_val = 2000 + int(year_str)
            std_month_for_strptime = month_text_matched.lower().replace('.', '')
            normalized_month_found = False
            for k_orig, v_std in all_month_maps_for_regex.items(): 
                if k_orig.lower().replace('.', '') == std_month_for_strptime: std_month_for_strptime = v_std; normalized_month_found = True; break
            if not normalized_month_found: std_month_for_strptime = std_month_for_strptime[:3].capitalize()
            try:
                date_obj = dt.strptime(f"{day_str} {std_month_for_strptime} {year_val}", "%d %b %Y")
                print_to_gui(f"DEBUG_DATE_PARSE_ABS_SUCCESS: Parsed absolute date: {date_obj}")
            except ValueError as e_abs_strptime: print_to_gui(f"DEBUG_DATE_PARSE_ABS_STRPTIME_ERROR: Failed for '{day_str} {std_month_for_strptime} {year_val}': {e_abs_strptime}"); date_obj = None
    
    if not date_obj:
        m_slash_dash = re.search(r"(\d{1,2})[/\.-](\d{1,2})(?:[/\.-](\d{2,4}))?", date_text)
        if m_slash_dash:
            d_sd, mo_sd, y_str_sd = m_slash_dash.groups()
            y_sd = int(y_str_sd) if y_str_sd and y_str_sd.isdigit() else now.year
            if y_str_sd and len(y_str_sd) == 2 and y_str_sd.isdigit(): y_sd = 2000 + int(y_sd)
            try:
                date_obj = dt(year=y_sd, month=int(mo_sd), day=int(d_sd))
                print_to_gui(f"DEBUG_DATE_PARSE_SLASH_DASH: Matched d/m/y pattern: {date_obj}")
            except ValueError as e_sd_val: print_to_gui(f"DEBUG_DATE_PARSE_SLASH_DASH_ERROR: Failed for '{d_sd}/{mo_sd}/{y_sd}': {e_sd_val}")
    
    if date_obj:
        year_be = date_obj.year + 543; display_month_th = "???"; eng_short_month_from_obj = date_obj.strftime("%b")
        month_map_th_to_en_std_short = {'ม.ค.':'Jan','ก.พ.':'Feb','มี.ค.':'Mar','เม.ย.':'Apr','พ.ค.':'May','มิ.ย.':'Jun','ก.ค.':'Jul','ส.ค.':'Aug','ก.ย.':'Sep','ต.ค.':'Oct','พ.ย.':'Nov','ธ.ค.':'Dec'}
        original_had_thai_month = any(th_m_key.lower() in date_text.lower() for th_m_key in month_map_th_to_en_std_short.keys())
        if original_had_thai_month:
            for th_name_short, en_name_short_map in month_map_th_to_en_std_short.items():
                if en_name_short_map.lower() == eng_short_month_from_obj.lower(): display_month_th = th_name_short; break
        if display_month_th == "???": display_month_th = eng_short_month_from_obj 
        result_to_return = f"{date_obj.day} {display_month_th} {year_be}"
        print_to_gui(f"DEBUG_DATE_PARSE_FORMATTED_SUCCESS: Input '{date_text_input}', Formatted Output: '{result_to_return}'")
        return result_to_return
    else:
        result_to_return = date_text_input 
        print_to_gui(f"DEBUG_DATE_PARSE_FALLBACK_FINAL: Input '{date_text_input}', Output (fallback): '{result_to_return}'")
        return result_to_return
    
# <<< เพิ่มฟังก์ชันใหม่นี้เข้าไปใน fb_engine.py >>>


# --- helper for manual jump (ใช้แค่ Auto-mode ถ้าอยาก) ---
def get_jump_height_from_clip_count(total_clips):
    jump_map = [
        (30,15000),(40,22000),(50,28000),(60,34000),
        (70,38000),(80,42000),(90,46000),(100,53000),
        (110,60000),(120,65000),(140,76000)
    ]
    for limit, height in jump_map:
        if total_clips >= limit:
            jump_height = height
    # helper ควร pure → คืนค่า jump_height ตรงๆ
    return jump_height if 'jump_height' in locals() else 0

# Global variables
standby_driver_for_dates = None
manual_date_pending        = False
manual_using_auto_driver   = False

def run_manual_date_fetch(profile_url, reel_url, reel_index, callback):
    global manual_date_pending, standby_driver_for_dates, manual_using_auto_driver
    manual_date_pending = False

    def print_to_gui(m):
        callback({"type":"log","message":str(m)})

    print_to_gui(f"# FB_MANUAL_FETCH: Fetching date for {reel_url} …")

    # reuse หรือสร้าง driver
    if standby_driver_for_dates:
        driver = standby_driver_for_dates
        manual_using_auto_driver = True
        print_to_gui("# 🧠 Reusing standby driver")
    else:
        driver = create_chrome_driver(print_to_gui=print_to_gui, headless=True)
        standby_driver_for_dates = driver
        manual_using_auto_driver = False
        print_to_gui("# 🧱 Created new headless driver")

    try:
        # —— ยิง JSON-path ก่อนเลย ——
        dt = get_reel_date_via_json_driver(driver, reel_url)
        formatted = f"{dt.day} {TH_MONTHS[dt.month-1]} {dt.year}"
        print_to_gui(f"# ✅ JSON fetch success: {formatted}")
        callback({"type":"update_date_final","data":{"link":reel_url,"date":formatted}})
        return

    except Exception as e:
        # 5) Fallback → XPath ดึงวันที่ตามโค้ดเดิม
        print_to_gui(f"# ⚠️ JSON fetch failed ({e}), fallback to XPath…")
        fetch_fb_reel_post_date_from_profile(
            driver_instance=headless_driver,
            reel_url_to_find=reel_url,
            target_reel_id_to_find=target_reel_id,
            callback=callback,
            print_to_gui=print_to_gui,
            is_manual=True,
            manual_reel_index=reel_index   # ← ส่ง reel_index เข้ามา
        )

    finally:
        manual_date_pending = False
        # ถ้าเราเป็นคนสร้าง driver เอง ให้ปิดและรีเซ็ต
        if not manual_using_auto_driver:
            try:
                driver.quit()
                standby_driver_for_dates = None
                callback({"type": "driver_status", "mode": "none"})
                print_to_gui("# ✅ Manual driver closed (created by manual).")
            except Exception as e:
                print_to_gui(f"# ⚠️ Manual driver close failed: {e}")
        else:
            # ถ้า reuse มาจาก auto-scan ให้เก็บค้างไว้
            print_to_gui("# ℹ️ Skipped driver close (auto driver reused).")

        # **อย่า** reset manual_using_auto_driver ตรงนี้ ให้ค้างไว้รอบต่อไป



# <<< ของใหม่: เพิ่ม callback, print_to_gui และเอา parameter ที่เกี่ยวกับ Treeview ออก
def fetch_fb_reel_post_date_from_profile(
    driver_instance,
    reel_url_to_find,
    target_reel_id_to_find,
    callback,
    print_to_gui,
    is_manual=False,
    manual_reel_index: int = 0   # ← เพิ่มพารามนี้
):
    if is_manual:
        # แก้ไขบรรทัดนี้โดยการลบส่วนที่เรียกหา main_profile_url ออก
        print_to_gui(f"# FB_DATE_FETCH (MANUAL MODE): Starting for Reel ID {target_reel_id_to_find}")
    else:
        print_to_gui(f"# FB_DATE_FETCH (AUTO MODE - Driver pre-scrolled): Starting for Reel ID {target_reel_id_to_find}. Driver URL: {driver_instance.current_url[:70]}...")

    post_date_str = "⏳..."

    
    callback({
        "type": "update_date_status",
        "data": {
            "link": reel_url_to_find, # <-- ใช้ reel_url_to_find ที่รับเข้ามา
            "status": "⏳..."
        }
    })

    final_date_found = "N/A (Feed Scan)"
    
    
    # --- Parameters การ Scroll (ปรับได้ที่นี่) ---
    if is_manual:

        scroll_pause_time_date_fetch = 1.0 
        # ใช้ helper map ตามจำนวนคลิป (reel_index เริ่มจาก 0 → +1)
        scroll_jump               = get_jump_height_from_clip_count(manual_reel_index)
        max_scrolls_in_function = 20     # จำนวน scroll สูงสุดในฟังก์ชันสำหรับ manual
        burst_scrolls_count       = 3      # จำนวน "Burst Scroll" เริ่มต้นสำหรับ manual
    else:  # Auto-fetch mode
        scroll_pause_time_date_fetch = 0.25 
        scroll_jump                 = 1000                
        max_scrolls_in_function     = 3       
        burst_scrolls_count         = 0

    try:
        
        if is_manual:
            print_to_gui(f"# FB_DATE_FETCH (MANUAL MODE): Using driver pre-navigated and pre-scrolled by caller.")
           
            
        else: # Auto mode
            print_to_gui(f"# FB_DATE_FETCH (AUTO MODE): Using pre-loaded driver.")
            
            

        # ส่วน Logic การเตรียมตัวแปรนี้ดีแล้วครับ ไม่ต้องแก้ไข
        last_height_in_loop = driver_instance.execute_script("return document.body.scrollHeight")
        scrolls_done_this_func = 0
        print_to_gui(f"⚡ Starting process for Reel ID {target_reel_id_to_find} (fetch_fb_reel_post_date): max_scrolls_in_func={max_scrolls_in_function}")

        reel_matched = False
        processed_posts_this_func = set()
    

        
        def get_date_from_post_element(post_element_arg, log_prefix=""):
            nonlocal reel_matched, final_date_found

            date_text_candidate_local = None
            try: # 1. JS SCRIPT
                date_text_js_specific_local = driver_instance.execute_script("""
                    const post = arguments[0];
                    const abbrElement = post.querySelector('abbr[title]');
                    if (abbrElement && abbrElement.title) {
                        if (abbrElement.title.match(/(\\d{1,2}\\s*(ม\\.ค\\.|ก\\.พ\\.|มี\\.ค\\.|เม\\.ย\\.|พ\\.ค\\.|มิ\\.ย\\.|ก\\.ค\\.|ส\\.ค\\.|ก\\.ย\\.|ต\\.ค\\.|พ\\.ย\\.|ธ\\.ค\\.)|\\d{1,2}\\s*[A-Za-z]{3,}|\\d{4}-\\d{2}-\\d{2}|เมื่อวาน|วันนี้|yesterday|\\d+\\s+(นาที|ชั่วโมง|วัน|สัปดาห์|ชม\\.|น\\.))/i)) {
                            return abbrElement.title.trim();
                        }
                    }
                    const timeElement = post.querySelector('time[datetime]');
                    if (timeElement && timeElement.getAttribute('datetime')) {
                        return timeElement.getAttribute('datetime').trim();
                    }
                    const spans = post.querySelectorAll('span');
                    for (let span of spans) {
                        const text = (span.textContent || span.innerText || "").trim();
                        if (text.length > 2 && text.length < 50 && text.match(/(\\d{1,2}\\s*(?:ม\\.ค\\.|ก\\.พ\\.|มี\\.ค\\.|เม\\.ย\\.|พ\\.ค\\.|มิ\\.ย\\.|ก\\.ค\\.|ส\\.ค\\.|ก\\.ย\\.|ต\\.ค\\.|พ\\.ย\\.|ธ\\.ค\\.|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)|[A-Za-z]{3,}\\s+\\d{1,2}(?:,?\\s*\\d{4})?|\\d{1,2}\\/\\d{1,2}\\/\\d{2,4}|เมื่อวาน|วันนี้|\\d+\\s+(?:นาที|ชั่วโมง|วัน|สัปดาห์|ชม\\.|น\\.|วิ|วินาที|ชมที่แล้ว|วันที่แล้ว|นาทีที่แล้ว))/i)) {
                            if (!text.startsWith('#')) {
                                return text;
                            }
                        }
                    }
                    return null;
                """, post_element_arg)

                if date_text_js_specific_local:
                    print_to_gui(f"# FB_DATE_FETCH (JS {log_prefix}): Raw date text: '{date_text_js_specific_local}'")
                    date_text_candidate_local = date_text_js_specific_local
                else:
                    print_to_gui(f"# FB_DATE_FETCH (JS {log_prefix}): JS returned no specific date text.")
            except Exception as e_js_fetch_date:
                print_to_gui(f"# FB_DATE_FETCH (JS {log_prefix}): Error during JS date scan: {e_js_fetch_date}")

            # 2. Python + XPath Fallback
            if not date_text_candidate_local:
                print_to_gui(f"# FB_DATE_FETCH ({log_prefix}): JS did not yield a candidate. Trying Python XPath...")
                found_with_xpath_local = False
                try:
                    date_elements_local = post_element_arg.find_elements(By.XPATH, XPATH_DATE_TEXT)
                    if not date_elements_local and XPATHS_PRIORITY_LIST:
                        for prio_xpath_local in XPATHS_PRIORITY_LIST:
                            try:
                                current_prio_elements_local = post_element_arg.find_elements(By.XPATH, prio_xpath_local)
                                if current_prio_elements_local:
                                    date_elements_local = current_prio_elements_local
                                    print_to_gui(f"# FB_DATE_FETCH (PyXPath Prio {log_prefix}): Found elements with: {prio_xpath_local}")
                                    break
                            except Exception: continue
                    
                    potential_texts_xpath_local = []
                    for el_local in date_elements_local:
                        title_local = el_local.get_attribute("title")
                        text_local = el_local.text
                        if title_local and len(title_local.strip()) > 3 and not title_local.strip().startswith("#"): potential_texts_xpath_local.append(title_local.strip())
                        if text_local and len(text_local.strip()) > 3 and not text_local.strip().startswith("#"): potential_texts_xpath_local.append(text_local.strip())
                    
                    if potential_texts_xpath_local:
                        print_to_gui(f"# FB_DATE_FETCH (PyXPath {log_prefix}): Candidates: {list(dict.fromkeys(potential_texts_xpath_local))[:3]}")
                        for dt_cand_xpath_local in list(dict.fromkeys(potential_texts_xpath_local)):
                            if re.search(r"(\d{1,2}|ม\.ค|ก\.พ|มี\.ค|เม\.ย|พ\.ค|มิ\.ย|ก\.ค|ส\.ค|ก\.ย|ต\.ค|พ\.ย|ธ\.ค|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|256\d|202\d|วัน|ชม|นาที|ที่แล้ว|ago|yesterday|today)", dt_cand_xpath_local, re.I):
                                date_text_candidate_local = dt_cand_xpath_local
                                found_with_xpath_local = True
                                print_to_gui(f"# FB_DATE_FETCH (PyXPath {log_prefix}): Selected candidate: '{date_text_candidate_local}'")
                                break 
                        if not found_with_xpath_local:
                            print_to_gui(f"# FB_DATE_FETCH (PyXPath {log_prefix}): No suitable date text found via XPaths.")
                except Exception as e_py_xpath_fetch_date:
                    print_to_gui(f"# FB_DATE_FETCH (PyXPath {log_prefix}): Error: {e_py_xpath_fetch_date}")
            
            # 3. Parse ตัวเต็งสุดท้าย
            if date_text_candidate_local:
                print_to_gui(f"# FB_DATE_FETCH ({log_prefix}): Final candidate for parsing: '{date_text_candidate_local}'")
                
                # <<< ของเดิม: parsed_date_final_local = parse_thai_date_text(date_text_candidate_local)
                # <<< ของใหม่: ส่ง print_to_gui เข้าไปในฟังก์ชัน parse วันที่ด้วย
                parsed_date_final_local = parse_thai_date_text(date_text_candidate_local, print_to_gui)
                
                print_to_gui(f"# FB_DATE_FETCH ({log_prefix}): Parsed final date: '{parsed_date_final_local}'")
                iso_check_local = (isinstance(date_text_candidate_local, str) and date_text_candidate_local.count('-') == 2 and 'T' in date_text_candidate_local)
                if parsed_date_final_local != "N/A" and (parsed_date_final_local != date_text_candidate_local or iso_check_local):
                    final_date_found = parsed_date_final_local
                    reel_matched = True
                else:
                    print_to_gui(f"# FB_DATE_FETCH ({log_prefix}): Final candidate '{date_text_candidate_local}' did not parse well ('{parsed_date_final_local}').")
            else:
                print_to_gui(f"# FB_DATE_FETCH ({log_prefix}): No date text candidate found for this post.")
        # --- END ฟังก์ชันย่อย ---


        # --- STRATEGY FOR AUTO-FETCH: INITIAL CHECK (NO SCROLL) ---
        # <<< ส่วนนี้ Logic ดีมากครับ แก้ไขเพียงจุดเดียว
        if not is_manual:
            print_to_gui(f"# FB_DATE_FETCH (AUTO MODE): Attempting Initial Check for Reel ID {target_reel_id_to_find} in currently loaded DOM.")
            try:
                all_articles_on_page = driver_instance.find_elements(By.XPATH, "//div[@role='article']")
                print_to_gui(f"# FB_DATE_FETCH (AUTO MODE Initial Check): Found {len(all_articles_on_page)} articles.")
                
                for post_idx, post_cv in enumerate(all_articles_on_page):
                    if reel_matched: break 
                    post_uid_cv = post_cv.get_attribute("data-ft") or post_cv.get_attribute("data-testid") or str(post_cv.id)
                    if post_uid_cv in processed_posts_this_func: continue
                    processed_posts_this_func.add(post_uid_cv)
                    
                    reel_links_cv = post_cv.find_elements(By.XPATH, ".//a[contains(@href, '/reel/') or contains(@href, 'watch/?v=') or contains(@href, '/videos/') or contains(@href, 'video.php')]")
                    for link_cv in reel_links_cv:
                        url_cv = link_cv.get_attribute('href')
                        
                        # <<< ของเดิม: reel_id_cv = extract_reel_id_from_url(url_cv)
                        # <<< ของใหม่: ส่ง print_to_gui ต่อไปให้ฟังก์ชันลูก
                        reel_id_cv = extract_reel_id_from_url(url_cv, print_to_gui)

                        if reel_id_cv == target_reel_id_to_find:
                            print_to_gui(f"# FB_DATE_FETCH (AUTO MODE Initial Check): ✅ Matched Reel ID {target_reel_id_to_find}! (Article index ~{post_idx})")
                            get_date_from_post_element(post_cv, log_prefix="Initial Check")
                            if reel_matched: break 
                    if reel_matched: break 
            except Exception as e_initial_check_outer:
                print_to_gui(f"# FB_DATE_FETCH (AUTO MODE Initial Check Outer): Error - {e_initial_check_outer}")
        # --- END STRATEGY FOR AUTO-FETCH ---

        # --- MAIN SCROLL LOOP (ทำงานถ้ายังไม่เจอ หรือถ้าเป็น manual mode) ---
        # <<< Logic ส่วนนี้ดีเยี่ยมครับ แก้ไขเพียงจุดเดียว
        while scrolls_done_this_func < max_scrolls_in_function and not reel_matched:
            if is_manual or scrolls_done_this_func > 0 or (not is_manual and not reel_matched):
                print_to_gui(f"# FB_DATE_FETCH: Scroll in func {scrolls_done_this_func + 1}/{max_scrolls_in_function} → Target Reel ID {target_reel_id_to_find}")
                if is_manual and scrolls_done_this_func < burst_scrolls_count:
                    driver_instance.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.25)
                elif not is_manual and scrolls_done_this_func >= (max_scrolls_in_function - 2) and max_scrolls_in_function > 2 : 
                    print_to_gui(f"# FB_DATE_FETCH (AUTO): Near end, SuperBoot scroll {scrolls_done_this_func +1}.")
                    driver_instance.execute_script("window.scrollBy(0, 3000);") 
                else:
                    driver_instance.execute_script(f"window.scrollBy(0, {scroll_jump});")
                time.sleep(scroll_pause_time_date_fetch)
            else:
                print_to_gui(f"# FB_DATE_FETCH (AUTO MODE): Initial check did not find ID {target_reel_id_to_find}. Proceeding to scroll.")

            try:
                wait_for_articles_timeout = 4 if is_manual else 2.0 
                WebDriverWait(driver_instance, wait_for_articles_timeout).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@role='article']")))
                posts_after_scroll = driver_instance.find_elements(By.XPATH, "//div[@role='article']")
                print_to_gui(f"# FB_DATE_FETCH: Found {len(posts_after_scroll)} articles after scroll.")
            except TimeoutException:
                if not is_manual: break
                posts_after_scroll = []
            except Exception: break
            
            for post_as in posts_after_scroll: 
                if reel_matched: break
                try:
                    post_uid_as = post_as.get_attribute("data-ft") or post_as.get_attribute("data-testid") or str(post_as.id)
                    if post_uid_as in processed_posts_this_func: continue
                    processed_posts_this_func.add(post_uid_as)
                    
                    if is_manual or scrolls_done_this_func == 0 : 
                        driver_instance.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", post_as)
                        time.sleep(0.3)

                    reel_links_as = post_as.find_elements(By.XPATH, ".//a[contains(@href, '/reel/') or contains(@href, 'watch/?v=') or contains(@href, '/videos/') or contains(@href, 'video.php')]")
                    for link_as in reel_links_as:
                        url_as = link_as.get_attribute('href')
                        
                        # <<< ของเดิม: reel_id_as = extract_reel_id_from_url(url_as)
                        # <<< ของใหม่: ส่ง print_to_gui ต่อไปให้ฟังก์ชันลูก
                        reel_id_as = extract_reel_id_from_url(url_as, print_to_gui)
                        
                        if reel_id_as == target_reel_id_to_find:
                            print_to_gui(f"# FB_DATE_FETCH: ✅ Matched Reel ID {target_reel_id_to_find} in scroll loop!")
                            get_date_from_post_element(post_as, log_prefix="Scroll Loop")
                            if reel_matched: break 
                    if reel_matched: break 
                except StaleElementReferenceException:
                    print_to_gui("# FB_DATE_FETCH: StaleElement in scroll loop. Breaking from post loop.")
                    break 
                except Exception as e_post_scroll_inner:
                    print_to_gui(f"# FB_DATE_FETCH: Inner error processing post in scroll loop: {e_post_scroll_inner}")

            if reel_matched: break

            if not reel_matched:
                new_height = driver_instance.execute_script("return document.body.scrollHeight")
                if new_height == last_height_in_loop: 
                    if not is_manual:
                        if scrolls_done_this_func < max_scrolls_in_function -1:
                            driver_instance.execute_script(f"window.scrollBy(0, {scroll_jump // 2 + 50});")
                            time.sleep(scroll_pause_time_date_fetch + 0.1)
                            newer_height = driver_instance.execute_script("return document.body.scrollHeight")
                            if newer_height == new_height: break
                            last_height_in_loop = newer_height
                        else: break
                    else: 
                        if scrolls_done_this_func > 2 and new_height == driver_instance.execute_script("return document.body.scrollHeight"): break
                else: last_height_in_loop = new_height
            scrolls_done_this_func += 1
        
        if not reel_matched:
            print_to_gui(f"# FB_DATE_FETCH: ❌ Target Reel ID {target_reel_id_to_find} not found after {scrolls_done_this_func} scrolls.")
            final_date_found = "N/A (Not Found)"

    except WebDriverException as e_wd_func:
        final_date_found = "N/A (Driver Error)"
        print_to_gui(f"# FB_DATE_FETCH: WebDriverException in func: {e_wd_func}")
    except Exception as e_main_func:
        final_date_found = "N/A (Error)"
        print_to_gui(f"# FB_DATE_FETCH: General error in func: {e_main_func}")
    finally:
        # ส่งผลลัพธ์สุดท้ายกลับไปที่ UI ผ่าน callback โดยใช้ "link" เป็น key
        print_to_gui(f"# FB_DATE_FETCH: Final result for {target_reel_id_to_find} is '{final_date_found}'.")
        callback({
            "type": "update_date_final",
            "data": {
                "link": reel_url_to_find, # <-- ใช้ reel_url_to_find ที่รับเข้ามา
                "date": final_date_found
            }
        })

     # ไม่ต้อง return อะไรแล้ว เพราะเราใช้ callback จัดการทั้งหมด



# ✅ เพิ่ม Worker ที่จะใช้ใน Driver Pool
def get_date_worker(reel_url: str):
    worker_driver = None
    try:
        worker_driver = create_chrome_driver(headless=True)
        if worker_driver:
            dt_obj = get_reel_date_via_json_driver(worker_driver, reel_url)
            th_months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
            formatted_date = f"{dt_obj.day} {th_months[dt_obj.month - 1]} {dt_obj.year + 543}"
            return reel_url, formatted_date, True
    except Exception:
        return reel_url, None, False
    finally:
        if worker_driver:
            worker_driver.quit()
    return reel_url, None, False


# <<< ของใหม่: เปลี่ยนชื่อเป็น run_fb_scan และรับ parameter เฉพาะที่จำเป็น + callback

def run_fb_scan(url_reels_tab_from_entry, url_profile_main_from_entry, max_clips_str, callback):
    is_reels_tab = 'reels_tab' in url_reels_tab_from_entry.lower()  
    def print_to_gui(message):
        callback({"type": "log", "message": str(message)})

    print("[DEBUG 1] Entered run_fb_scan function.")
    callback({"type": "status", "message": "⏳ [FB] เริ่มการทำงาน..."})
    print_to_gui("# DEBUG_FB: Worker thread started for Facebook.")

    print("[DEBUG 2] Validating inputs.")
    max_clips = 0
    try:
        max_clips = int(max_clips_str)
        if max_clips <= 0:
            raise ValueError("จำนวนคลิปต้องมากกว่า 0")
    except ValueError as e:
        callback({"type": "error", "title": "ข้อมูลไม่ถูกต้อง (FB)", "message": str(e)})
        callback({"type": "status", "message": "❌ [FB] จำนวนคลิปไม่ถูกต้อง", "final": True})
        return

    driver = None
    headless_driver_for_dates = None # Standby Driver
    driver_pool_list = [] # สำหรับเก็บ Driver ใน Pool เพื่อปิดตอนท้าย

    # เคลียร์ Driver ที่ค้างจาก Manual (โค้ดเดิมของคุณ)
    global standby_driver_for_dates
    if standby_driver_for_dates:
        try:
            print_to_gui(f"⚙️ DEBUG: standby_driver_for_dates is not None: {standby_driver_for_dates}")
            standby_driver_for_dates.quit()
            print_to_gui("🧹 Cleared leftover standby driver from previous manual fetch.")
            callback({"type": "driver_status", "mode": "none"})
        except Exception as e:
            print_to_gui(f"⚠️ WARNING: Failed to close leftover standby driver: {e}")
        standby_driver_for_dates = None
    else:
        print_to_gui("⚙️ DEBUG: No standby driver found to close.")

    try:
        # --- ส่วนที่ 1: ดึงยอดวิว (โค้ดเดิมของคุณทั้งหมด) ---
        callback({"type": "status", "message": "🔗 [FB] กำลังเชื่อมต่อ Driver..."})

        # เตรียม standby driver สำหรับ Fallback ล่วงหน้า (โค้ดเดิมของคุณ)
        def setup_date_driver():
            global standby_driver_for_dates
            standby_driver_for_dates = create_chrome_driver(print_to_gui=print_to_gui, headless=True)
            fb_login(standby_driver_for_dates, callback, print_to_gui)
            standby_driver_for_dates.get(url_profile_main_from_entry)
            print_to_gui("✅ Standby browser (for fallback) loaded with profile page.")

        threading.Thread(target=setup_date_driver, daemon=True).start()

        driver = create_chrome_driver(print_to_gui=print_to_gui, headless=False)
        if not fb_login(driver, callback, print_to_gui): return

        callback({"type": "status", "message": "🔍 [FB] กำลังค้นหา Reels และยอดวิว..."})
        total_views, counted_clips, collected_reels_list = count_views_fb(
            driver, url_reels_tab_from_entry, max_clips, print_to_gui, callback
        )

        if not collected_reels_list:
            callback({"type": "status", "message": "⚠️ [FB] ไม่พบข้อมูล Reels เลย", "final": True})
            return
            
        if driver:
            driver.quit()
            driver = None


        # --- ส่วนที่ 2: ดึงวันที่ (ผสานระบบใหม่เข้ามา) ---
        if url_profile_main_from_entry and collected_reels_list:
            callback({"type": "driver_status", "mode": "auto"})

            list_len = len(collected_reels_list)
            first_indices = list(range(min(15, list_len)))
            last_indices = list(range(max(0, list_len - 15), list_len))
            reels_to_process_indices = sorted(set(first_indices + last_indices))
            
            # 🚀 ส่งสัญญาณ Spinner (โค้ดเดิมของคุณ)
            callback({"type": "auto_date_fetch_start", "data": { "indices": reels_to_process_indices, "platform": "fb" }})
            
            # ✅ --- วิธีหลัก: ใช้ Driver Pool ที่รวดเร็ว ---
            urls_to_fetch = [collected_reels_list[i]['link'] for i in reels_to_process_indices]
            failed_indices = []
            
            print_to_gui(f"🚀 Starting parallel date fetch for {len(urls_to_fetch)} reels...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_to_url = {executor.submit(get_date_worker, url): url for url in urls_to_fetch}
                for future in concurrent.futures.as_completed(future_to_url):
                    url, date, success = future.result()
                    if success:
                        # ใช้ callback เดิมของคุณ
                        callback({"type": "update_date_final", "data": {"link": url, "date": date}})
                    else:
                        # หา index ของ url ที่พลาดเพื่อส่งให้ Fallback
                        idx = next((i for i, item in enumerate(collected_reels_list) if item['link'] == url), -1)
                        if idx != -1:
                            failed_indices.append(idx)

            # ✅ --- แผนสำรอง: ใช้ Standby Driver (โค้ดเดิมของคุณ) ---
            if failed_indices:
                print_to_gui(f"⚠️ {len(failed_indices)} reels failed JSON fetch, starting fallback...")
                headless_driver_for_dates = standby_driver_for_dates # ใช้ standby driver ที่เตรียมไว้
                if headless_driver_for_dates:    

            

                    # ——— PRE-SCROLL + FAST-EXIT (เฉพาะ Auto-Mode) ———
                    total_needed_clips = len(collected_reels_list_fb)

                    jump_map = [
                        (30, 15000),
                        (40, 22000),
                        (50, 30000),
                        (60, 34000),
                        (70, 38000),
                        (80, 42000),
                        (90, 46000),
                        (100, 53000),
                        (110, 60000),
                        (120, 65000),
                        (140, 76000),
                    ]

                    jump_height = 0
                    for limit, height in jump_map:
                        if total_needed_clips >= limit:
                            jump_height = height


                    manual_date_pending = False  # ✅ กำหนดค่าก่อนใช้งาน        
                    # เพิ่มเช็ค manual_date_pending → ข้ามบล็อกนี้ใน Manual-Mode
                    if jump_height > 0 and not manual_date_pending:
                        print_to_gui(f"# DEBUG_FB: 🪂 Jump scroll pre-scroll to {jump_height}px (total_clips: {total_needed_clips})")
                        callback({
                            "type": "fb_jump_status",
                            "data": {
                                "jump_height": jump_height,
                                "total_needed_clips": total_needed_clips,
                                "total_clips": total_needed_clips,
                                "total_views": total_views
                            }
                        })

                        jump_scroll_script = f"""
                        let interval = setInterval(() => {{
                            window.scrollBy(0, 700);
                            if (window.scrollY >= {jump_height}) {{
                                clearInterval(interval);
                            }}
                        }}, 5);
                        """
                        headless_driver_for_dates.execute_script(jump_scroll_script)

                        timeout_jump = time.time() + 3
                        while True:
                            actual_y = headless_driver_for_dates.execute_script("return window.scrollY")
                            if actual_y >= jump_height:
                                break
                            if time.time() > timeout_jump:
                                print_to_gui("⚠️ Timeout waiting for JS jump scroll to finish")
                                break
                            time.sleep(0.05)

                        print_to_gui(f"# DEBUG_FB: 📍 After JS jump, Y is at {actual_y}px")

                        # ===== FAST-EXIT: Check Reel IDs after jump scroll =====
                        try:
                            articles = headless_driver_for_dates.find_elements(By.XPATH, "//div[@role='article']")
                            hrefs = []
                            for article in articles:
                                try:
                                    links = article.find_elements(By.TAG_NAME, "a")
                                    for link_elem in links:
                                        href = link_elem.get_attribute("href")
                                        if href and "/reel/" in href:
                                            hrefs.append(href)
                                except:
                                    continue

                            found_reel_ids = set(extract_id_from_url(h) for h in hrefs)
                            target_ids = { clip["id"] for clip in collected_reels_list_fb }

                            if target_ids.issubset(found_reel_ids) and counted_clips == len(collected_reels_list_fb):
                                print_to_gui("💎 Fast-Exit: ✅ ID ตรงครบ & ✅ Counted ตรง → ข้าม scroll-loop และเข้าสู่ดึงวันที่ทันที")
                                return
                            if target_ids.issubset(found_reel_ids):
                                print_to_gui("✅ Fast-Exit: DOM Boost & คลิปครบ → เข้าดึงวันที่ทันที")
                                return
                        except Exception as e:
                            print_to_gui(f"⚠️ Fast-Exit check failed: {e}")

                        # ✅ DOM Boost: รอให้ <article> โหลดก่อนเริ่ม scroll-loop
                        max_dom_wait = 2
                        start_dom_wait = time.time()
                        total_clips = max_clips
                        while True:
                            try:
                                articles = headless_driver_for_dates.find_elements(By.XPATH, "//div[@role='article']")
                                if len(articles) >= 5:
                                    print_to_gui(f"✅ DOM Boost: เจอ {len(articles)} articles แล้ว")
                                    if len(articles) > 5 and counted_clips == total_clips:
                                        print_to_gui("✅ Fast-Exit: DOM Boost & คลิปครบ → เข้าดึงวันที่ทันที")
                                        break
                                    if counted_clips == len(collected_reels_list_fb):
                                        print_to_gui("💨 Fast-Exit: เจอครบ clip แล้ว ข้าม scroll-loop ปกติ")
                                        break
                                    break
                            except StaleElementReferenceException:
                                pass

                            if time.time() - start_dom_wait > max_dom_wait:
                                print_to_gui("⚠️ DOM load timeout after jump")
                                break
                            time.sleep(0.1)
                    # —————— จบบล็อก Auto-Only ——————

                    # — Initial scroll-loop ของเดิม —
                    start_time = time.time()
                    last_height = 0
                    same_height_count = 0
                    max_same = 3
                    while True:
                        new_height = headless_driver_for_dates.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            same_height_count += 1
                            if same_height_count >= max_same:
                                print_to_gui(f"# DEBUG_FB: Scroll height not changing for {max_same} times → break")
                                break
                        else:
                            same_height_count = 0
                        last_height = new_height
                        time.sleep(scroll_pause)

                    for attempt in range(initial_scroll_attempts_target):
                        scroll_start_time = time.time()
                        new_height = headless_driver_for_dates.execute_script("return document.body.scrollHeight")
                        headless_driver_for_dates.execute_script(f"window.scrollTo(0, {new_height});")
                        time.sleep(0.5)
                        scroll_end_time = time.time()
                        elapsed_scroll = scroll_end_time - scroll_start_time

                        callback({
                            "type": "fb_scroll_progress",
                            "data": {
                                "attempt": attempt + 1,
                                "total": initial_scroll_attempts_target,
                                "scroll_height": new_height,
                                "total_views": total_views,
                                "counted_clips": counted_clips
                            }
                        })
                        print_to_gui(f"# DEBUG_FB: Initial scroll {attempt+1}/{initial_scroll_attempts_target} - height: {new_height}")

                        target_ids = set([collected_reels_list_fb[i]["id"] for i in reels_to_process_indices])

                        if is_reels_tab:
                            if counted_clips == len(collected_reels_list_fb):
                                print_to_gui("✅ Fast Exit (Reels Tab): ครบยอด count → หยุด scroll")
                                break
                        else:
                            if counted_clips == len(collected_reels_list_fb) and target_ids.issubset(found_reel_ids):
                                print_to_gui("✅ Smart Exit (ทั่วไป): Count + ID ครบ → หยุด scroll")
                                break

                        articles = headless_driver_for_dates.find_elements(By.XPATH, "//div[@role='article']")
                        hrefs = []
                        for i in range(len(articles)):
                            try:
                                article = articles[i]
                                links = article.find_elements(By.TAG_NAME, "a")
                                for link_elem in links:
                                    href = link_elem.get_attribute("href")
                                    if href and "/reel/" in href and href not in hrefs:
                                        hrefs.append(href)
                            except StaleElementReferenceException:
                                print_to_gui("⚠️ ข้าม article ที่ stale ไป")
                                continue

                        found_reel_ids = set()
                        for href in hrefs:
                            reel_id = extract_reel_id_from_url(href, print_to_gui)
                            if reel_id and reel_id in target_ids:
                                found_reel_ids.add(reel_id)

                        print_to_gui(f"# DEBUG_FB: 🔍 เจอ Reel IDs: {len(found_reel_ids)} / {len(target_ids)}")

                        if target_ids.issubset(found_reel_ids) and len(found_reel_ids) >= 5:
                            print_to_gui("✅ Fallback Exit: เจอครบ ID → หยุด scroll loop")
                            break

                        if found_reel_ids == target_ids:
                            print_to_gui("# DEBUG_FB: ✅ เจอครบ Reel ที่ต้องการ หยุด scroll")
                            break

                        if time.time() - start_time > timeout_seconds:
                            print_to_gui(f"# DEBUG_FB: Timeout after {timeout_seconds}s, breaking.")
                            break
                    else:
                        print_to_gui("# DEBUG_FB: Finished all initial scrolls without finding all target articles.")

                    # --- กำหนด is_reels_tab ก่อนใช้ เพื่อไม่ให้ Cython เตือน undeclared ---
                    
                    # — Legacy Fallback: ดึงวันที่ทีละตัว …
                    for idx in failed_indices:
                        reel = collected_reels_list[idx]
                        fetch_fb_reel_post_date_from_profile(
                            driver_instance=headless_driver_for_dates,
                            reel_url_to_find=reel["link"],
                            target_reel_id_to_find=reel["id"],
                            callback=callback,
                            print_to_gui=print_to_gui,
                            is_manual=False,
                            manual_reel_index=idx
                        )

                else:
                    print_to_gui("❌ Cannot start fallback: Standby Driver is not ready.")
                # ——— จบ JSON-first block ———


        if counted_clips > 0:
            callback({"type": "status", "message": f"✅ [FB] สแกนเสร็จสมบูรณ์: {counted_clips} คลิป | รวม {total_views:,} วิว", "final": True})
        else:
            callback({"type": "status", "message": "⚠️ [FB] ไม่พบ Reels", "final": True})

        print_to_gui("\n--- [FB] การทำงานเสร็จสิ้นทั้งหมด ---")

    except WebDriverException as e_wd_main:
        print_to_gui(f"# DEBUG_FB: WebDriverException in FB task: {e_wd_main}")
        callback({"type": "error", "title": "WebDriver Error (FB)", "message": str(e_wd_main)})
        callback({"type": "status", "message": "❌ [FB] WebDriver Error", "final": True})

    except Exception as e:
        print(f"[DEBUG FINAL] Exception caught in main try-block: {type(e).__name__} - {e}")
        callback({"type": "error", "title": "Error (FB)", "message": str(e)})
        callback({"type": "status", "message": "❌ [FB] เกิดข้อผิดพลาดร้ายแรง", "final": True})

    finally:
        manual_date_pending = False  # ✅ Reset ทันทีหลังจบทุกการทำงาน
        print("[DEBUG FINAL] Entering finally block. manual_date_pending reset=True")  # optional log

        if driver:
            try:
                print_to_gui("# 🔥 INFO: ปิดเบราว์เซอร์หลังสแกนเสร็จ (Auto Driver)...")
                driver.quit()
            except Exception as e:
                print_to_gui(f"# ⚠️ WARNING: ไม่สามารถปิดเบราว์เซอร์อัตโนมัติได้: {e}")
            driver = None
        else:
            print_to_gui(f"# 🕹️ Driver ยังเปิดไว้ manual_date_pending={manual_date_pending}")
            callback({
                "type": "driver_status",
                "mode": "manual-ready"
            })