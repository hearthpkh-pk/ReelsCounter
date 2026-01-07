# Documentation Directory

เอกสารและคู่มือสำหรับผู้ใช้และ developers

## ไฟล์สำหรับผู้ใช้:

### `USER_TROUBLESHOOTING_GUIDE.md` ⭐ สำคัญ
- คู่มือแก้ปัญหาสำหรับผู้ใช้ที่เบราว์เซอร์ไม่เด้ง
- มีวิธีแก้ไขทั้งอัตโนมัติและด้วยตนเอง
- **ควรให้ผู้ใช้อ่านไฟล์นี้เมื่อมีปัญหา**

### `BROWSER_FIX_README.md`
- รายละเอียดเทคนิคของการแก้ปัญหา
- อธิบายสาเหตุและวิธีแก้ไข
- สำหรับผู้ใช้ที่ต้องการเข้าใจลึก

## ไฟล์สำหรับ Developers:

### `FIX_SUMMARY.md`
- สรุปการแก้ไขที่ทำไป
- อธิบายปัญหาที่เกิดจาก Kiro IDE autofix
- รายละเอียดการแก้ไข

### `DEPLOYMENT_CONFIDENCE_REPORT.md`
- รายงานความมั่นใจในการปล่อยแพตช์
- ผลการทดสอบและการวิเคราะห์ความเสี่ยง
- คำแนะนำการปล่อย

## การใช้งาน:

### สำหรับผู้ใช้ที่มีปัญหา:
1. อ่าน `USER_TROUBLESHOOTING_GUIDE.md`
2. ทำตามขั้นตอนแก้ไข
3. หากต้องการรายละเอียดเพิ่มเติม อ่าน `BROWSER_FIX_README.md`

### สำหรับ Developers:
1. อ่าน `FIX_SUMMARY.md` เพื่อเข้าใจการแก้ไข
2. อ่าน `DEPLOYMENT_CONFIDENCE_REPORT.md` เพื่อดูผลการทดสอบ

## หมายเหตุ:
- ไฟล์ `USER_TROUBLESHOOTING_GUIDE.md` ควรรวมใน distribution
- ไฟล์อื่นๆ เป็น optional สำหรับ advanced users