#!/usr/bin/env python3
# pyre-ignore-all-errors
# -*- coding: utf-8 -*-
"""
GPF Investment Analysis Web Application
วิเคราะห์แผนการลงทุน กบข. — ข้อมูลจริงจาก Factsheet ณ 10 พ.ย. 2568

Run:  pip install flask
      python gpfinvest.py
Open: http://localhost:5000

PATCH NOTE: ลบ yfinance dependency ออก → ใช้ TradingView Widgets (client-side)
            แก้ปัญหากราฟและ Technical Sentiment ไม่แสดงผล
"""

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, render_template_string
import datetime
import itertools
import urllib.request
import xml.etree.ElementTree as ET
import os
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

app = Flask(__name__)

# =========================================================================
# ข้อมูลจริงจาก PDF Factsheet กบข. (ข้อมูล ณ วันที่ 10 พฤศจิกายน 2568)
# =========================================================================
FUNDS = [
    {
        "id": "deposit_short",
        "name_th": "แผนเงินฝากและตราสารหนี้ระยะสั้น",
        "name_en": "Deposit & Short-Term Bond",
        "icon": "💰",
        "color": "#43A047",
        "risk_level": 1,
        "risk_label": "ต่ำมาก",
        "risk_gauge": 1,
        "started": "27 ก.ย. 2553",
        "desc": "ลงทุนในเงินฝากและตราสารหนี้ไทยระยะสั้น กลุ่มอ่อนไหวต่ออัตราดอกเบี้ย อายุคงเหลือไม่เกิน 1 ปี สภาพคล่องสูง เน้นรักษาเงินต้น",
        "assets": {"ตราสารหนี้ตลาดเงินไทย": 100},
        "avg_3y": 1.83, "avg_5y": 1.40, "since_inception": 1.81,
        "r2564": 0.66, "r2565": 0.64, "r2566": 1.65, "r2567": 2.44, "r_jun68": 1.07,
        "max_drawdown": -0.02,
        "suitable": "สมาชิกใกล้เกษียณ ต้องการรักษาเงินต้น รับความเสี่ยงได้น้อยมาก",
    },
    {
        "id": "fixed_income",
        "name_th": "แผนตราสารหนี้",
        "name_en": "Fixed Income",
        "icon": "📄",
        "color": "#1E88E5",
        "risk_level": 4,
        "risk_label": "ปานกลาง",
        "risk_gauge": 4,
        "started": "25 ส.ค. 2553",
        "desc": "ลงทุนในตราสารหนี้ไทยทั้งภาครัฐและเอกชน เน้นรักษามูลค่าเงินลงทุน ให้ไม่ต่ำไปกว่าอัตราเงินเฟ้อในระยะยาว",
        "assets": {"ตราสารหนี้ภาครัฐไทย": 40, "ตราสารหนี้ระยะสั้นไทย": 35, "ตราสารหนี้เอกชนไทย": 25},
        "avg_3y": 3.43, "avg_5y": 2.11, "since_inception": 2.75,
        "r2564": 0.05, "r2565": 0.54, "r2566": 1.61, "r2567": 4.06, "r_jun68": 2.76,
        "max_drawdown": -2.43,
        "suitable": "สมาชิกที่ต้องการกำหนดสัดส่วนเอง รับความผันผวนจากราคาสินทรัพย์ได้น้อย",
    },
    {
        "id": "fixed_intl",
        "name_th": "แผนตราสารหนี้ต่างประเทศ",
        "name_en": "International Bond",
        "icon": "🌐",
        "color": "#5E35B1",
        "risk_level": 5,
        "risk_label": "ปานกลาง-สูง",
        "risk_gauge": 5,
        "started": "8 ธ.ค. 2565",
        "desc": "ลงทุนในตราสารหนี้ภาครัฐโลกและตราสารหนี้เอกชนโลก (Investment Grade) มีความผันผวนมากกว่าตราสารหนี้ไทย รวมความเสี่ยงอัตราแลกเปลี่ยน",
        "assets": {"ตราสารหนี้ภาครัฐโลก": 70, "ตราสารหนี้เอกชนโลก": 30},
        "avg_3y": None, "avg_5y": None, "since_inception": 0.90,
        "r2564": None, "r2565": -1.64, "r2566": 2.13, "r2567": 0.17, "r_jun68": 1.68,
        "max_drawdown": -5.30,
        "suitable": "สมาชิกที่ต้องการกระจายลงทุนในตราสารหนี้ต่างประเทศ รับความผันผวนปานกลาง-สูงได้",
    },
    {
        "id": "gold",
        "name_th": "แผนทองคำ",
        "name_en": "Gold",
        "icon": "🥇",
        "color": "#FF8F00",
        "risk_level": 5,
        "risk_label": "ปานกลาง-สูง",
        "risk_gauge": 5,
        "started": "8 ธ.ค. 2565",
        "desc": "ลงทุนในหน่วยลงทุนของกองทุนรวมทองคำในต่างประเทศ เพื่อสร้างผลตอบแทนในระยะยาวและช่วยกระจายความผันผวน",
        "assets": {"ทองคำ": 100},
        "avg_3y": None, "avg_5y": None, "since_inception": 20.47,
        "r2564": None, "r2565": 0.93, "r2566": 8.46, "r2567": 24.67, "r_jun68": 18.08,
        "max_drawdown": -8.48,
        "suitable": "สมาชิกที่ต้องการป้องกันเงินเฟ้อ กระจายพอร์ต รับความผันผวนสูงจากราคาทองคำโลกได้",
    },
    {
        "id": "reit_thai",
        "name_th": "แผนกองทุนอสังหาริมทรัพย์ไทย",
        "name_en": "Thai REITs & Property",
        "icon": "🏢",
        "color": "#6D4C41",
        "risk_level": 6,
        "risk_label": "สูง",
        "risk_gauge": 6,
        "started": "31 ก.ค. 2563",
        "desc": "ลงทุนในกองทุนรวมอสังหาริมทรัพย์และกองทุนรวมโครงสร้างพื้นฐานไทยที่จดทะเบียนในตลาดหลักทรัพย์",
        "assets": {"อสังหาริมทรัพย์ไทย": 100},
        "avg_3y": -1.46, "avg_5y": None, "since_inception": -3.94,
        "r2564": 2.87, "r2565": -7.85, "r2566": -4.35, "r2567": 6.06, "r_jun68": -6.89,
        "max_drawdown": -26.87,
        "suitable": "สมาชิกที่ต้องการกระจายลงทุนในอสังหาริมทรัพย์ มีระยะเวลาลงทุนยาว",
    },
    {
        "id": "equity_intl",
        "name_th": "แผนหุ้นต่างประเทศ",
        "name_en": "International Equity",
        "icon": "🌍",
        "color": "#1565C0",
        "risk_level": 6,
        "risk_label": "สูง",
        "risk_gauge": 6,
        "started": "30 พ.ย. 2564",
        "desc": "ลงทุนในหุ้นต่างประเทศโดยกระจายการลงทุนไปในหุ้นโลกทั้งตลาดพัฒนาแล้วและตลาดเกิดใหม่ เน้นสร้างผลตอบแทนสูงในระยะยาว",
        "assets": {"ตราสารทุนโลก ตลาดพัฒนาแล้ว": 65, "ตราสารทุนโลก ตลาดเกิดใหม่": 35},
        "avg_3y": 9.90, "avg_5y": None, "since_inception": 1.46,
        "r2564": 0.39, "r2565": -22.87, "r2566": 10.10, "r2567": 15.45, "r_jun68": 7.04,
        "max_drawdown": -23.57,
        "suitable": "สมาชิกที่ต้องการผลตอบแทนสูงจากหุ้นต่างประเทศ รับความผันผวนสูงได้ ลงทุนระยะยาว",
    },
    {
        "id": "equity_thai",
        "name_th": "แผนหุ้นไทย",
        "name_en": "Thai Equity",
        "icon": "🇹🇭",
        "color": "#E53935",
        "risk_level": 7,
        "risk_label": "สูงมาก",
        "risk_gauge": 7,
        "started": "8 ม.ค. 2562",
        "desc": "ลงทุนในหุ้นจดทะเบียนในตลาดหลักทรัพย์แห่งประเทศไทย มีเป้าหมายพื้นฐานดีและสภาพคล่อง เน้นสร้างผลตอบแทนสูงในระยะยาว",
        "assets": {"ตราสารทุนไทย": 100},
        "avg_3y": -6.93, "avg_5y": -0.77, "since_inception": -5.03,
        "r2564": 15.73, "r2565": 6.55, "r2566": -11.45, "r2567": -0.36, "r_jun68": -15.10,
        "max_drawdown": -37.58,
        "suitable": "สมาชิกที่ต้องการลงทุนในหุ้นไทยโดยเฉพาะ รับความผันผวนสูงมากได้ ลงทุนระยะยาว",
    },
    {
        "id": "growth35",
        "name_th": "แผนเชิงรุก 35",
        "name_en": "Growth 35",
        "icon": "📈",
        "color": "#00897B",
        "risk_level": 5,
        "risk_label": "ปานกลาง-สูง",
        "risk_gauge": 5,
        "started": "25 ส.ค. 2553",
        "desc": "ลงทุนในสินทรัพย์หลายประเภท กลุ่มรองรับการเติบโตประมาณ 35% เพิ่มโอกาสสร้างผลตอบแทนให้ชนะอัตราเงินเฟ้อในระยะยาว",
        "assets": {"กลุ่มรองรับการเติบโต": 35, "กลุ่มอ่อนไหวต่อดอกเบี้ย": 50, "กลุ่มรองรับเงินเฟ้อ": 9, "กลุ่มรองรับความผันผวน": 6},
        "avg_3y": 2.71, "avg_5y": 3.46, "since_inception": 4.84,
        "r2564": 8.32, "r2565": -3.58, "r2566": 1.46, "r2567": 5.13, "r_jun68": 0.28,
        "max_drawdown": -8.13,
        "suitable": "สมาชิกที่ต้องการผลตอบแทนสูงกว่าแผนเชิงรุก 20 รับความเสี่ยงปานกลาง-สูงได้",
    },
    {
        "id": "basic",
        "name_th": "แผนลงทุนพื้นฐานทั่วไป",
        "name_en": "Basic Plan",
        "icon": "📊",
        "color": "#F9A825",
        "risk_level": 5,
        "risk_label": "ปานกลาง-สูง",
        "risk_gauge": 5,
        "started": "27 มี.ค. 2540",
        "desc": "แผนแรกตั้งแต่เริ่มจัดตั้ง กบข. ลงทุนในสินทรัพย์หลายประเภท กลุ่มรองรับการเติบโต ~39% ความผันผวนปานกลาง-สูง",
        "assets": {"กลุ่มรองรับการเติบโต": 39, "กลุ่มอ่อนไหวต่อดอกเบี้ย": 43, "กลุ่มรองรับเงินเฟ้อ": 11, "กลุ่มรองรับความผันผวน": 7},
        "avg_3y": 2.42, "avg_5y": 2.96, "since_inception": 5.57,
        "r2564": 5.83, "r2565": -1.54, "r2566": 1.46, "r2567": 3.50, "r_jun68": 1.19,
        "max_drawdown": -5.46,
        "suitable": "สมาชิกที่ต้องการผลตอบแทนและความผันผวนระดับปานกลาง-สูง",
    },
    {
        "id": "growth65",
        "name_th": "แผนเชิงรุก 65",
        "name_en": "Growth 65",
        "icon": "🚀",
        "color": "#D84315",
        "risk_level": 5,
        "risk_label": "ปานกลาง-สูง",
        "risk_gauge": 5,
        "started": "12 เม.ย. 2556",
        "desc": "ลงทุนในสินทรัพย์หลายประเภท กลุ่มรองรับการเติบโตประมาณ 65% เพิ่มโอกาสสร้างผลตอบแทนสูงชนะอัตราเงินเฟ้อ",
        "assets": {"กลุ่มรองรับการเติบโต": 65, "กลุ่มอ่อนไหวต่อดอกเบี้ย": 20, "กลุ่มรองรับเงินเฟ้อ": 10, "กลุ่มรองรับความผันผวน": 5},
        "avg_3y": 4.00, "avg_5y": 5.01, "since_inception": 5.54,
        "r2564": 12.83, "r2565": -8.68, "r2566": 2.45, "r2567": 8.26, "r_jun68": 0.81,
        "max_drawdown": -12.39,
        "suitable": "สมาชิกที่ต้องการผลตอบแทนสูง ลงทุนระยะยาว รับความเสี่ยงระดับปานกลาง-สูงได้",
    },
    {
        "id": "shariah",
        "name_th": "แผนการลงทุนตามหลักชะรีอะฮ์",
        "name_en": "Shariah",
        "icon": "☪️",
        "color": "#4E342E",
        "risk_level": 5,
        "risk_label": "ปานกลาง-สูง",
        "risk_gauge": 5,
        "started": "11 ธ.ค. 2568",
        "desc": "ลงทุนตามหลักชะรีอะฮ์ของศาสนาอิสลาม ในตราสารทุนและตราสารหนี้ที่สอดคล้องกับหลักศาสนา",
        "assets": {"กลุ่มรองรับการเติบโต": 60, "กลุ่มรองรับเงินเฟ้อ": 40},
        "avg_3y": 1.75, "avg_5y": 6.69, "since_inception": None,
        "r2564": None, "r2565": None, "r2566": 13.45, "r2567": 3.10, "r_jun68": None,
        "max_drawdown": -9.59,
        "suitable": "สมาชิกที่ต้องการลงทุนเป็นไปตามหลักชะรีอะฮ์ของศาสนาอิสลาม",
    },
]

MARKET_OUTLOOK = {
    "date": "มีนาคม 2569",
    "global_economy": "เศรษฐกิจโลกมีแนวโน้มทยอยฟื้นตัวในลักษณะ Soft Landing ท่ามกลางวัฏจักรดอกเบี้ยขาลงของธนาคารกลางหลัก (FED, ECB) ซึ่งเป็นปัจจัยบวกต่อสินทรัพย์เสี่ยงและตราสารหนี้โลกในระยะกลาง",
    "thai_economy": "ฟื้นตัวอย่างค่อยเป็นค่อยไป ได้รับแรงหนุนจากภาคการท่องเที่ยวและการเปิดประเทศ แต่ยังมีแรงกดดันจากหนี้ครัวเรือนระดับสูง ตลาดหุ้นไทยฟื้นตัวอย่างจำกัดเมื่อเทียบกับภูมิภาค",
    "gold_view": "ทิศทางดอกเบี้ยขาลง ประกอบกับความตึงเครียดทางภูมิรัฐศาสตร์รบกวนตลาดอย่างต่อเนื่อง ทำให้ทองคำยังคงมีความสำคัญในฐานะสินทรัพย์ปลอดภัย (Safe Haven) ของโลก",
    "strategy": "แนะนำเพิ่มสัดส่วน 'หุ้นต่างประเทศ' เพื่อรับโอกาสเติบโตจากกลุ่มเทคโนโลยีและนวัตกรรม พร้อมแบกสัดส่วน 'ทองคำ' และ 'ตราสารหนี้' เพื่อรักษาสมดุล ลดความผันผวนรวมของพอร์ต"
}

USER_PORTFOLIO = {
    "account_no": "18022041",
    "as_of": "25 กุมภาพันธ์ 2569",
    "risk_assessment": "สูง",
    "risk_valid_until": "18/11/2569",
    "total": 284414.68,
    "principal": 203640.60,
    "profit": 80774.08,
    "profit_pct": round(80774.08 / 203640.60 * 100, 2),
    "member_total": 122899.61,
    "gov_total": 161515.07,
    "changes_remaining": 11,
    "holdings": [
        {"plan": "แผนหุ้นต่างประเทศ", "id": "equity_intl", "units": 6237.8818,
         "nav": 34.2212, "value": 213467.80, "pct": 75.07},
        {"plan": "แผนทองคำ", "id": "gold", "units": 1047.5947,
         "nav": 67.7236, "value": 70946.88, "pct": 24.93},
    ],
}


import json as _json

# ──────────────────────────────────────────────────────────────────
# SET & Thai REIT data — ใช้ yfinance (pip install yfinance)
# หรือ fallback ผ่าน requests session / SET official API
# ──────────────────────────────────────────────────────────────────

def _fetch_set_yfinance():
    """ดึง SET Index ด้วย yfinance (จัดการ Yahoo crumb อัตโนมัติ)"""
    import yfinance as yf
    import pandas as pd
    t = yf.Ticker("^SET.BK")
    hist = t.history(period="3mo", interval="1d")
    if hist.empty:
        raise ValueError("Empty history for ^SET.BK")
    fi = t.fast_info
    prices = []
    for dt, row in hist.iterrows():
        d = dt.strftime("%Y-%m-%d") if hasattr(dt, 'strftime') else str(dt)[:10]
        prices.append({"date": d, "close": round(float(row["Close"]), 2)})
    price = getattr(fi, "last_price", None) or (prices[-1]["close"] if prices else None)
    prev  = getattr(fi, "previous_close", None) or (prices[-2]["close"] if len(prices) > 1 else price)
    chg   = round(price - prev, 2) if price and prev else 0
    pct   = round((chg / prev) * 100, 2) if prev else 0
    return {"symbol":"^SET.BK","name":"SET Index","price":price,"prev":prev,
            "change":chg,"pct":pct,"currency":"THB","prices":prices,"ok":True}


def _fetch_set_requests():
    """Fallback: urllib กับ Yahoo Finance API"""
    import urllib.request
    import json
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ESET.BK?interval=1d&range=3mo"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
        data = json.loads(r.read())
        
    result = data["chart"]["result"][0]
    meta   = result["meta"]
    ts     = result["timestamp"]
    closes = result["indicators"]["quote"][0].get("close", [])
    prices = []
    for t_ts, c in zip(ts, closes):
        if c is not None:
            import datetime as _dt
            d = _dt.datetime.utcfromtimestamp(t_ts).strftime("%Y-%m-%d")
            prices.append({"date": d, "close": round(c, 2)})
            
    price = meta.get("regularMarketPrice")
    prev  = meta.get("previousClose", 0)
    chg   = round(price - prev, 2) if price else 0
    pct   = round((chg / prev) * 100, 2) if prev else 0
    
    return {"symbol":"^SET.BK","name":"SET Index","price":price,"prev":prev,
            "change":chg,"pct":pct,"currency":"THB","prices":prices,"ok":True}


def _fetch_set_official():
    """Fallback: SET official API (ไม่ต้อง auth, ข้อมูลเปิด)"""
    endpoints = [
        "https://www.set.or.th/api/set/index/info/SET?lang=en",
        "https://www.set.or.th/api/set/index/chart/price/SET?period=3M&accumulated=false&lang=en",
    ]
    hdrs = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.set.or.th/",
        "X-Requested-With": "XMLHttpRequest",
    }
    prices = []
    snapshot = {}
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=6) as r:
                d = _json.loads(r.read())
            # chart endpoint returns list of {date, value}
            if isinstance(d, list) and len(d) > 0 and "value" in d[0]:
                prices = [{"date": x.get("datetime","")[:10], "close": x.get("value",0)} for x in d]
            elif isinstance(d, dict):
                snapshot = d
        except Exception:
            pass
    price = snapshot.get("close") or snapshot.get("last") or (prices[-1]["close"] if prices else None)
    prev  = snapshot.get("prior") or snapshot.get("previousClose") or (prices[-2]["close"] if len(prices)>1 else price)
    chg   = round(float(price) - float(prev), 2) if price and prev else 0
    pct   = round((chg / float(prev)) * 100, 2) if prev else 0
    if not prices and not price:
        raise ValueError("SET official API returned no data")
    return {"symbol":"^SET.BK","name":"SET Index","price":price,"prev":prev,
            "change":chg,"pct":pct,"currency":"THB","prices":prices[-60:],"ok":True}


def _fetch_reit_yfinance(symbol, label):
    import yfinance as yf
    t  = yf.Ticker(symbol)
    fi = t.fast_info
    price = getattr(fi, "last_price", None)
    prev  = getattr(fi, "previous_close", None)
    chg   = round(price - prev, 2) if price and prev else 0
    pct   = round((chg / prev) * 100, 2) if prev else 0
    return {"symbol":symbol,"label":label,"price":price,"change":chg,"pct":pct,"ok":True}


def _fetch_reit_urllib(symbol, label):
    """Fallback urllib สำหรับ REIT .BK"""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           "?interval=1d&range=5d&includePrePost=false")
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"}
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=8) as r:
        data = _json.loads(r.read())
    meta   = data["chart"]["result"][0]["meta"]
    price  = meta.get("regularMarketPrice")
    prev   = meta.get("previousClose", 0)
    chg    = round(price - prev, 2) if price else 0
    pct    = round((chg / prev) * 100, 2) if prev else 0
    return {"symbol":symbol,"label":label,"price":price,"change":chg,"pct":pct,"ok":True}


_THAI_REITS = [
    {"symbol": "SSPF.BK",   "label": "SSPF REIT"},
    {"symbol": "WHART.BK",  "label": "WHA Premium FREEHOLD"},
    {"symbol": "LHPF.BK",   "label": "LH Shopping Centers REIT"},
    {"symbol": "TPRIME.BK", "label": "Ticon PRIME FREEHOLD"},
    {"symbol": "IMPACT.BK", "label": "Impact Growth REIT"},
]


@app.route("/api/market")
def api_market():
    """Return SET Index + Thai REIT quotes as JSON."""
    from flask import jsonify

    # ── SET Index: ลอง 3 วิธีเรียงลำดับ ──
    set_data = None
    for fn in [_fetch_set_yfinance, _fetch_set_requests, _fetch_set_official]:
        try:
            set_data = fn()
            if set_data.get("ok") and (set_data.get("prices") or set_data.get("price")):
                break
        except Exception as e:
            print(f"[SET fallback] {fn.__name__}: {e}")
            continue
    if not set_data:
        set_data = {"symbol":"^SETI","name":"SET Index","ok":False,
                    "error":"ไม่สามารถดึงข้อมูลได้","prices":[],"price":None,"pct":None}

    # ── Thai REITs: yfinance ก่อน, urllib fallback ──
    reits = []
    for r in _THAI_REITS:
        d = None
        for fn in [_fetch_reit_yfinance, _fetch_reit_urllib]:
            try:
                d = fn(r["symbol"], r["label"])
                break
            except Exception as e:
                print(f"[REIT fallback] {r['symbol']} {fn.__name__}: {e}")
        if not d:
            d = {"symbol":r["symbol"],"label":r["label"],"ok":False,"price":None,"pct":None}
        reits.append(d)

    return jsonify({"set_index": set_data, "reits": reits})


# =========================================================================
# Realtime News Fetcher + Pagination
# =========================================================================
NEWS_CACHE = {"data": [], "last_fetch": None}

def fetch_all_news():
    from email.utils import parsedate_to_datetime
    from datetime import timezone, timedelta
    urls = [
        "https://www.kaohoon.com/feed",
        "https://mgronline.com/rss/stockmarket.xml",
        "https://www.thansettakij.com/rss/finance",
        "https://www.efinancethai.com/rss/rss_news.xml"
    ]
    news_items = []
    thirty_days_ago = datetime.datetime.now(timezone.utc) - timedelta(days=30)
    
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                tree = ET.parse(response)
                root = tree.getroot()
                
                for item in root.findall('./channel/item'):
                    title = item.find('title')
                    link = item.find('link')
                    pubDate = item.find('pubDate')
                    
                    t_text = title.text.strip() if title is not None and title.text else ""
                    l_text = link.text.strip() if link is not None and link.text else ""
                    pd_text = pubDate.text.strip() if pubDate is not None and pubDate.text else ""
                    
                    if t_text and l_text and pd_text:
                        try:
                            dt = parsedate_to_datetime(pd_text)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                                
                            if dt >= thirty_days_ago:
                                news_items.append({
                                    "title": t_text,
                                    "link": l_text,
                                    "date": dt.strftime("%d %b %Y %H:%M"),
                                    "timestamp": dt.timestamp()
                                })
                        except Exception:
                            pass
        except Exception as e:
            print(f"RSS Error for {url}: {e}")
            
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    
    seen = set()
    unique_news = []
    for item in news_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique_news.append(item)
            
    return unique_news

@app.route("/api/news")
def api_news():
    from flask import request, jsonify
    global NEWS_CACHE
    now = datetime.datetime.now()
    
    if NEWS_CACHE["last_fetch"] is None or (now - NEWS_CACHE["last_fetch"]).total_seconds() > 1800:
        NEWS_CACHE["data"] = fetch_all_news()
        NEWS_CACHE["last_fetch"] = now
        
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    
    start = (page - 1) * limit
    end = start + limit
    
    items = NEWS_CACHE["data"][start:end]
    has_more = end < len(NEWS_CACHE["data"])
    
    return jsonify({
        "items": items,
        "has_more": has_more,
        "total": len(NEWS_CACHE["data"])
    })


# =========================================================================
# AI-Powered Market Outlook (Phase 1)
# =========================================================================
AI_OUTLOOK_CACHE = {"data": None, "last_fetch": None}

def generate_ai_outlook():
    global AI_OUTLOOK_CACHE, NEWS_CACHE
    now = datetime.datetime.now()
    if AI_OUTLOOK_CACHE["data"] and AI_OUTLOOK_CACHE["last_fetch"]:
        # Cache for 6 hours
        if (now - AI_OUTLOOK_CACHE["last_fetch"]).total_seconds() < 21600:
            return AI_OUTLOOK_CACHE["data"]

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or not GENAI_AVAILABLE:
        # Fallback to static if no API key or genai not installed
        return MARKET_OUTLOOK

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Get latest news for context
        if not NEWS_CACHE["data"]:
            NEWS_CACHE["data"] = fetch_all_news()
            NEWS_CACHE["last_fetch"] = now
            
        news_items = NEWS_CACHE["data"]
            
        recent_news = news_items[:40] # Top 40 recent news
        news_titles = "\n".join([f"- {n['title']} ({n['date']})" for n in recent_news])
        
        prompt = f"""
คุณเป็นผู้เชี่ยวชาญด้านการลงทุนของ กองทุนบำเหน็จบำนาญข้าราชการ (กบข.)
จงสรุปสถานการณ์ตลาดและการลงทุนจากหัวข้อข่าวล่าสุดต่อไปนี้ ให้อยู่ในรูปแบบ JSON เท่านั้น:

ข่าวล่าสุดที่จะใช้วิเคราะห์:
{news_titles}

รูปแบบ JSON ที่ต้องการ (ห้ามมี Markdown หรือข้อความอื่นปน):
{{
  "date": "ระบุชื่อเดือนปัจจุบัน พ.ศ. ปัจจุบัน (เช่น มีนาคม 2569)",
  "global_economy": "สรุปสถานการณ์เศรษฐกิจโลกใน 1-2 ประโยค",
  "thai_economy": "สรุปสถานการณ์เศรษฐกิจไทย ดัชนีหลักทรัพย์ไทย ใน 1-2 ประโยค",
  "gold_view": "ทิศทางราคาทองคำจากข่าว",
  "strategy": "คำแนะนำกลยุทธ์การลงทุน กบข. ให้เหมาะกับสถานการณ์นี้",
  "academy_tip": "คำแนะนำให้ความรู้การลงทุนสั้นๆ (Educational Tip) ที่เชื่อมโยงกับสถานการณ์ตลาดปัจจุบัน เช่น อธิบายว่าทำไมสินทรัพย์ประเภทหนึ่งถึงขึ้น/ลง เพื่อให้ความรู้สมาชิก",
  "long_term_insight": "มุมมองการลงทุนระยะยาว (3-5 ปีขึ้นไป) ที่ควรรักษาไว้แม้ตลาดระยะสั้นจะผันผวน เพื่อเสริมวินัยการลงทุน",
  "fear_greed_score": "ตัวเลข 0-100 ประเมินความกลัวและความโลภของตลาดจากข่าว (0=Extreme Fear, 100=Extreme Greed)"
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean up JSON if it has markdown block
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        ai_data = _json.loads(text)
        ai_data['is_ai'] = True 
        
        AI_OUTLOOK_CACHE["data"] = ai_data
        AI_OUTLOOK_CACHE["last_fetch"] = now
        return ai_data
        
    except Exception as e:
        print(f"AI Generation Error: {e}")
        return MARKET_OUTLOOK

@app.route("/api/outlook")
def api_outlook():
    from flask import jsonify
    outlook = generate_ai_outlook()
    return jsonify(outlook)


# =========================================================================
# Market Timing & Momentum Indicators (Phase 2)
# =========================================================================
MOMENTUM_CACHE = {"data": {}, "last_fetch": None}

def get_asset_momentum():
    """
    Returns momentum scores for assets.
    Note: yfinance dependency removed - using neutral fallback values.
    Real-time data is displayed via TradingView widgets on client-side.
    """
    global MOMENTUM_CACHE
    now = datetime.datetime.now()
    if MOMENTUM_CACHE["data"] and MOMENTUM_CACHE["last_fetch"]:
        # Cache for 2 hours
        if (now - MOMENTUM_CACHE["last_fetch"]).total_seconds() < 7200:
            return MOMENTUM_CACHE["data"]

    # Fallback: return neutral momentum scores
    # Real momentum indicators are shown via TradingView widgets (client-side)
    momentum_scores = {
        "equity_intl": 0.0,
        "gold": 0.0,
        "equity_thai": 0.0,
        "reit_thai": 0.0
    }

    MOMENTUM_CACHE["data"] = momentum_scores
    MOMENTUM_CACHE["last_fetch"] = now

    return momentum_scores


# =========================================================================
# Phase 5 & 6: Smart Chatbot & What-If Simulator
# =========================================================================

@app.route("/api/chat", methods=["POST"])
def api_chat():
    from flask import request, jsonify
    data = request.json
    user_message = data.get("message", "")
    history = data.get("history", [])
    
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE:
        return jsonify({"reply": "ขออภัยครับ ฟีเจอร์ AI Chatbot จำเป็นต้องติดตั้ง google-generativeai ก่อนครับ (pip install google-generativeai)"})
    if not API_KEY:
        return jsonify({"reply": "ขออภัยครับ ฟีเจอร์ AI Chatbot จำเป็นต้องเชื่อมต่อกับ API ก่อนครับ (กรุณาตั้งค่า GEMINI_API_KEY)"})

    try:
        genai.configure(api_key=API_KEY)
        
        formatted_history = []
        for h in history:
            formatted_history.append({
                "role": h["role"],
                "parts": [h["parts"]]
            })

        system_instruction = f"""
คุณคือ "น้อง กบข. AI" ผู้ช่วยส่วนตัวและที่ปรึกษาด้านการลงทุนของ กองทุนบำเหน็จบำนาญข้าราชการ (กบข.)
ตอบคำถามด้วยความสุภาพ เป็นกันเอง และอ้างอิงข้อมูลของ กบข. (GPF) เป็นหลัก ใช้ภาษาไทยที่เข้าใจง่าย มี Emoticon ประกอบบ้าง

ข้อมูลปัจจุบันของผู้ใช้ (เพื่อให้บริการแบบ Personalized):
- ผู้ใช้ถือแผนการลงทุน: {', '.join([h['plan'] for h in USER_PORTFOLIO['holdings']])}
- ยอดเงินฝากสะสมรวม: {USER_PORTFOLIO['total']:,.2f} บาท
- ผลตอบแทนปัจจุบัน: กำไร {USER_PORTFOLIO['profit']:,.2f} บาท
- สภาพตลาดปัจจุบัน (ใช้เพื่ออ้างอิงเหตุการณ์รายวัน): 
  - เศรษฐกิจโลก: {MARKET_OUTLOOK['global_economy']}
  - เศรษฐกิจไทย: {MARKET_OUTLOOK['thai_economy']}
  - ทองคำ: {MARKET_OUTLOOK['gold_view']}
        
ถ้าผู้ใช้ถามเกี่ยวกับพอร์ตของตัวเอง ให้วิเคราะห์หรือตอบอ้างอิงจากข้อมูลด้านบนนี้
ถ้าผู้ใช้ขอคำแนะนำการลงทุน ให้สอดแทรกความรู้เรื่องวินัยการออมและการลงทุนระยะยาวเสมอ
"""
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        
        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(user_message)
        
        return jsonify({"reply": response.text})

    except Exception as e:
        print(f"Chatbot Error: {e}")
        return jsonify({"reply": "ขออภัยครับ ระบบประมวลผล AI ของน้อง กบข. มีปัญหาขัดข้องชั่วคราว ลองใหม่อีกครั้งนะครับ 🙏"})


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    from flask import request, jsonify
    data = request.json
    scenario = data.get("scenario", "")
    
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE:
        return jsonify({"error": "google-generativeai not installed"})
    if not API_KEY:
        return jsonify({"error": "No API Key"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
วิเคราะห์สถานการณ์สมมติทางเศรษฐกิจต่อไปนี้: "{scenario}"
และประเมินผลกระทบที่อาจเกิดขึ้นกับสินทรัพย์ 3 ประเภท (หุ้นต่างประเทศ, หุ้นไทย, ทองคำ)
ให้ตอบเป็น JSON เท่านั้น โดยระบุตัวเลขประเมินผลกระทบเป็นเปอร์เซ็นต์ (% impact) จาก -100 ถึง +100
ตัวอย่าง: หุ้นตกรุนแรงอาจจะเป็น -20, ทองคำขึ้นอาจจะเป็น +5

รูปแบบ JSON:
{{
  "equity_intl_impact": 0.0,
  "equity_thai_impact": 0.0,
  "gold_impact": 0.0,
  "reasoning": "อธิบายเหตุผลสั้นๆ 1 ประโยค"
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        impact_data = _json.loads(text.strip())
        
        # Calculate specific impact on Current Portfolio (75% intl, 25% gold)
        p_intl = 0.7507
        p_gold = 0.2493
        total_impact = (p_intl * impact_data.get("equity_intl_impact", 0)) + (p_gold * impact_data.get("gold_impact", 0))
        
        est_loss = (USER_PORTFOLIO['total'] * (total_impact / 100))
        new_balance = USER_PORTFOLIO['total'] + est_loss
        
        return jsonify({
            "scenario": scenario,
            "total_impact_pct": round(total_impact, 2),
            "est_loss_thb": round(est_loss, 2),
            "new_balance_thb": round(new_balance, 2),
            "reasoning": impact_data.get("reasoning", "")
        })

    except Exception as e:
        print(f"Simulation Error: {e}")
        return jsonify({"error": "Simulation failed"})


# =========================================================================
# GPF Knowledge Base for RAG (Retrieval-Augmented Generation)
# =========================================================================
GPF_KNOWLEDGE_BASE = {
    "general": """
กองทุนบำเหน็จบำนาญข้าราชการ (กบข.) คือกองทุนที่จัดตั้งขึ้นตาม พ.ร.บ. กองทุนบำเหน็จบำนาญข้าราชการ พ.ศ. 2539
เพื่อเป็นหลักประกันการจ่ายบำเหน็จบำนาญและให้ประโยชน์ตอบแทนการรับราชการแก่ข้าราชการเมื่อออกจากราชการ
สมาชิก กบข. ประกอบด้วยข้าราชการพลเรือน ข้าราชการครู ข้าราชการตำรวจ ข้าราชการทหาร และข้าราชการอื่นๆ
""",
    "investment_plans": """
กบข. มีแผนการลงทุนให้เลือก 10 แผน:
1. แผนเงินฝากและตราสารหนี้ระยะสั้น (ความเสี่ยงต่ำมาก ระดับ 1)
2. แผนตราสารหนี้ (ความเสี่ยงปานกลาง ระดับ 4)
3. แผนตราสารหนี้ต่างประเทศ (ความเสี่ยงปานกลาง-สูง ระดับ 5)
4. แผนทองคำ (ความเสี่ยงปานกลาง-สูง ระดับ 5)
5. แผนหุ้นไทย (ความเสี่ยงสูง ระดับ 6)
6. แผน Thai ESG (ความเสี่ยงสูง ระดับ 6)
7. แผนหุ้นต่างประเทศ (ความเสี่ยงสูง ระดับ 6)
8. แผนกองทุนอสังหาริมทรัพย์ไทย (ความเสี่ยงสูง ระดับ 6)
9. แผนสมดุลตามอายุ (Life Path) - ปรับสัดส่วนอัตโนมัติตามอายุ
10. แผนหลัก (Default Plan) - กระจายลงทุนหลายสินทรัพย์
""",
    "contribution": """
อัตราเงินสะสม กบข.:
- ข้าราชการสะสม: 3% ของเงินเดือน (ส่งเพิ่มได้สูงสุด 15%)
- รัฐสมทบ: 3% ของเงินเดือน
- รัฐชดเชย: 2% ของเงินเดือน
- เงินประเดิม: รัฐจ่ายให้ครั้งเดียวตามอายุราชการ
รวมแล้วรัฐช่วยออมให้ 5% + เงินประเดิม
""",
    "withdrawal": """
การขอรับเงินคืน กบข.:
- เกษียณอายุ: รับเงินก้อน + บำนาญรายเดือน หรือเลือกรับแบบผสม
- ลาออก/โอนย้าย: รับเงินสะสม + ผลประโยชน์ (ส่วนรัฐสมทบได้ตามเงื่อนไข)
- ทุพพลภาพ/เสียชีวิต: รับเงินทั้งหมดตามสิทธิ
""",
    "tax_benefits": """
สิทธิประโยชน์ทางภาษี:
- เงินสะสมส่วนเพิ่ม (สูงสุด 15%) สามารถนำไปลดหย่อนภาษีได้
- รวมกับ RMF, SSF, กองทุนสำรองเลี้ยงชีพ ไม่เกิน 500,000 บาท/ปี
- เงินที่ได้รับคืนเมื่อเกษียณ ยกเว้นภาษีตามเงื่อนไข
""",
    "risk_assessment": """
การประเมินความเสี่ยง:
- ทำแบบประเมินผ่าน My GPF App หรือเว็บไซต์ กบข.
- แบ่งระดับความเสี่ยง: ต่ำ, ปานกลาง, สูง
- ผลประเมินใช้ได้ 2 ปี ต้องทำใหม่เมื่อหมดอายุ
- เลือกแผนลงทุนได้ตามระดับความเสี่ยงที่ประเมินได้หรือต่ำกว่า
""",
    "plan_change": """
การเปลี่ยนแผนการลงทุน:
- เปลี่ยนได้ 12 ครั้ง/ปี (นับตามปีปฏิทิน)
- มีผลวันที่ 1 ของเดือนถัดไป
- สามารถแบ่งสัดส่วนลงทุนหลายแผนได้ (รวม 100%)
- แนะนำให้ทบทวนแผนอย่างน้อยปีละ 1 ครั้ง
"""
}

def get_relevant_knowledge(query):
    """Simple keyword-based retrieval for RAG"""
    query_lower = query.lower()
    relevant = []

    keyword_map = {
        "general": ["กบข", "คืออะไร", "ประวัติ", "สมาชิก", "ข้าราชการ"],
        "investment_plans": ["แผน", "ลงทุน", "กองทุน", "ตราสารหนี้", "หุ้น", "ทองคำ", "อสังหาริมทรัพย์", "life path", "สมดุล"],
        "contribution": ["สะสม", "สมทบ", "เงินเดือน", "ออม", "ประเดิม", "เปอร์เซ็นต์", "%"],
        "withdrawal": ["รับเงิน", "ถอน", "เกษียณ", "ลาออก", "บำนาญ", "บำเหน็จ"],
        "tax_benefits": ["ภาษี", "ลดหย่อน", "สิทธิประโยชน์", "rmf", "ssf"],
        "risk_assessment": ["ความเสี่ยง", "ประเมิน", "แบบประเมิน", "ระดับ"],
        "plan_change": ["เปลี่ยนแผน", "สับเปลี่ยน", "สัดส่วน", "ครั้ง"]
    }

    for key, keywords in keyword_map.items():
        if any(kw in query_lower for kw in keywords):
            relevant.append(GPF_KNOWLEDGE_BASE[key])

    if not relevant:
        relevant = [GPF_KNOWLEDGE_BASE["general"], GPF_KNOWLEDGE_BASE["investment_plans"]]

    return "\n\n".join(relevant[:3])


# =========================================================================
# Phase 8: Automated Data Pipeline (Factsheet OCR)
# =========================================================================
@app.route("/api/admin/update_funds", methods=["POST"])
def api_admin_update_funds():
    from flask import request, jsonify
    import tempfile
    
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE or not API_KEY:
        return jsonify({"error": "Google Generative AI not available or API Key missing"})

    if 'factsheet' not in request.files:
        return jsonify({"error": "No file uploaded. Please provide a GPF Factsheet PDF."})
        
    file = request.files['factsheet']
    if file.filename == '':
        return jsonify({"error": "Empty filename."})
        
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            file.save(temp_pdf.name)
            temp_pdf_path = temp_pdf.name
            
        with open(temp_pdf_path, "rb") as f:
            pdf_data = f.read()
            
        prompt = '''
        คุณคือ AI อ่านเอกสาร Factsheet ของ กบข. หน้าที่ของคุณคือสกัดข้อมูล 'ผลตอบแทนล่าสุด' และ 'ผลตอบแทนปี 2567' 
        ของแผนการลงทุนทั้ง 12 แผน ให้ตอบเป็น JSON array ของ object ที่มีโครงสร้างดังนี้:
        [
          {"plan_id": "deposit_short", "latest_return": 1.25, "annual_return": 1.50},
          ...
        ]
        ตอบเฉพาะ JSON เท่านั้น ห้ามมีคำอธิบายอื่น
        '''
        
        response = model.generate_content([
            {'mime_type': 'application/pdf', 'data': pdf_data},
            prompt
        ])
        
        # Clean up temp file
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        extracted_data = _json.loads(text.strip())
        
        return jsonify({
            "success": True, 
            "message": "Factsheet processed successfully. (Mock dictionary update)",
            "extracted_data": extracted_data
        })
        
    except Exception as e:
        print(f"Factsheet OCR Error: {e}")
        return jsonify({"error": "Failed to process the factsheet."})


# =========================================================================
# Phase 2 & 9: AI-Powered Personalized Portfolio Allocation & Goal
# =========================================================================
@app.route("/api/ai/portfolio-advice", methods=["POST"])
def api_portfolio_advice():
    from flask import request, jsonify
    data = request.json

    age = data.get("age", 35)
    years_to_retire = data.get("years_to_retire", 25)
    risk_tolerance = data.get("risk_tolerance", "medium")  # low, medium, high
    monthly_salary = data.get("monthly_salary", 30000)
    current_savings = data.get("current_savings", 0)
    investment_goal = data.get("investment_goal", "retirement")

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE:
        return jsonify({"error": "google-generativeai not installed"})
    if not API_KEY:
        return jsonify({"error": "No API Key"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Get current fund data for context
        fund_summary = "\n".join([
            f"- {f['name_th']}: ผลตอบแทน 3 ปี {f['avg_3y'] or 'N/A'}%, ความเสี่ยงระดับ {f['risk_level']}"
            for f in FUNDS
        ])

        prompt = f"""
คุณเป็นที่ปรึกษาการลงทุน กบข. ให้คำแนะนำ Asset Allocation ที่เหมาะสม

ข้อมูลผู้ใช้:
- อายุ: {age} ปี
- ปีที่จะเกษียณ: {years_to_retire} ปี
- ระดับความเสี่ยงที่รับได้: {risk_tolerance}
- เงินเดือน: {monthly_salary:,} บาท
- เงินออมปัจจุบัน: {current_savings:,} บาท
- เป้าหมาย: {investment_goal}

แผนการลงทุน กบข. ที่มี:
{fund_summary}

ให้ตอบเป็น JSON เท่านั้น:
{{
  "recommended_allocation": [
    {{"plan_id": "equity_intl", "plan_name": "แผนหุ้นต่างประเทศ", "percentage": 40, "reason": "เหตุผลสั้นๆ"}},
    {{"plan_id": "gold", "plan_name": "แผนทองคำ", "percentage": 20, "reason": "เหตุผลสั้นๆ"}},
    {{"plan_id": "fixed_income", "plan_name": "แผนตราสารหนี้", "percentage": 40, "reason": "เหตุผลสั้นๆ"}}
  ],
  "risk_score": 6,
  "expected_return_yearly": 5.5,
  "summary": "สรุปคำแนะนำ 2-3 ประโยค",
  "key_advice": ["คำแนะนำ 1", "คำแนะนำ 2", "คำแนะนำ 3"],
  "rebalance_frequency": "ปีละ 1 ครั้ง"
}}

หมายเหตุ: percentage รวมกันต้องเท่ากับ 100
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        advice = _json.loads(text.strip())
        advice["user_profile"] = {
            "age": age,
            "years_to_retire": years_to_retire,
            "risk_tolerance": risk_tolerance
        }

        return jsonify(advice)

    except Exception as e:
        print(f"Portfolio Advice Error: {e}")
        return jsonify({"error": str(e)})


# =========================================================================
# Phase 2: Rebalancing Alert System
# =========================================================================
@app.route("/api/ai/rebalance-check", methods=["POST"])
def api_rebalance_check():
    from flask import request, jsonify
    data = request.json

    # Current allocation from user or use default portfolio
    current_allocation = data.get("current_allocation", USER_PORTFOLIO.get("holdings", []))
    target_allocation = data.get("target_allocation", None)
    threshold_pct = data.get("threshold", 5)  # Default 5% drift threshold

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE:
        return jsonify({"error": "google-generativeai not installed"})
    if not API_KEY:
        # Return rule-based analysis without AI
        alerts = []
        for holding in current_allocation:
            if target_allocation:
                target = next((t for t in target_allocation if t["id"] == holding["id"]), None)
                if target:
                    drift = abs(holding["pct"] - target["pct"])
                    if drift > threshold_pct:
                        alerts.append({
                            "plan": holding["plan"],
                            "current_pct": holding["pct"],
                            "target_pct": target["pct"],
                            "drift": round(drift, 2),
                            "action": "ลด" if holding["pct"] > target["pct"] else "เพิ่ม"
                        })
        return jsonify({
            "needs_rebalance": len(alerts) > 0,
            "alerts": alerts,
            "ai_analysis": None
        })

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        allocation_str = "\n".join([
            f"- {h['plan']}: {h['pct']}% (มูลค่า {h.get('value', 0):,.2f} บาท)"
            for h in current_allocation
        ])

        prompt = f"""
วิเคราะห์พอร์ตการลงทุน กบข. และแนะนำการ Rebalance

พอร์ตปัจจุบัน:
{allocation_str}

เกณฑ์ Drift ที่ยอมรับได้: {threshold_pct}%

ตอบเป็น JSON:
{{
  "needs_rebalance": true/false,
  "overall_risk_level": "ต่ำ/ปานกลาง/สูง",
  "concentration_risk": "มี/ไม่มี ความเสี่ยงกระจุกตัว",
  "alerts": [
    {{"plan": "ชื่อแผน", "issue": "ปัญหา", "suggestion": "แนวทางแก้ไข"}}
  ],
  "rebalance_actions": [
    {{"from_plan": "แผน A", "to_plan": "แผน B", "amount_pct": 10, "reason": "เหตุผล"}}
  ],
  "market_timing_note": "ความเห็นเรื่องจังหวะตลาดในการ rebalance"
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        analysis = _json.loads(text.strip())
        return jsonify(analysis)

    except Exception as e:
        print(f"Rebalance Check Error: {e}")
        return jsonify({"error": str(e)})


# =========================================================================
# Phase 3: Advanced Scenario Analysis
# =========================================================================
SCENARIO_TEMPLATES = {
    "recession": "เศรษฐกิจโลกเข้าสู่ภาวะถดถอย (Recession) GDP ติดลบ 2%",
    "inflation": "อัตราเงินเฟ้อพุ่งสูงขึ้นเกิน 8% ธนาคารกลางขึ้นดอกเบี้ยเร่งด่วน",
    "war": "เกิดสงครามในภูมิภาคตะวันออกกลาง ราคาน้ำมันพุ่ง 50%",
    "tech_crash": "ฟองสบู่หุ้นเทคโนโลยีแตก Nasdaq ร่วง 30%",
    "china_crisis": "วิกฤตอสังหาริมทรัพย์จีนลุกลาม ส่งผลกระทบเศรษฐกิจเอเชีย",
    "fed_pivot": "Fed ประกาศลดดอกเบี้ยเร็วกว่าคาด 1.5% ภายในปีนี้",
    "gold_surge": "ราคาทองคำพุ่งทะลุ $3,000/oz จากความไม่แน่นอนทางภูมิรัฐศาสตร์",
    "baht_weak": "เงินบาทอ่อนค่าแตะ 40 บาท/ดอลลาร์"
}

@app.route("/api/ai/scenario-analysis", methods=["POST"])
def api_scenario_analysis():
    from flask import request, jsonify
    data = request.json

    scenario_type = data.get("scenario_type", "custom")
    custom_scenario = data.get("custom_scenario", "")
    portfolio = data.get("portfolio", USER_PORTFOLIO)
    time_horizon = data.get("time_horizon", "6 เดือน")

    # Get scenario description
    if scenario_type != "custom" and scenario_type in SCENARIO_TEMPLATES:
        scenario = SCENARIO_TEMPLATES[scenario_type]
    else:
        scenario = custom_scenario

    if not scenario:
        return jsonify({"error": "กรุณาระบุสถานการณ์"})

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE:
        return jsonify({"error": "google-generativeai not installed"})
    if not API_KEY:
        return jsonify({"error": "No API Key"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        holdings_str = "\n".join([
            f"- {h['plan']}: {h['pct']}%"
            for h in portfolio.get("holdings", [])
        ])

        prompt = f"""
วิเคราะห์ผลกระทบจากสถานการณ์สมมติต่อพอร์ตการลงทุน กบข. อย่างละเอียด

สถานการณ์: {scenario}
ระยะเวลาวิเคราะห์: {time_horizon}

พอร์ตปัจจุบัน (มูลค่ารวม {portfolio.get('total', 0):,.2f} บาท):
{holdings_str}

ตอบเป็น JSON:
{{
  "scenario_summary": "สรุปสถานการณ์ 1-2 ประโยค",
  "probability": "ความน่าจะเป็นที่เกิดขึ้น (ต่ำ/ปานกลาง/สูง)",
  "impact_by_asset": [
    {{"asset": "หุ้นต่างประเทศ", "impact_pct": -15, "explanation": "อธิบาย"}},
    {{"asset": "ทองคำ", "impact_pct": 10, "explanation": "อธิบาย"}},
    {{"asset": "ตราสารหนี้ไทย", "impact_pct": -2, "explanation": "อธิบาย"}}
  ],
  "portfolio_impact": {{
    "total_impact_pct": -8.5,
    "estimated_loss_thb": 24000,
    "worst_case_pct": -15,
    "best_case_pct": -3
  }},
  "protective_actions": [
    {{"action": "ลดสัดส่วนหุ้นต่างประเทศ", "to_pct": 50, "timing": "ทันที"}},
    {{"action": "เพิ่มทองคำ", "to_pct": 30, "timing": "ทยอยซื้อ"}}
  ],
  "recovery_outlook": "คาดการณ์การฟื้นตัว 1-2 ประโยค",
  "historical_parallel": "เหตุการณ์ในอดีตที่คล้ายกัน (ถ้ามี)"
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        analysis = _json.loads(text.strip())
        analysis["scenario_input"] = scenario
        analysis["time_horizon"] = time_horizon

        return jsonify(analysis)

    except Exception as e:
        print(f"Scenario Analysis Error: {e}")
        return jsonify({"error": str(e)})

@app.route("/api/ai/scenario-templates")
def api_scenario_templates():
    from flask import jsonify
    return jsonify(SCENARIO_TEMPLATES)


# =========================================================================
# Phase 3: Retirement Projection with Monte Carlo Simulation
# =========================================================================
import random
import math

def monte_carlo_retirement(
    current_age, retirement_age, current_savings, monthly_contribution,
    expected_return, volatility, simulations=1000
):
    """Run Monte Carlo simulation for retirement projection"""
    years = retirement_age - current_age
    months = years * 12

    final_values = []
    paths = []

    monthly_return = expected_return / 12 / 100
    monthly_vol = volatility / math.sqrt(12) / 100

    for _ in range(simulations):
        value = current_savings
        path = [value]

        for _ in range(months):
            # Random return based on normal distribution
            r = random.gauss(monthly_return, monthly_vol)
            value = value * (1 + r) + monthly_contribution
            if len(paths) < 10:  # Only store 10 sample paths for visualization
                path.append(value)

        final_values.append(value)
        if len(paths) < 10:
            paths.append(path)

    final_values.sort()

    return {
        "percentile_10": round(final_values[int(simulations * 0.10)], 2),
        "percentile_25": round(final_values[int(simulations * 0.25)], 2),
        "percentile_50": round(final_values[int(simulations * 0.50)], 2),
        "percentile_75": round(final_values[int(simulations * 0.75)], 2),
        "percentile_90": round(final_values[int(simulations * 0.90)], 2),
        "mean": round(sum(final_values) / len(final_values), 2),
        "min": round(min(final_values), 2),
        "max": round(max(final_values), 2),
        "sample_paths": paths
    }

@app.route("/api/ai/retirement-projection", methods=["POST"])
def api_retirement_projection():
    from flask import request, jsonify
    data = request.json

    current_age = data.get("current_age", 35)
    retirement_age = data.get("retirement_age", 60)
    current_savings = data.get("current_savings", USER_PORTFOLIO.get("total", 100000))
    monthly_salary = data.get("monthly_salary", 30000)
    contribution_rate = data.get("contribution_rate", 3)  # percent
    employer_match = data.get("employer_match", 5)  # percent (3% match + 2% compensation)
    expected_return = data.get("expected_return", 6)  # percent annually
    volatility = data.get("volatility", 12)  # percent annually
    desired_monthly_pension = data.get("desired_monthly_pension", 20000)

    # Calculate monthly contribution
    monthly_contribution = monthly_salary * (contribution_rate + employer_match) / 100

    # Run Monte Carlo simulation
    mc_result = monte_carlo_retirement(
        current_age, retirement_age, current_savings,
        monthly_contribution, expected_return, volatility
    )

    # Calculate if projection meets goal
    years_in_retirement = 25  # Assume 25 years in retirement
    total_needed = desired_monthly_pension * 12 * years_in_retirement

    # Get AI interpretation
    API_KEY = os.environ.get("GEMINI_API_KEY")
    ai_interpretation = None

    if GENAI_AVAILABLE and API_KEY:
        try:
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')

            prompt = f"""
วิเคราะห์ผลการจำลองเงินเกษียณ กบข. และให้คำแนะนำ

ข้อมูลผู้ใช้:
- อายุปัจจุบัน: {current_age} ปี
- อายุเกษียณ: {retirement_age} ปี
- เงินออมปัจจุบัน: {current_savings:,.2f} บาท
- เงินสะสมต่อเดือน: {monthly_contribution:,.2f} บาท
- ผลตอบแทนคาดหวัง: {expected_return}% ต่อปี

ผลการจำลอง Monte Carlo (1000 รอบ):
- กรณีแย่ (10th percentile): {mc_result['percentile_10']:,.2f} บาท
- กรณีปกติ (50th percentile): {mc_result['percentile_50']:,.2f} บาท
- กรณีดี (90th percentile): {mc_result['percentile_90']:,.2f} บาท

เป้าหมาย: ต้องการเงินบำนาญเดือนละ {desired_monthly_pension:,} บาท (รวม {total_needed:,} บาท สำหรับ 25 ปี)

ตอบเป็น JSON:
{{
  "goal_achievement": "บรรลุเป้าหมาย/ใกล้เคียง/ต้องปรับปรุง",
  "probability_of_success": 75,
  "interpretation": "อธิบายผลลัพธ์ 2-3 ประโยค ภาษาง่าย",
  "recommendations": [
    "คำแนะนำ 1",
    "คำแนะนำ 2",
    "คำแนะนำ 3"
  ],
  "risk_warning": "คำเตือนความเสี่ยง (ถ้ามี)",
  "monthly_pension_estimate": 15000
}}
"""
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            ai_interpretation = _json.loads(text.strip())

        except Exception as e:
            print(f"AI Interpretation Error: {e}")

    return jsonify({
        "input": {
            "current_age": current_age,
            "retirement_age": retirement_age,
            "years_to_retire": retirement_age - current_age,
            "current_savings": current_savings,
            "monthly_contribution": monthly_contribution,
            "expected_return": expected_return,
            "volatility": volatility
        },
        "simulation": mc_result,
        "goal": {
            "desired_monthly_pension": desired_monthly_pension,
            "total_needed": total_needed,
            "years_in_retirement": years_in_retirement
        },
        "ai_interpretation": ai_interpretation
    })


# =========================================================================
# Phase 4: Auto-Research Agent
# =========================================================================
RESEARCH_CACHE = {"data": None, "last_fetch": None}

@app.route("/api/ai/daily-research")
def api_daily_research():
    from flask import jsonify
    global RESEARCH_CACHE

    now = datetime.datetime.now()
    # Cache for 4 hours
    if RESEARCH_CACHE["data"] and RESEARCH_CACHE["last_fetch"]:
        if (now - RESEARCH_CACHE["last_fetch"]).total_seconds() < 14400:
            return jsonify(RESEARCH_CACHE["data"])

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE:
        return jsonify({"error": "google-generativeai not installed"})
    if not API_KEY:
        return jsonify({"error": "No API Key"})

    try:
        # Get latest news
        news_data = fetch_all_news()
        recent_news = news_data[:50] if news_data else []
        news_titles = "\n".join([f"- {n['title']} ({n['date']})" for n in recent_news])

        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""
คุณเป็นนักวิเคราะห์การลงทุนของ กบข. สร้างรายงานวิจัยประจำวันจากข่าวล่าสุด

ข่าวล่าสุด:
{news_titles}

สร้างรายงานวิจัยในรูปแบบ JSON:
{{
  "report_date": "วันที่ปัจจุบัน",
  "market_summary": "สรุปภาพรวมตลาด 2-3 ประโยค",
  "key_events": [
    {{"event": "เหตุการณ์สำคัญ 1", "impact": "ผลกระทบ", "relevance": "high/medium/low"}},
    {{"event": "เหตุการณ์สำคัญ 2", "impact": "ผลกระทบ", "relevance": "high/medium/low"}},
    {{"event": "เหตุการณ์สำคัญ 3", "impact": "ผลกระทบ", "relevance": "high/medium/low"}}
  ],
  "asset_outlook": {{
    "thai_equity": {{"trend": "bullish/neutral/bearish", "reason": "เหตุผล"}},
    "intl_equity": {{"trend": "bullish/neutral/bearish", "reason": "เหตุผล"}},
    "gold": {{"trend": "bullish/neutral/bearish", "reason": "เหตุผล"}},
    "fixed_income": {{"trend": "bullish/neutral/bearish", "reason": "เหตุผล"}}
  }},
  "risk_alerts": [
    "ความเสี่ยงที่ต้องจับตา 1",
    "ความเสี่ยงที่ต้องจับตา 2"
  ],
  "opportunities": [
    "โอกาสการลงทุน 1",
    "โอกาสการลงทุน 2"
  ],
  "gpf_recommendation": "คำแนะนำสำหรับสมาชิก กบข. 1-2 ประโยค",
  "educational_insight": "ความรู้การลงทุนที่เกี่ยวข้องกับสถานการณ์วันนี้"
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        research = _json.loads(text.strip())
        research["generated_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        research["news_analyzed"] = len(recent_news)

        RESEARCH_CACHE["data"] = research
        RESEARCH_CACHE["last_fetch"] = now

        return jsonify(research)

    except Exception as e:
        print(f"Daily Research Error: {e}")
        return jsonify({"error": str(e)})


# =========================================================================
# Phase 4: Document Q&A System
# =========================================================================
@app.route("/api/ai/document-qa", methods=["POST"])
def api_document_qa():
    from flask import request, jsonify
    data = request.json

    question = data.get("question", "")
    document_context = data.get("document_context", "")

    if not question:
        return jsonify({"error": "กรุณาระบุคำถาม"})

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE:
        return jsonify({"error": "google-generativeai not installed"})
    if not API_KEY:
        return jsonify({"error": "No API Key"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Get relevant knowledge from RAG
        knowledge = get_relevant_knowledge(question)

        # If user provides document context, add it
        full_context = knowledge
        if document_context:
            full_context = f"เอกสารที่อัพโหลด:\n{document_context}\n\n{knowledge}"

        prompt = f"""
คุณเป็นผู้เชี่ยวชาญ กบข. ตอบคำถามจากข้อมูลที่ให้

ข้อมูลอ้างอิง:
{full_context}

คำถาม: {question}

ตอบเป็น JSON:
{{
  "answer": "คำตอบที่ชัดเจน เข้าใจง่าย",
  "confidence": "high/medium/low",
  "sources": ["แหล่งข้อมูลที่ใช้อ้างอิง"],
  "related_topics": ["หัวข้อที่เกี่ยวข้องที่อาจสนใจ"],
  "disclaimer": "ข้อจำกัดความรับผิดชอบ (ถ้าจำเป็น)"
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        answer = _json.loads(text.strip())
        return jsonify(answer)

    except Exception as e:
        print(f"Document QA Error: {e}")
        return jsonify({"error": str(e)})


# =========================================================================
# Enhanced AI Chat with RAG
# =========================================================================
@app.route("/api/ai/chat-enhanced", methods=["POST"])
def api_chat_enhanced():
    from flask import request, jsonify
    data = request.json
    user_message = data.get("message", "")
    history = data.get("history", [])
    include_market_data = data.get("include_market_data", True)

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GENAI_AVAILABLE:
        return jsonify({"reply": "ขออภัยครับ ฟีเจอร์นี้ต้องติดตั้ง google-generativeai ก่อน"})
    if not API_KEY:
        return jsonify({"reply": "ขออภัยครับ กรุณาตั้งค่า GEMINI_API_KEY"})

    try:
        genai.configure(api_key=API_KEY)

        # Get relevant knowledge for RAG
        knowledge = get_relevant_knowledge(user_message)

        # Get current market context if requested
        market_context = ""
        if include_market_data:
            try:
                outlook = generate_ai_outlook()
                market_context = f"""
สถานการณ์ตลาดปัจจุบัน:
- เศรษฐกิจโลก: {outlook.get('global_economy', 'N/A')}
- เศรษฐกิจไทย: {outlook.get('thai_economy', 'N/A')}
- ทองคำ: {outlook.get('gold_view', 'N/A')}
"""
            except:
                pass

        formatted_history = []
        for h in history[-10:]:  # Keep last 10 messages
            formatted_history.append({
                "role": h["role"],
                "parts": [h["parts"]]
            })

        system_instruction = f"""
คุณคือ "น้อง กบข. AI" ผู้ช่วยอัจฉริยะของกองทุนบำเหน็จบำนาญข้าราชการ (กบข.)

ความสามารถของคุณ:
1. ตอบคำถามเกี่ยวกับ กบข. และการลงทุน
2. ให้คำแนะนำการจัดพอร์ตตามความเสี่ยง
3. อธิบายแนวคิดการลงทุนให้เข้าใจง่าย
4. วิเคราะห์สถานการณ์ตลาดปัจจุบัน

ฐานความรู้ กบข.:
{knowledge}

{market_context}

ข้อมูลพอร์ตผู้ใช้:
- แผนที่ถือ: {', '.join([h['plan'] for h in USER_PORTFOLIO['holdings']])}
- มูลค่ารวม: {USER_PORTFOLIO['total']:,.2f} บาท
- กำไร: {USER_PORTFOLIO['profit']:,.2f} บาท ({USER_PORTFOLIO['profit_pct']:.2f}%)

แนวทางการตอบ:
- ใช้ภาษาไทยที่เข้าใจง่าย เป็นกันเอง
- ใส่ Emoji ประกอบบ้างให้ดูน่าสนใจ
- อ้างอิงข้อมูลจากฐานความรู้เมื่อเกี่ยวข้อง
- ถ้าไม่แน่ใจ ให้บอกตรงๆ ว่าไม่มีข้อมูล
- เตือนเรื่องความเสี่ยงเมื่อเหมาะสม
"""
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )

        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(user_message)

        return jsonify({
            "reply": response.text,
            "knowledge_used": len(knowledge) > 100,
            "market_data_included": include_market_data and len(market_context) > 0
        })

    except Exception as e:
        print(f"Enhanced Chat Error: {e}")
        return jsonify({"reply": "ขออภัยครับ ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง 🙏"})


# =========================================================================
# AI Feature Summary Endpoint
# =========================================================================
@app.route("/api/ai/features")
def api_ai_features():
    from flask import jsonify
    return jsonify({
        "available_features": [
            {
                "name": "AI Market Outlook",
                "endpoint": "/api/outlook",
                "method": "GET",
                "description": "วิเคราะห์ภาพรวมตลาดจากข่าวล่าสุดด้วย AI"
            },
            {
                "name": "AI Portfolio Advice",
                "endpoint": "/api/ai/portfolio-advice",
                "method": "POST",
                "description": "แนะนำ Asset Allocation ตาม profile ผู้ใช้",
                "params": ["age", "years_to_retire", "risk_tolerance", "monthly_salary"]
            },
            {
                "name": "Rebalance Check",
                "endpoint": "/api/ai/rebalance-check",
                "method": "POST",
                "description": "ตรวจสอบและแนะนำการ Rebalance พอร์ต",
                "params": ["current_allocation", "target_allocation", "threshold"]
            },
            {
                "name": "Scenario Analysis",
                "endpoint": "/api/ai/scenario-analysis",
                "method": "POST",
                "description": "วิเคราะห์ผลกระทบจากสถานการณ์สมมติ",
                "params": ["scenario_type", "custom_scenario", "time_horizon"]
            },
            {
                "name": "Scenario Templates",
                "endpoint": "/api/ai/scenario-templates",
                "method": "GET",
                "description": "รายการสถานการณ์สมมติที่มีให้เลือก"
            },
            {
                "name": "Retirement Projection",
                "endpoint": "/api/ai/retirement-projection",
                "method": "POST",
                "description": "จำลองเงินเกษียณด้วย Monte Carlo + AI",
                "params": ["current_age", "retirement_age", "current_savings", "monthly_salary", "expected_return"]
            },
            {
                "name": "Daily Research",
                "endpoint": "/api/ai/daily-research",
                "method": "GET",
                "description": "รายงานวิจัยประจำวันจาก AI"
            },
            {
                "name": "Document Q&A",
                "endpoint": "/api/ai/document-qa",
                "method": "POST",
                "description": "ถาม-ตอบจากเอกสาร กบข.",
                "params": ["question", "document_context"]
            },
            {
                "name": "Enhanced Chat",
                "endpoint": "/api/ai/chat-enhanced",
                "method": "POST",
                "description": "AI Chatbot พร้อม RAG และข้อมูลตลาด",
                "params": ["message", "history", "include_market_data"]
            },
            {
                "name": "What-If Simulator",
                "endpoint": "/api/simulate",
                "method": "POST",
                "description": "จำลองผลกระทบต่อพอร์ตจากสถานการณ์",
                "params": ["scenario"]
            }
        ],
        "genai_available": GENAI_AVAILABLE,
        "api_key_configured": bool(os.environ.get("GEMINI_API_KEY"))
    })


# =========================================================================
# AI Enhanced Section APIs - Real-time Analysis
# =========================================================================

# Cache for AI section analyses
AI_SECTION_CACHE = {
    "top_plans": {"data": None, "last_fetch": None},
    "market_deep": {"data": None, "last_fetch": None},
    "technical_summary": {"data": None, "last_fetch": None},
    "news_impact": {"data": None, "last_fetch": None},
    "academy_insight": {"data": None, "last_fetch": None},
    "roadmap_insight": {"data": None, "last_fetch": None}
}

@app.route("/api/ai/top-plans")
def api_ai_top_plans():
    """AI แนะนำ 2 แผนที่ดีที่สุดสำหรับสภาวะตลาดปัจจุบัน"""
    from flask import jsonify
    global AI_SECTION_CACHE, NEWS_CACHE

    now = datetime.datetime.now()
    cache = AI_SECTION_CACHE["top_plans"]
    if cache["data"] and cache["last_fetch"]:
        if (now - cache["last_fetch"]).total_seconds() < 3600:  # 1 hour cache
            return jsonify(cache["data"])

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or not GENAI_AVAILABLE:
        return jsonify({
            "error": "AI ไม่พร้อมใช้งาน",
            "fallback": True,
            "recommendation": "หุ้นต่างประเทศ + ทองคำ เป็นคู่ที่มี Sharpe Ratio สูงที่สุด",
            "reasoning": "การกระจายความเสี่ยงระหว่างสินทรัพย์ที่มี Correlation ต่ำช่วยลดความผันผวน"
        })

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Get news for context
        if not NEWS_CACHE["data"]:
            NEWS_CACHE["data"] = fetch_all_news()
            NEWS_CACHE["last_fetch"] = now

        recent_news = NEWS_CACHE["data"][:30]
        news_context = "\n".join([f"- {n['title']}" for n in recent_news])

        # Fund performance data
        fund_data = "\n".join([
            f"- {f['name_th']}: ผลตอบแทนล่าสุด {f['r_jun68'] or f['r2567'] or 0}%, ปี 2567: {f['r2567'] or 0}%, ความเสี่ยง {f['risk_level']}/8"
            for f in FUNDS
        ])

        prompt = f"""คุณเป็นผู้เชี่ยวชาญด้านการลงทุน กบข. วิเคราะห์สถานการณ์ปัจจุบันและแนะนำ 2 แผนที่ดีที่สุดสำหรับช่วงนี้

ข่าวล่าสุด:
{news_context}

ผลการดำเนินงานแผน กบข.:
{fund_data}

ตอบเป็น JSON เท่านั้น:
{{
  "plan1": {{
    "name": "ชื่อแผนที่ 1",
    "weight": 60,
    "reasoning": "เหตุผลสั้นๆ ทำไมถึงแนะนำแผนนี้ในช่วงนี้"
  }},
  "plan2": {{
    "name": "ชื่อแผนที่ 2",
    "weight": 40,
    "reasoning": "เหตุผลสั้นๆ"
  }},
  "market_condition": "สรุปสภาวะตลาดปัจจุบันใน 1 ประโยค",
  "risk_alert": "คำเตือนความเสี่ยงที่ควรระวังในช่วงนี้ (ถ้ามี)",
  "confidence": "high/medium/low",
  "time_horizon": "แนะนำสำหรับระยะ (สั้น/กลาง/ยาว)"
}}"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        result = _json.loads(text.strip())
        result["is_ai"] = True
        result["generated_at"] = now.strftime("%Y-%m-%d %H:%M")

        AI_SECTION_CACHE["top_plans"]["data"] = result
        AI_SECTION_CACHE["top_plans"]["last_fetch"] = now

        return jsonify(result)

    except Exception as e:
        print(f"AI Top Plans Error: {e}")
        return jsonify({"error": str(e), "fallback": True})


@app.route("/api/ai/market-deep-analysis")
def api_ai_market_deep():
    """AI วิเคราะห์เจาะลึกตลาดอ้างอิง Real-time"""
    from flask import jsonify
    global AI_SECTION_CACHE, NEWS_CACHE

    now = datetime.datetime.now()
    cache = AI_SECTION_CACHE["market_deep"]
    if cache["data"] and cache["last_fetch"]:
        if (now - cache["last_fetch"]).total_seconds() < 1800:  # 30 min cache
            return jsonify(cache["data"])

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or not GENAI_AVAILABLE:
        return jsonify({"error": "AI ไม่พร้อมใช้งาน"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        if not NEWS_CACHE["data"]:
            NEWS_CACHE["data"] = fetch_all_news()
            NEWS_CACHE["last_fetch"] = now

        recent_news = NEWS_CACHE["data"][:25]
        news_context = "\n".join([f"- {n['title']}" for n in recent_news])

        prompt = f"""วิเคราะห์ตลาดสินทรัพย์ที่เกี่ยวข้องกับแผนลงทุน กบข. จากข่าวล่าสุด:

{news_context}

สินทรัพย์ที่ กบข. ลงทุน:
1. ทองคำ (XAUUSD) - แผนทองคำ
2. S&P 500 / หุ้นโลก - แผนหุ้นต่างประเทศ
3. SET Index / หุ้นไทย - แผนหุ้นไทย
4. ตราสารหนี้โลก - แผนตราสารหนี้ต่างประเทศ
5. USD/THB - อัตราแลกเปลี่ยน (กระทบทุกแผนต่างประเทศ)

ตอบเป็น JSON:
{{
  "gold": {{
    "trend": "bullish/bearish/neutral",
    "signal": "buy/sell/hold",
    "key_driver": "ปัจจัยหลักที่ส่งผล",
    "impact_gpf": "ผลกระทบต่อแผนทองคำ กบข."
  }},
  "us_equity": {{
    "trend": "bullish/bearish/neutral",
    "signal": "buy/sell/hold",
    "key_driver": "ปัจจัยหลัก",
    "impact_gpf": "ผลกระทบต่อแผนหุ้นต่างประเทศ"
  }},
  "thai_equity": {{
    "trend": "bullish/bearish/neutral",
    "signal": "buy/sell/hold",
    "key_driver": "ปัจจัยหลัก",
    "impact_gpf": "ผลกระทบต่อแผนหุ้นไทย"
  }},
  "bond": {{
    "trend": "bullish/bearish/neutral",
    "signal": "buy/sell/hold",
    "key_driver": "ปัจจัยหลัก เช่น นโยบาย Fed",
    "impact_gpf": "ผลกระทบต่อแผนตราสารหนี้"
  }},
  "forex": {{
    "usd_thb_trend": "แข็งค่า/อ่อนค่า/ทรงตัว",
    "impact": "ผลกระทบต่อผลตอบแทนแผนต่างประเทศ (บาท)"
  }},
  "overall_summary": "สรุปภาพรวมตลาดทั้งหมดใน 2-3 ประโยค",
  "top_opportunity": "โอกาสที่น่าสนใจที่สุดในช่วงนี้"
}}"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        result = _json.loads(text.strip())
        result["is_ai"] = True
        result["timestamp"] = now.strftime("%Y-%m-%d %H:%M")

        AI_SECTION_CACHE["market_deep"]["data"] = result
        AI_SECTION_CACHE["market_deep"]["last_fetch"] = now

        return jsonify(result)

    except Exception as e:
        print(f"AI Market Deep Analysis Error: {e}")
        return jsonify({"error": str(e)})


@app.route("/api/ai/technical-summary")
def api_ai_technical_summary():
    """AI สรุปสัญญาณเทคนิคจากตลาดหลัก"""
    from flask import jsonify
    global AI_SECTION_CACHE

    now = datetime.datetime.now()
    cache = AI_SECTION_CACHE["technical_summary"]
    if cache["data"] and cache["last_fetch"]:
        if (now - cache["last_fetch"]).total_seconds() < 1800:
            return jsonify(cache["data"])

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or not GENAI_AVAILABLE:
        return jsonify({"error": "AI ไม่พร้อมใช้งาน"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = """คุณเป็นนักวิเคราะห์ทางเทคนิค ให้สรุปสัญญาณเทคนิคสำหรับสินทรัพย์หลักที่เกี่ยวข้องกับ กบข.

สินทรัพย์: ทองคำ (XAUUSD), S&P 500, SET Index, USD/THB

ตอบเป็น JSON:
{
  "gold_xauusd": {
    "signal": "Strong Buy/Buy/Neutral/Sell/Strong Sell",
    "oscillators": "Overbought/Neutral/Oversold",
    "moving_avg": "Above/Below MA20/MA50",
    "support": "ระดับแนวรับสำคัญ",
    "resistance": "ระดับแนวต้านสำคัญ",
    "recommendation": "คำแนะนำสำหรับสมาชิก กบข."
  },
  "sp500": {
    "signal": "Strong Buy/Buy/Neutral/Sell/Strong Sell",
    "oscillators": "Overbought/Neutral/Oversold",
    "moving_avg": "Above/Below MA20/MA50",
    "support": "ระดับแนวรับ",
    "resistance": "ระดับแนวต้าน",
    "recommendation": "คำแนะนำ"
  },
  "set_index": {
    "signal": "Strong Buy/Buy/Neutral/Sell/Strong Sell",
    "oscillators": "Overbought/Neutral/Oversold",
    "moving_avg": "Above/Below MA20/MA50",
    "support": "ระดับแนวรับ",
    "resistance": "ระดับแนวต้าน",
    "recommendation": "คำแนะนำ"
  },
  "usd_thb": {
    "signal": "บาทแข็ง/บาทอ่อน/ทรงตัว",
    "trend": "Uptrend/Downtrend/Sideways",
    "impact_foreign_plans": "ผลกระทบต่อแผนลงทุนต่างประเทศ"
  },
  "overall_technical_view": "สรุปมุมมองภาพรวมจากสัญญาณเทคนิค",
  "action_suggestion": "คำแนะนำสำหรับสมาชิก กบข. ที่ต้องการปรับแผน"
}"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        result = _json.loads(text.strip())
        result["is_ai"] = True
        result["timestamp"] = now.strftime("%Y-%m-%d %H:%M")

        AI_SECTION_CACHE["technical_summary"]["data"] = result
        AI_SECTION_CACHE["technical_summary"]["last_fetch"] = now

        return jsonify(result)

    except Exception as e:
        print(f"AI Technical Summary Error: {e}")
        return jsonify({"error": str(e)})


@app.route("/api/ai/news-impact")
def api_ai_news_impact():
    """AI วิเคราะห์ข่าวและให้คะแนนผลกระทบต่อแต่ละแผน"""
    from flask import jsonify
    global AI_SECTION_CACHE, NEWS_CACHE

    now = datetime.datetime.now()
    cache = AI_SECTION_CACHE["news_impact"]
    if cache["data"] and cache["last_fetch"]:
        if (now - cache["last_fetch"]).total_seconds() < 3600:
            return jsonify(cache["data"])

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or not GENAI_AVAILABLE:
        return jsonify({"error": "AI ไม่พร้อมใช้งาน"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        if not NEWS_CACHE["data"]:
            NEWS_CACHE["data"] = fetch_all_news()
            NEWS_CACHE["last_fetch"] = now

        recent_news = NEWS_CACHE["data"][:20]
        news_list = "\n".join([f"{i+1}. {n['title']} ({n['date']})" for i, n in enumerate(recent_news)])

        prompt = f"""วิเคราะห์ข่าวล่าสุดและให้คะแนนผลกระทบต่อแผนลงทุน กบข.:

ข่าว:
{news_list}

แผนลงทุน กบข. ที่ต้องวิเคราะห์:
1. แผนหุ้นต่างประเทศ (equity_intl)
2. แผนทองคำ (gold)
3. แผนหุ้นไทย (equity_thai)
4. แผนตราสารหนี้ (fixed_income)
5. แผนตราสารหนี้ต่างประเทศ (fixed_intl)

ตอบเป็น JSON:
{{
  "news_analysis": [
    {{
      "headline": "หัวข้อข่าว (ย่อให้สั้น)",
      "sentiment": "positive/negative/neutral",
      "impact_scores": {{
        "equity_intl": {{ "score": -5 ถึง +5, "reason": "เหตุผลสั้นๆ" }},
        "gold": {{ "score": -5 ถึง +5, "reason": "เหตุผล" }},
        "equity_thai": {{ "score": -5 ถึง +5, "reason": "เหตุผล" }},
        "fixed_income": {{ "score": -5 ถึง +5, "reason": "เหตุผล" }}
      }}
    }}
  ],
  "aggregate_impact": {{
    "most_positive_plan": "แผนที่ได้ประโยชน์มากสุด",
    "most_negative_plan": "แผนที่เสียประโยชน์มากสุด",
    "overall_sentiment": "positive/negative/neutral",
    "recommendation": "คำแนะนำสำหรับสมาชิก กบข. จากข่าวเหล่านี้"
  }},
  "top_3_impactful_news": ["ข่าวที่มีผลกระทบมากที่สุด 3 ข่าว"]
}}

วิเคราะห์เฉพาะ 5 ข่าวที่สำคัญที่สุด"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        result = _json.loads(text.strip())
        result["is_ai"] = True
        result["analyzed_at"] = now.strftime("%Y-%m-%d %H:%M")
        result["news_count"] = len(recent_news)

        AI_SECTION_CACHE["news_impact"]["data"] = result
        AI_SECTION_CACHE["news_impact"]["last_fetch"] = now

        return jsonify(result)

    except Exception as e:
        print(f"AI News Impact Error: {e}")
        return jsonify({"error": str(e)})


@app.route("/api/ai/academy-insight")
def api_ai_academy_insight():
    """AI สร้าง Educational Content ตามสถานการณ์ตลาด"""
    from flask import jsonify
    global AI_SECTION_CACHE, NEWS_CACHE

    now = datetime.datetime.now()
    cache = AI_SECTION_CACHE["academy_insight"]
    if cache["data"] and cache["last_fetch"]:
        if (now - cache["last_fetch"]).total_seconds() < 7200:  # 2 hour cache
            return jsonify(cache["data"])

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or not GENAI_AVAILABLE:
        return jsonify({"error": "AI ไม่พร้อมใช้งาน"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        if not NEWS_CACHE["data"]:
            NEWS_CACHE["data"] = fetch_all_news()
            NEWS_CACHE["last_fetch"] = now

        recent_news = NEWS_CACHE["data"][:15]
        news_context = "\n".join([f"- {n['title']}" for n in recent_news])

        prompt = f"""คุณเป็นอาจารย์สอนการลงทุนของ กบข. สร้าง Educational Content ที่เชื่อมโยงกับสถานการณ์ตลาดปัจจุบัน

ข่าวล่าสุด:
{news_context}

ตอบเป็น JSON:
{{
  "daily_lesson": {{
    "title": "หัวข้อบทเรียนวันนี้ (เชื่อมโยงกับข่าว)",
    "content": "เนื้อหาอธิบายความรู้การลงทุน 2-3 ประโยค",
    "practical_tip": "เคล็ดลับที่นำไปใช้ได้จริง"
  }},
  "term_of_the_day": {{
    "term": "ศัพท์การลงทุนที่ควรรู้",
    "definition": "คำอธิบาย",
    "example": "ตัวอย่างที่เกี่ยวข้องกับ กบข."
  }},
  "myth_buster": {{
    "myth": "ความเชื่อผิดๆ เกี่ยวกับการลงทุน",
    "truth": "ความจริง",
    "evidence": "หลักฐานหรือเหตุผล"
  }},
  "market_connection": {{
    "current_event": "เหตุการณ์ในข่าวที่เกิดขึ้น",
    "lesson_learned": "บทเรียนที่ได้จากเหตุการณ์นี้",
    "how_gpf_member_benefits": "สมาชิก กบข. จะได้ประโยชน์อย่างไร"
  }},
  "quiz": {{
    "question": "คำถามทดสอบความรู้",
    "options": ["ตัวเลือก A", "ตัวเลือก B", "ตัวเลือก C"],
    "correct_answer": "A/B/C",
    "explanation": "คำอธิบายคำตอบ"
  }}
}}"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        result = _json.loads(text.strip())
        result["is_ai"] = True
        result["generated_date"] = now.strftime("%Y-%m-%d")

        AI_SECTION_CACHE["academy_insight"]["data"] = result
        AI_SECTION_CACHE["academy_insight"]["last_fetch"] = now

        return jsonify(result)

    except Exception as e:
        print(f"AI Academy Insight Error: {e}")
        return jsonify({"error": str(e)})


@app.route("/api/ai/roadmap-insight")
def api_ai_roadmap_insight():
    """AI วิเคราะห์แผนการลงทุนสำหรับอนาคต"""
    from flask import jsonify
    global AI_SECTION_CACHE, NEWS_CACHE

    now = datetime.datetime.now()
    cache = AI_SECTION_CACHE["roadmap_insight"]
    if cache["data"] and cache["last_fetch"]:
        if (now - cache["last_fetch"]).total_seconds() < 7200:
            return jsonify(cache["data"])

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or not GENAI_AVAILABLE:
        return jsonify({"error": "AI ไม่พร้อมใช้งาน"})

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        if not NEWS_CACHE["data"]:
            NEWS_CACHE["data"] = fetch_all_news()
            NEWS_CACHE["last_fetch"] = now

        recent_news = NEWS_CACHE["data"][:20]
        news_context = "\n".join([f"- {n['title']}" for n in recent_news])

        prompt = f"""คุณเป็นผู้เชี่ยวชาญวางแผนการลงทุนระยะยาวของ กบข. วิเคราะห์และแนะนำแผนการลงทุนสำหรับอนาคต

ข่าวและแนวโน้มล่าสุด:
{news_context}

แผน กบข. ที่มี:
- แผนตราสารหนี้ระยะสั้น (ความเสี่ยงต่ำมาก)
- แผนตราสารหนี้ (ความเสี่ยงปานกลาง)
- แผนทองคำ (ความเสี่ยงปานกลาง-สูง)
- แผนหุ้นต่างประเทศ (ความเสี่ยงสูง)
- แผนหุ้นไทย (ความเสี่ยงสูงมาก)
- แผน Life Path / สมดุลตามอายุ

ตอบเป็น JSON:
{{
  "short_term": {{
    "horizon": "0-1 ปี",
    "recommended_plans": ["แผนที่ 1", "แผนที่ 2"],
    "allocation": "สัดส่วนที่แนะนำ",
    "reasoning": "เหตุผลที่แนะนำ ตามสถานการณ์ปัจจุบัน",
    "risk_factors": ["ความเสี่ยงที่ต้องระวัง"]
  }},
  "medium_term": {{
    "horizon": "1-3 ปี",
    "recommended_plans": ["แผนที่ 1", "แผนที่ 2"],
    "allocation": "สัดส่วน",
    "reasoning": "เหตุผล",
    "opportunities": ["โอกาสที่น่าสนใจ"]
  }},
  "long_term": {{
    "horizon": "3+ ปี",
    "recommended_plans": ["แผนที่ 1", "แผนที่ 2"],
    "allocation": "สัดส่วน",
    "reasoning": "เหตุผล",
    "growth_drivers": ["ปัจจัยขับเคลื่อนการเติบโต"]
  }},
  "mega_trends": [
    {{
      "trend": "ชื่อ Mega Trend",
      "impact_on_gpf": "ผลกระทบต่อการลงทุน กบข.",
      "recommended_action": "คำแนะนำ"
    }}
  ],
  "key_message": "ข้อความสำคัญสำหรับสมาชิก กบข.",
  "disclaimer": "คำเตือน: การลงทุนมีความเสี่ยง..."
}}"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        result = _json.loads(text.strip())
        result["is_ai"] = True
        result["analyzed_at"] = now.strftime("%Y-%m-%d %H:%M")

        AI_SECTION_CACHE["roadmap_insight"]["data"] = result
        AI_SECTION_CACHE["roadmap_insight"]["last_fetch"] = now

        return jsonify(result)

    except Exception as e:
        print(f"AI Roadmap Insight Error: {e}")
        return jsonify({"error": str(e)})


def get_latest_return(f):
    if f["r_jun68"] is not None:
        return f["r_jun68"]
    if f["r2567"] is not None:
        return f["r2567"]
    return 0.0


def get_recent_annual(f):
    return f["r2567"] if f["r2567"] is not None else 0.0


def compute_scores():
    scored = []
    momentum = get_asset_momentum()
    
    for f in FUNDS:
        latest = get_latest_return(f)
        annual = get_recent_annual(f)
        avg3 = f["avg_3y"] if f["avg_3y"] is not None else latest
        avg5 = f["avg_5y"] if f["avg_5y"] is not None else avg3
        si = f["since_inception"] if f["since_inception"] is not None else avg3
        mdd = abs(f["max_drawdown"])
        
        # Calculate momentum proxy
        f_mom = 0.0
        if f["id"] in momentum:
            f_mom = momentum[f["id"]]
        elif "equity_intl" in f["id"] or f["id"] == "growth65":
            f_mom = momentum.get("equity_intl", 0) * 0.65
        elif "growth35" in f["id"] or "basic" in f["id"] or "shariah" in f["id"]:
            f_mom = momentum.get("equity_intl", 0) * 0.35
            
        raw = (
            latest * 0.20 + annual * 0.20 + avg3 * 0.15 + si * 0.15
            + (8 - f["risk_level"]) * 0.5 * 0.10 - mdd * 0.05
            + (latest - avg3) * 0.15
            + f_mom * 0.15  # Incorporate short-term momentum
        )
        scored.append({**f, "raw_score": raw, "latest_return": latest,
                       "annual_return": annual, "eff_avg3": avg3,
                       "eff_avg5": avg5, "eff_si": si, "momentum_score": f_mom})
    mn = min(s["raw_score"] for s in scored)
    mx = max(s["raw_score"] for s in scored)
    rng = mx - mn if mx != mn else 1
    for s in scored:
        s["score"] = round((s["raw_score"] - mn) / rng * 100)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def estimate_correlation(f1_id, f2_id):
    if ("gold" in f1_id and "equity" in f2_id) or ("gold" in f2_id and "equity" in f1_id):
        return -0.05
    if ("gold" in f1_id and "reit" in f2_id) or ("gold" in f2_id and "reit" in f1_id):
        return 0.05
    if "gold" in f1_id and ("fixed" in f2_id or "deposit" in f2_id):
        return 0.10
    if "gold" in f2_id and ("fixed" in f1_id or "deposit" in f1_id):
        return 0.10
    if ("fixed" in f1_id or "deposit" in f1_id) and "equity" in f2_id:
        return 0.15
    if ("fixed" in f2_id or "deposit" in f2_id) and "equity" in f1_id:
        return 0.15
    if f1_id == "equity_thai" and f2_id == "equity_intl":
        return 0.55
    if f2_id == "equity_thai" and f1_id == "equity_intl":
        return 0.55
    if f1_id == f2_id:
        return 1.0
    return 0.35


def estimate_volatility(f):
    mdd = abs(f["max_drawdown"])
    returns = [f[k] for k in ["r2564", "r2565", "r2566", "r2567", "r_jun68"] if f[k] is not None]
    if len(returns) >= 2:
        avg = sum(returns) / len(returns)
        var = sum((r - avg) ** 2 for r in returns) / len(returns)
        std = var ** 0.5
        return max(std, mdd * 0.4)
    return mdd * 0.5


def best_two_plan_combos(scored):
    combos = []
    weights = list(range(5, 100, 5))
    for f1, f2 in itertools.combinations(scored, 2):
        vol1 = estimate_volatility(f1)
        vol2 = estimate_volatility(f2)
        corr = estimate_correlation(f1["id"], f2["id"])
        best_metric = -999
        best_data = None
        for w1 in weights:
            w2 = 100 - w1
            if f1["id"] == "gold" and w1 > 25:
                continue
            if f2["id"] == "gold" and w2 > 25:
                continue
            a1, a2 = w1 / 100, w2 / 100
            bl_latest = f1["latest_return"] * a1 + f2["latest_return"] * a2
            bl_annual = f1["annual_return"] * a1 + f2["annual_return"] * a2
            bl_avg3 = f1["eff_avg3"] * a1 + f2["eff_avg3"] * a2
            bl_si = f1["eff_si"] * a1 + f2["eff_si"] * a2
            pv1 = vol1 * a1
            pv2 = vol2 * a2
            bl_vol = (pv1 ** 2 + pv2 ** 2 + 2 * corr * pv1 * pv2) ** 0.5
            bl_sharpe = bl_latest / bl_vol if bl_vol > 0.01 else 0
            metric = (
                bl_latest * 0.25 + bl_annual * 0.20 + bl_avg3 * 0.15
                + bl_si * 0.10 + bl_sharpe * 2 * 0.20 - bl_vol * 0.05 * 0.10
            )
            if metric > best_metric:
                best_metric = metric
                best_data = {"w1": w1, "w2": w2,
                             "latest": round(bl_latest, 2), "annual": round(bl_annual, 2),
                             "avg3": round(bl_avg3, 2), "si": round(bl_si, 2),
                             "vol": round(bl_vol, 2), "sharpe": round(bl_sharpe, 2), "corr": corr}
        combos.append({"f1": f1, "f2": f2, "metric": round(best_metric, 2), **best_data})
    combos.sort(key=lambda x: x["metric"], reverse=True)
    return combos[:5]


# =========================================================================
# HTML — Deep Analytics section ใช้ TradingView Widgets แทน yfinance
# =========================================================================
HTML = r"""
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GPF Investment Analysis | วิเคราะห์แผนการลงทุน กบข.</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--gpf:#003d8f;--dark:#001a4d;--gold:#d4a843;--light:#f0f4ff;--green:#2e7d32;--red:#c62828}
*{font-family:'Prompt',sans-serif}
body{background:var(--light);min-height:100vh}
.gpf-nav{background:linear-gradient(135deg,var(--dark),var(--gpf));padding:.5rem 0}
.hero{background:linear-gradient(135deg,var(--dark) 0%,var(--gpf) 50%,#1565c0 100%);color:#fff;padding:2rem 0 1.8rem;position:relative;overflow:hidden}
.hero::after{content:'';position:absolute;bottom:0;left:0;right:0;height:50px;background:linear-gradient(0deg,var(--light),transparent)}
.stitle{font-weight:700;margin-bottom:1rem;padding-left:.5rem;border-left:4px solid var(--gpf)}
.card-f{border:none;border-radius:1rem;overflow:hidden;transition:.3s;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.card-f:hover{transform:translateY(-6px);box-shadow:0 10px 30px rgba(0,0,0,.12)}
.ch{color:#fff;font-weight:600;padding:.6rem 1rem;font-size:.88rem}
.sc{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.9rem;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.sc-lg{width:75px;height:75px;font-size:1.4rem}
.risk-b{display:flex;gap:2px;align-items:flex-end}
.risk-b .b{width:12px;border-radius:2px}
.ab{height:22px;border-radius:11px;overflow:hidden;background:#e0e0e0;display:flex}
.ab div{height:100%;display:flex;align-items:center;justify-content:center;font-size:.55rem;color:#fff;font-weight:500}
.rec-box{border:none;border-left:6px solid var(--gold);background:linear-gradient(90deg,#fffde7,#fff);border-radius:1rem;box-shadow:0 4px 20px rgba(0,0,0,.07)}
.combo-card{border:2px solid transparent;border-radius:1rem;transition:.3s;overflow:hidden}
.combo-card:hover{border-color:var(--gpf);box-shadow:0 6px 20px rgba(0,0,0,.1)}
.combo-best{border:3px solid var(--gold);box-shadow:0 6px 25px rgba(212,168,67,.25)}
.sb{background:#fff;border-radius:.75rem;padding:1rem;text-align:center;box-shadow:0 1px 6px rgba(0,0,0,.04)}
.sb .n{font-size:1.3rem;font-weight:700}
.rk{position:absolute;top:-5px;left:-5px;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.72rem;color:#fff;z-index:2;box-shadow:0 2px 6px rgba(0,0,0,.2)}
.pp{width:110px;height:110px;border-radius:50%;position:relative;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.75rem;color:var(--dark)}
.ts th,.ts td{font-size:.8rem;padding:.35rem .5rem}
.alb{height:28px;border-radius:14px;overflow:hidden;display:flex;font-size:.72rem;font-weight:600;color:#fff}
.alb div{display:flex;align-items:center;justify-content:center}
footer{background:var(--dark);color:#fff;padding:1rem 0;margin-top:2rem}
.text-gold{color:var(--gold)}
.bg-gold{background:var(--gold)}
.val-pos{color:var(--green)}
.val-neg{color:var(--red)}
.tv-tab-btn{cursor:pointer;padding:.3rem .85rem;border-radius:20px;font-size:.8rem;border:1.5px solid #003d8f;color:#003d8f;background:#fff;transition:.2s;font-family:'Prompt',sans-serif}
.tv-tab-btn.active,.tv-tab-btn:hover{background:#003d8f;color:#fff}
.tv-widget-wrap{border-radius:.75rem;overflow:hidden;border:1px solid #e0e8f8}
@media(max-width:768px){.hero{padding:1rem 0}.stitle{font-size:1rem}}
</style>
</head>
<body>
<nav class="gpf-nav">
 <div class="container d-flex justify-content-between align-items-center">
  <span class="text-white fw-bold"><i class="bi bi-bank2"></i> GPF Investment Analysis</span>
  <span class="text-white-50 small"><i class="bi bi-clock"></i> ข้อมูล Factsheet ณ 10 พ.ย. 2568 | อัปเดต {{ now }}</span>
 </div>
</nav>

<section class="hero text-center">
 <div class="container" style="position:relative;z-index:1">
  <p class="small opacity-50 mb-0">กองทุนบำเหน็จบำนาญข้าราชการ (กบข.)</p>
  <h1 class="fw-bold mb-1" style="font-size:1.6rem"><i class="bi bi-graph-up-arrow"></i> วิเคราะห์แผนการลงทุน กบข.</h1>
  <p class="opacity-75 mb-0">ข้อมูลจริงจาก Factsheet — แนะนำ 2 แผนที่ดีที่สุดจาก {{ funds|length }} แผน</p>
 </div>
</section>

<div class="container py-3">

<!-- ======= YOUR PORTFOLIO ======= -->
<h4 class="stitle"><i class="bi bi-person-badge"></i> พอร์ตปัจจุบันของคุณ</h4>
<div class="card border-0 shadow-sm rounded-4 mb-4">
 <div class="card-body">
  <div class="row align-items-center">
   <div class="col-md-3 text-center mb-3 mb-md-0">
    <div class="pp mx-auto" style="background:conic-gradient(#1565C0 0% 75.07%, #FF8F00 75.07% 100%)">
     <div style="width:65px;height:65px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:.6rem;text-align:center;line-height:1.2">
      {{ "{:,.0f}".format(port.total) }}<br>บาท
     </div>
    </div>
    <p class="small text-muted mt-2 mb-0">ณ {{ port.as_of }}</p>
    <span class="badge bg-danger mt-1">ระดับความเสี่ยง: {{ port.risk_assessment }}</span>
   </div>
   <div class="col-md-9">
    <div class="row g-2 mb-2">
     <div class="col-4"><div class="sb"><div class="n text-primary">{{ "{:,.0f}".format(port.total) }}</div><div class="text-muted small">ยอดรวม (บาท)</div></div></div>
     <div class="col-4"><div class="sb"><div class="n val-pos">{{ "{:,.0f}".format(port.profit) }}</div><div class="text-muted small">ผลประโยชน์ (บาท)</div></div></div>
     <div class="col-4"><div class="sb"><div class="n text-gold">+{{ port.profit_pct }}%</div><div class="text-muted small">กำไรจากเงินต้น</div></div></div>
    </div>
    <table class="table table-sm ts mb-1">
     <thead class="table-light"><tr><th>แผน</th><th class="text-end">หน่วย</th><th class="text-end">NAV/หน่วย</th><th class="text-end">มูลค่า (บาท)</th><th class="text-end">%</th></tr></thead>
     <tbody>
     {% for h in port.holdings %}
      <tr><td>{{ h.plan }}</td><td class="text-end">{{ "{:,.4f}".format(h.units) }}</td><td class="text-end">{{ "{:,.4f}".format(h.nav) }}</td><td class="text-end fw-bold">{{ "{:,.2f}".format(h.value) }}</td><td class="text-end"><span class="badge bg-primary">{{ h.pct }}%</span></td></tr>
     {% endfor %}
     </tbody>
    </table>
    <p class="small text-muted mb-0"><i class="bi bi-arrow-repeat"></i> เปลี่ยนแผนได้อีก {{ port.changes_remaining }} ครั้งในปีนี้ | ผลประเมินความเสี่ยงหมดอายุ {{ port.risk_valid_until }}</p>
   </div>
  </div>
 </div>
</div>

<!-- ======= MARKET OUTLOOK ======= -->
<h4 class="stitle"><i class="bi bi-globe-americas"></i> สถานการณ์ปัจจุบันและมุมมองการลงทุน (<span id="out-date">{{ outlook.date }}</span>) <span class="badge bg-primary text-white ms-2 rounded-pill shadow-sm" id="out-ai-badge" style="font-size:0.65rem; display:none; background: linear-gradient(135deg, #1d4ed8, #9333ea) !important;"><i class="bi bi-robot"></i> AI Generated (Real-time)</span></h4>
<div class="card border-0 shadow-sm rounded-4 mb-4" style="border-left:5px solid #1E88E5 !important;">
 <div class="card-body">
  <div class="row g-3 small" id="outlook-content">
   <div class="col-md-6">
    <p class="mb-2"><strong class="text-primary"><i class="bi bi-graph-up-arrow"></i> เศรษฐกิจโลก:</strong> <span id="out-global">{{ outlook.global_economy }}</span></p>
    <p class="mb-0"><strong class="text-danger"><i class="bi bi-geo-alt-fill"></i> เศรษฐกิจไทย:</strong> <span id="out-thai">{{ outlook.thai_economy }}</span></p>
   </div>
   <div class="col-md-6">
    <p class="mb-2"><strong class="text-gold"><i class="bi bi-shield-fill-check"></i> มุมมองทองคำ:</strong> <span id="out-gold">{{ outlook.gold_view }}</span></p>
    <p class="mb-0"><strong class="text-success"><i class="bi bi-bullseye"></i> กลยุทธ์แนะนำ:</strong> <span id="out-strategy">{{ outlook.strategy }}</span></p>
   </div>
  </div>
  
  <hr class="text-muted opacity-25 my-3">
  
  <!-- GPF Fear & Greed Index Gauge -->
  <div class="row align-items-center">
    <div class="col-md-3 text-center mb-2 mb-md-0">
        <strong><i class="bi bi-speedometer2 text-danger"></i> GPF Fear & Greed Index</strong>
    </div>
    <div class="col-md-9">
        <div class="d-flex justify-content-between mb-1" style="font-size:0.75rem;">
            <span class="text-danger fw-bold">Extreme Fear (0)</span>
            <span class="text-warning fw-bold">Neutral (50)</span>
            <span class="text-success fw-bold">Extreme Greed (100)</span>
        </div>
        <div class="progress" style="height:14px; border-radius:7px; background:linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #198754 100%); position: relative;">
            <div id="fg-pointer" style="position:absolute; top:-4px; width:4px; height:22px; background:#000; border-radius:2px; box-shadow:0 0 4px white; left: 50%; transition: left 1s ease-in-out;"></div>
        </div>
        <div class="text-center mt-2 small text-muted" id="fg-text">
            กำลังวิเคราะห์ความเชื่อมั่นตลาด...
        </div>
        <!-- Hidden data from backend -->
        <span id="fg-data" style="display:none;">{{ outlook.fear_greed_score | default('50') }}</span>
    </div>
  </div>
 </div>
</div>

<!-- ======= TOP RECOMMENDATION ======= -->
<h4 class="stitle"><i class="bi bi-trophy-fill text-gold"></i> แนะนำ 2 แผนที่ดีที่สุดสำหรับสภาวะตลาดช่วงนี้</h4>
<div class="rec-box p-4 mb-4">
 <div class="row align-items-center">
  <div class="col-auto d-none d-md-block"><span style="font-size:2.5rem">🏆</span></div>
  <div class="col">
   <span class="badge bg-gold text-dark fw-bold px-3 py-2 mb-2" style="font-size:.9rem">#1 BEST COMBO</span>
   <h4 class="fw-bold mb-2">
    {{ best.f1.icon }} {{ best.f1.name_th }} <span class="text-gold fw-bold">{{ best.w1 }}%</span>
    &nbsp;+&nbsp;
    {{ best.f2.icon }} {{ best.f2.name_th }} <span class="text-gold fw-bold">{{ best.w2 }}%</span>
   </h4>
   <div class="alb mb-3" style="max-width:500px">
    <div style="width:{{ best.w1 }}%;background:{{ best.f1.color }}">{{ best.f1.name_en }} {{ best.w1 }}%</div>
    <div style="width:{{ best.w2 }}%;background:{{ best.f2.color }}">{{ best.f2.name_en }} {{ best.w2 }}%</div>
   </div>
   <div class="row g-2 mb-2" style="max-width:600px">
    <div class="col-auto"><span class="badge bg-success fs-6"><i class="bi bi-arrow-up"></i> ล่าสุด (มิ.ย.68) {{ best.latest }}%</span></div>
    <div class="col-auto"><span class="badge bg-info text-dark">ปี 2567: {{ best.annual }}%</span></div>
    <div class="col-auto"><span class="badge bg-secondary">เฉลี่ย 3 ปี: {{ best.avg3 }}%</span></div>
    <div class="col-auto"><span class="badge bg-warning text-dark">Sharpe {{ best.sharpe }}</span></div>
    <div class="col-auto"><span class="badge bg-light text-dark border">Vol {{ best.vol }}%</span></div>
   </div>
  </div>
  <div class="col-md-2 text-center mt-3 mt-md-0">
   <div class="sc sc-lg mx-auto mb-1" style="background:var(--gold)">{{ best.metric }}</div>
   <div class="small text-muted">Combo Score</div>
  </div>
 </div>
 <div class="mt-3 p-3 rounded" style="background:#fff9e6">
  <p class="mb-0 small">
   <i class="bi bi-lightbulb-fill text-warning"></i>
   <strong>เหตุผลที่ระบบแนะนำพอร์ตนี้:</strong>
   <strong>{{ best.f1.name_th }}</strong> เป็น Growth Engine ในขณะที่ <strong>{{ best.f2.name_th }}</strong> ทำหน้าที่ Safe Haven / Defensive Asset<br>
   <span class="text-muted mt-2 d-inline-block">
    <i class="bi bi-check-circle-fill text-success"></i> Correlation ต่ำระดับ {{ best.corr }} → กระจายความเสี่ยงได้ดีเยี่ยม<br>
    <i class="bi bi-check-circle-fill text-success"></i> Sharpe Ratio {{ best.sharpe }} → คุ้มค่าต่อความเสี่ยงสูงสุด
   </span>
  </p>
 </div>
</div>

<!-- ======= CURRENT vs RECOMMENDED ======= -->
<h4 class="stitle"><i class="bi bi-arrow-left-right"></i> เปรียบเทียบ: พอร์ตปัจจุบัน vs แผนแนะนำ</h4>
<div class="card border-0 shadow-sm rounded-4 mb-4">
 <div class="card-body">
  <div class="row g-3">
   <div class="col-md-6">
    <div class="p-3 rounded-3" style="background:#e3f2fd">
     <h6 class="fw-bold text-primary"><i class="bi bi-folder2-open"></i> พอร์ตปัจจุบัน</h6>
     <div class="alb mb-2"><div style="width:75%;background:#1565C0">หุ้นต่างประเทศ 75%</div><div style="width:25%;background:#FF8F00">ทองคำ 25%</div></div>
     <table class="table table-sm ts mb-0">
      <tr><td>ล่าสุด (มิ.ย.68)</td><td class="text-end fw-bold">{{ cur_latest }}%</td></tr>
      <tr><td>ปี 2567</td><td class="text-end">{{ cur_annual }}%</td></tr>
      <tr><td>Vol (ประมาณ)</td><td class="text-end">{{ cur_vol }}%</td></tr>
     </table>
    </div>
   </div>
   <div class="col-md-6">
    <div class="p-3 rounded-3" style="background:#fff8e1">
     <h6 class="fw-bold text-gold"><i class="bi bi-star-fill"></i> แผนแนะนำ</h6>
     <div class="alb mb-2"><div style="width:{{ best.w1 }}%;background:{{ best.f1.color }}">{{ best.f1.name_en }} {{ best.w1 }}%</div><div style="width:{{ best.w2 }}%;background:{{ best.f2.color }}">{{ best.f2.name_en }} {{ best.w2 }}%</div></div>
     <table class="table table-sm ts mb-0">
      <tr><td>ล่าสุด (มิ.ย.68)</td><td class="text-end fw-bold val-pos">{{ best.latest }}%</td></tr>
      <tr><td>ปี 2567</td><td class="text-end val-pos">{{ best.annual }}%</td></tr>
      <tr><td>Vol (ประมาณ)</td><td class="text-end">{{ best.vol }}%</td></tr>
     </table>
    </div>
   </div>
  </div>
  {% if diff_latest != 0 or action_required %}
  <div class="alert {% if action_required %}alert-warning border-warning{% elif diff_latest > 0 %}alert-success{% else %}alert-info{% endif %} mt-3 mb-0 small shadow-sm">
   <div class="d-flex align-items-start gap-2">
     <i class="bi bi-{% if action_required %}exclamation-triangle-fill text-warning fs-5{% elif diff_latest > 0 %}check-circle-fill text-success fs-5{% else %}info-circle-fill text-info fs-5{% endif %}" style="margin-top:-2px"></i>
     <div>
       {% if action_required %}
       <strong class="text-dark">⚠️ สัญญาณสับเปลี่ยนแผน (Action Required):</strong><br>
       <span class="text-dark">{{ action_msg }}</span>
       {% else %}
           {% if diff_latest > 0 %}
           แผนแนะนำให้ผลตอบแทนล่าสุดสูงกว่าพอร์ตปัจจุบัน <strong>+{{ diff_latest }}%</strong>
           (≈ <strong>{{ "{:,.0f}".format(port.total * diff_latest / 100) }} บาท/ปี</strong>) ยิ่งไปกว่านั้นยังมีแนวโน้มเชิงบวกจากกราฟเทคนิค
           {% else %}
           พอร์ตปัจจุบันของคุณแข็งแกร่งและเป็นหนึ่งในคู่ที่ดีที่สุดอยู่แล้ว! อาจปรับสัดส่วนเล็กน้อยตามแผนแนะนำเพื่อเพิ่ม Sharpe Ratio
           {% endif %}
       {% endif %}
     </div>
   </div>
  </div>
  {% endif %}
 </div>
</div>

<!-- ======= TOP 5 COMBOS ======= -->
<h4 class="stitle"><i class="bi bi-list-ol"></i> Top 5 คู่แผนที่ให้ผลตอบแทนดีที่สุด</h4>
<div class="row g-3 mb-4">
{% for c in combos %}
 <div class="col-12">
  <div class="card combo-card {% if loop.index==1 %}combo-best{% endif %}">
   <div class="card-body py-3">
    <div class="row align-items-center">
     <div class="col-auto">
      <span class="badge {% if loop.index==1 %}bg-gold text-dark{% elif loop.index==2 %}bg-secondary{% elif loop.index==3 %}bg-dark{% else %}bg-light text-dark border{% endif %} rounded-pill px-3 py-2 fw-bold">#{{ loop.index }}</span>
     </div>
     <div class="col">
      <strong>{{ c.f1.icon }} {{ c.f1.name_th }} {{ c.w1 }}%</strong> + <strong>{{ c.f2.icon }} {{ c.f2.name_th }} {{ c.w2 }}%</strong>
      <div class="alb mt-1" style="height:18px;max-width:350px;font-size:.6rem">
       <div style="width:{{ c.w1 }}%;background:{{ c.f1.color }}">{{ c.w1 }}%</div>
       <div style="width:{{ c.w2 }}%;background:{{ c.f2.color }}">{{ c.w2 }}%</div>
      </div>
     </div>
     <div class="col-auto text-end small">
      <span class="badge bg-success">มิ.ย.68: {{ c.latest }}%</span>
      <span class="badge bg-info text-dark">2567: {{ c.annual }}%</span>
      <span class="badge bg-warning text-dark">Sharpe {{ c.sharpe }}</span>
      <span class="badge bg-light text-dark border">Vol {{ c.vol }}%</span>
     </div>
     <div class="col-auto">
      <div class="sc" style="background:{% if loop.index==1 %}var(--gold){% elif loop.index<=3 %}var(--gpf){% else %}#78909c{% endif %};font-size:.8rem">{{ c.metric }}</div>
     </div>
    </div>
   </div>
  </div>
 </div>
{% endfor %}
</div>

<!-- ======= DEEP ANALYTICS — TradingView iframe embeds ======= -->
<h4 class="stitle"><i class="bi bi-display"></i> เจาะลึกตลาดอ้างอิง (Deep Analytics · Real-time)</h4>

<!-- ═══════════════════════════════════════════════════════════════
     LEGEND — สี badge สอดคล้องกับสินทรัพย์ใน กบข.
     🟡 #f59e0b  = แผนทองคำ (ทองคำ 100%)
     🔵 #1d4ed8  = ตราสารทุนโลก ตลาดพัฒนาแล้ว (หุ้นต่างประเทศ)
     🟣 #7c3aed  = ตราสารทุนโลก ตลาดเกิดใหม่
     🟢 #16a34a  = อัตราแลกเปลี่ยน (กระทบแผนต่างประเทศทุกแผน)
     🔴 #dc2626  = ตราสารหนี้โลก (World Bond)
     ⚫ #374151  = ตราสารทุนไทย / อสังหาริมทรัพย์ไทย (ไม่มี widget)
     ══════════════════════════════════════════════════════════════ -->

<!-- ── ส่วนที่ 1: Ticker Tape — ราคา real-time ทุกสินทรัพย์ กบข. ── -->
<div class="card border-0 shadow-sm rounded-4 mb-3">
  <div class="card-body p-3">
    <h6 class="fw-bold mb-2"><i class="bi bi-activity"></i> ราคาสินทรัพย์ กบข. Real-time</h6>

    <!-- Legend badges -->
    <div class="d-flex flex-wrap gap-2 mb-2">
      <span class="badge rounded-pill" style="background:#f59e0b">🥇 แผนทองคำ</span>
      <span class="badge rounded-pill" style="background:#1d4ed8">🌍 ตราสารทุนโลก (พัฒนาแล้ว)</span>
      <span class="badge rounded-pill" style="background:#7c3aed">🚀 ตราสารทุนโลก (เกิดใหม่/เทค)</span>
      <span class="badge rounded-pill" style="background:#dc2626">📄 ตราสารหนี้โลก</span>
      <span class="badge rounded-pill" style="background:#16a34a">🇹🇭 อัตราแลกเปลี่ยน (กระทบแผนต่างประเทศ)</span>
    </div>

    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
      {
        "symbols": [
          {"proName":"OANDA:XAUUSD",    "title":"🥇 ทองคำ XAUUSD · แผนทองคำ กบข."},
          {"proName":"SP:SPX", "title":"🌍 S&P500 · ตราสารทุนโลก (พัฒนาแล้ว) 65%"},
          {"proName":"FOREXCOM:NSXUSD", "title":"🚀 Nasdaq100 · ตราสารทุนโลก (เทค/เกิดใหม่) 35%"},
          {"proName":"TVC:US10Y",       "title":"📄 US10Y Yield · ตราสารหนี้โลก (ภาครัฐ) 70%"},
          {"proName":"OANDA:USDTHB",    "title":"🇹🇭 USD/THB · อัตราแลกเปลี่ยน (กระทบแผนต่างประเทศ)"}
        ],
        "showSymbolLogo": true,
        "isTransparent": false,
        "displayMode": "adaptive",
        "locale": "en",
        "colorTheme": "light"
      }
      </script>
    </div>

    <!-- SET Index + Thai REIT — ดึงจาก Flask /api/market (Yahoo Finance + SET API) -->
    <div class="mt-3">
      <div class="d-flex align-items-center gap-2 mb-2">
        <span class="badge" style="background:#003d8f">แผนหุ้นไทย · อสังหาริมทรัพย์ไทย</span>
        <span class="fw-bold small">🇹🇭 SET Index & Thai REIT — ข้อมูลตลาดหลักทรัพย์ไทย</span>
        <button onclick="loadSetData()" id="set-refresh-btn" class="btn btn-sm btn-outline-secondary ms-auto py-0 px-2" style="font-size:.72rem">
          <i class="bi bi-arrow-clockwise"></i> รีเฟรช
        </button>
      </div>
      <div class="row g-3">

        <!-- SET Index line chart -->
        <div class="col-lg-8">
          <div class="rounded-3 border p-3" style="background:#fff;min-height:240px">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <span class="fw-bold small">📈 SET Index (^SETI) — 3 เดือนล่าสุด</span>
              <div id="set-price-box" class="text-end small">
                <div class="text-muted"><div class="spinner-border spinner-border-sm"></div></div>
              </div>
            </div>
            <canvas id="set-chart" style="max-height:180px"></canvas>
            <p class="text-muted mt-1 mb-0 text-end" style="font-size:.68rem">ที่มา: Yahoo Finance (^SETI) · อัปเดตเมื่อโหลดหน้า</p>
          </div>
        </div>

        <!-- Thai REIT table -->
        <div class="col-lg-4">
          <div class="rounded-3 border p-3 h-100" style="background:#fff;min-height:240px">
            <p class="fw-bold small mb-2">🏢 Thai REIT Quotes</p>
            <div id="reit-table">
              <div class="text-center text-muted py-4">
                <div class="spinner-border spinner-border-sm me-1"></div> กำลังโหลด...
              </div>
            </div>
            <p class="text-muted mt-2 mb-0 text-end" style="font-size:.68rem">ที่มา: Yahoo Finance (.BK)</p>
          </div>
        </div>

      </div><!-- /row -->
    </div>
  </div>
</div>

<!-- ── ส่วนที่ 2: กราฟ Symbol Overview (OANDA forex เท่านั้นที่ใช้ได้) ── -->
<div class="card border-0 shadow-sm rounded-4 mb-3">
  <div class="card-body p-3">
    <h6 class="fw-bold mb-3"><i class="bi bi-graph-up"></i> กราฟราคา Interactive — สินทรัพย์หลัก กบข.</h6>
    <div class="row g-3">

      <!-- ทองคำ -->
      <div class="col-md-6">
        <div class="rounded-3 border overflow-hidden" style="height:320px">
          <div class="px-3 py-2 d-flex align-items-center gap-2" style="background:#fffbf0;border-bottom:2px solid #f59e0b">
            <span class="badge rounded-pill" style="background:#f59e0b">แผนทองคำ กบข.</span>
            <span class="fw-bold small">🥇 ทองคำ (XAUUSD)</span>
            <span class="ms-auto text-muted" style="font-size:.7rem">OANDA:XAUUSD</span>
          </div>
          <div class="tradingview-widget-container" style="height:calc(100% - 42px);width:100%">
            <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
            <div class="tradingview-widget-copyright"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
            {"symbols":[["แผนทองคำ กบข. | XAUUSD","OANDA:XAUUSD|1D"]],"chartOnly":false,"width":"100%","height":"100%","locale":"th","colorTheme":"light","autosize":true,"showVolume":false,"showMA":true,"hideDateRanges":false,"scalePosition":"right","scaleMode":"Normal","fontSize":"10","valuesTracking":"1","changeMode":"price-and-percent","chartType":"candlesticks","maLineColor":"#f59e0b","maLineWidth":1,"maLength":20,"dateRanges":["1d|1","1m|30","3m|60","12m|1D","all|1M"]}
            </script>
          </div>
        </div>
      </div>

      <!-- USD/THB -->
      <div class="col-md-6">
        <div class="rounded-3 border overflow-hidden" style="height:320px">
          <div class="px-3 py-2 d-flex align-items-center gap-2" style="background:#f0fdf4;border-bottom:2px solid #16a34a">
            <span class="badge rounded-pill" style="background:#16a34a">อัตราแลกเปลี่ยน</span>
            <span class="fw-bold small">🇹🇭 USD/THB</span>
            <span class="ms-auto text-muted" style="font-size:.7rem">กระทบแผนหุ้นต่างประเทศ + ตราสารหนี้โลก</span>
          </div>
          <div class="tradingview-widget-container" style="height:calc(100% - 42px);width:100%">
            <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
            <div class="tradingview-widget-copyright"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
            {"symbols":[["USD/THB | กระทบแผนต่างประเทศ กบข.","OANDA:USDTHB|1D"]],"chartOnly":false,"width":"100%","height":"100%","locale":"th","colorTheme":"light","autosize":true,"showVolume":false,"showMA":true,"hideDateRanges":false,"scalePosition":"right","scaleMode":"Normal","fontSize":"10","valuesTracking":"1","changeMode":"price-and-percent","chartType":"area","maLineColor":"#16a34a","maLineWidth":1,"maLength":20,"dateRanges":["1d|1","1m|30","3m|60","12m|1D","all|1M"]}
            </script>
          </div>
        </div>
      </div>

    </div>
  </div>
</div>

<!-- ── ส่วนที่ 3: Technical Sentiment — 3 สินทรัพย์หลัก กบข. ── -->
<div class="card border-0 shadow-sm rounded-4 mb-4">
  <div class="card-body p-3">
    <h6 class="fw-bold mb-1"><i class="bi bi-speedometer2"></i> สัญญาณเทคนิค (Technical Sentiment · Real-time)</h6>
    <p class="text-muted small mb-3">Buy/Sell signal จาก Oscillators + Moving Averages — แยกตามสินทรัพย์ใน กบข.</p>
    <div class="row g-3">

      <!-- ทองคำ — OANDA:XAUUSD -->
      <div class="col-md-4">
        <div class="rounded-3 border h-100 overflow-hidden">
          <div class="px-3 py-2 d-flex flex-column gap-1" style="background:#fffbf0;border-bottom:2px solid #f59e0b">
            <div class="d-flex align-items-center gap-2">
              <span class="badge rounded-pill" style="background:#f59e0b">แผนทองคำ กบข.</span>
              <span class="text-muted" style="font-size:.7rem">สินทรัพย์: ทองคำ 100%</span>
            </div>
            <div class="fw-bold small">🥇 ทองคำ (Gold Spot · XAUUSD)</div>
            <div class="text-muted" style="font-size:.68rem">OANDA:XAUUSD · ราคาทองคำโลก USD/ออนซ์</div>
          </div>
          <div class="tradingview-widget-container p-1">
            <div class="tradingview-widget-container__widget"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
            {"interval":"1D","width":"100%","isTransparent":true,"height":420,"symbol":"OANDA:XAUUSD","showIntervalTabs":true,"displayMode":"multiple","locale":"en","colorTheme":"light"}
            </script>
          </div>
        </div>
      </div>

      <!-- S&P500 — FOREXCOM:SPXUSD — ตราสารทุนโลก พัฒนาแล้ว -->
      <div class="col-md-4">
        <div class="rounded-3 border h-100 overflow-hidden">
          <div class="px-3 py-2 d-flex flex-column gap-1" style="background:#eff6ff;border-bottom:2px solid #1d4ed8">
            <div class="d-flex align-items-center gap-2">
              <span class="badge rounded-pill" style="background:#1d4ed8">ตราสารทุนโลก (พัฒนาแล้ว)</span>
              <span class="text-muted" style="font-size:.7rem">สัดส่วน: 65% ของหุ้นต่างประเทศ</span>
            </div>
            <div class="fw-bold small">🌍 S&P 500 Index (SP:SPX)</div>
            <div class="text-muted" style="font-size:.68rem">SP:SPX · ดัชนีหุ้นสหรัฐ 500 บริษัทใหญ่</div>
          </div>
          <div class="tradingview-widget-container p-1">
            <div class="tradingview-widget-container__widget"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
            {"interval":"1D","width":"100%","isTransparent":true,"height":420,"symbol":"SP:SPX","showIntervalTabs":true,"displayMode":"multiple","locale":"en","colorTheme":"light"}
            </script>
          </div>
        </div>
      </div>

      <!-- USD/THB — OANDA:USDTHB — อัตราแลกเปลี่ยน -->
      <div class="col-md-4">
        <div class="rounded-3 border h-100 overflow-hidden">
          <div class="px-3 py-2 d-flex flex-column gap-1" style="background:#f0fdf4;border-bottom:2px solid #16a34a">
            <div class="d-flex align-items-center gap-2">
              <span class="badge rounded-pill" style="background:#16a34a">อัตราแลกเปลี่ยน</span>
              <span class="text-muted" style="font-size:.7rem">กระทบแผนต่างประเทศทุกแผน</span>
            </div>
            <div class="fw-bold small">🇹🇭 USD / THB</div>
            <div class="text-muted" style="font-size:.68rem">OANDA:USDTHB · บาทอ่อน → ผลตอบแทนต่างประเทศ (THB) ↑</div>
          </div>
          <div class="tradingview-widget-container p-1">
            <div class="tradingview-widget-container__widget"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
            {"interval":"1D","width":"100%","isTransparent":true,"height":420,"symbol":"OANDA:USDTHB","showIntervalTabs":true,"displayMode":"multiple","locale":"en","colorTheme":"light"}
            </script>
          </div>
        </div>
      </div>

    </div><!-- /row -->

    <!-- คำอธิบายการเชื่อมโยงสินทรัพย์ กบข. กับสัญญาณ -->
    <div class="mt-3 p-3 rounded-3" style="background:#f8faff;border:1px solid #dbeafe">
      <p class="fw-bold small mb-2 text-primary"><i class="bi bi-link-45deg"></i> ความสัมพันธ์ของสัญญาณกับสินทรัพย์ใน กบข.</p>
      <div class="row g-2">
        <div class="col-md-4">
          <div class="d-flex align-items-start gap-2">
            <span class="badge mt-1 flex-shrink-0" style="background:#f59e0b">ทองคำ</span>
            <span class="small text-muted">XAUUSD <strong>Strong Buy</strong> = แผนทองคำ กบข. มีแนวโน้มดี | ราคาทองขึ้น → NAV แผนทองคำเพิ่ม</span>
          </div>
        </div>
        <div class="col-md-4">
          <div class="d-flex align-items-start gap-2">
            <span class="badge mt-1 flex-shrink-0" style="background:#1d4ed8">หุ้นต่างประเทศ</span>
            <span class="small text-muted">SPXUSD <strong>Strong Buy</strong> = แผนหุ้นต่างประเทศ 95% และแผน Life Path มีแนวโน้มดี</span>
          </div>
        </div>
        <div class="col-md-4">
          <div class="d-flex align-items-start gap-2">
            <span class="badge mt-1 flex-shrink-0" style="background:#16a34a">FX</span>
            <span class="small text-muted">USD/THB <strong>ขึ้น</strong> (บาทอ่อน) → ผลตอบแทนแผนต่างประเทศเมื่อแปลงเป็นบาทสูงขึ้น แม้ตลาดไม่เปลี่ยน</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ======= REALTIME NEWS ======= -->
<h4 class="stitle"><i class="bi bi-newspaper"></i> ข่าวสารการลงทุนล่าสุด (ย้อนหลัง 1 เดือน)</h4>
<div class="row g-3 mb-4" id="news-container">
    <div class="col-12 text-center py-4 text-muted" id="news-loading"><div class="spinner-border spinner-border-sm me-2"></div> กำลังโหลดข่าวสาร...</div>
</div>
<div class="text-center mb-5" id="news-load-more-container" style="display:none;">
    <button class="btn btn-outline-primary rounded-pill px-4" onclick="loadMoreNews()" id="btn-load-more">โหลดข่าวเพิ่มเติม <i class="bi bi-chevron-down"></i></button>
</div>

<!-- ======= GPF ACADEMY ======= -->
<h4 class="stitle" id="gpf-academy"><i class="bi bi-mortarboard-fill"></i> ศูนย์จัดระดับความรู้ กบข. (GPF Academy)</h4>
<div class="row g-3 mb-4">
    <!-- Level 101 -->
    <div class="col-md-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:#f0fdf4; border-left:4px solid #16a34a !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="bg-success text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width:36px;height:36px;"><i class="bi bi-book"></i></div>
                    <h6 class="fw-bold mb-0 text-success">ระดับ 101: มือใหม่หัดออม</h6>
                </div>
                <p class="small text-muted mb-2"><strong>กบข. คืออะไร?</strong> กองทุนบำเหน็จบำนาญข้าราชการ ช่วยให้คุณมีเงินใช้หลังเกษียณ</p>
                <p class="small text-muted mb-2"><strong>เงินสะสม vs เงินสมทบ:</strong> คุณออม 3% รัฐแถมให้ 3% ฟรีๆ! ยิ่งออมเพิ่ม (สูงสุด 30%) ยิ่งลดหย่อนภาษีได้มาก</p>
                <p class="small text-muted mb-0"><strong>ทำไมต้องเลือกแผน?</strong> แผนเริ่มต้น (แผนหลัก) มักมีผลตอบแทนต่ำกว่าอัตราเงินเฟ้อในระยะยาว การเลือกแผนให้เหมาะกับอายุจะช่วยให้เงินโตขึ้น</p>
            </div>
        </div>
    </div>
    <!-- Level 201 -->
    <div class="col-md-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:#eff6ff; border-left:4px solid #2563eb !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width:36px;height:36px;"><i class="bi bi-bar-chart-fill"></i></div>
                    <h6 class="fw-bold mb-0 text-primary">ระดับ 201: รู้จัก 12 แผนลงทุน</h6>
                </div>
                <p class="small text-muted mb-2"><strong>ความเสี่ยงต่ำ:</strong> แผนตลาดเงิน, แผนตราสารหนี้ (เงินไม่หาย แต่โตช้า)</p>
                <p class="small text-muted mb-2"><strong>ความเสี่ยงปานกลาง:</strong> แผนหลัก, แผนผสมหุ้น 35%, แผนสมดุลตามอายุ (ระบบปรับให้อัตโนมัติเมื่ออายุเยอะขึ้น)</p>
                <p class="small text-muted mb-0"><strong>ความเสี่ยงสูง:</strong> แผนตราสารทุนไทย, แผนหุ้นต่างประเทศ, แผนทองคำ (ผันผวนสูง แต่มีโอกาสผลตอบแทนสูงในระยะยาว)</p>
            </div>
        </div>
    </div>
    <!-- Level 301 -->
    <div class="col-md-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:#fefce8; border-left:4px solid #ca8a04 !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="bg-warning text-dark rounded-circle d-flex align-items-center justify-content-center me-2" style="width:36px;height:36px;"><i class="bi bi-lightbulb-fill"></i></div>
                    <h6 class="fw-bold mb-0 text-dark">ระดับ 301: กลยุทธ์จัดพอร์ต</h6>
                </div>
                <p class="small text-muted mb-2"><strong>การจับจังหวะ (Timing):</strong> ใช้เครื่องมือ "เจาะลึกตลาดอ้างอิง" เพื่อดูแนวโน้มว่าควรซื้อ/ขายในช่วงนี้</p>
                <p class="small text-muted mb-2"><strong>แผนผสม (Customized Plan):</strong> ไม่ต้องเลือกแผนเดียว สามารถจับคู่ เช่น "หุ้นนอก 60% + หุ้นไทย 30% + ทอง 10%" ด้วยสัดส่วนตัวเองได้</p>
                <p class="small text-muted mb-0"><strong>คำแนะนำที่สำคัญ:</strong> อย่าเปลี่ยนแผนบ่อยตามอารมณ์ตลาด ให้มองระยะยาว 3-5 ปีขึ้นไป</p>
            </div>
        </div>
    </div>
</div>

<div class="alert alert-info border-info shadow-sm rounded-4 mb-4" id="ai-academy-tip" style="display:none;">
   <div class="d-flex align-items-start gap-2">
     <i class="bi bi-robot text-primary fs-5 mt-1"></i>
     <div>
       <strong class="text-primary">💡 AI Insight ประจำวันนี้:</strong>
       <span class="text-dark d-block mt-1" id="out-academy-tip">กำลังวิเคราะห์ข้อมูล...</span>
     </div>
   </div>
</div>

<!-- ======= AI HUB - ADVANCED FEATURES ======= -->
<h4 class="stitle" id="ai-hub"><i class="bi bi-cpu-fill"></i> AI Hub — เครื่องมือวิเคราะห์อัจฉริยะ <span class="badge rounded-pill text-white ms-2" style="font-size:0.6rem; background:linear-gradient(135deg, #7c3aed, #db2777);">NEW</span></h4>

<!-- AI Usage Legend -->
<div class="alert mb-3 py-2 px-3 rounded-3 d-flex flex-wrap align-items-center gap-3" style="background:linear-gradient(135deg, #f8fafc, #f1f5f9); border:1px solid #e2e8f0;">
    <span class="small fw-bold text-muted"><i class="bi bi-info-circle"></i> สัญลักษณ์:</span>
    <span class="badge rounded-pill text-white" style="background:linear-gradient(135deg, #8b5cf6, #a855f7); font-size:0.65rem;"><i class="bi bi-robot"></i> Gemini AI</span>
    <span class="small text-muted">= ใช้ AI ประมวลผล</span>
    <span class="badge rounded-pill bg-secondary" style="font-size:0.65rem;"><i class="bi bi-calculator"></i> Algorithm</span>
    <span class="small text-muted">= คำนวณทางคณิตศาสตร์</span>
    <span class="badge rounded-pill bg-info text-dark" style="font-size:0.65rem;"><i class="bi bi-database"></i> RAG</span>
    <span class="small text-muted">= ค้นหาจากฐานความรู้</span>
</div>

<div class="row g-3 mb-4">
    <!-- AI Portfolio Advisor -->
    <div class="col-md-6 col-lg-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:linear-gradient(135deg, #f0f9ff, #e0f2fe); border-left:4px solid #0ea5e9 !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width:42px;height:42px;background:linear-gradient(135deg,#0284c7,#0ea5e9);"><i class="bi bi-pie-chart-fill"></i></div>
                    <div>
                        <h6 class="fw-bold mb-0" style="color:#0369a1;">AI Portfolio Advisor <span class="badge rounded-pill text-white" style="background:linear-gradient(135deg, #8b5cf6, #a855f7); font-size:0.55rem;"><i class="bi bi-robot"></i> AI</span></h6>
                        <small class="text-muted">แนะนำสัดส่วนลงทุนส่วนตัว</small>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="small text-muted">อายุ (ปี)</label>
                    <input type="number" id="ai-age" class="form-control form-control-sm" value="35" min="20" max="60">
                </div>
                <div class="mb-3">
                    <label class="small text-muted">ระดับความเสี่ยงที่รับได้</label>
                    <select id="ai-risk" class="form-select form-select-sm">
                        <option value="low">ต่ำ - รักษาเงินต้น</option>
                        <option value="medium" selected>ปานกลาง - สมดุล</option>
                        <option value="high">สูง - เน้นเติบโต</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="small text-muted">เงินเดือน (บาท)</label>
                    <input type="number" id="ai-salary" class="form-control form-control-sm" value="30000" step="1000">
                </div>
                <button class="btn btn-primary btn-sm w-100 rounded-pill" onclick="getPortfolioAdvice()">
                    <i class="bi bi-magic"></i> วิเคราะห์ด้วย AI
                </button>
                <div id="ai-portfolio-result" class="mt-3" style="display:none;"></div>
            </div>
        </div>
    </div>

    <!-- Retirement Projection -->
    <div class="col-md-6 col-lg-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:linear-gradient(135deg, #fefce8, #fef3c7); border-left:4px solid #eab308 !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width:42px;height:42px;background:linear-gradient(135deg,#ca8a04,#eab308);"><i class="bi bi-graph-up-arrow"></i></div>
                    <div>
                        <h6 class="fw-bold mb-0" style="color:#a16207;">Retirement Projection <span class="badge rounded-pill bg-secondary" style="font-size:0.55rem;"><i class="bi bi-calculator"></i> Algo</span> <span class="badge rounded-pill text-white" style="background:linear-gradient(135deg, #8b5cf6, #a855f7); font-size:0.55rem;"><i class="bi bi-robot"></i> AI</span></h6>
                        <small class="text-muted">จำลองเงินเกษียณ Monte Carlo</small>
                    </div>
                </div>
                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <label class="small text-muted">อายุปัจจุบัน</label>
                        <input type="number" id="retire-age-now" class="form-control form-control-sm" value="35">
                    </div>
                    <div class="col-6">
                        <label class="small text-muted">อายุเกษียณ</label>
                        <input type="number" id="retire-age-target" class="form-control form-control-sm" value="60">
                    </div>
                </div>
                <div class="mb-3">
                    <label class="small text-muted">ผลตอบแทนคาดหวัง (%/ปี)</label>
                    <input type="number" id="retire-return" class="form-control form-control-sm" value="6" step="0.5">
                </div>
                <div class="mb-3">
                    <label class="small text-muted">บำนาญที่ต้องการ (บาท/เดือน)</label>
                    <input type="number" id="retire-pension" class="form-control form-control-sm" value="20000" step="1000">
                </div>
                <button class="btn btn-warning btn-sm w-100 rounded-pill text-dark" onclick="runRetirementProjection()">
                    <i class="bi bi-calculator"></i> จำลอง Monte Carlo
                </button>
                <div id="retire-result" class="mt-3" style="display:none;"></div>
            </div>
        </div>
    </div>

    <!-- Scenario Analysis -->
    <div class="col-md-6 col-lg-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:linear-gradient(135deg, #fef2f2, #fee2e2); border-left:4px solid #ef4444 !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width:42px;height:42px;background:linear-gradient(135deg,#dc2626,#ef4444);"><i class="bi bi-exclamation-triangle-fill"></i></div>
                    <div>
                        <h6 class="fw-bold mb-0" style="color:#b91c1c;">Scenario Analysis <span class="badge rounded-pill text-white" style="background:linear-gradient(135deg, #8b5cf6, #a855f7); font-size:0.55rem;"><i class="bi bi-robot"></i> AI</span></h6>
                        <small class="text-muted">วิเคราะห์ผลกระทบวิกฤต</small>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="small text-muted">เลือกสถานการณ์</label>
                    <select id="scenario-type" class="form-select form-select-sm">
                        <option value="recession">📉 เศรษฐกิจถดถอย (Recession)</option>
                        <option value="inflation">💹 เงินเฟ้อพุ่งสูง</option>
                        <option value="war">⚔️ สงครามตะวันออกกลาง</option>
                        <option value="tech_crash">💻 ฟองสบู่เทคฯ แตก</option>
                        <option value="china_crisis">🇨🇳 วิกฤตจีน</option>
                        <option value="fed_pivot">🏦 Fed ลดดอกเบี้ยเร็ว</option>
                        <option value="gold_surge">🥇 ทองคำพุ่ง $3,000</option>
                        <option value="baht_weak">💱 บาทอ่อนค่า 40฿/$</option>
                        <option value="custom">✏️ กำหนดเอง...</option>
                    </select>
                </div>
                <div class="mb-3" id="custom-scenario-wrap" style="display:none;">
                    <label class="small text-muted">รายละเอียดสถานการณ์</label>
                    <textarea id="custom-scenario" class="form-control form-control-sm" rows="2" placeholder="อธิบายสถานการณ์ที่ต้องการวิเคราะห์..."></textarea>
                </div>
                <button class="btn btn-danger btn-sm w-100 rounded-pill" onclick="runScenarioAnalysis()">
                    <i class="bi bi-lightning-fill"></i> วิเคราะห์ผลกระทบ
                </button>
                <div id="scenario-result" class="mt-3" style="display:none;"></div>
            </div>
        </div>
    </div>

    <!-- Daily Research -->
    <div class="col-md-6 col-lg-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:linear-gradient(135deg, #f0fdf4, #dcfce7); border-left:4px solid #22c55e !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width:42px;height:42px;background:linear-gradient(135deg,#16a34a,#22c55e);"><i class="bi bi-newspaper"></i></div>
                    <div>
                        <h6 class="fw-bold mb-0" style="color:#15803d;">Daily AI Research <span class="badge rounded-pill text-white" style="background:linear-gradient(135deg, #8b5cf6, #a855f7); font-size:0.55rem;"><i class="bi bi-robot"></i> AI</span></h6>
                        <small class="text-muted">รายงานวิจัยประจำวัน</small>
                    </div>
                </div>
                <p class="small text-muted mb-3">AI รวบรวมข่าวและวิเคราะห์ตลาดให้อัตโนมัติทุกวัน พร้อมคำแนะนำสำหรับสมาชิก กบข.</p>
                <button class="btn btn-success btn-sm w-100 rounded-pill" onclick="loadDailyResearch()">
                    <i class="bi bi-file-earmark-text"></i> ดูรายงานวันนี้
                </button>
                <div id="research-result" class="mt-3" style="display:none;"></div>
            </div>
        </div>
    </div>

    <!-- Rebalance Check -->
    <div class="col-md-6 col-lg-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:linear-gradient(135deg, #faf5ff, #f3e8ff); border-left:4px solid #a855f7 !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width:42px;height:42px;background:linear-gradient(135deg,#9333ea,#a855f7);"><i class="bi bi-arrow-repeat"></i></div>
                    <div>
                        <h6 class="fw-bold mb-0" style="color:#7e22ce;">Rebalance Check <span class="badge rounded-pill text-white" style="background:linear-gradient(135deg, #8b5cf6, #a855f7); font-size:0.55rem;"><i class="bi bi-robot"></i> AI</span></h6>
                        <small class="text-muted">ตรวจสอบการปรับสมดุลพอร์ต</small>
                    </div>
                </div>
                <p class="small text-muted mb-3">วิเคราะห์ว่าพอร์ตปัจจุบันของคุณเบี่ยงเบนจากเป้าหมายหรือไม่ พร้อมคำแนะนำ</p>
                <button class="btn rounded-pill btn-sm w-100 text-white" style="background:linear-gradient(135deg,#9333ea,#a855f7);" onclick="checkRebalance()">
                    <i class="bi bi-clipboard-check"></i> ตรวจสอบพอร์ต
                </button>
                <div id="rebalance-result" class="mt-3" style="display:none;"></div>
            </div>
        </div>
    </div>

    <!-- Document Q&A -->
    <div class="col-md-6 col-lg-4">
        <div class="card border-0 shadow-sm rounded-4 h-100" style="background:linear-gradient(135deg, #fff7ed, #ffedd5); border-left:4px solid #f97316 !important;">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width:42px;height:42px;background:linear-gradient(135deg,#ea580c,#f97316);"><i class="bi bi-chat-square-quote-fill"></i></div>
                    <div>
                        <h6 class="fw-bold mb-0" style="color:#c2410c;">Document Q&A <span class="badge rounded-pill bg-info text-dark" style="font-size:0.55rem;"><i class="bi bi-database"></i> RAG</span> <span class="badge rounded-pill text-white" style="background:linear-gradient(135deg, #8b5cf6, #a855f7); font-size:0.55rem;"><i class="bi bi-robot"></i> AI</span></h6>
                        <small class="text-muted">ถาม-ตอบเกี่ยวกับ กบข.</small>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="small text-muted">พิมพ์คำถามเกี่ยวกับ กบข.</label>
                    <input type="text" id="qa-question" class="form-control form-control-sm" placeholder="เช่น อัตราเงินสะสมเท่าไหร่?">
                </div>
                <button class="btn btn-sm w-100 rounded-pill text-white" style="background:linear-gradient(135deg,#ea580c,#f97316);" onclick="askDocumentQA()">
                    <i class="bi bi-search"></i> ค้นหาคำตอบ
                </button>
                <div id="qa-result" class="mt-3" style="display:none;"></div>
            </div>
        </div>
    </div>
</div>

<!-- ======= ROADMAP ======= -->
<h4 class="stitle"><i class="bi bi-signpost-split-fill"></i> แผนการลงทุนสำหรับอนาคต</h4>
<div class="card border-0 shadow-sm rounded-4 mb-4">
 <div class="card-body">
  <div class="row g-3">
   <div class="col-md-4"><div class="p-3 border rounded-3 h-100" style="border-top:4px solid #1E88E5 !important">
    <h6 class="fw-bold text-primary"><i class="bi bi-1-circle-fill"></i> ระยะสั้น (0-1 ปี)</h6>
    <p class="small mb-0"><strong>แนะนำ:</strong> แผนตราสารหนี้ + แผนทองคำ เพื่อเป็นหลุมหลบภัยและสร้างฐานที่มั่นคง</p>
   </div></div>
   <div class="col-md-4"><div class="p-3 border rounded-3 h-100" style="border-top:4px solid #F9A825 !important">
    <h6 class="fw-bold text-warning"><i class="bi bi-2-circle-fill"></i> ระยะกลาง (1-3 ปี)</h6>
    <p class="small mb-0"><strong>แนะนำ:</strong> แผนหุ้นต่างประเทศ รับกระแสเงินทุนเคลื่อนย้ายเข้าตลาดหุ้นโลก</p>
   </div></div>
   <div class="col-md-4"><div class="p-3 border rounded-3 h-100" style="border-top:4px solid #D84315 !important">
    <h6 class="fw-bold text-danger"><i class="bi bi-3-circle-fill"></i> ระยะยาว (3+ ปี)</h6>
    <p class="small mb-0"><strong>แนะนำ:</strong> แผนเชิงรุก 65 หรือ แผนตราสารทุนไทย+โลก เพื่อ Compound Growth</p>
   </div></div>
  </div>
  
  <div class="mt-4 p-3 rounded-3" style="background:#f0e6ff; border:1px solid #d8b4fe; display:none;" id="ai-roadmap-insight">
   <div class="d-flex align-items-start gap-2">
     <i class="bi bi-stars text-purple fs-5 mt-1" style="color:#7e22ce"></i>
     <div>
       <strong style="color:#6b21a8">มุมมองระยะยาวจาก AI:</strong>
       <span class="text-dark d-block mt-1" id="out-long-term-insight">กำลังวิเคราะห์ข้อมูล...</span>
     </div>
   </div>
  </div>

 </div>
</div>

<!-- ======= ALL FUNDS ======= -->
<h4 class="stitle"><i class="bi bi-collection"></i> รายละเอียดทุกแผน — เรียงตามคะแนน</h4>
<div class="row g-3 mb-4">
{% for f in funds %}
 <div class="col-md-6 col-xl-4">
  <div class="card card-f h-100 position-relative">
   <span class="rk" style="background:{% if loop.index==1 %}#d4a843{% elif loop.index==2 %}#78909c{% elif loop.index==3 %}#8d6e63{% else %}#90a4ae{% endif %}">#{{ loop.index }}</span>
   <div class="ch" style="background:{{ f.color }}">{{ f.icon }} {{ f.name_th }} <span class="float-end opacity-75 small">{{ f.name_en }}</span></div>
   <div class="card-body">
    <p class="small mb-2">{{ f.desc }}</p>
    <div class="d-flex justify-content-between align-items-center mb-2">
     <div><div class="small text-muted">Score</div><div class="sc" style="background:{{ f.color }}">{{ f.score }}</div></div>
     <div class="text-end">
      <div class="small text-muted">เสี่ยง</div>
      <div class="risk-b justify-content-end mb-1">{% for i in range(1,9) %}<div class="b" style="height:{{ 4+i*3 }}px;background:{% if i<=f.risk_gauge %}{{ f.color }}{% else %}#e0e0e0{% endif %}"></div>{% endfor %}</div>
      <span class="badge {% if f.risk_level<=2 %}bg-success{% elif f.risk_level<=4 %}bg-warning text-dark{% else %}bg-danger{% endif %}" style="font-size:.65rem">{{ f.risk_label }} ({{ f.risk_level }}/8)</span>
     </div>
    </div>
    <table class="table table-sm ts mb-2">
     <thead class="table-light"><tr><th colspan="2">ผลตอบแทน (% ต่อปี)</th></tr></thead>
     <tbody>
      <tr><td>มิ.ย. 2568</td><td class="text-end fw-bold {% if f.r_jun68 is not none and f.r_jun68 > 0 %}val-pos{% elif f.r_jun68 is not none %}val-neg{% endif %}">{% if f.r_jun68 is not none %}{{ "%.2f"|format(f.r_jun68) }}%{% else %}-{% endif %}</td></tr>
      <tr><td>ปี 2567</td><td class="text-end {% if f.r2567 is not none and f.r2567 > 0 %}val-pos{% elif f.r2567 is not none %}val-neg{% endif %}">{% if f.r2567 is not none %}{{ "%.2f"|format(f.r2567) }}%{% else %}-{% endif %}</td></tr>
      <tr><td>ปี 2566</td><td class="text-end">{% if f.r2566 is not none %}{{ "%.2f"|format(f.r2566) }}%{% else %}-{% endif %}</td></tr>
      <tr><td>ปี 2565</td><td class="text-end">{% if f.r2565 is not none %}{{ "%.2f"|format(f.r2565) }}%{% else %}-{% endif %}</td></tr>
      <tr><td>ปี 2564</td><td class="text-end">{% if f.r2564 is not none %}{{ "%.2f"|format(f.r2564) }}%{% else %}-{% endif %}</td></tr>
      <tr class="table-light"><td>เฉลี่ย 3 ปี</td><td class="text-end fw-bold">{% if f.avg_3y is not none %}{{ "%.2f"|format(f.avg_3y) }}%{% else %}-{% endif %}</td></tr>
      <tr class="table-light"><td>เฉลี่ย 5 ปี</td><td class="text-end">{% if f.avg_5y is not none %}{{ "%.2f"|format(f.avg_5y) }}%{% else %}-{% endif %}</td></tr>
      <tr class="table-light"><td>ตั้งแต่จัดตั้ง</td><td class="text-end">{% if f.since_inception is not none %}{{ "%.2f"|format(f.since_inception) }}%{% else %}-{% endif %}</td></tr>
      <tr><td>Max Drawdown</td><td class="text-end val-neg">{{ "%.2f"|format(f.max_drawdown) }}%</td></tr>
     </tbody>
    </table>
    <p class="small fw-bold mb-1"><i class="bi bi-pie-chart-fill"></i> สัดส่วนการลงทุน</p>
    <div class="ab mb-1">{% set cs=['#1a237e','#1565c0','#42a5f5','#90caf9','#bbdefb','#cfd8dc'] %}{% for a,p in f.assets.items() %}<div style="width:{{ p }}%;background:{{ cs[loop.index0%6] }}" title="{{ a }} {{ p }}%">{% if p>=15 %}{{ p }}%{% endif %}</div>{% endfor %}</div>
    <div class="d-flex flex-wrap gap-1">{% for a,p in f.assets.items() %}<span class="badge bg-light text-dark border" style="font-size:.55rem">{{ a }} {{ p }}%</span>{% endfor %}</div>
    <div class="mt-2 p-2 rounded" style="background:#f5f5f5"><p class="mb-0 small"><i class="bi bi-person-check"></i> <strong>เหมาะกับ:</strong> {{ f.suitable }}</p></div>
   </div>
  </div>
 </div>
{% endfor %}
</div>

<!-- ======= TABLE ======= -->
<h4 class="stitle"><i class="bi bi-table"></i> ตารางเปรียบเทียบทุกแผน</h4>
<div class="card border-0 shadow-sm rounded-4 mb-4">
 <div class="card-body p-0 table-responsive">
  <table class="table table-hover ts align-middle mb-0">
   <thead class="table-dark">
    <tr><th class="ps-3">#</th><th>แผน</th><th class="text-center">Score</th><th class="text-end">มิ.ย.68</th><th class="text-end">2567</th><th class="text-end">2566</th><th class="text-end">3Y</th><th class="text-end">5Y</th><th class="text-end">Since</th><th class="text-end">MDD</th><th class="text-center">เสี่ยง</th></tr>
   </thead>
   <tbody>
   {% for f in funds %}
    <tr{% if loop.index==1 %} class="table-warning"{% endif %}>
     <td class="ps-3 fw-bold">{{ loop.index }}</td>
     <td class="text-nowrap">{{ f.icon }} {{ f.name_th }}</td>
     <td class="text-center"><span class="badge" style="background:{{ f.color }}">{{ f.score }}</span></td>
     <td class="text-end fw-bold {% if f.r_jun68 is not none and f.r_jun68>0 %}val-pos{% elif f.r_jun68 is not none %}val-neg{% endif %}">{% if f.r_jun68 is not none %}{{ "%.2f"|format(f.r_jun68) }}%{% else %}-{% endif %}</td>
     <td class="text-end {% if f.r2567 is not none and f.r2567>0 %}val-pos{% elif f.r2567 is not none %}val-neg{% endif %}">{% if f.r2567 is not none %}{{ "%.2f"|format(f.r2567) }}%{% else %}-{% endif %}</td>
     <td class="text-end">{% if f.r2566 is not none %}{{ "%.2f"|format(f.r2566) }}%{% else %}-{% endif %}</td>
     <td class="text-end">{% if f.avg_3y is not none %}{{ "%.2f"|format(f.avg_3y) }}%{% else %}-{% endif %}</td>
     <td class="text-end">{% if f.avg_5y is not none %}{{ "%.2f"|format(f.avg_5y) }}%{% else %}-{% endif %}</td>
     <td class="text-end">{% if f.since_inception is not none %}{{ "%.2f"|format(f.since_inception) }}%{% else %}-{% endif %}</td>
     <td class="text-end val-neg">{{ "%.2f"|format(f.max_drawdown) }}%</td>
     <td class="text-center"><span class="badge {% if f.risk_level<=2 %}bg-success{% elif f.risk_level<=4 %}bg-warning text-dark{% else %}bg-danger{% endif %}">{{ f.risk_level }}/8</span></td>
    </tr>
   {% endfor %}
   </tbody>
  </table>
 </div>
</div>

<!-- ======= METHODOLOGY ======= -->
<h4 class="stitle"><i class="bi bi-calculator"></i> วิธีการวิเคราะห์</h4>
<div class="card border-0 shadow-sm rounded-4 mb-4">
 <div class="card-body">
  <p class="small mb-3">ตัวเลขผลตอบแทนทั้งหมดมาจาก <strong>PDF Factsheet กบข. ณ วันที่ 10 พฤศจิกายน 2568</strong> โดยตรง</p>
  <table class="table table-sm ts mb-3">
   <thead class="table-light"><tr><th>ปัจจัย Composite Score</th><th>น้ำหนัก</th></tr></thead>
   <tbody>
    <tr><td>ผลตอบแทนล่าสุด / ปี 2567</td><td>20% + 20%</td></tr>
    <tr><td>เฉลี่ย 3 ปี / ตั้งแต่จัดตั้ง</td><td>15% + 15%</td></tr>
    <tr><td>Momentum / ระดับความเสี่ยง (กลับด้าน) / MDD</td><td>15% / 10% / 5%</td></tr>
   </tbody>
  </table>
  <div class="alert alert-warning small mb-0">
   <i class="bi bi-exclamation-triangle-fill"></i>
   <strong>คำเตือน:</strong> ข้อมูลเพื่อประกอบการตัดสินใจเท่านั้น ผลตอบแทนในอดีตไม่รับประกันอนาคต —
   <a href="https://www.gpf.or.th" target="_blank">ศึกษาเพิ่มเติมที่ กบข.</a>
  </div>
 </div>
</div>
</div><!-- /container -->

<footer class="text-center">
 <p class="mb-0 small"><i class="bi bi-bank2"></i> GPF Investment Analysis — {{ now }}</p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
// ── SET Index + Thai REIT — ดึงข้อมูลจาก Flask /api/market ──────────────
var setChartInstance = null;

function loadSetData() {
  var btn = document.getElementById('set-refresh-btn');
  if (btn) btn.innerHTML = '<div class="spinner-border spinner-border-sm"></div>';

  fetch('/api/market')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      renderSetChart(data.set_index);
      renderReitTable(data.reits);
      if (btn) btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> รีเฟรช';
    })
    .catch(function(e) {
      console.error('SET data error:', e);
      var pb = document.getElementById('set-price-box');
      if (pb) pb.innerHTML = '<span class="text-danger small"><i class="bi bi-exclamation-triangle"></i> ไม่สามารถโหลดข้อมูลได้</span>';
      var rt = document.getElementById('reit-table');
      if (rt) rt.innerHTML = '<p class="text-danger small text-center py-3"><i class="bi bi-exclamation-triangle"></i> กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต</p>';
      if (btn) btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> รีเฟรช';
    });
}

function renderSetChart(d) {
  var pb = document.getElementById('set-price-box');
  if (!pb) return;

  if (!d || !d.ok || !d.prices || d.prices.length === 0) {
    pb.innerHTML = '<span class="text-muted small">ไม่มีข้อมูล SET</span>';
    return;
  }

  // Price box
  var pct   = d.pct !== null ? d.pct : 0;
  var color = pct >= 0 ? '#16a34a' : '#dc2626';
  var arrow = pct >= 0 ? '▲' : '▼';
  pb.innerHTML =
    '<div class="fw-bold fs-5" style="color:' + color + '">' +
      (d.price ? d.price.toLocaleString('th-TH', {minimumFractionDigits:2}) : '-') +
    '</div>' +
    '<div class="small" style="color:' + color + '">' +
      arrow + ' ' + (d.change || 0).toFixed(2) +
      ' (' + pct.toFixed(2) + '%)' +
    '</div>';

  // Chart
  var labels = d.prices.map(function(p){ return p.date; });
  var values = d.prices.map(function(p){ return p.close; });
  var isUp   = values.length > 1 && values[values.length-1] >= values[0];
  var lineColor = isUp ? '#16a34a' : '#dc2626';
  var fillColor = isUp ? 'rgba(22,163,74,0.08)' : 'rgba(220,38,38,0.08)';

  var ctx = document.getElementById('set-chart');
  if (!ctx) return;
  if (setChartInstance) { setChartInstance.destroy(); }
  setChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        borderColor: lineColor,
        backgroundColor: fillColor,
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(ctx) {
              return ' ' + ctx.parsed.y.toLocaleString('th-TH',{minimumFractionDigits:2});
            }
          }
        }
      },
      scales: {
        x: {
          ticks: { maxTicksLimit: 6, font: { size: 10 } },
          grid:  { display: false }
        },
        y: {
          ticks: {
            font: { size: 10 },
            callback: function(v){ return v.toLocaleString('th-TH',{maximumFractionDigits:0}); }
          }
        }
      }
    }
  });
}

function renderReitTable(reits) {
  var el = document.getElementById('reit-table');
  if (!el) return;
  if (!reits || reits.length === 0) {
    el.innerHTML = '<p class="text-muted small text-center py-3">ไม่มีข้อมูล REIT</p>';
    return;
  }
  var rows = reits.map(function(r) {
    var pct   = r.ok && r.pct !== null ? r.pct : null;
    var color = pct === null ? '#6b7280' : (pct >= 0 ? '#16a34a' : '#dc2626');
    var arrow = pct === null ? '' : (pct >= 0 ? '▲' : '▼');
    return '<tr>' +
      '<td style="font-size:.75rem">' + (r.label || r.symbol) + '</td>' +
      '<td class="text-end fw-bold" style="font-size:.75rem">' +
        (r.ok && r.price ? r.price.toFixed(2) : '-') +
      '</td>' +
      '<td class="text-end" style="font-size:.75rem;color:' + color + '">' +
        (pct !== null ? arrow + ' ' + pct.toFixed(2) + '%' : 'N/A') +
      '</td>' +
      '</tr>';
  }).join('');
  el.innerHTML =
    '<table class="table table-sm mb-0">' +
      '<thead><tr>' +
        '<th style="font-size:.7rem">REIT</th>' +
        '<th class="text-end" style="font-size:.7rem">ราคา (THB)</th>' +
        '<th class="text-end" style="font-size:.7rem">เปลี่ยน</th>' +
      '</tr></thead>' +
      '<tbody>' + rows + '</tbody>' +
    '</table>';
}

// ── Logic for Fear & Greed Gauge ──────────────
document.addEventListener('DOMContentLoaded', function() {
    var fgDataObj = document.getElementById('fg-data');
    if (fgDataObj) {
        var rawText = fgDataObj.innerText;
        // Try to extract a number from the text
        var match = rawText.match(/(\d+)/);
        var score = 50; // Default Neutral
        if (match) {
            score = parseInt(match[1]);
            // Ensure bounds
            if (score < 0) score = 0;
            if (score > 100) score = 100;
        }
        
        // Update pointer position
        var pointer = document.getElementById('fg-pointer');
        if (pointer) {
            pointer.style.left = score + '%';
        }
        
        // Update text description based on score
        var textEl = document.getElementById('fg-text');
        var badgeEl = document.getElementById('fg-badge');
        if (textEl && badgeEl) {
            var label = "Neutral";
            var colorClass = "text-warning";
            var bgClass = "bg-warning";
            if (score < 25) { label = "Extreme Fear"; colorClass = "text-danger"; bgClass = "bg-danger"; }
            else if (score < 45) { label = "Fear"; colorClass = "text-danger"; bgClass = "bg-danger"; }
            else if (score > 75) { label = "Extreme Greed"; colorClass = "text-success"; bgClass = "bg-success"; }
            else if (score > 55) { label = "Greed"; colorClass = "text-success"; bgClass = "bg-success"; }
            
            textEl.innerHTML = '<strong class="' + colorClass + ' fs-6">' + score + ' - ' + label + '</strong> <br><span class="opacity-75" style="font-size:0.65rem;">' + rawText + '</span>';
            badgeEl.className = 'badge ' + bgClass;
            badgeEl.innerText = score + ' ' + label;
        }
    }
});

// ── News API Pagination ──────────────
var currentNewsPage = 1;

function loadMoreNews() {
  var btn = document.getElementById('btn-load-more');
  if(btn) btn.innerHTML = '<div class="spinner-border spinner-border-sm"></div> กำลังโหลด...';
  
  fetch('/api/news?page=' + currentNewsPage + '&limit=10')
    .then(function(r){ return r.json(); })
    .then(function(data) {
      if(document.getElementById('news-loading')) document.getElementById('news-loading').remove();
      renderNews(data.items, currentNewsPage === 1);
      
      var container = document.getElementById('news-load-more-container');
      if (data.has_more) {
        container.style.display = 'block';
        if(btn) btn.innerHTML = 'โหลดข่าวเพิ่มเติม <i class="bi bi-chevron-down"></i>';
      } else {
        container.style.display = 'none';
      }
      currentNewsPage++;
    })
    .catch(function(e) {
      console.error('News error:', e);
      if(btn) btn.innerHTML = 'โหลดข่าวเพิ่มเติม <i class="bi bi-chevron-down"></i>';
      if(currentNewsPage === 1) {
        if(document.getElementById('news-loading')) document.getElementById('news-loading').remove();
        document.getElementById('news-container').innerHTML = '<div class="col-12"><div class="alert alert-secondary mb-0">ไม่สามารถดึงข้อมูลข่าวสารในขณะนี้ได้</div></div>';
      }
    });
}

function renderNews(items, isFirstPage) {
  var container = document.getElementById('news-container');
  if (isFirstPage) container.innerHTML = '';
  
  if (items.length === 0 && isFirstPage) {
     container.innerHTML = '<div class="col-12"><div class="alert alert-secondary mb-0">ไม่มีข่าวสารในช่วง 1 เดือนที่ผ่านมา</div></div>';
     return;
  }
  
  var html = items.map(function(n) {
    return '<div class="col-md-12">' +
        '<div class="card border-0 shadow-sm rounded-3">' +
            '<div class="card-body py-2 d-flex justify-content-between align-items-center">' +
                '<div>' +
                   '<a href="' + n.link + '" target="_blank" class="text-decoration-none fw-bold" style="color:#003d8f;font-size:.95rem">' + n.title + '</a>' +
                   '<div class="text-muted small mt-1"><i class="bi bi-clock"></i> ' + n.date + '</div>' +
                '</div>' +
                '<div><a href="' + n.link + '" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill px-3">อ่านต่อ</a></div>' +
            '</div>' +
        '</div>' +
    '</div>';
  }).join('');
  
  container.insertAdjacentHTML('beforeend', html);
}

// ── AI Outlook Fetching ──────────────
function loadMarketOutlook() {
  fetch('/api/outlook')
    .then(r => r.json())
    .then(data => {
      document.getElementById('out-date').innerText = data.date;
      document.getElementById('out-global').innerText = data.global_economy;
      document.getElementById('out-thai').innerText = data.thai_economy;
      document.getElementById('out-gold').innerText = data.gold_view;
      document.getElementById('out-strategy').innerText = data.strategy;
      if (data.is_ai) {
          document.getElementById('out-ai-badge').style.display = 'inline-block';
          
          if(data.academy_tip) {
             document.getElementById('out-academy-tip').innerText = data.academy_tip;
             document.getElementById('ai-academy-tip').style.display = 'block';
          }
          if(data.long_term_insight) {
             document.getElementById('out-long-term-insight').innerText = data.long_term_insight;
             document.getElementById('ai-roadmap-insight').style.display = 'block';
          }
      }
    })
    .catch(e => console.error("Error fetching AI outlook", e));
}

function runSimulation() {
    const input = document.getElementById('sim-input').value.trim();
    if(!input) return;
    
    const btn = document.getElementById('sim-btn');
    const resBox = document.getElementById('sim-result');
    const spinner = document.getElementById('sim-spinner');
    const content = document.getElementById('sim-content');
    
    btn.disabled = true;
    resBox.style.display = 'block';
    spinner.style.display = 'block';
    content.style.display = 'none';
    
    fetch('/api/simulate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scenario: input})
    })
    .then(r => r.json())
    .then(data => {
        spinner.style.display = 'none';
        content.style.display = 'block';
        btn.disabled = false;
        
        if(data.error) {
             document.getElementById('sim-scenario-text').innerText = "เกิดข้อผิดพลาด";
             document.getElementById('sim-reasoning').innerText = data.error;
             return;
        }
        
        document.getElementById('sim-scenario-text').innerText = "สถานการณ์: " + data.scenario;
        document.getElementById('sim-reasoning').innerText = data.reasoning;
        
        const pctEl = document.getElementById('sim-pct');
        pctEl.innerText = (data.total_impact_pct > 0 ? "+" : "") + data.total_impact_pct + "%";
        pctEl.className = data.total_impact_pct > 0 ? "mb-0 fw-bold val-pos" : "mb-0 fw-bold val-neg";
        
        document.getElementById('sim-new-bal').innerText = data.new_balance_thb.toLocaleString() + " B";
        
        const lossEl = document.getElementById('sim-loss');
        lossEl.innerText = (data.est_loss_thb > 0 ? "+" : "") + data.est_loss_thb.toLocaleString() + " B";
        lossEl.className = data.est_loss_thb > 0 ? "mb-0 fw-bold val-pos" : "mb-0 fw-bold val-neg";
    })
    .catch(e => {
        spinner.style.display = 'none';
        btn.disabled = false;
        console.error("Simulation error", e);
    });
}

// ══════════════════════════════════════════════════════════════════════════
// AI Hub Functions
// ══════════════════════════════════════════════════════════════════════════

// Show/hide custom scenario input
document.addEventListener('change', function(e) {
    if(e.target && e.target.id === 'scenario-type') {
        const wrap = document.getElementById('custom-scenario-wrap');
        wrap.style.display = e.target.value === 'custom' ? 'block' : 'none';
    }
});

// AI Portfolio Advisor
function getPortfolioAdvice() {
    const age = document.getElementById('ai-age').value;
    const risk = document.getElementById('ai-risk').value;
    const salary = document.getElementById('ai-salary').value;
    const resultDiv = document.getElementById('ai-portfolio-result');

    resultDiv.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm text-primary"></div> กำลังวิเคราะห์...</div>';
    resultDiv.style.display = 'block';

    fetch('/api/ai/portfolio-advice', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            age: parseInt(age),
            years_to_retire: 60 - parseInt(age),
            risk_tolerance: risk,
            monthly_salary: parseInt(salary)
        })
    })
    .then(r => r.json())
    .then(data => {
        if(data.error) {
            resultDiv.innerHTML = '<div class="alert alert-danger small py-2">' + data.error + '</div>';
            return;
        }

        let allocHtml = '<div class="small">';
        allocHtml += '<div class="fw-bold text-primary mb-2">📊 แนะนำการจัดสัดส่วน:</div>';

        if(data.recommended_allocation) {
            data.recommended_allocation.forEach(a => {
                allocHtml += '<div class="d-flex justify-content-between align-items-center mb-1">';
                allocHtml += '<span>' + a.plan_name + '</span>';
                allocHtml += '<span class="badge bg-primary">' + a.percentage + '%</span>';
                allocHtml += '</div>';
                allocHtml += '<div class="progress mb-2" style="height:6px;">';
                allocHtml += '<div class="progress-bar" style="width:' + a.percentage + '%"></div></div>';
            });
        }

        allocHtml += '<div class="mt-2 p-2 rounded" style="background:#e0f2fe;">';
        allocHtml += '<div class="fw-bold">📈 ผลตอบแทนคาดหวัง: ' + (data.expected_return_yearly || 'N/A') + '%/ปี</div>';
        allocHtml += '<div class="text-muted small">' + (data.summary || '') + '</div>';
        allocHtml += '</div></div>';

        resultDiv.innerHTML = allocHtml;
    })
    .catch(e => {
        console.error(e);
        resultDiv.innerHTML = '<div class="alert alert-danger small py-2">เกิดข้อผิดพลาด กรุณาลองใหม่</div>';
    });
}

// Retirement Projection
function runRetirementProjection() {
    const ageNow = document.getElementById('retire-age-now').value;
    const ageTarget = document.getElementById('retire-age-target').value;
    const expectedReturn = document.getElementById('retire-return').value;
    const pension = document.getElementById('retire-pension').value;
    const resultDiv = document.getElementById('retire-result');

    resultDiv.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm text-warning"></div> กำลังจำลอง 1,000 รอบ...</div>';
    resultDiv.style.display = 'block';

    fetch('/api/ai/retirement-projection', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            current_age: parseInt(ageNow),
            retirement_age: parseInt(ageTarget),
            expected_return: parseFloat(expectedReturn),
            desired_monthly_pension: parseInt(pension)
        })
    })
    .then(r => r.json())
    .then(data => {
        if(data.error) {
            resultDiv.innerHTML = '<div class="alert alert-danger small py-2">' + data.error + '</div>';
            return;
        }

        const sim = data.simulation || {};
        let html = '<div class="small">';
        html += '<div class="fw-bold text-warning mb-2">📊 ผลการจำลอง Monte Carlo:</div>';
        html += '<table class="table table-sm mb-2" style="font-size:0.75rem;">';
        html += '<tr><td>กรณีแย่ (10%)</td><td class="text-end text-danger fw-bold">' + (sim.percentile_10 || 0).toLocaleString() + ' บ.</td></tr>';
        html += '<tr><td>กรณีปกติ (50%)</td><td class="text-end text-primary fw-bold">' + (sim.percentile_50 || 0).toLocaleString() + ' บ.</td></tr>';
        html += '<tr><td>กรณีดี (90%)</td><td class="text-end text-success fw-bold">' + (sim.percentile_90 || 0).toLocaleString() + ' บ.</td></tr>';
        html += '</table>';

        if(data.ai_interpretation) {
            const ai = data.ai_interpretation;
            html += '<div class="p-2 rounded" style="background:#fef3c7;">';
            html += '<div class="fw-bold">🤖 AI วิเคราะห์: ' + (ai.goal_achievement || '') + '</div>';
            html += '<div class="text-muted small">' + (ai.interpretation || '') + '</div>';
            if(ai.recommendations && ai.recommendations.length > 0) {
                html += '<div class="mt-1 small">💡 ' + ai.recommendations[0] + '</div>';
            }
            html += '</div>';
        }
        html += '</div>';

        resultDiv.innerHTML = html;
    })
    .catch(e => {
        console.error(e);
        resultDiv.innerHTML = '<div class="alert alert-danger small py-2">เกิดข้อผิดพลาด กรุณาลองใหม่</div>';
    });
}

// Scenario Analysis
function runScenarioAnalysis() {
    const scenarioType = document.getElementById('scenario-type').value;
    const customScenario = document.getElementById('custom-scenario').value;
    const resultDiv = document.getElementById('scenario-result');

    resultDiv.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm text-danger"></div> กำลังวิเคราะห์...</div>';
    resultDiv.style.display = 'block';

    fetch('/api/ai/scenario-analysis', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            scenario_type: scenarioType,
            custom_scenario: customScenario
        })
    })
    .then(r => r.json())
    .then(data => {
        if(data.error) {
            resultDiv.innerHTML = '<div class="alert alert-danger small py-2">' + data.error + '</div>';
            return;
        }

        const impact = data.portfolio_impact || {};
        let html = '<div class="small">';
        html += '<div class="fw-bold text-danger mb-2">⚠️ ผลกระทบต่อพอร์ต:</div>';

        const impactPct = impact.total_impact_pct || 0;
        const impactClass = impactPct >= 0 ? 'text-success' : 'text-danger';
        html += '<div class="text-center mb-2">';
        html += '<div class="' + impactClass + ' fw-bold" style="font-size:1.5rem;">' + (impactPct > 0 ? '+' : '') + impactPct + '%</div>';
        html += '<div class="text-muted small">ผลกระทบโดยรวม</div>';
        html += '</div>';

        if(data.impact_by_asset) {
            html += '<div class="mb-2">';
            data.impact_by_asset.forEach(a => {
                const pct = a.impact_pct || 0;
                const cls = pct >= 0 ? 'bg-success' : 'bg-danger';
                html += '<div class="d-flex justify-content-between small">';
                html += '<span>' + a.asset + '</span>';
                html += '<span class="badge ' + cls + '">' + (pct > 0 ? '+' : '') + pct + '%</span>';
                html += '</div>';
            });
            html += '</div>';
        }

        if(data.recovery_outlook) {
            html += '<div class="p-2 rounded" style="background:#fee2e2;">';
            html += '<div class="small">📈 <b>แนวโน้มฟื้นตัว:</b> ' + data.recovery_outlook + '</div>';
            html += '</div>';
        }
        html += '</div>';

        resultDiv.innerHTML = html;
    })
    .catch(e => {
        console.error(e);
        resultDiv.innerHTML = '<div class="alert alert-danger small py-2">เกิดข้อผิดพลาด กรุณาลองใหม่</div>';
    });
}

// Daily Research
function loadDailyResearch() {
    const resultDiv = document.getElementById('research-result');

    resultDiv.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm text-success"></div> กำลังโหลดรายงาน...</div>';
    resultDiv.style.display = 'block';

    fetch('/api/ai/daily-research')
    .then(r => r.json())
    .then(data => {
        if(data.error) {
            resultDiv.innerHTML = '<div class="alert alert-danger small py-2">' + data.error + '</div>';
            return;
        }

        let html = '<div class="small">';
        html += '<div class="fw-bold text-success mb-2">📰 ' + (data.report_date || 'รายงานวันนี้') + '</div>';
        html += '<div class="mb-2">' + (data.market_summary || '') + '</div>';

        if(data.asset_outlook) {
            html += '<div class="mb-2">';
            const outlook = data.asset_outlook;
            const trendIcon = {'bullish': '🟢', 'neutral': '🟡', 'bearish': '🔴'};

            if(outlook.thai_equity) html += '<div>' + (trendIcon[outlook.thai_equity.trend] || '⚪') + ' หุ้นไทย: ' + (outlook.thai_equity.reason || '') + '</div>';
            if(outlook.intl_equity) html += '<div>' + (trendIcon[outlook.intl_equity.trend] || '⚪') + ' หุ้นโลก: ' + (outlook.intl_equity.reason || '') + '</div>';
            if(outlook.gold) html += '<div>' + (trendIcon[outlook.gold.trend] || '⚪') + ' ทองคำ: ' + (outlook.gold.reason || '') + '</div>';
            html += '</div>';
        }

        if(data.gpf_recommendation) {
            html += '<div class="p-2 rounded" style="background:#dcfce7;">';
            html += '<div class="small">💡 <b>คำแนะนำ:</b> ' + data.gpf_recommendation + '</div>';
            html += '</div>';
        }
        html += '</div>';

        resultDiv.innerHTML = html;
    })
    .catch(e => {
        console.error(e);
        resultDiv.innerHTML = '<div class="alert alert-danger small py-2">เกิดข้อผิดพลาด กรุณาลองใหม่</div>';
    });
}

// Rebalance Check
function checkRebalance() {
    const resultDiv = document.getElementById('rebalance-result');

    resultDiv.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" style="color:#9333ea;"></div> กำลังวิเคราะห์...</div>';
    resultDiv.style.display = 'block';

    fetch('/api/ai/rebalance-check', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({threshold: 5})
    })
    .then(r => r.json())
    .then(data => {
        if(data.error) {
            resultDiv.innerHTML = '<div class="alert alert-danger small py-2">' + data.error + '</div>';
            return;
        }

        let html = '<div class="small">';

        if(data.needs_rebalance) {
            html += '<div class="alert alert-warning py-2 mb-2">⚠️ <b>ควร Rebalance</b></div>';
        } else {
            html += '<div class="alert alert-success py-2 mb-2">✅ <b>พอร์ตสมดุลดี</b></div>';
        }

        if(data.overall_risk_level) {
            html += '<div class="mb-2">ระดับความเสี่ยงรวม: <b>' + data.overall_risk_level + '</b></div>';
        }

        if(data.rebalance_actions && data.rebalance_actions.length > 0) {
            html += '<div class="fw-bold mb-1">📋 คำแนะนำ:</div>';
            data.rebalance_actions.forEach(a => {
                html += '<div class="small text-muted">• ' + a.from_plan + ' → ' + a.to_plan + ' (' + a.amount_pct + '%)</div>';
            });
        }

        if(data.market_timing_note) {
            html += '<div class="mt-2 p-2 rounded" style="background:#f3e8ff;">';
            html += '<div class="small">⏰ ' + data.market_timing_note + '</div>';
            html += '</div>';
        }
        html += '</div>';

        resultDiv.innerHTML = html;
    })
    .catch(e => {
        console.error(e);
        resultDiv.innerHTML = '<div class="alert alert-danger small py-2">เกิดข้อผิดพลาด กรุณาลองใหม่</div>';
    });
}

// Document Q&A
function askDocumentQA() {
    const question = document.getElementById('qa-question').value.trim();
    if(!question) return;

    const resultDiv = document.getElementById('qa-result');

    resultDiv.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" style="color:#f97316;"></div> กำลังค้นหา...</div>';
    resultDiv.style.display = 'block';

    fetch('/api/ai/document-qa', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: question})
    })
    .then(r => r.json())
    .then(data => {
        if(data.error) {
            resultDiv.innerHTML = '<div class="alert alert-danger small py-2">' + data.error + '</div>';
            return;
        }

        let html = '<div class="small">';
        html += '<div class="p-2 rounded mb-2" style="background:#fff7ed;">';
        html += '<div class="fw-bold mb-1" style="color:#c2410c;">💬 คำตอบ:</div>';
        html += '<div>' + (data.answer || 'ไม่พบคำตอบ') + '</div>';
        html += '</div>';

        if(data.confidence) {
            const confColor = data.confidence === 'high' ? 'success' : data.confidence === 'medium' ? 'warning' : 'danger';
            html += '<div class="small text-muted">ความมั่นใจ: <span class="badge bg-' + confColor + '">' + data.confidence + '</span></div>';
        }

        if(data.related_topics && data.related_topics.length > 0) {
            html += '<div class="mt-2 small text-muted">หัวข้อที่เกี่ยวข้อง: ' + data.related_topics.join(', ') + '</div>';
        }
        html += '</div>';

        resultDiv.innerHTML = html;
    })
    .catch(e => {
        console.error(e);
        resultDiv.innerHTML = '<div class="alert alert-danger small py-2">เกิดข้อผิดพลาด กรุณาลองใหม่</div>';
    });
}

// Auto-load on page ready
document.addEventListener('DOMContentLoaded', function() {
    loadSetData();
    loadMoreNews();
    loadMarketOutlook();
});
</script>
<!-- ======= AI CHATBOT WIDGET ======= -->
<div id="ai-chat-widget">
    <button id="chat-btn" class="btn btn-primary rounded-circle shadow-lg chat-bounce" onclick="toggleChat()" style="position:fixed; bottom:30px; right:30px; width:65px; height:65px; z-index:9999; border:none; background: linear-gradient(135deg, #2563eb, #1e40af);">
        <i class="bi bi-robot text-white fs-3"></i>
    </button>
    <div id="chat-window" class="card shadow-lg border-0 rounded-4" style="display:none; position:fixed; bottom:105px; right:30px; width:360px; height:500px; z-index:9999; flex-direction:column; overflow:hidden;">
        <div class="card-header text-white px-3 py-3 d-flex justify-content-between align-items-center" style="background: linear-gradient(135deg, #1e40af, #3b82f6);">
            <div class="d-flex align-items-center gap-2">
                <i class="bi bi-robot fs-4"></i>
                <div class="lh-1">
                    <h6 class="mb-1 fw-bold text-white">น้อง กบข. AI <span class="badge rounded-pill" style="font-size:0.5rem; background:rgba(255,255,255,0.2);">Gemini</span></h6>
                    <small class="text-white-50" style="font-size:0.75rem;"><i class="bi bi-cpu"></i> Powered by AI + RAG</small>
                </div>
            </div>
            <button class="btn btn-sm btn-link text-white p-0" onclick="toggleChat()">
                <i class="bi bi-x-lg fs-5"></i>
            </button>
        </div>
        <div id="chat-messages" class="card-body bg-light overflow-auto p-3" style="flex:1;">
            <div class="d-flex gap-2 mb-3">
                <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center flex-shrink-0" style="width:30px;height:30px;"><i class="bi bi-robot small"></i></div>
                <div class="bg-white p-2 px-3 rounded-3 shadow-sm text-dark align-self-start" style="max-width:85%; font-size:0.9rem;">
                    สวัสดีครับ! ผมคือ น้อง AI ผู้ช่วย กบข. 😊 <br>คุณสามารถพิมพ์คำถาม หรือเลือกจากคำถามที่พบบ่อยด้านล่างนี้ได้เลยครับ
                    <div class="mt-2 d-flex flex-column gap-1">
                        <button class="btn btn-sm btn-outline-primary text-start rounded-pill" onclick="sendPrompt('ถ้าอายุ 30 ควรเลือกแผนไหน?')">อายุ 30 ควรเลือกแผนไหน?</button>
                        <button class="btn btn-sm btn-outline-primary text-start rounded-pill" onclick="sendPrompt('กบข. ให้ผลตอบแทนเท่าไหร่?')">แผนผลตอบแทนสูงสุด 3 ปีย้อนหลังคือ?</button>
                    </div>
                </div>
            </div>
        </div>
        <div class="card-footer bg-white p-2 border-top">
            <div class="input-group">
                <input type="text" id="chat-input" class="form-control rounded-pill border-0 bg-light px-3" placeholder="พิมพ์ข้อความที่นี่..." onkeypress="if(event.key === 'Enter') sendMessage()">
                <button class="btn text-primary bg-transparent border-0" onclick="sendMessage()"><i class="bi bi-send-fill fs-5"></i></button>
            </div>
            <div class="text-center mt-1">
                 <small class="text-muted" style="font-size:0.6rem;">ระบบนี้มีโครงสร้าง UI พร้อมต่อ API หลังบ้านในอนาคต</small>
            </div>
        </div>
    </div>
</div>
<style>
.chat-bounce { animation: bounce 2s infinite; }
@keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateY(0);} 40% {transform: translateY(-10px);} 60% {transform: translateY(-5px);} }
</style>
<script>
let chatHistory = [];

function toggleChat() {
    const w = document.getElementById('chat-window');
    w.style.display = w.style.display === 'none' ? 'flex' : 'none';
    if(w.style.display === 'flex') document.getElementById('chat-input').focus();
}

function sendPrompt(text) {
    document.getElementById('chat-input').value = text;
    sendMessage();
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if(!msg) return;
    
    appendMessage(msg, 'user');
    chatHistory.push({role: "user", parts: msg});
    input.value = '';
    
    // Add loading indicator
    const loadingId = 'loading-' + Date.now();
    const chatMsgs = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = loadingId;
    loadingDiv.className = "d-flex gap-2 mb-3";
    loadingDiv.innerHTML = `<div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center flex-shrink-0" style="width:30px;height:30px;"><i class="bi bi-robot small"></i></div>
        <div class="bg-white p-2 px-3 rounded-3 shadow-sm text-dark align-self-start" style="max-width:85%; font-size:0.9rem;"><div class="spinner-grow spinner-grow-sm text-primary" role="status"></div> กำลังพิมพ์...</div>`;
    chatMsgs.appendChild(loadingDiv);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
    
    fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg, history: chatHistory.slice(0, -1)}) // send history excluding current msg
    })
    .then(r => r.json())
    .then(data => {
        document.getElementById(loadingId).remove();
        let reply = data.reply || "ขออภัยครับ เกิดข้อผิดพลาดในการเชื่อมต่อ";
        appendMessage(reply, 'model');
        chatHistory.push({role: "model", parts: reply});
    })
    .catch(e => {
        console.error(e);
        document.getElementById(loadingId).remove();
        appendMessage("ขออภัยครับ ระบบประมวลผล AI ขัดข้องชั่วคราว ลองใหม่อีกครั้งนะครับ", 'model');
    });
}

function appendMessage(text, sender) {
    const chatMsgs = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = "d-flex gap-2 mb-3 " + (sender==='user' ? "justify-content-end" : "");
    if(sender === 'user') {
        div.innerHTML = `<div class="bg-primary text-white p-2 px-3 rounded-3 shadow-sm align-self-end" style="max-width:85%; font-size:0.9rem;">${text}</div>`;
    } else {
        // Simple markdown parsing for bold text
        const formattedText = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
        div.innerHTML = `<div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center flex-shrink-0" style="width:30px;height:30px;"><i class="bi bi-robot small"></i></div>
            <div class="bg-white p-2 px-3 rounded-3 shadow-sm text-dark align-self-start" style="max-width:85%; font-size:0.9rem;">${formattedText}</div>`;
    }
    chatMsgs.appendChild(div);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
}
</script>
</body>
</html>
"""

THAI_MONTHS = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม",
               "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม",
               "พฤศจิกายน", "ธันวาคม"]


@app.route("/")
def index():
    now = datetime.datetime.now()
    scored = compute_scores()
    combos = best_two_plan_combos(scored)
    best = combos[0]

    intl = next(f for f in FUNDS if f["id"] == "equity_intl")
    gold = next(f for f in FUNDS if f["id"] == "gold")
    cur_latest = round(intl["r_jun68"] * 0.7507 + gold["r_jun68"] * 0.2493, 2)
    cur_annual = round(intl["r2567"] * 0.7507 + gold["r2567"] * 0.2493, 2)
    vol_i = estimate_volatility(intl) * 0.7507
    vol_g = estimate_volatility(gold) * 0.2493
    cur_vol = round((vol_i**2 + vol_g**2 + 2 * (-0.05) * vol_i * vol_g) ** 0.5, 2)
    diff_latest = round(best["latest"] - cur_latest, 2)

    # Determine UI momentum action flag
    momentum = get_asset_momentum()
    intl_mom = momentum.get("equity_intl", 0)
    thai_mom = momentum.get("equity_thai", 0)
    gold_mom = momentum.get("gold", 0)
    
    action_required = False
    action_msg = ""
    # Current portfolio holds 75% intl, 25% gold. 
    # If intl momentum is negative and we recommend something else.
    if intl_mom < -1.5 and best["f1"]["id"] != "equity_intl" and best["f2"]["id"] != "equity_intl":
        action_required = True
        action_msg = "ระบบตรวจพบโมเมนตัม 'ขาลง' (Downtrend) ใน แผนหุ้นต่างประเทศ แนะนำพิจารณาสับเปลี่ยนไปยังแผนตราสารหนี้ หรือแผนที่มีความเสี่ยงต่ำกว่าเพื่อหลบภัยชั่วคราว"
    elif best["metric"] > 60 and diff_latest > 2.0:
        action_required = True
        action_msg = f"แผนแนะนำมีแนวโน้มสร้างผลตอบแทนเหนือกว่าพอร์ตปัจจุบันอย่างชัดเจน (+{diff_latest}%) หนุนโดยโมเมนตัมตลาดเชิงบวก แนะนำให้พิจารณาปรับสัดส่วน"

    return render_template_string(
        HTML,
        funds=scored,
        combos=combos,
        best=best,
        port=USER_PORTFOLIO,
        outlook=MARKET_OUTLOOK,
        now=now.strftime("%d/%m/%Y %H:%M"),
        month_th=THAI_MONTHS[now.month],
        year=now.year + 543,
        cur_latest=cur_latest,
        cur_annual=cur_annual,
        cur_vol=cur_vol,
        diff_latest=diff_latest,
        action_required=action_required,
        action_msg=action_msg
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  GPF Investment Analysis Server")
    print("  http://0.0.0.0:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)