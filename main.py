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
import time

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError, OSError):
    pass

APP_VERSION = "1.4.2"
IS_POST_INSTALL = len(sys.argv) > 1 and sys.argv[1] == '/postinstall'

window = None

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def open_in_browser(url):
    if getattr(sys, 'frozen', False):  # ถ้ารันจาก .exe
        # เปิดแบบไม่ให้ console โผล่
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(['cmd', '/c', 'start', '', url], startupinfo=startupinfo)
    else:
        webbrowser.open(url)


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
        if not (url and url.startswith('http')):
            return

        print(f"API: เปิดลิงก์ด้วย UI แบบ Mini-Bar: {url}")

        spinner_html = """
        <html><head><style>
            body { margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background: #ffffff; }
            .spinner { border: 6px solid #f3f3f3; border-top: 6px solid #3498db; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style></head><body><div class="spinner"></div></body></html>
        """
        
        # --- ✅ แก้ไข: JS Payload สำหรับสร้าง Mini-Bar ที่กดขยายได้ ---
        js_payload = f"""
        try {{
            if (!document.getElementById('rcp-container')) {{
                
                // 1. สร้าง HTML: ประกอบด้วยตัว Container, ปุ่มไอคอน, และช่อง Input
                const rcpContainer = document.createElement('div');
                rcpContainer.id = 'rcp-container';
                rcpContainer.innerHTML = `
                    <div id="rcp-toggle-btn">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10.5858 13.4142L7.75736 16.2426C5.63604 18.364 3.51472 18.364 1.3934 16.2426C-0.727922 14.1213 -0.727922 11.8787 1.3934 9.75736L4.22183 6.92893C6.34315 4.80761 8.46447 4.80761 10.5858 6.92893L11.2929 7.63604" stroke="#333" stroke-width="2" stroke-linecap="round"/><path d="M13.4142 10.5858L16.2426 7.75736C18.364 5.63604 20.4853 5.63604 22.6066 7.75736C24.7279 9.87868 24.7279 12.1213 22.6066 14.2426L19.7782 17.0711C17.6569 19.1924 15.5355 19.1924 13.4142 17.0711L12.7071 16.364" stroke="#333" stroke-width="2" stroke-linecap="round"/></svg>
                    </div>
                    <input id="rcp-url-input" type="text" value="{url}" readonly />
                `;
                document.body.appendChild(rcpContainer);

                // 2. สร้าง CSS: กำหนดสไตล์ของปุ่มปกติและตอนที่ขยายแล้ว
                const style = document.createElement('style');
                style.textContent = `
                    #rcp-container {{
                        position: fixed; z-index: 99999999;
                        /* State 1: ปุ่มกลมๆ (ค่าเริ่มต้น) */
                        bottom: 20px; right: 20px; width: 55px; height: 55px;
                        background: #f0f0f0; border-radius: 50%;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                        cursor: pointer; transition: all 0.3s ease-in-out;
                        display: flex; justify-content: center; align-items: center;
                    }}
                    #rcp-container.rcp-expanded {{
                        /* State 2: แถบยาว (เมื่อถูกคลิก) */
                        width: 100%; height: auto; bottom: 0; right: 0;
                        border-radius: 0; padding: 15px 10px;
                        border-top: 1px solid #c0c0c0;
                        background: linear-gradient(to top, #e9e9e9, #f5f5f5);
                    }}
                    #rcp-url-input {{ display: none; }} /* ซ่อน input ไว้ก่อน */
                    #rcp-container.rcp-expanded #rcp-url-input {{
                        display: block; width: 95%; padding: 10px 15px; font-size: 14px;
                        border-radius: 8px; border: 1px solid #bbb; background-color: #ffffff;
                        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); text-align: center;
                        outline: none; color: #000 !important;
                    }}
                    #rcp-toggle-btn {{ display: flex; align-items: center; justify-content: center; }}
                    #rcp-container.rcp-expanded #rcp-toggle-btn {{ display: none; }} /* ซ่อนปุ่มไอคอนเมื่อขยาย */
                `;
                document.head.appendChild(style);

                // 3. สร้าง Logic: เพิ่ม Event Listener ให้ปุ่ม
                const urlInput = document.getElementById('rcp-url-input');
                rcpContainer.addEventListener('click', (event) => {{
                    if (event.target !== urlInput) {{
                        const isExpanded = rcpContainer.classList.contains('rcp-expanded');
                        rcpContainer.classList.toggle('rcp-expanded');
                        if (!isExpanded) {{
                            setTimeout(() => urlInput.select(), 50);
                        }}
                    }}
                }});
            }}
        }} catch (e) {{ console.error('Failed to inject RCP Mini-Bar:', e); }}
        """

        # --- ส่วนที่เหลือของฟังก์ชันทำงานเหมือนเดิม ---
        def on_page_loaded():
            time.sleep(0.5)
            if popup_window:
                try:
                    if popup_window and not popup_window.closed:
                        popup_window.evaluate_js(js_payload)
                except Exception as e:
                    print("Popup already closed or disposed:", e)

        popup_window = webview.create_window('ReelsCounterPro', html=spinner_html, width=1050, height=650, resizable=True)
        popup_window.events.loaded += on_page_loaded
        
        def navigate_to_target():
            time.sleep(0.1)
            if popup_window:
                popup_window.load_url(url)

        threading.Thread(target=navigate_to_target, daemon=True).start()

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
        """
        API สำหรับเปิดหน้าเอกสารของโปรแกรม
        """
        url = "https://github.com/Babydunx1/reels-counter-update/blob/main/docs/manual.md"
        print(f"API: กำลังเปิดเอกสารโปรแกรม (เรียกใช้ open_external_link) ที่ {url}")
        
        # --- จุดที่แก้ไข ---
        # เรียกใช้ฟังก์ชัน open_external_link ที่เราแก้ไขสมบูรณ์แล้ว
        # เพื่อให้การเปิดลิงก์ทั้งหมดทำงานเหมือนกันผ่าน Mini-Bar UI
        self.open_external_link(url)

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
    
    

