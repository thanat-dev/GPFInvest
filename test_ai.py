import os
import google.generativeai as genai

API_KEY = os.environ.get("GEMINI_API_KEY")
print(f"API KEY present: {bool(API_KEY)}")
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        
        # Test Chat logic
        print("Testing Chat logic...")
        history = []
        formatted_history = []
        for h in history:
            formatted_history.append({
                "role": h["role"],
                "parts": [h["parts"]]
            })

        system_instruction = "คุณคือ น้อง กบข. AI"
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        
        chat = model.start_chat(history=formatted_history)
        response = chat.send_message("สวัสดีครับ")
        print("Chat response:", response.text)
        
        # Test Simulator logic
        print("Testing Simulate logic...")
        prompt = '''
วิเคราะห์สถานการณ์สมมติทางเศรษฐกิจต่อไปนี้: "ถ้าเกิดสงคราม"
และประเมินผลกระทบที่อาจเกิดขึ้นกับสินทรัพย์ 3 ประเภท (หุ้นต่างประเทศ, หุ้นไทย, ทองคำ)
ให้ตอบเป็น JSON เท่านั้น โดยระบุตัวเลขประเมินผลกระทบเป็นเปอร์เซ็นต์ (% impact) จาก -100 ถึง +100
ตัวอย่าง: หุ้นตกรุนแรงอาจจะเป็น -20, ทองคำขึ้นอาจจะเป็น +5

รูปแบบ JSON:
{
  "equity_intl_impact": 0.0,
  "equity_thai_impact": 0.0,
  "gold_impact": 0.0,
  "reasoning": "อธิบายเหตุผลสั้นๆ 1 ประโยค"
}
'''
        sim_response = model.generate_content(prompt)
        print("Simulate response:", sim_response.text)

    except Exception as e:
        print("Error:", e)
