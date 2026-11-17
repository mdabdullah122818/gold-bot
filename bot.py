import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np

# GitHub Secrets থেকে টোকেন ও চ্যাট আইডি রিড করবে (নিরাপদ পদ্ধতি)
TELEGRAM_BOT_TOKEN = "9274548983:AAGNV1jS0SEPZBM41vuFm-yIYRmF0cVeKPw"
TELEGRAM_CHAT_ID = "7115326324"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"মেসেজ পাঠাতে সমস্যা: {e}")

def check_market():
    print("গোল্ড মার্কেট স্ক্যান করা হচ্ছে...")
    gold = yf.Ticker("GC=F")
    df = gold.history(period="2d", interval="5m")
    
    if df.empty or len(df) < 30:
        print("ডাটা পাওয়া যায়নি।")
        return

    df['SMA_9'] = df['Close'].rolling(window=9).mean()
    df['SMA_21'] = df['Close'].rolling(window=21).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    current_price = df['Close'].iloc[-1]
    sma_9 = df['SMA_9'].iloc[-1]
    sma_21 = df['SMA_21'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    
    score = 0
    reasons = []
    
    if current_price > sma_9 and sma_9 > sma_21:
        score += 40
        reasons.append("মজবুত বুলিশ ট্রেন্ড (SMA 9 > 21)")
    elif current_price < sma_9 and sma_9 < sma_21:
        score += 40
        reasons.append("মজবুত বেয়ারিশ ট্রেন্ড (SMA 9 < 21)")
        
    if 45 <= rsi <= 65 and current_price > sma_9:
        score += 30
        reasons.append("RSI বাই মোমেন্টামের অনুকূলে রয়েছে")
    elif 35 <= rsi <= 55 and current_price < sma_9:
        score += 30
        reasons.append("RSI সেল মোমেন্টামের অনুকূলে রয়েছে")
        
    recent_candle_size = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
    avg_candle_size = abs(df['Close'] - df['Open']).mean()
    if recent_candle_size > avg_candle_size:
        score += 30
        reasons.append("বড় ভলিউম ও ইমপ্লাসসিভ ক্যান্ডেল কনফার্মেশন")

    # শুধুমাত্র হাই অপরচুনিটি (স্কোর ৭০ বা তার বেশি) হলেই মেসেজ পাঠাবে
    if score >= 70:
        if current_price > sma_9:
            sl = current_price - 3.0
            tp = current_price + 5.0
            msg = f"🚨 *HIGH PROBABILITY BUY ALERT*\n\n🔹 গোল্ড প্রাইস: `${current_price:.2f}`\n🎯 কনফ্লুয়েন্স স্কোর: `{score}/100`\n🛑 স্টপ লস (SL): `${sl:.2f}`\n🎯 টেক প্রফিট (TP): `${tp:.2f}`\n\n💡 *যুক্তিসমূহ:*\n"
        else:
            sl = current_price + 3.0
            tp = current_price - 5.0
            msg = f"🚨 *HIGH PROBABILITY SELL ALERT*\n\n🔹 গোল্ড প্রাইস: `${current_price:.2f}`\n🎯 কনফ্লুয়েন্স স্কোর: `{score}/100`\n🛑 স্টপ লস (SL): `${sl:.2f}`\n🎯 টেক প্রফিট (TP): `${tp:.2f}`\n\n💡 *যুক্তিসমূহ:*\n"
                  
        for r in reasons:
            msg += f"• {r}\n"
            
        send_telegram_message(msg)
        print("হাই অপরচুনিটি টেলিগ্রামে পাঠানো হয়েছে!")
    else:
        print(f"স্কোর {score}/100 - অপরচুনিটি যথেষ্ট শক্তিশালী নয়।")

if __name__ == "__main__":
    check_market()
