import os
import re
import sys
import json
import time
import threading
import webbrowser
from datetime import datetime as dt
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    WebDriverException, 
    NoSuchElementException, 
    StaleElementReferenceException
)
from constants_ig import FALLBACK_XPATHS_IG, XPATH_POST_DATE_IG







def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import os

def create_chrome_driver(print_to_gui=print, headless=False):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    try:
        print_to_gui("🔄 พยายามเปิด Chrome แบบปกติ (WebDriverManager)...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print_to_gui("✅ เปิด Chrome สำเร็จ (WebDriverManager)")
        return driver

    except WebDriverException as e:
        print_to_gui(f"⚠️ WebDriverManager ล้มเหลว: {e}")
        print_to_gui("🔁 ลอง fallback: ระบุ path chrome.exe เอง")

        fallback_paths = [
            r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        ]

        for fallback_path in fallback_paths:
            if os.path.exists(fallback_path):
                options.binary_location = fallback_path
                try:
                    driver = webdriver.Chrome(service=service, options=options)
                    print_to_gui(f"✅ เปิด Chrome ด้วย fallback path: {fallback_path}")
                    return driver
                except Exception as fallback_error:
                    print_to_gui(f"❌ ล้มเหลวที่ path: {fallback_path} → {fallback_error}")

        print_to_gui("❌ fallback ทั้งหมดไม่สำเร็จ")
        return None


# ---- START: Utility Functions ----
def clean_url(url_raw):
    if not isinstance(url_raw, str):
        return ""
    url = url_raw.strip()
    url = re.sub(r'[\u200e\u200f\u202a-\u202e\u2066-\u2069]', '', url)
    return url
# ---- END: Utility Functions ----

def get_application_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    try:
        return os.path.dirname(__file__)
    except NameError:
        return os.getcwd()
    
# chromedriver_path และ chrome_binary_path ถูกลบออก เนื่องจากใช้ ChromeDriverManager แทน    
application_path = get_application_path()
cookie_file = os.path.join(application_path, "ig_cookies.json")
# ---- END: Paths Configuration ----


def save_cookies(driver, path, print_to_gui, callback):  # เพิ่ม callback ตรงนี้
    try:
        with open(path, "w") as file: json.dump(driver.get_cookies(), file)
        print_to_gui("Instagram cookies saved successfully.")
        callback({"type": "save_cookie"})    # <<< ใส่ตรงนี้!
    except Exception as e: print_to_gui(f"Error saving cookies to {path}: {e}")

# <<< ของเดิม: def load_cookies(driver, path):
# <<< ของใหม่: เพิ่ม print_to_gui เป็นพารามิเตอร์
def load_cookies(driver, path, print_to_gui, callback=None):
    try:
        with open(path, "r") as file:
            cookies = json.load(file)
        for cookie in cookies:
            try:
                if 'name' in cookie and 'value' in cookie:
                    if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                        cookie['expiry'] = int(cookie['expiry'])
                    driver.add_cookie(cookie)
                else:
                    print_to_gui(f"Warning: Skipping cookie (missing name/value): {cookie}")
            except Exception as e_cookie:
                print_to_gui(f"Warning: Could not add cookie {cookie.get('name', 'N/A')}: {e_cookie}")
        print_to_gui(f"Cookies loaded from {path}.")
        return True
    except FileNotFoundError:
        print_to_gui(f"Cookie file not found: {path}")
    except json.JSONDecodeError:
        print_to_gui(f"Error decoding JSON from cookie file: {path}.")
    except Exception as e:
        print_to_gui(f"Error loading cookies from {path}: {e}")
        if callback:
            callback({"type": "error", "title": "Error", "message": f"Error loading cookies: {e}"})
    return False

# <<< ของเดิม: def handle_generic_popups_ig(driver, quick_check_timeout=1.0):
# <<< ของใหม่: เพิ่ม print_to_gui เป็นพารามิเตอร์
def handle_generic_popups_ig(driver, print_to_gui, quick_check_timeout=1.0):
    print_to_gui("# DEBUG_IG: Attempting to handle pop-ups...")
    handled = False

    xpaths = [
        '//div[@role="dialog"]//button[contains(text(), "Not Now") or contains(text(), "ไม่ตอนนี้")]',
        '//button[text()="Not Now" or text()="ไม่ตอนนี้"]',
        '//div[@role="dialog"]//button[contains(text(), "Allow all cookies") or contains(text(), "Accept All")]',
        '//button[contains(text(), "Allow all cookies") or contains(text(), "ยอมรับทั้งหมด")]',
    ]

    for xpath in xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    print_to_gui(f"# DEBUG_IG: Clicking pop-up: {xpath[:30]}...")
                    WebDriverWait(driver, quick_check_timeout).until(EC.element_to_be_clickable(el)).click()
                    print_to_gui(f"Pop-up clicked.")
                    time.sleep(0.5)
                    handled = True
                    return True
        except:
            continue

    if not handled:
        print_to_gui("# DEBUG_IG: No known pop-ups found/handled.")
    return handled


# <<< ของเดิม: def ig_login(driver):
# <<< ของใหม่: เพิ่ม callback และ print_to_gui เป็นพารามิเตอร์
def ig_login(driver, callback, print_to_gui):
    # แจ้ง UI ว่ากำลังเริ่ม ig_login
    callback({"type": "wait_login"})
    print_to_gui("# DEBUG_IG: Starting ig_login...")

    # เปิดหน้า Instagram หลัก
    driver.get("https://www.instagram.com/")
    time.sleep(1)
    handle_generic_popups_ig(driver, print_to_gui)

    # หากมีไฟล์คุกกี้ ให้ลองโหลดก่อน
    if os.path.exists(cookie_file):
        try:
            print_to_gui(f"# DEBUG_IG: Loading cookies from: {cookie_file}")
            if load_cookies(driver, cookie_file, print_to_gui, callback):
                # รีเฟรชหน้าเพื่อให้ cookies ทำงาน
                driver.get("https://www.instagram.com/")
                time.sleep(2)
                handle_generic_popups_ig(driver, print_to_gui)

                # ตรวจสอบว่า login สำเร็จผ่าน cookies
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/direct/inbox")]')),
                        EC.presence_of_element_located((By.XPATH, '//img[contains(@alt, "profile picture")]'))
                    )
                )
                print_to_gui("✓ Logged in via cookies.")
                callback({"type": "cookie_loaded"})
                return True
        except TimeoutException:
            print_to_gui("Cookies expired/invalid. Manual login needed.")
        except Exception as e:
            print_to_gui(f"Cookie login error: {e}. Manual login.")

    # กรณีต้องล็อกอินด้วยตนเอง
    print_to_gui("# DEBUG_IG: Navigating to login page.")
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(1)
    handle_generic_popups_ig(driver, print_to_gui)

    # รอให้หน้า login โหลด
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
    except TimeoutException:
        callback({"type": "error", "title": "Error", "message": "Login page timeout."})
        return False

    # แจ้งให้ UI แสดง dialog ให้ผู้ใช้ล็อกอิน
    callback({
        "type": "info",
        "title": "Login Required",
        "message": (
            "กรุณาเข้าสู่ระบบ Instagram...\n"
            "ปิดหน้าต่างนี้หลังล็อกอินเสร็จ โปรแกรมจะทำงานต่ออัตโนมัติ"
        )
    })

    # วนรอจน user ล็อกอินเสร็จสมบูรณ์
    start_time = time.time()
    while time.time() - start_time < 300:
        url_current = driver.current_url.lower()
        if not any(fragment in url_current for fragment in ["accounts/login", "challenge"]):
            try:
                WebDriverWait(driver, 5).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/direct/inbox")]')),
                        EC.presence_of_element_located((By.XPATH, '//img[contains(@alt, "profile picture")]'))
                    )
                )
                print_to_gui("✓ Manual login confirmed.")
                break
            except:
                print_to_gui(f"Waiting for login confirmation... Current URL: {driver.current_url}")
        else:
            print_to_gui(f"Still on login/checkpoint ({driver.current_url}). Waiting...")
        time.sleep(2)
    else:
        # หาก timeout
        callback({"type": "error", "title": "Error", "message": "Login timeout or confirmation failed."})
        return False

    # เมื่อล็อกอินสำเร็จ ให้บันทึก cookies ใหม่
    print_to_gui("# DEBUG_IG: Manual login successful. Saving cookies.")
    save_cookies(driver, cookie_file, print_to_gui, callback)
    return True




def parse_view_count_ig(text):
    # <<< ฟังก์ชันนี้ Logic ดีเยี่ยมครับ เป็น Pure function ไม่ต้องแก้ไข
    try:
        text = text.replace(",", "").lower()
        if 'm' in text:
            return int(float(text.replace('m', '')) * 1_000_000)
        elif 'k' in text:
            return int(float(text.replace('k', '')) * 1_000)
        elif 'ล้าน' in text:
            return int(float(text.replace('ล้าน', '')) * 1_000_000)
        elif 'พัน' in text:
            return int(float(text.replace('พัน', '')) * 1_000)
        elif 'views' in text:
            return int(text.replace('views', '').strip())
        else:
            return int(text)
    except:
        return 0
    
def extract_view_count_ig(link_el):
    # <<< ฟังก์ชันนี้ Logic การวนลูปหา XPath ดีมากครับ ไม่ต้องแก้ไข
    best_raw = ''
    best_val = 0

    for xpath in FALLBACK_XPATHS_IG:
        try:
            elements = link_el.find_elements(By.XPATH, xpath)
            for el in elements:
                raw_text = el.text.strip()
                val = parse_view_count_ig(raw_text)
                if val > best_val:
                    best_val = val
                    best_raw = raw_text
        except Exception:
            continue

    if best_val == 0:
        return 0, 'N/A (Views Not Found)'
    return best_val, best_raw

def extract_post_date(driver):
    # <<< ฟังก์ชันนี้เป็น utility ที่ดีครับ ไม่ต้องแก้ไข
    try:
        time_el = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//time'))
        )
        date_text = time_el.get_attribute("datetime") or time_el.get_attribute("title") or time_el.text
        return date_text.strip() if date_text else "N/A"
    except Exception:
        return "N/A"


def count_views(driver, url_profile, max_target_clips, print_to_gui, callback):
    print_to_gui(f"# DEBUG_IG: Navigating to: {url_profile}")
    callback({"type": "scan_feed"})  # ← เพิ่มตรงนี้ก่อนเริ่ม scroll
    driver.get(url_profile)
    time.sleep(1)

    reels_list = []
    processed_hrefs = set()
    scrolls = 0
    max_scrolls = 50
    pause = 2.5

    print_to_gui("--- IG Phase: Collecting Reels ---")
    # Logic การวน Loop, Scroll, ดึงข้อมูล ยอดเยี่ยมอยู่แล้วครับ คงไว้ทั้งหมด


    
    same_links_threshold = 3  # สามารถปรับได้
    processed_hrefs = set()
    prev_reels_count = 0

    while len(reels_list) < max_target_clips and scrolls < max_scrolls:
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//main[@role="main"]//a[contains(@href, "/reel/")]')))
            links = driver.find_elements(By.XPATH, '//main[@role="main"]//a[contains(@href, "/reel/")]')
            print_to_gui(f"Step 2: Found {len(links)} potential links.")

            new_links_count = 0

            for link_el in links:
                if len(reels_list) >= max_target_clips:
                    break

                current_href = link_el.get_attribute("href")
                if current_href:
                    current_href = current_href.split('?')[0].split('&')[0]

                if current_href and "/reel/" in current_href and current_href not in processed_hrefs:
                    processed_hrefs.add(current_href)

                    parsed_views, raw_view_text = extract_view_count_ig(link_el)
                    reels_list.append({
                        'link': current_href,
                        'views': parsed_views,
                        'text': raw_view_text
                    })

                    new_links_count += 1  # ✅ นับลิงก์ใหม่จริง

                    # 🔔 ส่งสถานะความคืบหน้า ยอดวิว
                    callback({
                        "type": "view_fetch_progress",
                        "data": {
                            "current": len(reels_list),
                            "total": max_target_clips
                        }
                    })
                    print_to_gui(f"Collected: {current_href} | V: {parsed_views:,} (Raw: '{raw_view_text}'). Total: {len(reels_list)}/{max_target_clips}")

            if new_links_count == 0:
                same_links_count += 1
                if same_links_count >= same_links_threshold:
                    print_to_gui(f"# IG: ไม่พบคลิปใหม่ {same_links_threshold} รอบติด — หยุดเพราะฟีดน่าจะหมดจริง")
                    break
            else:
                same_links_count = 0

            scrolls += 1
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)

        except Exception as e:
            print_to_gui(f"# IG ERROR: {e}")
            break

    total_v = sum(r['views'] for r in reels_list)
    counted_c = len(reels_list)
    print_to_gui(f"--- Finished. Reels: {counted_c}, Views: {total_v:,} ---")

    return total_v, counted_c, reels_list



# (สมมติว่าตัวแปร Path และ XPATH_POST_DATE_IG อยู่ในไฟล์เดียวกัน)

# ฟังก์ชันดึงวันที่โพสต์ Instagram Reels (แทนบล็อกเดิมแบบ 1:1)
def fetch_reel_post_date_ig(reel_url, callback, print_to_gui):
    print_to_gui(f"# DATE_FETCHER (Parallel): Starting for: {reel_url}")
    callback({"type":"update_date_status","data":{"link": reel_url,"status":"⌛ ..."}})

    driver_date = create_chrome_driver(print_to_gui, headless=True)
    if not driver_date:
        callback({"type": "update_date_status", "data": {"link": reel_url, "status": "❌ เปิดเบราว์เซอร์ไม่สำเร็จ"}})
        return "N/A"
    
    final_date_display = "N/A"

    try:
        driver_date.get(reel_url)
        time.sleep(4)

        WebDriverWait(driver_date, 20).until(
            EC.presence_of_element_located((By.XPATH, XPATH_POST_DATE_IG))
        )
        time.sleep(2)
        date_elements = driver_date.find_elements(By.XPATH, XPATH_POST_DATE_IG)

        datetime_attr_val = None
        title_attr_val = None



        if date_elements:
            for de_element in date_elements:
                dt_attr = de_element.get_attribute("datetime")
                if dt_attr:
                    datetime_attr_val = dt_attr
                    break

            if not datetime_attr_val:
                for de_element in date_elements:
                    title_attr_val = de_element.get_attribute("title")
                    if title_attr_val:
                        break
        
        if datetime_attr_val:
            date_obj = dt.fromisoformat(datetime_attr_val.replace("Z", "+00:00"))
            month_map_th = {
                'Jan': 'ม.ค.', 'Feb': 'ก.พ.', 'Mar': 'มี.ค.', 'Apr': 'เม.ย.',
                'May': 'พ.ค.', 'Jun': 'มิ.ย.', 'Jul': 'ก.ค.', 'Aug': 'ส.ค.',
                'Sep': 'ก.ย.', 'Oct': 'ต.ค.', 'Nov': 'พ.ย.', 'Dec': 'ธ.ค.'
            }
            final_date_display = (
                f"{date_obj.day} "
                f"{month_map_th.get(date_obj.strftime('%b'), date_obj.strftime('%b'))} "
                f"{date_obj.year + 543}"
            )
        elif title_attr_val:
            final_date_display = title_attr_val
        else:
            final_date_display = "N/A (No Attr)"

    except TimeoutException:
        final_date_display = "N/A (Timeout)"
    except Exception as e_date_inner:
        final_date_display = f"Error ({type(e_date_inner).__name__})"
    finally:
        if driver_date:
            driver_date.quit()
        callback({"type": "update_date_final", "data": {"link": reel_url, "date": final_date_display}})


# <<< ของเดิม: def start_count_thread(...):
# <<< ของใหม่: เปลี่ยนชื่อเป็น run_ig_scan และรับ parameter เฉพาะที่จำเป็น + callback
def run_ig_scan(url_from_entry, max_clips_str, callback):
    def print_to_gui(message):
        callback({"type": "log", "message": str(message)})

        
    
    try: max_clips = int(max_clips_str)
    except:
        callback({"type": "error", "title": "ข้อมูลไม่ถูกต้อง", "message": "จำนวนคลิปไม่ถูกต้อง"})
        return
    
    driver = None
    # สร้างลิสต์รอไว้ตรงนี้เสมอ เพื่อให้แน่ใจว่ามีตัวแปรนี้อยู่
    date_threads = [] 
    

    
    try:
        driver = create_chrome_driver(print_to_gui)
        #service = Service(ChromeDriverManager().install())
        #options = webdriver.ChromeOptions()
        #options.add_argument("--start-maximized")
        #driver = webdriver.Chrome(service=service, options=options)

        if not ig_login(driver, callback, print_to_gui): return
        callback({"type": "fetch_views_start"})
        
        total_views, counted_clips, collected_reels_list = count_views(driver, url_from_entry, max_clips, print_to_gui, callback)
        
        if not collected_reels_list:
            callback({"type": "status", "message": "⚠️ [IG] ไม่พบข้อมูล Reels", "final": True})
            return
            
        callback({ "type": "initial_data", "data": { "reels": collected_reels_list, "total_views": total_views }})

        # ==================== ✅ จุดที่เพิ่มเข้ามา (เหมือน FB) ✅ ====================
        # หลังจากส่งข้อมูลชุดแรกลงตารางแล้ว ให้ปิดเบราว์เซอร์หลักทันที
        if driver:
            try:
                print_to_gui("# INFO: ปิดเบราว์เซอร์หลักของ IG หลังสแกนวิวเสร็จสิ้น...")
                driver.quit()
                driver = None # ตั้งเป็น None เพื่อไม่ให้ finally พยายามปิดซ้ำ
            except Exception as e:
                print_to_gui(f"# WARNING: ไม่สามารถปิดเบราว์เซอร์หลักของ IG ได้: {e}")
        # =======================================================================

        reels_to_fetch_dates_for = []
        if collected_reels_list:
            list_len = len(collected_reels_list)
            indices_to_fetch = sorted(list(set(list(range(min(4, list_len))) + list(range(max(0, list_len - 4), list_len)))))
            reels_to_fetch_dates_for = [collected_reels_list[i] for i in indices_to_fetch]

        if reels_to_fetch_dates_for:
            callback({"type": "status", "message": f"📅 [IG] เริ่มดึงวันที่ {len(reels_to_fetch_dates_for)} คลิป (แบบ Parallel)..."})

           

            # (ข้างใน if จะไม่มีการสร้าง date_threads = [] ซ้ำแล้ว)
            for i, reel_to_fetch in enumerate(reels_to_fetch_dates_for):
                callback({
                    "type": "ig_date_fetch_progress",
                    "data": {"current": i + 1, "total": len(reels_to_fetch_dates_for)}
                })
                reel_url = reel_to_fetch.get('link')
                if reel_url and reel_url.startswith("http"):
                    date_fetch_thread = threading.Thread(
                        target=fetch_reel_post_date_ig,
                        args=(reel_url, callback, print_to_gui),
                        daemon=True
                    )
                    date_threads.append(date_fetch_thread)
                    date_fetch_thread.start()
                if not threading.main_thread().is_alive(): break
            
            # รอให้ thread ทำงานให้เสร็จ
            print_to_gui(f"# DEBUG_IG: Main thread is now waiting for {len(date_threads)} date-fetching threads to complete...")
            for thread in date_threads:
                thread.join()
            print_to_gui("# DEBUG_IG: All date-fetching threads have completed.")
        
        # --- ✅ แก้ไขบรรทัดนี้ครับ ✅ ---
        callback({"type": "status", "message": f"✅ [IG] สแกนเสร็จสมบูรณ์: {counted_clips} คลิป | รวม {total_views:,} วิว", "final": True})

    except Exception as e:
        import traceback
        print("--- IG ENGINE CRITICAL ERROR ---")
        traceback.print_exc()
        print("------------------------------")
        
        callback({"type": "error", "title": "Error (IG)", "message": str(e)})
        callback({"type": "status", "message": "❌ [IG] เกิดข้อผิดพลาด", "final": True})
    finally:
        
                pass
