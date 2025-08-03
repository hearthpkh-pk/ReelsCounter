from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import sys
import ctypes
from selenium.common.exceptions import TimeoutException

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
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1024,600")
        options.add_argument("--disable-features=RendererCodeIntegrity")
        if headless:
            print(f"{get_symbol('debug')} เปิดโหมด Headless")
            options.add_argument("--headless")

        # หา chrome.exe แบบ fallback
        fallback_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for chrome_path in fallback_paths:
            if os.path.exists(chrome_path):
                options.binary_location = chrome_path
                break

        service = Service(ChromeDriverManager().install())
        driver  = webdriver.Chrome(service=service, options=options)
        driver.get(target_url)

        # ตรวจสอบเบื้องต้นว่า Login สำเร็จอยู่แล้วหรือไม่ (timeout สั้น 5 วินาที)
        try:
            if platform == 'ig':
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/direct/inbox")]'))
                )
            else:  # fb
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//input[@type="search" and contains(@aria-label, "ค้นหา")]'))
                )
        except TimeoutException:
            # โปรไฟล์ยังไม่ล็อกอินหรือพัง ให้เด้ง MessageBox ให้ผู้ใช้ล็อกอินใหม่
            ctypes.windll.user32.MessageBoxW(
                None,
                f"กรุณาล็อกอินใน {platform.upper()} แล้วกด OK เพื่อดำเนินการต่อ",
                "ReelsCounterPro",
                0
            )
            # รอจนกว่าจะล็อกอินสำเร็จ (นานสุด 360 วินาที)
            if platform == 'ig':
                WebDriverWait(driver, 360).until(
                    EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/direct/inbox")]'))
                )
            else:
                WebDriverWait(driver, 360).until(
                    EC.presence_of_element_located((By.XPATH, '//input[@type="search" and contains(@aria-label, "ค้นหา")]'))
                )

        return driver

    except Exception as e:
        print(f"{get_symbol('error')} start_browser ผิดพลาด ({platform}): {e}")
        try:
            if driver:
                driver.quit()
        except:
            pass
        return None

