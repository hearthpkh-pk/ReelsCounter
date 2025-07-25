import webview
import threading
import json
import webbrowser
import os
import urllib.request
import tempfile
import subprocess
import sys
# Import engine ที่เราแยกไฟล์ไว้
import fb_engine
import ig_engine
import fb_video_engine
import ctypes

# ทำให้โปรแกรม DPI Aware (เพื่อให้ขนาดหน้าต่างถูกต้องบน Windows)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError, OSError):
    pass # ทำงานเฉพาะบน Windows ที่รองรับ


# ✅ 1. กำหนดเวอร์ชันปัจจุบันของโปรแกรม
APP_VERSION = "1.3"

# ✅ 2. ตัวรับสัญญาณ "เพิ่งติดตั้งเสร็จ"
IS_POST_INSTALL = len(sys.argv) > 1 and sys.argv[1] == '/postinstall'

window = None

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)



class Api:
    """
    คลาส 'สะพาน' ระหว่าง Python (Backend) และ JavaScript (Frontend)
    """
    def __init__(self):
        self.window = None

    def python_callback_to_js(self, response_data):
        """
        Callback เดียวสำหรับส่งข้อมูลกลับไปที่ JS ผ่าน handle_python_callback(...)
        """
        if self.window:
            js_response_str = json.dumps(response_data)
            self.window.evaluate_js(f'handle_python_callback({js_response_str})')

    def start_scan(self, platform, data):
        print(f"API: ได้รับคำสั่ง start_scan สำหรับ '{platform}' พร้อมข้อมูล: {data}")

        target_function = None
        args = ()

        if platform == 'fb':
            # อ่านโหมด (default เป็น 'reel' ถ้า client เก่าไม่ได้ส่งมา)
            mode = data.get('mode', 'reel')
            if mode == 'video':
                target_function = fb_video_engine.run_fb_video_scan
                args = (
                    data.get('reelsUrl'),
                    int(data.get('clipCount')),
                    self.python_callback_to_js,
                    lambda msg: self.python_callback_to_js({"type": "log", "message": str(msg)})
                )
            else:
                # branch เดิมสำหรับ Facebook Reels
                target_function = fb_engine.run_fb_scan
                args = (
                    data.get('reelsUrl'),
                    data.get('profileUrl'),
                    data.get('clipCount'),
                    self.python_callback_to_js
                )

        elif platform == 'ig':
            # ไม่เปลี่ยนแปลง IG ของเดิม
            target_function = ig_engine.run_ig_scan
            args = (
                data.get('reelsUrl'),
                data.get('clipCount'),
                self.python_callback_to_js
            )

        if target_function:
            threading.Thread(target=target_function, args=args, daemon=True).start()
        else:
            self.python_callback_to_js({
                "type": "error",
                "title": "Error",
                "message": f"Platform '{platform}' ไม่รู้จัก"
            })



    def open_external_link(self, url):
        """
        API สำหรับให้ JS เรียกใช้เพื่อเปิดลิงก์ในเบราว์เซอร์หลัก (สำหรับ dblclick ตาราง)
        """
        if url and url.startswith('http'):
            print(f"API: กำลังเปิดลิงก์ภายนอก: {url}")
            webbrowser.open_new_tab(url)

    def start_manual_date_fetch(self, platform, data):
        """
        API สำหรับเริ่มดึงวันที่ของ URL ที่ระบุแบบ Manual
        """
        print(f"API: ได้รับคำสั่ง Manual Date Fetch สำหรับ '{platform}' Data: {data}")

        target_function = None
        args = ()

        if platform == 'ig':
            target_function = ig_engine.fetch_reel_post_date_ig
            args = (
                data.get('reelUrl'),
                self.python_callback_to_js,
                lambda msg: self.python_callback_to_js({"type": "log", "message": str(msg)})
            )
        elif platform == 'fb':
            target_function = fb_engine.run_manual_date_fetch
            args = (
                data.get('profileUrl'),
                data.get('reelUrl'),
                data.get('reelIndex'),
                self.python_callback_to_js
            )

        if target_function:
            threading.Thread(target=target_function, args=args, daemon=True).start()
        else:
            self.python_callback_to_js({
                "type": "error",
                "title": "Error",
                "message": f"Manual fetch ไม่รองรับ platform '{platform}'"
            })

    def showDocs(self):
        """
        เปิดหน้า GitHub Manual.md ในเบราเซอร์หลัก
        """
        url = "https://github.com/Babydunx1/reels-counter-update/blob/main/docs/manual.md"
        print(f"API: กำลังเปิดเอกสารโปรแกรมที่ {url}")
        webbrowser.open_new_tab(url)
    
        

    # ------ เพิ่มฟังก์ชันนี้ ------
    def log_from_js(self, msg):
        """
        ฟังก์ชันนี้ให้ JS เรียกใช้งาน เพื่อ print log กลับมาที่ Python Console
        """
        print(f"[JS LOG] {msg}")
   

     # ✅ 3. ฟังก์ชันสำหรับเช็คอัปเดต
    def get_update_info(self):
        url = "https://raw.githubusercontent.com/Babydunx1/reels-counter-update/main/app_version.json?" + str(os.urandom(8).hex())
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read().decode())
            return {
                "version": data["version"],
                "date": data.get("date", ""),
                "changelog": data.get("changelog", []),
                "download_url": data["download_url"],
                "current_version": APP_VERSION,
                "is_post_install": IS_POST_INSTALL
            }
        except Exception as e:
            print(f"Error fetching update info: {e}")
            return {"error": str(e), "current_version": APP_VERSION, "is_post_install": IS_POST_INSTALL}
        
    
    def run_repair(self):
        """
        ให้ JS สั่งซ่อมแซม โดยดาวน์โหลด installer เวอร์ชันล่าสุด
        แล้วรันแบบ Silent (เหมือน auto-update)
        """
        # 1) ดึง URL ของ installer เวอร์ชันล่าสุด
        info = self.get_update_info()
        download_url = info.get('download_url')
        if not download_url:
            return {'error': 'ไม่พบ download_url'}

        # 2) เรียกโค้ด run_updater เพื่อดาวน์โหลด+ติดตั้ง
        return self.run_updater(download_url)



        

    # ── ฟังก์ชันใหม่ให้ JS เรียกเพื่อดาวน์โหลด+ติดตั้ง ──
    

     # ✅ 4. ฟังก์ชันสำหรับรันตัวอัปเดต
    def run_updater(self, download_url):
        def task():
            try:
                # 1. หาโฟลเดอร์ติดตั้ง ของ exe จริง ๆ
                if getattr(sys, 'frozen', False):
                    # รันจาก PyInstaller-packed exe
                    install_dir = os.path.dirname(sys.executable)
                else:
                    # รันในโค้ด Python ปกติ
                    install_dir = os.path.dirname(os.path.abspath(__file__))

                # 2. เตรียมโฟลเดอร์อัพเดต
                update_dir = os.path.join(install_dir, '_internal', 'updates')
                os.makedirs(update_dir, exist_ok=True)

                # 3. ตั้งชื่อไฟล์คงที่สำหรับ updater
                updater_path = os.path.join(update_dir, 'ReelsCounterUpdater.exe')

                # 4. ดาวน์โหลดไปเขียนทับ updater_path
                with urllib.request.urlopen(download_url, timeout=600) as resp, \
                    open(updater_path, 'wb') as f:
                    total_size = int(resp.getheader('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk: break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size and self.window:
                            percent = int(downloaded / total_size * 100)
                            self.window.evaluate_js(f'updateDownloadProgress({percent})')

                # 5. แจ้ง UI ว่าโหลดเสร็จ
                if self.window:
                    self.window.evaluate_js(
                        'document.getElementById("updateStatus").innerText ='
                        ' "ดาวน์โหลดสำเร็จ! กำลังติดตั้ง..."'
                    )

                # 6. รัน installer ของเรา
                subprocess.Popen(
                    [updater_path, '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART'],
                    cwd=update_dir,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

                # 7. เดี๋ยวรอก่อน แล้วปิดโปรเซสนี้
                import time; time.sleep(3)
                os._exit(0)

            except Exception as e:
                print(f"run_updater error: {e}")
                if self.window:
                    msg = str(e).replace("'", "\\'")
                    self.window.evaluate_js(
                        f"alert('เกิดข้อผิดพลาดระหว่างดาวน์โหลดอัปเดต: {msg}')"
                    )

        threading.Thread(target=task, daemon=True).start()
        return {'status': 'download_started'}


    # ... ฟังก์ชัน API อื่น ๆ เช่น start_scan, open_external_link ตามเดิม ...

    # --------------------------------------------------    


if __name__ == '__main__':
    api = Api()
    window = webview.create_window(
        f'Reels Counter Pro {APP_VERSION}',
        resource_path('index.html'),
        js_api=api,
        width=1550,
        height=950,
        min_size=(1250, 700)
    )
    api.window = window
    webview.start(debug=True) #True #False
    

