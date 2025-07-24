# ศูนย์รวม XPath และค่าคงที่ต่างๆสำหรับ IG
# *** เวลา IG อัปเดต ให้มาแก้ไขที่นี่เป็นหลัก ***
# ===================================================================

# --- XPath for View Count ---
# List of XPaths to find the view count on a reel thumbnail, ordered from most specific to most general.
FALLBACK_XPATHS_IG = [
    # Most specific: Looks for a span that is a direct child of the link element 'a'. This is often the case.
    './span', 
    # Looks for a span inside any div, which is inside the link. Good fallback.
    './/div/span',
    # Looks for a span that has a specific class often used for meta-data like views or likes.
    './/span[contains(@class, "x1jgp53x")]',
    # Looks for any span with text containing digits. This is less specific but a good catch-all.
    './/span[contains("0123456789", substring(text(), 1, 1))]',
    # Original text-based fallbacks, now with lower priority.
    './/span[contains(text(), "views") or contains(text(), "การดู")]',
    './/span[string-length(normalize-space(text())) > 0 and string-length(normalize-space(text())) < 12]'
]

# --- XPath for Post Date ---
# XPath to find the <time> element on a single reel's page.
XPATH_POST_DATE_IG = '//time[@datetime]'
# เราจะเอารูปแบบที่เจาะจงและรวดเร็วกลับมา โดยมีรูปแบบที่ครอบคลุมเป็นแผนสำรอง (ใช้ | เชื่อม)
XPATH_POST_DATE_IG = '//time[@datetime and (contains(@class, "x1p4m5qa") or contains(@class, "_aaqe"))] | //time[@datetime]'

# ===================================================================
# END: XPATH & CONFIGURATION CONSTANTS
# ===================================================================