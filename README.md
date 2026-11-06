# Gemini Fast OS & Workspace Center (Modularized & Updated)

ระบบควบคุม Windows ความเร็วสูงด้วย Gemini AI & Local Ollama แบบแยกโครงสร้างไฟล์เป็นสัดส่วน

## 📁 โครงสร้างไฟล์ในโปรเจกต์
- `app.py`: ไฟล์หลักควบคุมหน้าตา UI และระบบหลักทั้งหมด
- `styles.py`: รวมแต่งดีไซน์ CSS, การตั้งค่า Theme สี และ Font
- `system_tools.py`: ฟังก์ชันควบคุมระบบ Windows (ปรับระดับเสียง 0 Delay ด้วย Win32 API, ปรับความสว่างหน้าจอทั้ง Desktop & Laptop, แคปจอ, สั่งงาน CMD/PowerShell, ตรวจคำสั่งอันตราย)
- `fast_path.py`: ระบบประมวลผลคำสั่งด่วน (Fast-Path) พร้อมระบบ Smart Fuzzy Matching (`difflib`)
- `ai_engine.py`: ตัวเชื่อมต่อกับ Gemini API และ Ollama Local AI Agent

## 🚀 วิธีการติดตั้งและรันใช้งาน

1. ติดตั้งไลบรารีที่จำเป็น (แนะนำให้เรียกผ่าน python -m pip):
   ```bash
   python -m pip install -r requirements.txt
   ```
   *(หรือสั่ง `py -m pip install -r requirements.txt` หากเครื่องหา pip ไม่เจอ)*

2. รันแอปพลิเคชัน:
   ```bash
   streamlit run app.py
   ```

## 🎙️ สั่งงานด้วยเสียงต่อเนื่อง

- กด **เริ่มฟังต่อเนื่อง** เพื่อพูดสั่งงานได้หลายวลีโดยไม่ต้องกดไมค์ซ้ำ และกด **หยุดฟัง** เมื่อใช้งานเสร็จ
- ระบบใช้ตัวรู้จำเสียงตามโหมดที่เลือกไว้ตอนเริ่มฟัง: Google Speech Recognition ในโหมดออนไลน์ หรือ Whisper ในโหมดออฟไลน์
- หากเปลี่ยนโหมดออนไลน์/ออฟไลน์ระหว่างฟัง ให้หยุดแล้วเริ่มใหม่เพื่อใช้โหมดที่เปลี่ยน
- คำสั่งที่มีผลต่อระบบยังต้องยืนยันผ่านหน้าต่างยืนยันเดิม
