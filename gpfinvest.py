#!/usr/bin/env python3
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

from flask import Flask, render_template_string
import datetime
import itertools
import urllib.request
import xml.etree.ElementTree as ET

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
    for f in FUNDS:
        latest = get_latest_return(f)
        annual = get_recent_annual(f)
        avg3 = f["avg_3y"] if f["avg_3y"] is not None else latest
        avg5 = f["avg_5y"] if f["avg_5y"] is not None else avg3
        si = f["since_inception"] if f["since_inception"] is not None else avg3
        mdd = abs(f["max_drawdown"])
        raw = (
            latest * 0.20 + annual * 0.20 + avg3 * 0.15 + si * 0.15
            + (8 - f["risk_level"]) * 0.5 * 0.10 - mdd * 0.05
            + (latest - avg3) * 0.15
        )
        scored.append({**f, "raw_score": raw, "latest_return": latest,
                       "annual_return": annual, "eff_avg3": avg3,
                       "eff_avg5": avg5, "eff_si": si})
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
<h4 class="stitle"><i class="bi bi-globe-americas"></i> สถานการณ์ปัจจุบันและมุมมองการลงทุน ({{ outlook.date }})</h4>
<div class="card border-0 shadow-sm rounded-4 mb-4" style="border-left:5px solid #1E88E5 !important;">
 <div class="card-body">
  <div class="row g-3 small">
   <div class="col-md-6">
    <p class="mb-2"><strong class="text-primary"><i class="bi bi-graph-up-arrow"></i> เศรษฐกิจโลก:</strong> {{ outlook.global_economy }}</p>
    <p class="mb-0"><strong class="text-danger"><i class="bi bi-geo-alt-fill"></i> เศรษฐกิจไทย:</strong> {{ outlook.thai_economy }}</p>
   </div>
   <div class="col-md-6">
    <p class="mb-2"><strong class="text-gold"><i class="bi bi-shield-fill-check"></i> มุมมองทองคำ:</strong> {{ outlook.gold_view }}</p>
    <p class="mb-0"><strong class="text-success"><i class="bi bi-bullseye"></i> กลยุทธ์แนะนำ:</strong> {{ outlook.strategy }}</p>
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
  {% if diff_latest != 0 %}
  <div class="alert {% if diff_latest > 0 %}alert-success{% else %}alert-info{% endif %} mt-3 mb-0 small">
   <i class="bi bi-{% if diff_latest > 0 %}check-circle{% else %}info-circle{% endif %}-fill"></i>
   {% if diff_latest > 0 %}
   แผนแนะนำให้ผลตอบแทนล่าสุดสูงกว่าพอร์ตปัจจุบัน <strong>+{{ diff_latest }}%</strong>
   (≈ <strong>{{ "{:,.0f}".format(port.total * diff_latest / 100) }} บาท/ปี</strong>)
   {% else %}
   พอร์ตปัจจุบันของคุณเป็นหนึ่งในคู่ที่ดีที่สุดอยู่แล้ว! แนะนำปรับสัดส่วนเล็กน้อยเพื่อเพิ่ม Sharpe Ratio
   {% endif %}
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

// Auto-load on page ready
document.addEventListener('DOMContentLoaded', function() {
    loadSetData();
    loadMoreNews();
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
                    <h6 class="mb-1 fw-bold text-white">น้อง กบข. AI</h6>
                    <small class="text-white-50" style="font-size:0.75rem;">ผู้ช่วยส่วนตัว พร้อมให้คำแนะนำ</small>
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
    input.value = '';
    setTimeout(() => {
        let reply = "ขออภัยครับ ตอนนี้ผมเป็นเพียงระบบ Demo ที่มาพร้อม UI ให้เห็นภาพรวม พร้อมรอการเชื่อมต่อกับ AI API เต็มรูปแบบ (เช่น OpenAI หรือ Gemini) ในอนาคต แต่คุณสามารถอ่านข้อมูลพื้นฐานได้จาก <b>ศูนย์จัดระดับความรู้ กบข.</b> บนหน้าเว็บเลยครับ!";
        if(msg.includes('30') || msg.includes('วัยรุ่น')) {
            reply = "สำหรับช่วงอายุ 30 ปี ซึ่งมีระยะเวลาลงทุนอีกยาวนาน (25-30 ปี) แนะนำให้เน้น <b>แผนตราสารทุนไทย/ต่างประเทศ</b> หรือ <b>แผนเชิงรุก 65</b> ครับ เพราะสามารถก้าวข้ามความผันผวนระยะสั้นเพื่อเป้าหมายผลตอบแทนที่สูงขึ้นในระยะยาวได้ครับ 📈";
        } else if(msg.includes('ผลตอบแทน') || msg.includes('สูงสุด')) {
            reply = "จากข้อมูล 3 ปีย้อนหลังล่าสุด <b>แผนหุ้นต่างประเทศ 95% + แผนหลัก 5%</b> ให้ผลตอบแทนเฉลี่ยสูงที่สุดครับ (ประมาณ 14.03% ต่อปี) แต่ก็มีความเสี่ยงจากอัตราแลกเปลี่ยนและความผันผวนของตลาดโลกด้วยนะครับ";
        }
        appendMessage(reply, 'bot');
    }, 800);
}
function appendMessage(text, sender) {
    const chatMsgs = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = "d-flex gap-2 mb-3 " + (sender==='user' ? "justify-content-end" : "");
    if(sender === 'user') {
        div.innerHTML = `<div class="bg-primary text-white p-2 px-3 rounded-3 shadow-sm align-self-end" style="max-width:85%; font-size:0.9rem;">${text}</div>`;
    } else {
        div.innerHTML = `<div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center flex-shrink-0" style="width:30px;height:30px;"><i class="bi bi-robot small"></i></div>
            <div class="bg-white p-2 px-3 rounded-3 shadow-sm text-dark align-self-start" style="max-width:85%; font-size:0.9rem;">${text}</div>`;
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
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  GPF Investment Analysis Server")
    print("  http://0.0.0.0:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)