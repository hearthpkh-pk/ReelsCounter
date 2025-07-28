import webview
import threading
import json
import webbrowser
import os
import urllib.request
import tempfile
import subprocess
import sys
import fb_engine
import ig_engine
import fb_video_engine
import ctypes
import sys



try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError, OSError):
    pass

APP_VERSION = "1.3.2"
IS_POST_INSTALL = len(sys.argv) > 1 and sys.argv[1] == '/postinstall'

window = None

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class Api:
    def __init__(self):
        self.window = None

    def python_callback_to_js(self, response_data):
        if self.window:
            js_response_str = json.dumps(response_data, ensure_ascii=False)
            self.window.evaluate_js(f'handle_python_callback({js_response_str})')

    def start_scan(self, platform, data):
        print(f"API: ได้รับคำสั่ง start_scan สำหรับ '{platform}' พร้อมข้อมูล: {data}".encode('utf-8', errors='replace').decode())

        target_function = None
        args = ()

        if platform == 'fb':
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
                target_function = fb_engine.run_fb_scan
                args = (
                    data.get('reelsUrl'),
                    data.get('profileUrl'),
                    data.get('clipCount'),
                    self.python_callback_to_js
                )

        elif platform == 'ig':
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
        if url and url.startswith('http'):
            print(f"API: กำลังเปิดลิงก์ภายนอก: {url}".encode('utf-8', errors='replace').decode())
            webbrowser.open_new_tab(url)

    def start_manual_date_fetch(self, platform, data):
        print(f"API: ได้รับคำสั่ง Manual Date Fetch สำหรับ '{platform}' Data: {data}".encode('utf-8', errors='replace').decode())

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
        url = "https://github.com/Babydunx1/reels-counter-update/blob/main/docs/manual.md"
        print(f"API: กำลังเปิดเอกสารโปรแกรมที่ {url}".encode('utf-8', errors='replace').decode())
        webbrowser.open_new_tab(url)

    def log_from_js(self, msg):
        print(f"[JS LOG] {msg}".encode('utf-8', errors='replace').decode())

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
            print(f"Error fetching update info: {e}".encode('utf-8', errors='replace').decode())
            return {"error": str(e), "current_version": APP_VERSION, "is_post_install": IS_POST_INSTALL}

    def run_repair(self):
        info = self.get_update_info()
        download_url = info.get('download_url')
        if not download_url:
            return {'error': 'ไม่พบ download_url'}
        return self.run_updater(download_url)

    def run_updater(self, download_url):
        def task():
            try:
                if getattr(sys, 'frozen', False):
                    install_dir = os.path.dirname(sys.executable)
                else:
                    install_dir = os.path.dirname(os.path.abspath(__file__))

                update_dir = os.path.join(install_dir, '_internal', 'updates')
                os.makedirs(update_dir, exist_ok=True)

                updater_path = os.path.join(update_dir, 'ReelsCounterUpdater.exe')

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

                if self.window:
                    self.window.evaluate_js(
                        'document.getElementById("updateStatus").innerText ='
                        ' "ดาวน์โหลดสำเร็จ! กำลังติดตั้ง..."'
                    )

                subprocess.Popen(
                    [updater_path, '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART'],
                    cwd=update_dir,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

                import time; time.sleep(3)
                os._exit(0)

            except Exception as e:
                print(f"run_updater error: {e}".encode('utf-8', errors='replace').decode())
                if self.window:
                    msg = str(e).replace("'", "\\'")
                    self.window.evaluate_js(
                        f"alert('เกิดข้อผิดพลาดระหว่างดาวน์โหลดอัปเดต: {msg}')"
                    )

        threading.Thread(target=task, daemon=True).start()
        return {'status': 'download_started'}

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
    
    

