# วิธีสมัคร Gemini API Key (ฟรี)

## ข้อมูล Free Tier (มีนาคม 2026)

| Model | RPM | Requests/Day | Context |
|-------|-----|-------------|---------|
| **gemini-2.5-flash** | 10 | 250 | 1M tokens |
| **gemini-2.5-flash-lite** | 15 | 1,000 | 1M tokens |
| **gemini-2.5-pro** | 5 | 100 | 1M tokens |

App นี้ใช้ **gemini-2.5-flash** — ดีที่สุดสำหรับ balance ระหว่างคุณภาพและ quota

## ขั้นตอนการสมัคร

### 1. เข้า Google AI Studio
1. ไปที่ **https://aistudio.google.com/apikey**
2. ล็อกอินด้วย Google Account
3. คลิก **Create API Key**
4. เลือก Project (หรือสร้างใหม่)
5. **Copy API Key ทันที**

### 2. ตั้งค่า API Key ในโปรเจค
1. เปิดไฟล์ `.env` ในโฟลเดอร์โปรเจค
2. ใส่ API Key:
   ```
   GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. **บันทึกไฟล์**

### 3. ทดสอบ
```bash
python test_ai.py
python gpfinvest.py
```

เปิดเบราว์เซอร์ไปที่ `http://localhost:5000` — AI ทุก section ควรทำงานได้แล้ว!

## หมายเหตุ
- ไฟล์ `.env` **ห้ามอัปโหลดขึ้น Git** (มีอยู่ใน `.gitignore` แล้ว)
- API Key เป็นความลับ — อย่าแชร์ใครเห็น
- Free tier มี rate limit — ถ้าใช้เยอะอาจโดน 429 (rate limited)
