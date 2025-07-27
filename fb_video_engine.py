# fb_video_engine.py

import re
import time
import json
import datetime
import queue
import concurrent.futures
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException



# ✅ 1. Import ฟังก์ชันที่คุณสร้างไว้จาก fb_engine.py
from fb_engine import create_chrome_driver, fb_login, get_reel_date_via_json_driver, get_symbol
from fb_engine import check_and_prepare_facebook_language, auto_change_language_to_thai

def safe_utf8(text):
    try:
        return str(text).encode('utf-8', errors='replace').decode('utf-8')
    except Exception:
        return "[Encode Error]"


def parse_views_to_int(view_str: str) -> int:
    if not view_str or not isinstance(view_str, str): return 0
    text = view_str.lower().strip().replace(',', '')
    try:
        num_match = re.search(r'[\d\.]+', text)
        if not num_match: return 0
        num = float(num_match.group(0))
        if 'm' in text or 'ล้าน' in text: return int(num * 1000000)
        if 'แสน' in text: return int(num * 100000)
        if 'หมื่น' in text: return int(num * 10000)
        if 'k' in text or 'พัน' in text: return int(num * 1000)
        return int(num)
    except: return 0

# ✅ 2. สร้าง "ลูกมือ" (Worker) ที่จะทำงานในแต่ละ Thread
# ✅ 1. แก้ไข Worker ให้ "ยืม" และ "คืน" Driver จาก Pool
def get_date_worker(video_url: str, driver_pool: queue.Queue):
    """
    ฟังก์ชันนี้จะ "ยืม" Driver จาก Pool มาใช้งาน และ "คืน" เมื่อเสร็จ
    """
    worker_driver = None
    try:
        # ยืม Driver จาก Pool, ถ้า Pool ว่างจะรอจนกว่าจะมี Driver ว่าง
        worker_driver = driver_pool.get()
        
        dt_obj = get_reel_date_via_json_driver(worker_driver, video_url)
        th_months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
        formatted_date = f"{dt_obj.day} {th_months[dt_obj.month - 1]} {dt_obj.year + 543}"
        return video_url, formatted_date
    except Exception:
        return video_url, "N/A"
    finally:
        # คืน Driver กลับเข้า Pool เสมอ ไม่ว่าจะสำเร็จหรือพลาด
        if worker_driver:
            driver_pool.put(worker_driver)

def run_fb_video_scan(page_url: str, max_count: int, callback_func: callable, log_func: callable):
    driver = None
    driver_pool_list = [] 
    try:
        # --- ส่วนที่ 1: ดึงยอดวิว (ใช้ Driver หลักที่ล็อกอิน) ---
        log_func(safe_utf8("กำลังเริ่มต้น WebDriver หลัก..."))
        driver = create_chrome_driver(headless=False)
        if not driver:
            log_func(safe_utf8(f"{get_symbol('error')} ไม่สามารถสร้าง Chrome Driver ได้"))
            return

        log_func(safe_utf8("กำลังล็อกอิน..."))
        fb_login(driver, lambda _: None, log_func)

        # ================== บล็อกที่แก้ไข ==================
        # 👇 ลบเครื่องหมาย # ทั้ง 5 บรรทัดนี้ออกได้เลย
        
        log_func(safe_utf8("กำลังตรวจสอบและตั้งค่าภาษา Facebook..."))
        check_and_prepare_facebook_language(
            driver,
            url="https://www.facebook.com/",
            js_callback=lambda data: log_func(data.get("message", safe_utf8("")))  # ส่ง log จาก callback ไปที่ log_func
        )
        # ================== จบบล็อกที่แก้ไข ==================
        log_func(safe_utf8("✓ ล็อกอินสำเร็จ"))
        
        log_func(safe_utf8(f"{get_symbol('scan')} กำลังไปยังหน้าเพจ: {page_url}"))
        driver.get(page_url)
        header = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//span[text()='วิดีโอ']")))
        section = header.find_element(By.XPATH, "../following-sibling::div")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", section)
        time.sleep(2)
        
        all_video_data = []
        seen_urls = set()
        last_height = driver.execute_script("return document.body.scrollHeight")
        patience, patience_counter = 3, 0
        
        log_func(safe_utf8(f"{get_symbol('start')} เริ่มการสแกนยอดวิว..."))
        while len(all_video_data) < max_count:
            current_anchors = section.find_elements(By.XPATH, ".//a[contains(@href,'/videos/') and .//img]")
            for anchor in current_anchors:
                if len(all_video_data) >= max_count: break
                try:
                    href = anchor.get_attribute('href')
                    if href and href not in seen_urls:
                        seen_urls.add(href)
                        card = anchor.find_element(By.XPATH, "ancestor::div[contains(@class,'x1n2onr6')][1]")
                        views_text = "0"
                        try:
                            info_divs = card.find_elements(By.XPATH, ".//div[contains(@class,'xt0e3qv')]")
                            for d in info_divs:
                                txt = d.text.strip()
                                if 'ครั้ง' in txt:
                                    m = re.search(r"([\d\.,]+\s*(?:K|M|พัน|หมื่น|แสน|ล้าน)?)", txt)
                                    if m: views_text = m.group(1).strip()
                                    break
                        except: pass
                        numeric_views = parse_views_to_int(views_text)
                        all_video_data.append({"link": href, "views": numeric_views})
                        callback_func({"type": "view_fetch_progress", "data": {"current": len(all_video_data), "total": max_count, "link": href, "views": numeric_views}})
                except StaleElementReferenceException: continue
            if len(all_video_data) >= max_count: break
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                patience_counter += 1
                if patience_counter >= patience: break
            else: patience_counter = 0
            last_height = new_height
            
        if driver:
            driver.quit()
            driver = None
            log_func(safe_utf8("✓ ปิด Driver หลักแล้ว"))

        # --- ส่วนที่ 2: ดึงวันที่แบบคู่ขนาน (ไม่ล็อกอิน) ---
        log_func(safe_utf8("✓ สแกนยอดวิวครบ, เริ่มดึงวันที่แบบไม่ล็อกอิน..."))
        
        # ✅ 1. สร้าง list ของ index ที่จะทำการดึงข้อมูล
        indices_to_process = []
        if len(all_video_data) > 20:
            indices_to_process.extend(range(10)) # index 0-9
            indices_to_process.extend(range(len(all_video_data) - 10, len(all_video_data))) # 10 index สุดท้าย
        else:
            indices_to_process = list(range(len(all_video_data)))
        
        # ทำให้ index ไม่ซ้ำกัน (กรณีมีน้อยกว่า 20) และเรียงลำดับ
        indices_to_process = sorted(list(set(indices_to_process)))

        # ✅ 2. เลือก URL เป้าหมายจาก index ที่เราสร้างไว้
        urls_to_fetch = [all_video_data[i]['link'] for i in indices_to_process]

        # ✅ 3. แทรก Callback สั่งให้ JS แสดง Spinner ตรงนี้!
        log_func(safe_utf8(f"กำลังส่งสัญญาณให้ UI แสดง Spinner สำหรับ {len(indices_to_process)} รายการ..."))
        callback_func({
            "type": "auto_date_fetch_start",
            "data": { "indices": indices_to_process }
        })
        time.sleep(0.5) # หน่วงเวลาเล็กน้อยเพื่อให้ UI มีเวลาวาด Spinner

        log_func(safe_utf8(f"กำลังดึงวันที่ {len(urls_to_fetch)} คลิป ด้วย 10 Threads (ใช้ Driver Pool)..."))
        
        # สร้าง Driver Pool
        pool_size = 6
        driver_pool = queue.Queue()
        driver_pool_list = []
        for _ in range(pool_size):
            d = create_chrome_driver(headless=True)
            if d:
                driver_pool_list.append(d)
                driver_pool.put(d)
        
        # ใช้ ThreadPoolExecutor จัดการงาน (ส่วนนี้ทำงานได้ดีอยู่แล้ว)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(get_date_worker, url, driver_pool): url for url in urls_to_fetch}
            for future in concurrent.futures.as_completed(future_to_url):
                url, date = future.result()
                if date:
                    callback_func({"type": "update_date_status", "data": {"link": url, "date": date}})

        # --- ส่วนจบการทำงาน (เหมือนเดิม) ---
        total_views = sum(item['views'] for item in all_video_data)
        final_message = safe_utf8(f"{get_symbol('ok')} [FB] สแกนเสร็จสมบูรณ์: {len(all_video_data)} คลิป | รวม {total_views:,} วิว")
        log_func(final_message)
        callback_func({"type": "update_date_final", "data": {}})
        time.sleep(0.1)
        callback_func({"type": "status", "message": "พร้อมทำงาน", "final": True})

    except Exception as e:
        log_func(safe_utf8(f"เกิดข้อผิดพลาดร้ายแรง: {e}"))
        callback_func({"type": "error", "title": safe_utf8("Video Scan Error"), "message": safe_utf8(f"{e}")})
    finally:
        if driver:
            driver.quit()
        # ปิด Driver ทุกตัวใน Pool
        log_func(safe_utf8("กำลังปิด Driver ทั้งหมดใน Pool..."))
        for d_in_pool in driver_pool_list:
            try:
                d_in_pool.quit()
            except:
                pass
        log_func(safe_utf8("ปิด WebDriver ทั้งหมดแล้ว"))