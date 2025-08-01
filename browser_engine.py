from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import sys

# ================== START: ฟังก์ชันแสดงสัญลักษณ์ ==================
IS_DEV_MODE = False

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
            "manual": "[MANUAL]"
        }
    return symbols.get(symbol_type, "")
# ================== END: ฟังก์ชันแสดงสัญลักษณ์ ==================


# แก้ไขที่ signature ของฟังก์ชัน ให้รับ headless ได้
def start_browser(platform: str = "ig", headless: bool = False):
    driver = None  # ✅ ต้องกำหนดก่อน เพื่อให้ except จับได้แน่

    # ✅ ใช้ path ถาวร: ที่โฟลเดอร์เดียวกับ EXE หรือ .py
    if getattr(sys, 'frozen', False):  # กรณีเป็น EXE
        base_path = os.path.dirname(sys.executable)
    else:  # กรณีรันจาก Python ปกติ
        base_path = os.path.abspath(".")

    if platform == "ig":
        profile_path = os.path.join(base_path, "chrome_profile_ig")
        target_url = "https://www.instagram.com/"
    elif platform == "fb":
        profile_path = os.path.join(base_path, "chrome_profile_fb")
        target_url = "https://www.facebook.com/"
    else:
        raise ValueError("Platform ต้องเป็น 'ig' หรือ 'fb'")

    try:
        print(f"{get_symbol('wait')} เริ่มเปิด Chrome สำหรับ {platform}...")
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={profile_path}")

        # ✅ ป้องกัน crash เมื่อ build EXE
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1024,600")
        #options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-features=RendererCodeIntegrity")

        if headless:
            print(f"{get_symbol('debug')} เปิดโหมด Headless")
            options.add_argument("--headless")

        # ✅ สำคัญ: หา chrome.exe แบบ fallback
        fallback_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for chrome_path in fallback_paths:
            if os.path.exists(chrome_path):
                options.binary_location = chrome_path
                break

        driver = webdriver.Chrome(
           service=Service(ChromeDriverManager().install()),
           options=options
       )
        driver.get(target_url)
        


        # ลดการใช้ time.sleep และเปลี่ยนไปใช้ WebDriverWait
        wait = WebDriverWait(driver, 10)

        # ตรวจสอบว่า login สำเร็จหรือยัง
        print(f"{get_symbol('wait')} รอตรวจสอบสถานะ Login...")
        if platform == 'ig':
            try:
                # รอจนเจอ element ที่ยืนยันว่า login แล้ว (เช่น ปุ่ม inbox)
                wait.until(EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/direct/inbox")]')))
                print(f"{get_symbol('ok')} Login Instagram สำเร็จแล้ว")
            except:
                # ถ้าไม่เจอ แสดงว่ายังไม่ login
                print(f"{get_symbol('manual')} ยังไม่ได้ Login Instagram → กรุณา Login แล้วโปรแกรมจะทำงานต่อ")
                # รอไปเรื่อยๆ จนกว่าจะ login สำเร็จ
                WebDriverWait(driver, 360).until(EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/direct/inbox")]')))
                print(f"{get_symbol('ok')} Login สำเร็จ!")
        elif platform == 'fb':
            try:
                # รอจนเจอ element ที่ยืนยันว่า login แล้ว (เช่น search bar)
                wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="search" and contains(@aria-label, "ค้นหา")]')))
                print(f"{get_symbol('ok')} Login Facebook สำเร็จแล้ว")
            except:
                print(f"{get_symbol('manual')} ยังไม่ได้ Login Facebook → กรุณา Login แล้วโปรแกรมจะทำงานต่อ")
                # รอไปเรื่อยๆ จนกว่าจะ login สำเร็จ
                WebDriverWait(driver, 360).until(EC.presence_of_element_located((By.XPATH, '//input[@type="search" and contains(@aria-label, "ค้นหา")]')))
                print(f"{get_symbol('ok')} Login สำเร็จ!")

        return driver

    except Exception as e:
        print(f"{get_symbol('error')} start_browser ผิดพลาด ({platform}): {e}")
        try:
            driver.quit()
        except:
            pass
        return None
