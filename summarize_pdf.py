# pyre-ignore-all-errors
import google.generativeai as genai
import os
import sys

print('Configuring Gemini...')
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

try:
    print('Reading PDF...')
    with open('C:/Users/tanat/Documents/GPFInvest/MembershipGuide_2567.pdf', 'rb') as f:
        pdf_data = f.read()

    print('Sending to Gemini...')
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = '''
    จงสรุปเนื้อหาสำคัญจากคู่มือสมาชิก กบข. เล่มนี้ และเสนอแนะว่า 
    จากเนื้อหาในเล่มนี้ มีฟีเจอร์หรือแง่มุมไหนบ้างที่ควรนำมาพัฒนาต่อยอดใน AI Robo-Advisor Project ที่กำลังทำอยู่ 
    (ตอนนี้เรามีฟีเจอร์ เลือกแผน 2 กองทุน, วิเคราะห์ข่าว, Simulator และ Chatbot แล้ว)
    ขอเป็น Bullet point สั้นๆ เข้าใจง่าย
    '''
    
    response = model.generate_content([
        {'mime_type': 'application/pdf', 'data': pdf_data},
        prompt
    ])
    
    with open('pdf_summary.txt', 'w', encoding='utf-8') as f:
        f.write(response.text)
        
    print('Done! Saved to pdf_summary.txt')

except Exception as e:
    print('Error:', e)
