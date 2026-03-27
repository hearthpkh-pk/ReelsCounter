import webview
import threading
import time
import os
from local_db import init_db, get_db, add_page

class MonitorApi:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def get_all_pages(self):
        """เรียกจาก JS เพื่อดูรายชื่อเพจทั้งหมด"""
        db = get_db()
        return db['pages']

    def add_new_page(self, name, url):
        """เรียกจาก JS เพื่อเพิ่มเพจใหม่"""
        success, result = add_page(name, url)
        if success:
            return {"success": True, "page": result}
        else:
            return {"success": False, "message": result}

def main():
    # 1. Init Database 
    init_db()

    # 2. Setup API & Window
    api = MonitorApi()
    
    # สำหรับเวอร์ชั่นแรก เราจะใช้ HTML ง่ายๆ ไปก่อนเพื่อทดสอบระบบ
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Page Monitor Phase 1</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f0f2f5; }
            .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
            input { padding: 8px; margin-right: 10px; border: 1px solid #ddd; border-radius: 4px; width: 200px; }
            button { padding: 8px 15px; background: #1877f2; color: white; border: none; border-radius: 4px; cursor: pointer; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>เพิ่มเพจ Facebook ที่ต้องการติดตาม</h2>
            <input type="text" id="pageName" placeholder="ชื่อเพจ (เช่น Facebook Thai)">
            <input type="text" id="pageUrl" placeholder="URL ของเพจ">
            <button onclick="addPage()">เพิ่มเพจ</button>
        </div>

        <div class="card">
            <h2>รายการเพจที่ติดตามอยู่</h2>
            <table id="pageTable">
                <thead>
                    <tr>
                        <th>ลำดับ</th>
                        <th>ชื่อเพจ</th>
                        <th>URL</th>
                        <th>สถานะ</th>
                    </tr>
                </thead>
                <tbody id="pageList"></tbody>
            </table>
        </div>

        <script>
            function refreshList() {
                window.pywebview.api.get_all_pages().then(pages => {
                    const list = document.getElementById('pageList');
                    list.innerHTML = '';
                    pages.forEach(p => {
                        list.innerHTML += `
                            <tr>
                                <td>${p.id}</td>
                                <td>${p.name}</td>
                                <td>${p.url}</td>
                                <td>${p.status}</td>
                            </tr>
                        `;
                    });
                });
            }

            function addPage() {
                const name = document.getElementById('pageName').value;
                const url = document.getElementById('pageUrl').value;
                if(!name || !url) return alert('กรุณากรอกข้อมูลให้ครบ');
                
                window.pywebview.api.add_new_page(name, url).then(res => {
                    if(res.success) {
                        alert('เพิ่มเพจสำเร็จ!');
                        refreshList();
                    } else {
                        alert('เกิดข้อผิดพลาด: ' + res.message);
                    }
                });
            }

            // โหลดข้อมูลครั้งแรกเมื่อโปรแกรมเปิด
            window.addEventListener('pywebviewready', refreshList);
        </script>
    </body>
    </html>
    """

    window = webview.create_window(
        'FB Page Monitor - Phase 1', 
        html=html, 
        js_api=api,
        width=900,
        height=700
    )
    api.set_window(window)
    webview.start()

if __name__ == "__main__":
    main()
