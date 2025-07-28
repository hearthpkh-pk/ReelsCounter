# fb_video_engine.py

import re
import time
import json
from datetime import datetime, timedelta, timezone
import queue
import concurrent.futures
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import threading


# ✅ 1. Import ฟังก์ชันที่คุณสร้างไว้จาก fb_engine.py
from fb_engine import create_chrome_driver, fb_login, get_reel_date_via_json_driver, get_symbol
from fb_engine import check_and_prepare_facebook_language, auto_change_language_to_thai
from fb_engine import extract_reel_id_from_url, clean_url 
# 1. import fb_engine มาทั้งโมดูล
import fb_engine

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
# ✅ 2. สร้าง "ลูกมือ" (Worker) ใหม่ ที่จะเปิดเบราว์เซอร์ของตัวเอง
# เปลี่ยนชื่อฟังก์ชันเป็น get_date_with_dedicated_browser_return
def get_date_with_dedicated_browser_return(video_url, video_id, log_func):
    """
    ฟังก์ชันนี้จะ return tuple (video_id, video_url, formatted_date)
    """
    driver = None
    try:
        # ... (ส่วนสร้าง driver และหา creation_timestamp เหมือนเดิมเป๊ะ) ...
        driver = fb_engine.create_chrome_driver(headless=True)
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
                        ts = fb_engine.find_creation_time(data)
                        if ts:
                            creation_timestamp = ts
                            log_func(safe_utf8(f"  [Thread ID: {video_id}] เจอ creation_time ในรอบที่ {attempt + 1}"))
                            break
                except Exception:
                    continue
            
            if creation_timestamp:
                break

        if not creation_timestamp:
            return video_id, video_url, "N/A"

        if creation_timestamp > 1e12:
            creation_timestamp //= 1000
        
        dt_utc = datetime.fromtimestamp(creation_timestamp, timezone.utc)
        dt_bkk = dt_utc + timedelta(hours=7)
        
        th_months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
        formatted_date = f"{dt_bkk.day} {th_months[dt_bkk.month - 1]} {dt_bkk.year + 543}"
        
        log_func(safe_utf8(f"  [Thread ID: {video_id}] ดึงข้อมูลสำเร็จ: {formatted_date}"))
        return video_id, video_url, formatted_date

    except Exception as e:
        log_func(safe_utf8(f"  [Thread ID: {video_id}] ดึงข้อมูลล้มเหลว: {e}"))
        return video_id, video_url, "N/A"
    finally:
        if driver:
            driver.quit()

      
def run_fb_video_scan(page_url: str, max_count: int, callback_func: callable, log_func: callable):
    # --- ส่วนที่ 1: ปิด Standby Driver เก่า ---
    if fb_engine.standby_driver_for_dates:
        try:
            log_func(safe_utf8(f"{get_symbol('debug')} Closing previous standby driver..."))
            fb_engine.standby_driver_for_dates.quit()
            callback_func({"type": "driver_status", "mode": "none"})
        except Exception as e:
            log_func(safe_utf8(f"{get_symbol('warn')} Failed to close leftover standby driver: {e}"))
    fb_engine.standby_driver_for_dates = None
    
    driver = None
    driver_pool_list = [] 
    try:
        # --- ส่วนที่ 2: สร้าง Standby Driver ใหม่ใน Thread แยก ---
        def setup_date_driver():
            log_func(safe_utf8("⚙️ Creating new standby driver for Video mode..."))
            fb_engine.standby_driver_for_dates = create_chrome_driver(headless=True)
            if fb_engine.standby_driver_for_dates:
                fb_login(fb_engine.standby_driver_for_dates, lambda _: None, log_func)
                fb_engine.standby_driver_for_dates.get(page_url)
                log_func(safe_utf8(f"{get_symbol('ok')} Standby browser for Video mode is ready."))
                callback_func({"type": "driver_status", "mode": "manual-ready"})

        threading.Thread(target=setup_date_driver, daemon=True).start()

        # --- ส่วนที่ 3: การทำงานของ Driver หลัก (โค้ดเดิมของคุณ) ---
        log_func(safe_utf8("กำลังเริ่มต้น WebDriver หลัก..."))
        driver = create_chrome_driver(headless=False)
        if not driver:
            log_func(safe_utf8(f"{get_symbol('error')} ไม่สามารถสร้าง Chrome Driver ได้"))
            return
        
        
        log_func(safe_utf8("กำลังล็อกอิน..."))
        fb_login(driver, lambda _: None, log_func)

        log_func(safe_utf8("กำลังตรวจสอบและตั้งค่าภาษา Facebook..."))
        check_and_prepare_facebook_language(
            driver,
            url="https://www.facebook.com/",
            js_callback=lambda data: log_func(data.get("message", safe_utf8("")))
        )
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
        
        callback_func({"type": "driver_status", "mode": "auto"})
        log_func(safe_utf8(f"{get_symbol('start')} เริ่มการสแกนยอดวิว..."))
        while len(all_video_data) < max_count:
            current_anchors = section.find_elements(By.XPATH, ".//a[contains(@href,'/videos/') and .//img]")
            for anchor in current_anchors:
                if len(all_video_data) >= max_count: break
                try:
                    href = anchor.get_attribute('href')
                    if href and href not in seen_urls:
                        cleaned_href = clean_url(href) 
                        reel_id = extract_reel_id_from_url(cleaned_href, log_func)
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
                        
                        all_video_data.append({
                            "link": cleaned_href,
                            "views": numeric_views,
                            "id": reel_id  # ✅ เพิ่ม field นี้
                        })
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

        # ✅ 1. สร้าง list ของ index: หน้า 4 หลัง 4 (เหมือนเดิม)
        indices_to_process = []
        if len(all_video_data) > 12:
            indices_to_process.extend(range(6))
            indices_to_process.extend(range(len(all_video_data) - 6, len(all_video_data)))
        else:
            indices_to_process = list(range(len(all_video_data)))

        indices_to_process = sorted(list(set(indices_to_process)))

        # ✅ 2. เตรียมข้อมูล (เหมือนเดิม)
        urls_to_fetch = [all_video_data[i]['link'] for i in indices_to_process]
        ids_to_fetch = [all_video_data[i]['id'] for i in indices_to_process]

        # ✅ 3. Spinner UI (เหมือนเดิม)
        log_func(safe_utf8(f"กำลังส่งสัญญาณให้ UI แสดง Spinner สำหรับ {len(indices_to_process)} รายการ..."))
        callback_func({
            "type": "auto_date_fetch_start",
            "data": { "indices": indices_to_process }
        })
        time.sleep(0.5)

        # ✅ 4. รัน Thread พร้อมกันทีเดียว (แผน A: หน่วยจู่โจมเร็ว)
        log_func(safe_utf8(f"▶ เริ่มดึงวันที่ (รอบแรก): รวม {len(indices_to_process)} รายการ"))
        
        failed_tasks = []

        # ใช้ get_date_with_dedicated_browser_return ที่ return ค่าออกมา
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_data = {
                executor.submit(get_date_with_dedicated_browser_return, url, video_id, log_func): (url, video_id, indices_to_process[i])
                for i, (url, video_id) in enumerate(zip(urls_to_fetch, ids_to_fetch))
            }

            # *** จุดแก้ไขสำคัญ: รอจนกว่าจะประมวลผล future ครบทั้งหมด ***
            for future in concurrent.futures.as_completed(future_to_data):
                url, video_id, index = future_to_data[future]
                try:
                    _vid, _url, date = future.result()
                    
                    if date == "N/A":
                        log_func(safe_utf8(f"  [รอบแรก] ID: {video_id} ได้ผล N/A, ส่งต่อให้ผู้เชี่ยวชาญ"))
                        failed_tasks.append({'link': _url, 'id': _vid, 'index': index})
                    else:
                        callback_func({
                            "type": "update_date_status",
                            "data": {"id": _vid, "link": _url, "date": date}
                        })
                except Exception as e:
                    log_func(safe_utf8(f"⚠️ ดึงวันที่ล้มเหลว (รอบแรก): {video_id} | {str(e)}"))
                    failed_tasks.append({'link': url, 'id': video_id, 'index': index})

        # ✅ 5. แผน B: เรียกใช้ "ผู้เชี่ยวชาญ" พร้อม "แผนที่" ที่ถูกต้อง
        if failed_tasks:
            log_func(safe_utf8(f"▶ เริ่มเก็บตกงานที่พลาด {len(failed_tasks)} รายการ โดยผู้เชี่ยวชาญ..."))
            
            sorted_failed_tasks = sorted(failed_tasks, key=lambda x: x['index'])

            for task in sorted_failed_tasks:
                log_func(safe_utf8(f"  [ผู้เชี่ยวชาญ] กำลังทำงานกับ ID: {task['id']}"))
                
                # *** จุดแก้ไขสำคัญที่สุด: เพิ่ม profile_url=page_url เข้าไป ***
                fb_engine.run_manual_date_fetch(
                    profile_url=page_url, # page_url คือ profile_url สำหรับโหมดวิดีโอ
                    reel_url=task['link'],
                    reel_index=task['index'],
                    callback=callback_func
                )
                time.sleep(1) 
        
        # --- ส่วนจบการทำงาน (เหมือนเดิม) ---
        total_views = sum(item['views'] for item in all_video_data)
        final_message = safe_utf8(f"✅ [FB] สแกนเสร็จสมบูรณ์: {len(all_video_data)} คลิป | รวม {total_views:,} วิว")
        log_func(final_message)
        
        callback_func({"type": "update_date_final", "data": {}})
        time.sleep(0.1)
        
        callback_func({"type": "status", "message": final_message, "final": True})

        log_func(safe_utf8("Checking final standby driver state (before cleanup)..."))
        try:
            if fb_engine.standby_driver_for_dates and fb_engine.standby_driver_for_dates.session_id:
                callback_func({"type": "driver_status", "mode": "manual-ready"})
            else:
                callback_func({"type": "driver_status", "mode": "none"})
        except Exception:
            callback_func({"type": "driver_status", "mode": "none"})


        

        
        # --- ส่วนจบการทำงาน (ฉบับปรับปรุง) ---
        total_views = sum(item['views'] for item in all_video_data)
        final_message = safe_utf8(f"✅ [FB] สแกนเสร็จสมบูรณ์: {len(all_video_data)} คลิป | รวม {total_views:,} วิว")
        log_func(final_message)
        callback_func({"type": "update_date_final", "data": {}})
        time.sleep(0.1)
        callback_func({"type": "status", "message": "พร้อมทำงาน", "final": True})
        
        # 1. ส่งข้อความ "สแกนเสร็จ" ไปที่ UI status หลัก
        callback_func({"type": "status", "message": final_message, "final": True})

        # 2. ตรวจสอบสถานะ Standby Driver และคืนไฟสถานะเป็นคำสั่งสุดท้ายก่อนทำความสะอาด
        log_func(safe_utf8("Checking final standby driver state (before cleanup)..."))
        try:
            if fb_engine.standby_driver_for_dates and fb_engine.standby_driver_for_dates.session_id:
                # ถ้ายังอยู่ ให้สั่งเปิดไฟเขียว
                callback_func({"type": "driver_status", "mode": "manual-ready"})
            else:
                # ถ้าไม่อยู่ ให้สั่งเปิดไฟแดง
                callback_func({"type": "driver_status", "mode": "none"})
        except Exception:
            callback_func({"type": "driver_status", "mode": "none"})

    except Exception as e:
        log_func(safe_utf8(f"เกิดข้อผิดพลาดร้ายแรง: {e}"))
        callback_func({"type": "error", "title": safe_utf8("Video Scan Error"), "message": safe_utf8(f"{e}")})
    finally:
        # เหลือไว้แค่ส่วนทำความสะอาด Driver เท่านั้น
        if driver:
            try: 
                driver.quit()
            except Exception: 
                pass
        
        log_func(safe_utf8("กำลังปิด Driver ทั้งหมดใน Pool..."))
        for d_in_pool in driver_pool_list:
            try: 
                d_in_pool.quit()
            except Exception: 
                pass
        
        log_func(safe_utf8("ปิด WebDriver ทั้งหมดแล้ว"))