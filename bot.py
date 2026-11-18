import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("টেলিগ্রাম টোকেন বা চ্যাট আইডি পাওয়া যায়নি!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"টেলিগ্রাম মেসেজ পাঠাতে সমস্যা: {e}")

def institutional_top_down_analysis():
    print("⏳ টপ-ডাউন মাল্টি-টাইমফ্রেম (H1 -> M15 -> M5) এনালাইসিস চলছে...")
    gold = yf.Ticker("GC=F")
    
    # মাল্টি-টাইমফ্রেম ডাটা ফেচ করা (H1, M15, M5)
    df_h1 = gold.history(period="7d", interval="1h")
    df_m15 = gold.history(period="3d", interval="15m")
    df_m5 = gold.history(period="1d", interval="5m")
    
    if df_h1.empty or df_m15.empty or df_m5.empty or len(df_m5) < 30:
        print("❌ পর্যাপ্ত লাইভ ডাটা পাওয়া যায়নি (মার্কেট বন্ধ থাকতে পারে)।")
        return

    # ১. ১ ঘণ্টা (H1) ম্যাক্রো ট্রেন্ড ইঞ্জিন
    df_h1['EMA_50'] = df_h1['Close'].ewm(span=50, adjust=False).mean()
    h1_bullish = df_h1['Close'].iloc[-1] > df_h1['EMA_50'].iloc[-1]
    h1_bearish = df_h1['Close'].iloc[-1] < df_h1['EMA_50'].iloc[-1]

    # ২. ১৫ মিনিট (M15) স্ট্রাকচার ও সাপোর্ট/রেজিস্ট্যান্স ইঞ্জিন
    df_m15['EMA_20'] = df_m15['Close'].ewm(span=20, adjust=False).mean()
    current_m15_price = df_m15['Close'].iloc[-1]
    m15_bullish = current_m15_price > df_m15['EMA_20'].iloc[-1]
    m15_bearish = current_m15_price < df_m15['EMA_20'].iloc[-1]

    # ৩. ৫ মিনিট (M5) এন্ট্রি, প্রাইস অ্যাকশন ও SMC (FVG) ইঞ্জিন
    df_m5['EMA_9'] = df_m5['Close'].ewm(span=9, adjust=False).mean()
    df_m5['EMA_21'] = df_m5['Close'].ewm(span=21, adjust=False).mean()
    
    # RSI মোমেন্টাম ক্যালকুলেশন
    delta = df_m5['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df_m5['RSI'] = 100 - (100 / (1 + rs))

    curr_price = df_m5['Close'].iloc[-1]
    m5_ema9 = df_m5['EMA_9'].iloc[-1]
    m5_ema21 = df_m5['EMA_21'].iloc[-1]
    rsi = df_m5['RSI'].iloc[-1]

    # ব্রেকআউট ও ফেয়ার ভ্যালু গ্যাপ (FVG) চেক
    recent_high = df_m5['High'].tail(10).max()
    recent_low = df_m5['Low'].tail(10).min()
    
    bullish_fvg = df_m5['Low'].iloc[-1] > df_m5['High'].iloc[-3]
    bearish_fvg = df_m5['High'].iloc[-1] < df_m5['Low'].iloc[-3]

    score = 0
    direction = None
    reasons = []

    # --- BUY (বুলিশ) কনফ্লুয়েন্স চেক ---
    if h1_bullish:
        score += 25
        reasons.append("১ ঘণ্টা (H1) ম্যাক্রো ট্রেন্ড বুলিশ")
        
    if m15_bullish:
        score += 25
        reasons.append("১৫ মিনিট (M15) স্ট্রাকচার বুলিশ কনফার্মেশন")
        
    if curr_price > m5_ema9 and m5_ema9 > m5_ema21:
        score += 20
        reasons.append("৫ মিনিট (M5) এন্ট্রি ট্রিগার (EMA 9 > 21)")
        
    if bullish_fvg or curr_price >= recent_high:
        score += 15
        reasons.append("ব্রেকআউট অথবা Bullish Fair Value Gap (FVG) কনফার্মড")
        
    if 40 <= rsi <= 65:
        score += 15
        reasons.append(f"RSI মোমেন্টাম নিরাপদ জোনে আছে ({rsi:.1f})")

    if score >= 80 and h1_bullish and m15_bullish:
        direction = "BUY"
        sl = curr_price - 3.0  # ৩ ডলার টাইট এসএল
        tp = curr_price + 6.0  # ১:২ রিওয়ার্ড রেশিও
        header = "💎 *INSTITUTIONAL SMC BUY SIGNAL (H1->M15->M5)*"
    
    # --- SELL (বেয়ারিশ) কনফ্লুয়েন্স চেক ---
    elif h1_bearish:
        score += 25
        reasons.append("১ ঘণ্টা (H1) ম্যাক্রো ট্রেন্ড বেয়ারিশ")
        
    if m15_bearish:
        score += 25
        reasons.append("১৫ মিনিট (M15) স্ট্রাকচার বেয়ারিশ কনফার্মেশন")
        
    if curr_price < m5_ema9 and m5_ema9 < m5_ema21:
        score += 20
        reasons.append("৫ মিনিট (M5) এন্ট্রি ট্রিগার (EMA 9 < 21)")
        
    if bearish_fvg or curr_price <= recent_low:
        score += 15
        reasons.append("ব্রেকডাউন অথবা Bearish Fair Value Gap (FVG) কনফার্মড")
        
    if 35 <= rsi <= 60:
        score += 15
        reasons.append(f"RSI মোমেন্টাম নিরাপদ জোনে আছে ({rsi:.1f})")

    if score >= 80 and h1_bearish and m15_bearish:
        direction = "SELL"
        sl = curr_price + 3.0  # ৩ ডলার টাইট এসএল
        tp = curr_price - 6.0  # ১:২ রিওয়ার্ড রেশিও
        header = "💎 *INSTITUTIONAL SMC SELL SIGNAL (H1->M15->M5)*"

    # শুধুমাত্র ৮০ বা তার বেশি স্কোর পেলেই টেলিগ্রাম অ্যালার্ট পাঠাবে
    if score >= 80 and direction:
        msg = f"{header}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📍 *Entry Price:* `${curr_price:.2f}`\n"
        msg += f"🛑 *Stop Loss:* `${sl:.2f}` (টাইট রিস্ক)\n"
        msg += f"🎯 *Take Profit:* `${tp:.2f}` (১:২ রিওয়ার্ড)\n"
        msg += f"🔥 *Confluence Score:* `{score}/100`\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🧠 *প্রাইস অ্যাকশন ও SMC যুক্তি:*\n"
        for r in reasons:
            msg += f"✅ {r}\n"
            
        send_telegram_message(msg)
        print("✨ ইনস্টিটিউশনাল হাই-অপরচুনিটি সিগন্যাল টেলিগ্রামে পাঠানো হয়েছে!")
    else:
        print(f"ℹ️ বর্তমান স্কোর: {score}/100 — মাল্টি-টাইমফ্রেম কনফ্লুয়েন্স পারফেক্ট নয়, অপেক্ষা করা হচ্ছে...")

if __name__ == "__main__":
    institutional_top_down_analysis()
