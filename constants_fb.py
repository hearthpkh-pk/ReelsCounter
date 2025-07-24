# constants_FB.py (Updated)

# === View Count XPath Selector (v2 - Handles unit-less numbers) ===
XPATH_VIEW_COUNT = (
    './/span[contains(@class, "x1lliihq") and ('
    # --- Existing checks for units ---
    'contains(translate(., "KMBกขคฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮABCDEFGHIJKLMNOPQRSTUVWXYZ", "kmb"), "k") or '
    'contains(normalize-space(.), "ครั้ง") or '
    'contains(normalize-space(.), "พัน") or '
    'contains(normalize-space(.), "หมื่น") or '
    'contains(normalize-space(.), "แสน") or '
    'contains(normalize-space(.), "ล้าน") or '
    'contains(normalize-space(.), "views") or '
    # --- Existing check for decimals ---
    '(string-length(normalize-space(text())) > 1 and contains(normalize-space(text()), ".") and translate(normalize-space(text()), "0123456789.", "") = "") or '
    # --- NEW: Check for pure, unit-less numbers ---
    '(translate(normalize-space(.), "0123456789", "") = "" and string-length(normalize-space(.)) > 0)'
    # --- End of checks ---
    ') and string-length(normalize-space(text())) > 0 and string-length(normalize-space(text())) < 25]'
    '| .//span[contains(@class, "x193iq5w")]/span[contains(@class, "x1lliihq") '
    'and string-length(normalize-space(text())) > 0 and string-length(normalize-space(text())) < 25]'
    '| .//span[(contains(@aria-label, "ครั้งที่ดู") or contains(@aria-label, "views")) '
    'and string-length(normalize-space(@aria-label)) < 50]'
    # ✅ Fallback: รองรับภาษาอังกฤษล้วน เช่น 1.2K, 3M, 789
'| .//span['
    'translate(normalize-space(text()), "0123456789KMBkmb.", "") = "" and '
    'string-length(normalize-space(text())) <= 10'
']'
)

# ===== Facebook Reel Post Date XPaths =====
# (ส่วนนี้ไม่มีการเปลี่ยนแปลง)
XPATH_DATE_TEXT = (
    "./abbr[@title] | "
    "./span[contains(text(),'ม.ค.') or contains(text(),'ก.พ.') or contains(text(),'มี.ค.') or "
    "contains(text(),'เม.ย.') or contains(text(),'พ.ค.') or contains(text(),'มิ.ย.') or "
    "contains(text(),'ก.ค.') or contains(text(),'ส.ค.') or contains(text(),'ก.ย.') or "
    "contains(text(),'ต.ค.') or contains(text(),'พ.ย.') or contains(text(),'ธ.ค.') or "
    "contains(text(),'นาที') or contains(text(),'ชั่วโมง') or contains(text(),'โพสต์เมื่อ') or "
    "contains(text(),'202') or contains(text(),'256') or contains(text(),'/') or "
    "contains(text(),'ago') or contains(text(),'yesterday')]"
)

XPATHS_PRIORITY_LIST = [
    "./span[contains(text(), '..')]",
    "./div[contains(text(), 'โพสต์เมื่อ')]",
    "./time",
    "./span",
    "./a",
    "./div"
]