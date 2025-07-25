
// =======================================================
// ส่วนที่ 1: การตั้งค่าและฟังก์ชันพื้นฐาน
// =======================================================
console.log('✅ script.js โหลดมาแล้ว');
// --- ค่าคงที่ (ลูกพี่ต้องแก้ LOCAL_VERSION ทุกครั้งที่สร้างเวอร์ชันใหม่) ---
const LOCAL_VERSION   = "1.3";
const UPDATE_JSON_URL = "https://raw.githubusercontent.com/Babydunx1/reels-counter-update/main/app_version.json";

// --- ตัวแปรสำหรับเก็บข้อมูลเวอร์ชันล่าสุดจาก Server ---
let LATEST_VERSION_INFO = {};

/**
 * ฟังก์ชันเปรียบเทียบเวอร์ชัน (เช่น '1.0' ใหม่กว่า '0.9')
 */
function isNewerVersion(latest, local) {
  if (!latest || !local) return false;
  const a = latest.split('.').map(Number);
  const b = local.split('.').map(Number);
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if ((a[i] || 0) > (b[i] || 0)) return true;
    if ((a[i] || 0) < (b[i] || 0)) return false;
  }
  return false;
}

/**
 * ฟังก์ชันที่ Python จะเรียกเพื่ออัปเดต % การดาวน์โหลด
 */
function updateDownloadProgress(percent) {
    const statusEl = document.getElementById("updateStatus");
    if (statusEl) {
        statusEl.innerText = `กำลังดาวน์โหลด… ${percent}%`;
    }
}

// Driver Status Display ว่าเป็น "🟢 Manual Driver Active" หรือ "🟠 Auto Driver in use // 

function updateDriverStatusUI(mode) {
  const dot = document.getElementById("driverStatusDot");
  const text = document.getElementById("driverStatusText");

if (mode === "manual-ready") {
  dot.className = "dot driver green";
  text.textContent = "Manual Driver Active";
} else if (mode === "auto") {
  dot.className = "dot driver orange";
  text.textContent = "Auto Scanning...";
} else {
  dot.className = "dot driver red blinking";
  text.textContent = "No Driver Active";
}
}



// Driver Status Display ว่าเป็น "🟢 Manual Driver Active" หรือ "🟠 Auto Driver in use // 


// =======================================================
// ส่วนที่ 2: การจัดการหน้าต่าง Popup (Modal)
// =======================================================

/**
 * ฟังก์ชันแสดง/ซ่อนหน้าต่าง Popup
 */
function showUpdateModal() { document.getElementById("updateModalBackdrop").style.display = "flex"; }
function hideUpdateModal() { document.getElementById("updateModalBackdrop").style.display = "none"; }


/**
 * ฟังก์ชันเติมข้อมูลลงในหน้าต่าง Popup และผูกปุ่มดาวน์โหลด
 */
function fillUpdateModal(isLatest) {
  // --- แสดงข้อความหัวเรื่อง ---
  document.getElementById("updateVersionTitle").innerHTML =
    isLatest
      ? `✅ <span style="color:#17b93a;">คุณใช้เวอร์ชันล่าสุดแล้ว (v${LATEST_VERSION_INFO.current_version})</span>`
      : `🎉 <span style="color:#17b93a;">พบเวอร์ชันใหม่! v${LATEST_VERSION_INFO.version}</span>`;

  // --- แสดงรายละเอียดการอัปเดต (Changelog) ---
  document.getElementById("updateChangelog").innerHTML = (LATEST_VERSION_INFO.changelog || []).map(item => "- " + item).join("<br>");
  document.getElementById("updateDate").innerHTML = LATEST_VERSION_INFO.date ? `<div style="color:#888; font-size:13px; margin-top:3px;">${LATEST_VERSION_INFO.date}</div>` : "";
  
  // --- จัดการปุ่มดาวน์โหลด ---
  const btn = document.getElementById("btn-update-download");
  btn.style.display = isLatest ? "none" : "block";
  
  const statusEl = document.getElementById("updateStatus");
  statusEl.style.display = "none";
  statusEl.innerText = "";

  // --- ผูกคำสั่งให้ปุ่มดาวน์โหลด ---
  btn.onclick = () => {
    statusEl.style.display = "block";
    statusEl.innerText = "กำลังดาวน์โหลด… 0%";
    if (window.pywebview?.api?.run_updater) {
      window.pywebview.api.run_updater(LATEST_VERSION_INFO.download_url);
    }
  };
}

// ——— ปุ่ม “ดูประวัติอัปเดต” → เปิด GitHub Releases ———
document.body.addEventListener('click', e => {
  // ถ้า target คือปุ่มดูประวัติอัปเดต
  if (e.target && e.target.id === 'ud-changelog') {
    e.preventDefault();
    e.stopPropagation();

    // ซ่อน modal ถ้ามันยังเปิดอยู่
    const modal = document.getElementById('updateModalBackdrop');
    if (modal) modal.style.display = 'none';

    // เปิด Releases บน GitHub
    const url = 'https://github.com/Babydunx1/reels-counter-update/releases';
    if (window.api && typeof window.api.invoke === 'function') {
      window.api.invoke('open_external_link', url);
    } else {
      window.open(url, '_blank');
    }
  }
});

// =======================================================
// ส่วนที่ 3: การทำงานเมื่อโปรแกรมเปิด (หัวใจหลัก)
// =======================================================

// รอให้ Python พร้อม 100% แล้วค่อยเริ่มทำงาน
window.addEventListener('pywebviewready', function() {
    
    // สร้างฟังก์ชันสำหรับเรียกเช็คอัปเดต
    const checkUpdate = () => {
        // สั่งให้ Python ไปดึงข้อมูลมาให้
        window.pywebview.api.get_update_info().then(info => {
            if (info && !info.error) {
                LATEST_VERSION_INFO = info;
                // หลังจากได้ข้อมูลจาก Python เราจะใช้ LOCAL_VERSION ของ JS เองในการเปรียบเทียบ
                const hasNew = isNewerVersion(info.version, LOCAL_VERSION);
                fillUpdateModal(!hasNew);
                showUpdateModal();
            } else {
                alert("เกิดข้อผิดพลาดในการตรวจสอบเวอร์ชัน: " + (info.error || "Unknown Error"));
            }
        });
    };

    // Auto-check ครั้งแรกตอนเปิดโปรแกรม
    setTimeout(() => {
        if (window.pywebview.api && window.pywebview.api.get_update_info) {
             window.pywebview.api.get_update_info().then(info => {
                // เช็คอัปเดตก็ต่อเมื่อ: (มีข้อมูล && ไม่มี error && มีเวอร์ชันใหม่ && ไม่ใช่การเปิดหลังติดตั้ง)
                if (info && !info.error && isNewerVersion(info.version, LOCAL_VERSION) && !info.is_post_install) {
                    LATEST_VERSION_INFO = info;
                    fillUpdateModal(false);
                    showUpdateModal();
                }
            });
        }
    }, 2000); 

    // Bind ปุ่มเฟืองให้ทำงาน
    document.getElementById('btn-check-update').onclick = checkUpdate;
    
    // Bind ปุ่มปิด Modal
    document.getElementById('updateModalCloseBtn').onclick = hideUpdateModal;
});

// ─── ปิด modal เมื่อคลิกที่ backdrop รอบๆ card ─────────
const updateModal = document.getElementById('updateModalBackdrop');
if (updateModal) {
  updateModal.addEventListener('click', e => {
    // ถ้า target ตรงกับ backdrop เรียก hideUpdateModal()
    if (e.target === updateModal) {
      hideUpdateModal();
    }
  });
}

// ==== Update & Repair Widget ====
window.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-auto-update');
  const log = document.getElementById('update-log');
  if (!btn || !log) return;

  btn.addEventListener('click', async () => {
    log.textContent = 'กำลังตรวจสอบ...';
    try {
      // เรียก Python API เช็กเวอร์ชัน
      const info = await window.api.invoke('check_update'); 
      // ตัวอย่าง return: { version: '1.0.6', isLatest: true, changelog: [...], downloadUrl: '...' }
      
      if (info.isLatest) {
        log.textContent = `ล่าสุดแล้ว (${info.version})`;
      } else {
        log.innerHTML = `พบ v${info.version}<br>กดปุ่มเดิมเพื่อติดตั้ง`;
        btn.textContent = '📥 ดาวน์โหลด & ติดตั้ง';
        btn.onclick = async () => {
          log.textContent = 'กำลังดาวน์โหลด...';
          await window.api.invoke('run_updater', info.downloadUrl);
          log.textContent = 'เรียบร้อย! กำลังรีสตาร์ท';
        };
      }
    } catch (e) {
      log.textContent = 'Error: ' + e.message;
    }
  });
});
// ================================

// รอ DOM โหลดเสร็จ
// โหลดเมื่อ DOM พร้อมใช้งาน
document.addEventListener('DOMContentLoaded', () => {
  // ─── ดึง element ต่างๆ ───────────────────────────────
  const updateBlock    = document.getElementById('update-block');
  const updateDropdown = document.getElementById('update-dropdown');
  const btnCheckGear   = document.getElementById('btn-check-update');
  const btnHelp        = document.getElementById('ud-help');
  const btnDocs        = document.getElementById('ud-docs');
  const btnCheck       = document.getElementById('ud-check');
  const btnRepair      = document.getElementById('ud-repair');
  const btnAbout       = document.getElementById('ud-about');


  // ─── ถ้า critical element หาย ให้หยุด ─────────────────
  if (!updateBlock || !updateDropdown) return;

  // ─── 1) เปิด/ปิด dropdown ─────────────────────────────
  updateBlock.addEventListener('click', e => {
    e.stopPropagation();
    updateDropdown.classList.toggle('hidden');
  });
  document.addEventListener('click', e => {
    if (!updateBlock.contains(e.target)) {
      updateDropdown.classList.add('hidden');
    }
  });

  // ─── 2) เมนูย่อย ───────────────────────────────────────

  // ——— About Modal ——————————————————————————————
const aboutModal      = document.getElementById('aboutModalBackdrop');
const aboutModalClose = document.getElementById('aboutModalClose');
const aboutModalOk    = document.getElementById('aboutModalOk');


// แสดงเวอร์ชัน
const spanVersion = document.getElementById('app-version');
if (spanVersion) spanVersion.textContent = LOCAL_VERSION;



btnAbout.addEventListener('click', e => {
  e.stopPropagation();
  updateDropdown.classList.add('hidden');
  aboutModal.classList.remove('hidden');
});
aboutModalClose.addEventListener('click', () => aboutModal.classList.add('hidden'));
aboutModalOk   .addEventListener('click', () => aboutModal.classList.add('hidden'));
aboutModal     .addEventListener('click', e => {
  if (e.target === aboutModal) aboutModal.classList.add('hidden');
});


// ลิงก์ไปหน้า GitHub
aboutRepoLink.addEventListener('click', e => {
  e.preventDefault();
  const repoUrl = 'https://github.com/Babydunx1/reels-counter-update';
  if (window.api?.invoke) {
    window.api.invoke('open_external_link', repoUrl);
  } else {
    window.open(repoUrl, '_blank');
  }
});

 // ——— About Modal ——————————————————————————————



// ——— เริ่มปุ่ม “วิธีใช้” → เปิด usage.md บน GitHub ———
const helpUrl = 'https://github.com/Babydunx1/reels-counter-update/blob/main/docs/usage.md';

btnHelp.addEventListener('click', e => {
  e.stopPropagation();
  updateDropdown.classList.add('hidden');

  // ถ้าเป็น WebView ให้เรียก Python API open_external_link(url)
  if (window.pywebview && window.pywebview.api && 
      typeof window.pywebview.api.open_external_link === 'function') {
    window.pywebview.api.open_external_link(helpUrl);
  }
  // ถ้าไม่ใช่ WebView (รันในเบราเซอร์) ก็เปิดแท็บใหม่
  else {
    window.open(helpUrl, '_blank');
  }
});
 // ——— จบ ปุ่ม “วิธีใช้” → เปิด usage.md บน GitHub ———

 // ——— ปุ่ม เรียก handler ปุ่มเฟืองเดิม ———
  btnCheck.addEventListener('click', () => {
    updateDropdown.classList.add('hidden');
    btnCheckGear.click(); // เรียก handler ปุ่มเฟืองเดิม
  });
   // ——— ปุ่ม เรียก handler ปุ่มเฟืองเดิม ———




  


  // ปุ่มลิ้งรายละเอียดโปรแกรม ลิ้งไป github
btnDocs.addEventListener('click', () => {
  updateDropdown.classList.add('hidden');
  if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.showDocs === 'function') {
    window.pywebview.api.showDocs();
  } else {
    // fallback เปิดด้วย window.open เผื่อ run นอก webview
    window.open('https://github.com/Babydunx1/reels-counter-update/blob/main/docs/manual.md', '_blank');
  }
});
  // ปุ่มลิ้งรายละเอียดโปรแกรม ลิ้งไป github

  // ──────────────────────────────────────────
  
  // ─── 3) จับเหตุการณ์ Repair Modal ─────────────────────
  const repairModal              = document.getElementById('repairModalBackdrop');
  const closeRepair              = document.getElementById('repairModalClose');
  const cancelRepair             = document.getElementById('repairCancelBtn');
  const confirmRepair            = document.getElementById('repairConfirmBtn');
  const repairBodyText           = document.getElementById('repairBodyText');
  const repairProgressContainer  = document.getElementById('repairProgressContainer');
  const repairProgressBar        = document.getElementById('repairProgressBar');

// **1. ถ้ามี backdrop ให้จับคลิกนอกตัว card ปิด modal**
if (repairModal) {
  repairModal.addEventListener('click', e => {
    if (e.target === repairModal) {
      repairModal.classList.add('hidden');
    }
  });
}

// **2. ถ้าไม่มี or ปุ่ม Confirm หาย ให้ข้ามบล็อกนี้**
if (!repairModal || !confirmRepair) return;

// 3. เปิด modal (btnRepair ของเดิม)
btnRepair.addEventListener('click', e => {
  e.stopPropagation();
  updateDropdown.classList.add('hidden');
  repairModal.classList.remove('hidden');
});

// 4. ปิด modal (X / ยกเลิก)
closeRepair .addEventListener('click', () => repairModal.classList.add('hidden'));
cancelRepair.addEventListener('click', () => repairModal.classList.add('hidden'));

  // อัพเดต: ตกลง → แสดง progress + เรียก API + สรุปผล
  confirmRepair.addEventListener('click', async e => {
    e.stopPropagation();
    updateDropdown.classList.add('hidden');

    // 1) เตรียม Progress Bar
    repairProgressContainer.classList.remove('hidden');
    repairProgressBar.style.width   = '0%';
    repairProgressBar.textContent   = '0%';

    // เปลี่ยนข้อความ body + ลบปุ่มเดิม
    repairBodyText.textContent = '⏳ กำลังดาวน์โหลดและซ่อมแซม… กรุณารอสักครู่';
    repairModal.querySelector('.modal-footer').innerHTML = '';

    try {
      // สมมติ run_repair รับ callback และเรียกกลับด้วยเปอร์เซนต์
      await window.pywebview.api.run_repair(progress => {
        repairProgressBar.style.width = `${progress}%`;
        repairProgressBar.textContent = `${progress}%`;
      });

      repairBodyText.textContent = '🔧 ซ่อมแซมเรียก API เรียบร้อยแล้ว';
    } catch (err) {
      repairBodyText.textContent = '❌ ซ่อมแซมล้มเหลว: ' + err;
    } finally {
      // ซ่อน Progress Bar
      repairProgressContainer.classList.add('hidden');

      // สร้างปุ่ม OK ปิด modal
      const footer = repairModal.querySelector('.modal-footer');
      const okBtn = document.createElement('button');
      okBtn.textContent = 'ตกลง';
      okBtn.className   = 'btn-confirm';
      okBtn.addEventListener('click', () => repairModal.classList.add('hidden'));
      footer.appendChild(okBtn);
      
      
    }
  });
});




// ———————————————


// จบส่วนระบบ Update ================================


// --- Tab Switching ---
function showTab(tabName) {
    console.log("[DEBUG] showTab called:", tabName);
    if (tabName === 'fb') {
        document.getElementById('content-fb').classList.remove('hidden');
        document.getElementById('content-ig').classList.add('hidden');
        document.getElementById('btn-fb').classList.add('active');
        document.getElementById('btn-ig').classList.remove('active');
    } else {
        document.getElementById('content-fb').classList.add('hidden');
        document.getElementById('content-ig').classList.remove('hidden');
        document.getElementById('btn-fb').classList.remove('active');
        document.getElementById('btn-ig').classList.add('active');
    }
    console.log("[DEBUG] showTab DONE");
    const switcher = document.querySelector('.tab-switcher');
    if (switcher) {
    switcher.classList.remove('fb-mode', 'ig-mode');
    switcher.classList.add(tabName === 'fb' ? 'fb-mode' : 'ig-mode');
    }
    // ✅ Toggle Driver Status Display
  const driverStatusBox = document.getElementById("driver-floating-status");
  if (driverStatusBox) {
    driverStatusBox.style.display = (tabName === 'fb') ? 'inline-flex' : 'none';
  }

}

// 🧠 เพิ่ม debug log ทุกรูปแบบ 🧠
function handle_python_callback(response) {
    try {
        console.log("[DEBUG] handle_python_callback called! Raw response:", response, "type:", typeof response);

        // ถ้าเป็น string ให้ลอง parse
        if (typeof response === "string") {
            try {
                response = JSON.parse(response);
                console.log("[DEBUG] Parsed response string to object:", response);
            } catch (e) {
                console.error("[DEBUG] JSON.parse failed!", e, response);
                return;
            }
        }

        if (!response || !response.type) {
            console.error("[DEBUG] No .type in response", response);
            return;
        }

        const active_platform = document.getElementById('btn-fb').classList.contains('active') ? 'fb' : 'ig';
        console.log("[DEBUG] active_platform:", active_platform);

        // ==== log กลับ Python ทุกเคส ====
        if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.log_from_js === "function") {
    try {
        let msg = `[${response.type}] `;

        if (response.type === 'initial_data') {
            const reelsCount = response.data && response.data.reels ? response.data.reels.length : 0;
            const viewsTotal = response.data && response.data.total_views ? response.data.total_views : 0;
            msg += `reels=${reelsCount}, views=${viewsTotal}`;
        } else if (response.type === 'update_date_final' || response.type === 'update_date_status') {
            msg += JSON.stringify(response.data);
        } else if (response.message) {
            msg += response.message;
        } else {
            msg += JSON.stringify(response);
        }

        // 🔒 Normalize ป้องกัน Unicode error
        const safeMsg = msg.normalize ? msg.normalize("NFKD") : msg;

        // ✅ ลองส่ง ถ้าพังจะไม่แครชโปรแกรม
        window.pywebview.api.log_from_js(safeMsg);

    } catch (e) {
        console.warn("⚠️ log_from_js Unicode fail:", msg, e);
    }
}

        // ==== END ====

        switch (response.type) {
            // ==== Log ข้อความ (ไม่ใช่สถานะกลาง) ====
            case 'log':
                console.log(`[PY LOG] ${response.message}`);
                appendLog(active_platform, response.message);
                break;

            // ==== ขั้นตอนตาม flow จริง ====
            case 'wait_login':
                updateStatus(active_platform, `🖥️ รอ login`);
                startStatusDotLoop(active_platform, `🖥️ รอ login`);
                break;

            case 'save_cookie':
                updateStatus(active_platform, `✓ บันทึก cookie`);
                startStatusDotLoop(active_platform, `✓ บันทึก cookie`);
                break;

            case 'cookie_loaded':
                set_status("✓ โหลด cookie สำเร็จ", active_platform);
                startStatusDotLoop(active_platform, "✓ โหลด cookie สำเร็จ");
                break;

            case 'fetch_views_start':
            case 'start_fetch_views':
                updateStatus(active_platform, `✓ 🔎กำลังสแกนยอดวิว...`);
                startStatusDotLoop(active_platform, `🔎 กำลังสแกนยอดวิว`);
                break;

            case 'scan_feed':
                updateStatus(active_platform, `🔎 สแกนฟีดเพื่อหายอดวิว`);
                startStatusDotLoop(active_platform, `🔎 สแกนฟีดเพื่อหายอดวิว`);
                break;

                // ★ ตรงนี้ ให้เพิ่มบล็อกใหม่ทั้งสองตัว ★

            case 'view_fetch_progress': {
                const { current, total, link, views } = response.data;

                // — อัปเดตสถานะแบบเดิม —
                if (typeof clearStatusDotLoop === 'function') clearStatusDotLoop(active_platform);
                const msg = `🔍 กำลังสแกนยอดวิว ${current}/${total}`;
                updateStatus(active_platform, msg);
                startStatusDotLoop(active_platform, msg);

                // — แทรกหรืออัปเดตแถวในตารางทันที —
                const table = document.getElementById(`${active_platform}-table`);
                const tbody = table.querySelector('tbody');
                let row = tbody.querySelector(`tr[data-link="${link}"]`);

                // --- Logic การไฮไลท์และใส่ Emoji ---
                let view_text = Number(views).toLocaleString();
                let rowClass = '';
                if (views >= 1000000) {
                    rowClass = 'highlight-red';
                    view_text = `🔥 ${view_text}`;
                } else if (views >= 100000) {
                    rowClass = 'highlight-green';
                }
                // --- จบ Logic ---

                if (!row) {
                    row = tbody.insertRow();
                    row.setAttribute('data-link', link);
                    row.insertCell(0).innerText = current;
                    row.insertCell(1).innerText = link;
                    row.insertCell(2).innerText = view_text; // ใช้ตัวแปรใหม่
                    row.insertCell(3).innerText = '…';
                } else {
                    row.cells[2].innerText = view_text; // อัปเดตด้วยตัวแปรใหม่
                }

                // กำหนด class ให้กับแถว
                row.className = rowClass;

                // (ถ้ามี) อัปเดตสรุปยอดรวม
                recalculateTotalViews(active_platform);
            } break;




            case 'driver_status':
                // ○ เมื่อโหมดกลายเป็น manual-ready → ยกเลิกล็อกปุ่ม
                if (response.mode === 'manual-ready') {
                    window.manualDatePendingFB = false;
                }
                updateDriverStatusUI(response.mode);
                break;

                // ★ เพิ่มบล็อกจับ auto-date-fetch-start ★
            case 'auto_date_fetch_start': {
                const platform = active_platform;
                const indices = Array.isArray(response.data.indices)
                    ? response.data.indices
                    : [];

                const table = document.getElementById(`${platform}-table`);
                const rows = Array.from(
                    table.querySelectorAll('tbody tr:not(.summary-row)')  
                );

                indices.forEach(i => {
                    const tr = rows[i];
                    if (tr && tr.cells[3]) {
                        tr.cells[3].innerHTML = '<span class="spinner"></span>';
                    }
                });

                // ✅ FIX: เพิ่มตัวแปร local
                let reels = rows.length;
                let totalViews = 0;
                rows.forEach(tr => {
                    const viewText = tr.cells[2]?.innerText?.replace(/[^0-9]/g, '') || '0';
                    totalViews += parseInt(viewText, 10);
                });

                const msg = `✅ พบ ${reels} คลิป: ${totalViews.toLocaleString()} วิว | 📅 กำลังสแกนวันที่`;
                updateStatus(platform, msg);
                startStatusDotLoop(platform, msg);
            }
            break;

                
           

            // ==== สถานะทั่วไปจาก backend (เช่น บอกสำเร็จ/จบงาน/ข้อความพิเศษ) ====
            case 'status':
                set_status(response.message, active_platform, response.final);
                if (response.final) {
                    const progressContainer = document.getElementById(`${active_platform}-progress-container`);
                    if (progressContainer) progressContainer.classList.add('hidden');
                }
                break;

            // ==== แจ้ง error/info ====
            case 'error':
            case 'info':
                alert(`[${response.title}]\n${response.message}`);
                const progressContainerError = document.getElementById(`${active_platform}-progress-container`);
                if (progressContainerError) progressContainerError.classList.add('hidden');
                const btnError = document.getElementById(`btn-start-${active_platform}`);
                if (btnError) btnError.disabled = false;
                break;

            // ==== หลังดึงยอดวิวสำเร็จ (โชว์ยอดวิว/คลิป และสั่งขึ้นสแกนวันที่) ====
            case 'initial_data':
                // เราไม่ต้องรัน populate_initial_data() อีก ให้ใช้ view_fetch_progress
                // แต่ถ้าต้องการสรุปยอดวิวครบแล้วเริ่มสแกนวันที่ ก็เขียนแค่:
                const reelsCount = response.data.reels.length;
                const totalViews = response.data.total_views.toLocaleString();
                updateStatus(
                  active_platform,
                  `✅ สแกนวิวครบ ${reelsCount} คลิป: ${totalViews} วิว | 📅 เริ่มดึงวันที่`
                );
                // สมมติว่าคุณมีฟังก์ชันสั่งดึงวันที่ชื่อ startDateFetch()
                if (typeof startDateFetch === 'function') {
                  startDateFetch(active_platform);
                }
                break;
                

            // ✅ เพิ่มไว้ตรงนี้ — หลัง initial_data และก่อน update_date_status
            case 'fb_scroll_progress':
                if (response.data) {
                    const { attempt, total, scroll_height, total_views, counted_clips } = response.data;
                    const msg = `✅ พบ ${counted_clips} คลิป: ${Number(total_views).toLocaleString()} วิว |สถานะ สแกนวันที่ ${attempt}/${total} ดึงข้อมูลฟีด📋 ${scroll_height}`;
                    updateStatus(active_platform, msg);
                    startStatusDotLoop(active_platform, msg);
                }
                break;

            // ✅Jump Scroll Callback //    

            case 'fb_jump_status':
                if (response.data) {
                    const { jump_height, max_needed_index, total_clips, total_views } = response.data;
                    const views_formatted = Number(total_views).toLocaleString();
                    const msg = `
                        ✅ พบ ${total_clips} คลิป: ${views_formatted} วิว |
                        สถานะ <span style="
                            color:#e53935;
                            font-weight:bold;
                            animation: pulseJump 1s infinite;
                        ">🪂 Jump scroll to ${jump_height}px</span>`;
                    updateStatus(active_platform, msg);
                    startStatusDotLoop(active_platform, msg);
                }
                break;    

            case 'fb_jump_status':
                if (response.data) {
                    const { jump_height, max_needed_index, total_clips, total_views, super_jump_mode } = response.data;
                    const views_formatted = Number(total_views).toLocaleString();

                    let msg = `✅ พบ ${total_clips} คลิป: ${views_formatted} วิว | สถานะ <span style="
                        color:#e53935;
                        font-weight:bold;
                        animation: pulseJump 1s infinite;
                    ">🚀 Jump scroll to ${jump_height}px</span>`;

                    if (super_jump_mode) {
                        msg += `<br><span style="color:#FF9800;font-weight:bold">⚠️ โหมดพิเศษ: พบคลิปลึกผิดปกติ, กระโดดลึกพิเศษ</span>`;
                    }

                    updateStatus(active_platform, msg);
                    startStatusDotLoop(active_platform, msg);
                }
                break;
    

                

            // ==== ขณะอัปเดตวันที่ทีละแถว (ในตาราง) ====
            case 'update_date_status':
                {
                    const { link, status } = response.data;
                    console.log("[DEBUG] update_date_status:", link, status, "platform:", active_platform);

                    // ถ้า status เป็น '⌛ …' (IG auto-fetch) ให้แสดง spinner แทน
                    if (status && status.includes('⌛')) {
                        const row = document.querySelector(
                            `#${active_platform}-table tr[data-link="${link}"]`
                        );
                        if (row && row.cells.length > 3) {
                            row.cells[3].innerHTML = '<span class="spinner"></span>';
                        }
                    } else {
                        // กรณีอื่นๆ (วันที่จริง หรือ error) ให้ใช้เดิม
                        update_date_cell(link, response.data.date || status, active_platform);
                    }
                }
                break;

                 // ================== ✅ เพิ่ม case ใหม่นี้เข้าไป ==================
            case 'ig_date_fetch_progress':
                if (response.data) {
                    // ดึงข้อมูล "คลิปปัจจุบัน" และ "คลิปทั้งหมด" ที่ส่งมาจาก Python
                    const { current, total } = response.data;
                    const table = document.getElementById(`ig-table`);
                    const rows = Array.from(table.querySelectorAll('tbody tr')).filter(r => !r.classList.contains('summary-row'));
                    const sum = rows.reduce((s, row) => s + (Number(row.cells[2].innerText.replace(/[^\d]/g, '')) || 0), 0);
                    
                    // สร้างข้อความสถานะใหม่
                    const msg = `✅ พบ ${rows.length} คลิป: ${sum.toLocaleString()} วิว | สถานะ ♻️กำลังสแกนวันที่ (${current}/${total})`;
                    
                    // อัปเดต UI และเริ่ม animation
                    updateStatus(active_platform, msg);
                    startStatusDotLoop(active_platform, msg);
                }
                break;

            // ==== หลังอัปเดตวันที่ครบทุกคลิป ====
            case 'update_date_final':
                if (Array.isArray(response.data)) {
                    response.data.forEach(row => {
                        update_date_cell(row.link, row.date, active_platform);
                    });
                } else if (response.data && response.data.link && response.data.date) {
                    update_date_cell(response.data.link, response.data.date, active_platform);
                }
                stopStatusDotLoop();
                let table = document.getElementById(`${active_platform}-table`);
                let rows = Array.from(table.querySelectorAll('tbody tr')).filter(r=>!r.classList.contains('summary-row'));
                let sum = rows.reduce((s,row)=>s + (Number(row.cells[2].innerText.replace(/[^\d]/g, '')) || 0), 0);
                updateStatus(
                    active_platform,
                    `✅ สแกนสำเร็จ | รวมยอดวิว ${sum.toLocaleString()} จาก ${rows.length} คลิป`
                );
                window.manualDatePendingFB = false;
                break;
                

            // ==== ไม่รู้จัก type ====
            default:
                console.warn("[DEBUG] Unknown response.type:", response.type, response);
        }
    } catch (err) {
        console.error("[DEBUG] handle_python_callback CATCH ERROR:", err, response);
    }
}






function set_status(message, platform, is_final = false) {
    console.log("[DEBUG] set_status", {message, platform, is_final});
    const statusLabel = document.getElementById(`${platform}-status-label`);
    if (!statusLabel) {
        console.error(`[DEBUG] set_status: statusLabel not found for platform: ${platform}`);
        return;
    }
    statusLabel.innerText = message;
    statusLabel.style.color = is_final ? '#28a745' : '';
    if (is_final) {
        const btn = document.getElementById(`btn-start-${platform}`);
        if (btn) btn.disabled = false;
    }
    console.log("[DEBUG] set_status DONE", {message, platform, is_final});
}

function populate_initial_data(data, platform) {
    try {
        console.log("[DEBUG] populate_initial_data START", {data, platform});
        if (!data || !Array.isArray(data.reels)) {
            console.error("[DEBUG] populate_initial_data: data.reels ไม่ถูกต้อง", data);
            return;
        }
        const tbody = document.querySelector(`#${platform}-table tbody`);
        if (!tbody) {
            console.error(`[DEBUG] populate_initial_data: tbody not found for platform: ${platform}`);
            return;
        }
        tbody.innerHTML = '';

        // *** เพิ่มตรงนี้ ***
        const resultCard = document.querySelector(`#content-${platform} .result-card`);
        if (resultCard) resultCard.classList.add('expanded');
        // *** จบเพิ่ม ***

        

        data.reels.forEach((reel, index) => {
            const row = tbody.insertRow();
            row.setAttribute('data-link', reel.link);

            // [ส่วนแก้ไข Logic]
            const views = reel.views || 0;
            let view_text = views.toLocaleString();
            
            // เพิ่ม class และ emoji ตามเงื่อนไข
            if (views >= 1000000) {
              row.className = 'highlight-red';
              view_text = `🔥 ${view_text}`;
            } else if (views >= 100000) {
              row.className = 'highlight-green';
            }
            // [จบส่วนแก้ไข Logic]

            row.insertCell(0).innerText = index + 1;
            const linkCell = row.insertCell(1);
            linkCell.innerText = reel.link;
            linkCell.title = reel.link;
            const viewCell = row.insertCell(2);
            viewCell.innerText = view_text; // ใช้ view_text ที่ผ่านการปรับแต่งแล้ว
            const dateCell = row.insertCell(3);
            dateCell.innerText = reel.date_text || '...';
        });

        if (data.reels && data.reels.length > 0) {
            const summaryRow = tbody.insertRow();
            summaryRow.className = 'summary-row';
            let cell1 = summaryRow.insertCell(0);
            cell1.colSpan = "2";
            cell1.innerText = 'รวมยอดวิวทั้งหมด:';
            cell1.style.fontWeight = 'bold';
            cell1.style.textAlign = 'right';
            let cell2 = summaryRow.insertCell(1);
            cell2.innerText = data.total_views ? data.total_views.toLocaleString() : 'N/A';
            cell2.style.fontWeight = 'bold';
            cell2.style.textAlign = 'right';
            summaryRow.insertCell(2);
        }
        // ✅ คำนวณยอดรวม / ค่าเฉลี่ย / ยอดสูงสุด ทันทีหลัง populate
        recalculateTotalViews(platform);


    } catch (err) {
        console.error("[DEBUG] populate_initial_data ERROR", err, data, platform);
    }
}

function update_date_cell(link, new_date, platform) {
    try {
        console.log("[DEBUG] update_date_cell", { link, new_date, platform });
        const row = document.querySelector(`#${platform}-table tr[data-link="${link}"]`);
        if (row && row.cells.length > 3) {
            row.cells[3].innerText = new_date;
            console.log("[DEBUG] update_date_cell success");
        } else {
            console.warn("[DEBUG] update_date_cell: Row not found or too few cells", { link, platform });
        }
    } catch (err) {
        console.error("[DEBUG] update_date_cell ERROR", err, link, new_date, platform);
    }
}

// --- Utility: อัปเดตข้อความสถานะแบบเด้ง ---
function updateStatus(platform, message) {
    const label = document.getElementById(`${platform}-status-label`);
    if (!label) return;
    label.innerHTML = message;
    label.classList.remove("status-animate");
    void label.offsetWidth;
    label.classList.add("status-animate");
}

let statusDotInterval = null;

function startStatusDotLoop(platform, baseText = '') {
    const label = document.getElementById(`${platform}-status-label`);
    if (!label) return;
    let dotCount = 0;
    clearInterval(statusDotInterval);
    statusDotInterval = setInterval(() => {
        dotCount = (dotCount + 1) % 4;
        const dots = '.'.repeat(dotCount);
        label.innerHTML = `${baseText}${dots}`;
    }, 400);
}

function stopStatusDotLoop() {
    clearInterval(statusDotInterval);
}

// --- Function to Start Scan (ปรับข้อความสถานะตาม flow ใหม่) ---
function startScan(platform) {
    try {
        console.log("[DEBUG] startScan called for platform:", platform);

        // ✅ เคลียร์ตารางและข้อมูลสรุปเก่าก่อนเริ่มสแกนใหม่
        const tableBody = document.querySelector(`#${platform}-table tbody`);
        if (tableBody) {
            tableBody.innerHTML = '';
        }
        recalculateTotalViews(platform); // รีเซ็ตการ์ดสรุป (ยอดรวม, เฉลี่ย, สูงสุด)

        // ปิดปุ่มสแกน และเอา animation ออก
        const btn = document.getElementById(`btn-start-${platform}`);
        if (btn) {
            btn.classList.remove("attention");
            btn.disabled = true;
        }

        // ✅ แสดง Progress Bar Container
        const progressContainer = document.getElementById(`${platform}-progress-container`);
        if (progressContainer) {
            progressContainer.classList.remove('hidden');
        }

        // ✅ ดึง progress bar และเซ็ตสีให้ถูกต้อง
        const progressBar = document.querySelector(`#${platform}-progress-container .progress-bar`);
        if (progressBar) {
            progressBar.className = 'progress-bar';
            const barClass = `progress-bar-${platform}`;
            progressBar.classList.add(barClass);
            console.log(`[DEBUG] เพิ่ม class: ${barClass}`);
            console.log(`[DEBUG] ได้ class สุดท้าย:`, progressBar.className);
        }

        // ✅ สถานะเริ่มต้น
        updateStatus(platform, `⏳ กำลังเริ่มต้น...`);
        startStatusDotLoop(platform, `⏳ กำลังเริ่มต้น`);

        // เตรียม data จากฟอร์ม
        let data = {};
        if (platform === 'fb') {
            data.profileUrl = document.getElementById('fb-profile-url').value;
            data.reelsUrl   = document.getElementById('fb-reels-url').value;
            data.clipCount  = document.getElementById('fb-clip-count').value;
        } else {
            data.reelsUrl   = document.getElementById('ig-reels-url').value;
            data.clipCount  = document.getElementById('ig-clip-count').value;
        }

        // ← ตรงนี้ ให้แทรกโค้ดอ่าน mode เพิ่มเข้าไป
        const mode = document.querySelector('input[name="mode"]:checked').value;
        console.log('🕵️‍♀️ Selected mode =', mode);
        data.mode = mode;   // ถ้าต้องส่งไป Python ด้วย

        console.log("[DEBUG] startScan sending to pywebview.api.start_scan", platform, data);
        window.pywebview.api.start_scan(platform, data);

      } catch (err) {
        console.error("[DEBUG] startScan ERROR", err, platform);
      }
    }





// --- Function for Manual Date Fetch ---

function manualFetchDate(platform) {
  // 1) กันคลิกซ้ำเฉพาะ Facebook ขณะกำลังดึงวันที่อยู่
  if (platform === 'fb' && window.manualDatePendingFB) {
    const prevScroll = window.scrollY;
    Swal.fire({
      icon: 'info',
      title: 'กรุณารอ…',
      text:  'กำลังดึงวันที่อยู่…',
      showConfirmButton: false,
      timer: 2000,
      width: '280px',
      position: 'center',
      heightAuto: false,
      scrollbarPadding: false,
      didOpen: () => {
        document.querySelector('.swal2-container').style.backdropFilter = 'blur(3px)';
        // บังคับ container อยู่ fixed ไม่นำ content เลื่อนตาม
        document.querySelector('.swal2-container').style.position = 'fixed';
      },
      willClose: () => {
        window.scrollTo({ top: prevScroll, behavior: 'auto' });
      }
    });
    return;
  }

  // ถ้าเป็น FB ให้ตั้ง flag
  if (platform === 'fb') {
    window.manualDatePendingFB = true;
  }

  const initialScroll = window.scrollY;

  try {
    // 2) ตรวจว่าเลือกรายการในตารางหรือยัง
    const tableBody   = document.querySelector(`#${platform}-table tbody`);
    const selectedRow = tableBody ? tableBody.querySelector('tr.selected') : null;
    if (!selectedRow) {
      Swal.fire({
        icon: 'warning',
        title: 'กรุณาคลิกเลือกแถว',
        text:  'เลือกแถวในตารางที่ต้องการดึงวันที่ก่อนครับ',
        confirmButtonText: 'ตกลง',
        width: '380px',
        position: 'center',
        heightAuto: false,
        scrollbarPadding: false,
        didOpen: () => {
          // เน้นปุ่มยืนยัน
          const btn = document.querySelector('.swal2-confirm');
          if (btn) btn.style.background = '#f0ad4e';
          document.querySelector('.swal2-container').style.backdropFilter = 'blur(3px)';
          document.querySelector('.swal2-container').style.position = 'fixed';
        },
        willClose: () => {
          // ล้าง flag และ reset scroll
          if (platform === 'fb') window.manualDatePendingFB = false;
          window.scrollTo({ top: initialScroll, behavior: 'auto' });
        }
      });
      return;
    }

    // 3) แสดง Spinner ในคอลัมน์ Date ของแถวที่เลือก
    const dateCell = selectedRow.cells[3];
    if (dateCell) {
      dateCell.innerHTML = '<span class="spinner"></span>';
    }

    // 4) ยิง callback ไป Python ดึงวันที่
    const reelUrl = selectedRow.getAttribute('data-link');
    let data = { reelUrl };
    if (platform === 'fb') {
      data.profileUrl = document.getElementById('fb-profile-url').value;
      data.reelIndex  = parseInt(selectedRow.cells[0].innerText, 10) || 0;
    }
    console.log(`[DEBUG] Manual fetch for ${platform}`, data);
    window.pywebview.api.start_manual_date_fetch(platform, data);

  } catch (err) {
    console.error("[DEBUG] manualFetchDate ERROR", err, platform);
    // ถ้ามี error ล้าง flag ด้วย
    if (platform === 'fb') window.manualDatePendingFB = false;
    alert('เกิดข้อผิดพลาด ไม่สามารถดึงวันที่ได้');
  }
}



// --- Event Listeners (เหมือนเดิม) ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("[DEBUG] DOMContentLoaded");
    

    // ... โค้ดส่วนยืดหดคอลัมน์ และ คลิก/ดับเบิลคลิก เหมือนเดิมทั้งหมด ...
    const resizers = document.querySelectorAll('.resizer');
    resizers.forEach(resizer => {
        let startX, startWidth, th;
        resizer.addEventListener('mousedown', (e) => {
            th = e.target.parentElement;
            startX = e.pageX;
            startWidth = th.offsetWidth;
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
        function onMouseMove(e) {
            const newWidth = startWidth + (e.pageX - startX);
            if (newWidth > 40) {
                th.style.width = `${newWidth}px`;
            }
        }
        function onMouseUp() {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        }
    });


   // --- Logic การคลิก และ ดับเบิลคลิกบนตาราง (รวมไว้ในที่เดียว) ---
    ['fb-table', 'ig-table'].forEach(tableId => {
        const table = document.getElementById(tableId);
        if (!table) return;

        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        // **คนดักฟังที่ 1: การคลิกเพื่อเลือกแถว (Click)**
       

        // **คนดักฟังที่ 2: การดับเบิลคลิกเพื่อเปิดลิงก์ (Double Click)**
        tbody.addEventListener('dblclick', (event) => {
            const tr = event.target.closest('tr');
            if (!tr || tr.classList.contains('summary-row') || tr.cells.length < 2) return;
            
            // ใช้ data-link เพื่อความแม่นยำ
            const url = tr.getAttribute('data-link');

            if (url && url.startsWith('http') && window.pywebview) {
                window.pywebview.api.open_external_link(url);
            }
        });
    });

    showTab('fb');
    console.log("[DEBUG] DOMContentLoaded DONE");
});

// ==================================
// View Tab Switching Logic
// ==================================

function showView(platform, viewToShow) {
    // platform คือ 'fb' หรือ 'ig'
    // viewToShow คือ 'reels' หรือ 'log'

    // 1. หากลุ่มของปุ่มและเนื้อหาสำหรับ platform นั้นๆ
    const viewContainer = document.getElementById(`content-${platform}`);
    if (!viewContainer) return;

    const allTabs = viewContainer.querySelectorAll('.view-tab');
    const allContents = viewContainer.querySelectorAll('.view-content');

    // 2. รีเซ็ตสถานะทั้งหมดก่อน (เอา active/hidden ออก)
    allTabs.forEach(tab => tab.classList.remove('active'));
    allContents.forEach(content => content.classList.add('hidden'));

    // 3. ตั้งค่า Active ให้กับสิ่งที่ถูกเลือก
    // หาปุ่มที่ถูกคลิก แล้วใส่ class 'active'
    const selectedTab = viewContainer.querySelector(`.view-tab[onclick*="'${viewToShow}'"]`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // หาเนื้อหาที่ต้องแสดง แล้วเอา class 'hidden' ออก
    const selectedContent = document.getElementById(`${platform}-${viewToShow}-view`);
    if (selectedContent) {
        selectedContent.classList.remove('hidden');
    }
}

// ===== เพิ่ม function นี้ไว้ตรงไหนก็ได้ =====
function appendLog(platform, message) {
    const textarea = document.getElementById(`${platform}-log-textarea`);
    if (textarea) {
        textarea.value += (textarea.value ? "\n" : "") + message;
        textarea.scrollTop = textarea.scrollHeight;
    }
}
// ===== จบ function ที่เพิ่ม =====

// --- Multi-row selection, Enable/Disable Delete Button, Delete Logic ---

function setupTableRowSelection(platform) {
    const table = document.getElementById(`${platform}-table`);
    const deleteBtn = document.getElementById(`${platform}-delete-btn`);
    if (!table || !deleteBtn) return;

    let lastSelectedRowIndex = null;

    // Table row click event
    table.addEventListener('click', function (e) {
        const tbody = table.tBodies[0];
        const tr = e.target.closest('tr');
        if (!tr || tr.classList.contains('summary-row')) return;

        const allRows = Array.from(tbody.rows).filter(row => !row.classList.contains('summary-row'));
        const rowIndex = allRows.indexOf(tr);

        if (e.shiftKey && lastSelectedRowIndex !== null) {
            // Shift: select range
            let [start, end] = [lastSelectedRowIndex, rowIndex].sort((a, b) => a - b);
            allRows.forEach((row, i) => {
                if (i >= start && i <= end) row.classList.add('selected');
            });
        } else if (e.ctrlKey || e.metaKey) {
            // Ctrl: toggle selection (สามารถเลือกแยกแถว)
            tr.classList.toggle('selected');
            // ไม่ clear อันเดิม แต่ update index ล่าสุด
            lastSelectedRowIndex = rowIndex;
        } else {
            // Single click: clear ทั้งหมด เลือกใหม่
            allRows.forEach(row => row.classList.remove('selected'));
            tr.classList.add('selected');
            lastSelectedRowIndex = rowIndex;
        }
        updateDeleteBtnState(platform);
    });

    // Enable/Disable delete button
    function updateDeleteBtnState(platform) {
        const table = document.getElementById(`${platform}-table`);
        const btn = document.getElementById(`${platform}-delete-btn`);
        const selected = table.querySelectorAll('tbody tr.selected');
        btn.disabled = selected.length === 0;
    }

    // ลบแถวที่เลือก
    deleteBtn.onclick = function () {
        const selectedRows = Array.from(table.querySelectorAll('tbody tr.selected'));
        selectedRows.forEach(row => row.remove());
        updateDeleteBtnState(platform);
        recalculateTotalViews(platform);
    };

    updateDeleteBtnState(platform);
}

// เรียกใช้หลัง populate_initial_data ทุกครั้ง (หรือ DOMContentLoaded ครั้งแรก)
setupTableRowSelection('fb');
setupTableRowSelection('ig');

function enableCardCopy(cardSelector, valueId) {
  const card = document.querySelector(cardSelector);
  const valueEl = document.getElementById(valueId);

  if (card && valueEl) {
    card.style.cursor = 'pointer';
    card.title = 'คลิกเพื่อคัดลอกยอดวิว';

    card.addEventListener('click', () => {
      const value = valueEl.innerText.replace(/,/g, '').trim();
      if (!isNaN(value)) {
        navigator.clipboard.writeText(value);

        // แสดง popup "คัดลอกแล้ว"
        const toast = document.createElement('div');
        toast.innerText = '✅ คัดลอกแล้ว';
        toast.className = 'copy-toast';
        document.body.appendChild(toast);

        const rect = card.getBoundingClientRect();
        toast.style.top = `${rect.top - 10}px`;
        toast.style.left = `${rect.left + rect.width / 2}px`;

        setTimeout(() => {
          toast.remove();
        }, 1500);
      }
    });
  }
}

// เรียกใช้งาน
enableCardCopy('#content-ig .card', 'ig-total-views');
enableCardCopy('#content-fb .card', 'fb-total-views');




// --- Recalculate total views after row deletion ---
// --- Recalculate total views after row deletion ---
function recalculateTotalViews(platform) {
    const table = document.getElementById(`${platform}-table`);
    if (!table) return;

    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows).filter(row => !row.classList.contains('summary-row'));

    let sum = 0;
    let max = 0;

    rows.forEach(row => {
        const viewCell = row.cells[2];
        if (viewCell) {
            let txt = viewCell.innerText.replace(/[^\d]/g, '');
            let views = Number(txt) || 0;
            sum += views;
            if (views > max) max = views;
        }
    });

    const avg = rows.length > 0 ? Math.round(sum / rows.length) : 0;

    // === อัปเดต Summary Row ===
    const summaryRow = table.querySelector('.summary-row');
    if (summaryRow) {
        for (let i = 0; i < summaryRow.cells.length; i++) {
            if (summaryRow.cells[i].innerText.includes('รวมยอดวิว')) {
                if (summaryRow.cells[i + 1]) {
                    summaryRow.cells[i + 1].innerText = sum.toLocaleString();
                }
                break;
            }
        }
    }

    // === อัปเดต Status Label ===
    const statusLabel = document.getElementById(`${platform}-status-label`);
    if (statusLabel) {
        statusLabel.innerHTML = `<span style="color: #22c55e; font-weight: bold;">&#10003; [${platform.toUpperCase()}] ${rows.length} คลิป: ${sum.toLocaleString()} วิว</span>`;
    }

    // ✅ อัปเดต 3 การ์ดด้านบน
    document.getElementById(`${platform}-total-views`).innerText = sum.toLocaleString();
    document.getElementById(`${platform}-avg-views`).innerText = avg.toLocaleString();
    document.getElementById(`${platform}-max-views`).innerText = max.toLocaleString();
}

















