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
from pathlib import Path



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
def start_browser(platform: str = "ig", print_to_gui=print, headless: bool = False):
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
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(target_url)

        # ตรวจว่าต้อง initialize pop-ups/locale หรือยัง
        init_flag = Path(profile_path) / ".reels_initialized"
        need_init = not init_flag.exists()

        # ตรวจล็อกอินสั้น ๆ (5 วินาที) ว่ายังล็อกอินอยู่ไหม
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
            # ยังไม่ล็อกอินหรือคุกกี้หมดอายุ → เด้งให้ล็อกอินใหม่
            ctypes.windll.user32.MessageBoxW(
                None,
                f"กรุณาล็อกอินใน {platform.upper()} แล้วกด OK เพื่อดำเนินการต่อ",
                "ReelsCounterPro",
                0
            )
            # รอจนล็อกอินเสร็จ (360 วินาที)
            if platform == 'ig':
                WebDriverWait(driver, 360).until(
                    EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/direct/inbox")]'))
                )
            else:
                WebDriverWait(driver, 360).until(
                    EC.presence_of_element_located((By.XPATH, '//input[@type="search" and contains(@aria-label, "ค้นหา")]'))
                )
            need_init = True

        # ถ้าต้อง initialize (ครั้งแรกหรือหลัง login ใหม่) ให้จัดการ pop-ups & locale
        if need_init:
            if platform == 'fb':
                from fb_engine import handle_generic_popups_fb
                handle_generic_popups_fb(driver, print_to_gui, quick_check_timeout=1.0, skip_if_known_clean=False)
                lang = driver.find_element(By.TAG_NAME, "html").get_attribute("lang")
                if not lang.startswith("th"):
                    driver.get(f"{target_url}?locale=th_TH")
            else:  # ig
                from ig_engine import handle_generic_popups_ig
                handle_generic_popups_ig(driver, print_to_gui, quick_check_timeout=1.0, skip_if_known_clean=False)
            init_flag.write_text("initialized")

        return driver

    except Exception as e:
        print(f"{get_symbol('error')} start_browser ผิดพลาด ({platform}): {e}")
        try:
            if driver:
                driver.quit()
        except:
            pass
        return None


