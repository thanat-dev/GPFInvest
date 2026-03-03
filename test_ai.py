import os
import sys

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.environ.get("GEMINI_API_KEY")
print(f"GEMINI_API_KEY present: {bool(API_KEY)}")

if not API_KEY:
    print("ERROR: No GEMINI_API_KEY found. Please set it in .env file.")
    print("Get your free key at: https://aistudio.google.com/apikey")
    sys.exit(1)

try:
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)

    MODEL_NAME = "gemini-2.5-flash"

    # Test Chat logic
    print(f"Testing Chat logic with {MODEL_NAME}...")
    system_instruction = "คุณคือ น้อง กบข. AI"
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_instruction
    )

    chat = model.start_chat(history=[])
    response = chat.send_message("สวัสดีครับ")
    print("Chat response:", response.text[:200])

    # Test Generate Content logic
    print(f"\nTesting Generate Content with {MODEL_NAME}...")
    prompt = '''
วิเคราะห์สถานการณ์สมมติทางเศรษฐกิจต่อไปนี้: "ถ้าเกิดสงคราม"
ให้ตอบเป็น JSON เท่านั้น:
{
  "equity_intl_impact": 0.0,
  "equity_thai_impact": 0.0,
  "gold_impact": 0.0,
  "reasoning": "อธิบายเหตุผลสั้นๆ 1 ประโยค"
}
'''
    sim_response = model.generate_content(prompt)
    print("Simulate response:", sim_response.text[:300])

    print(f"\n✅ All tests passed! Gemini AI ({MODEL_NAME}) is working correctly.")

except ImportError:
    print("ERROR: google-generativeai not installed. Run: pip install google-generativeai")
except Exception as e:
    print(f"ERROR: {e}")
