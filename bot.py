import os
import telebot
from telebot import types
import yfinance as yf
import pandas as pd
import numpy as np

# টেলিগ্রাম টোকেন ও চ্যাট আইডি রিড করা
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def generate_institutional_analysis():
    gold = yf.Ticker("GC=F")
    
    # মাল্টি-টাইমফ্রেম ডাটা ফেচ করা (H1, M15, M5)
    df_h1 = gold.history(period="7d", interval="1h")
    df_m15 = gold.history(period="3d", interval="15m")
    df_m5 = gold.history(period="1d", interval="5m")
    
    if df_h1.empty or df_m15.empty or df_m5.empty or len(df_m5) < 30:
        return "❌ লাইভ মার্কেট ডাটা পাওয়া যায়নি। বাজার বন্ধ থাকতে পারে।"

    # ১. ১ ঘণ্টা (H1) ম্যাক্রো ট্রেন্ড ইঞ্জিন
    df_h1['EMA_50'] = df_h1['Close'].ewm(span=50, adjust=False).mean()
    h1_bullish = df_h1['Close'].iloc[-1] > df_h1['EMA_50'].iloc[-1]
    h1_bearish = df_h1['Close'].iloc[-1] < df_h1['EMA_50'].iloc[-1]

    # ২. ১৫ মিনিট (M15) স্ট্রাকচার ইঞ্জিন
    df_m15['EMA_20'] = df_m15['Close'].ewm(span=20, adjust=False).mean()
    current_m15_price = df_m15['Close'].iloc[-1]
    m15_bullish = current_m15_price > df_m15['EMA_20'].iloc[-1]
    m15_bearish = current_m15_price < df_m15['EMA_20'].iloc[-1]

    # ৩. ৫ মিনিট (M5) এন্ট্রি, প্রাইস অ্যাকশন ও SMC (FVG) ইঞ্জিন
    df_m5['EMA_9'] = df_m5['Close'].ewm(span=9, adjust=False).mean()
    df_m5['EMA_21'] = df_m5['Close'].ewm(span=21, adjust=False).mean()
    
    delta = df_m5['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df_m5['RSI'] = 100 - (100 / (1 + rs))

    curr_price = df_m5['Close'].iloc[-1]
    m5_ema9 = df_m5['EMA_9'].iloc[-1]
    m5_ema21 = df_m5['EMA_21'].iloc[-1]
    rsi = df_m5['RSI'].iloc[-1]

    bullish_fvg = df_m5['Low'].iloc[-1] > df_m5['High'].iloc[-3]
    bearish_fvg = df_m5['High'].iloc[-1] < df_m5['Low'].iloc[-3]

    score = 0
    direction = "WAIT"
    reasons = []

    # বুলিশ লজিক
    if h1_bullish: score += 25; reasons.append("H1 ম্যাক্রো ট্রেন্ড বুলিশ")
    if m15_bullish: score += 25; reasons.append("M15 স্ট্রাকচার বুলিশ")
    if curr_price > m5_ema9 and m5_ema9 > m5_ema21: score += 20; reasons.append("M5 এন্ট্রি ট্রিগার (EMA 9 > 21)")
    if bullish_fvg: score += 15; reasons.append("Bullish Fair Value Gap (FVG) কনফার্মড")
    if 40 <= rsi <= 65: score += 15; reasons.append(f"RSI নিরাপদ জোনে আছে ({rsi:.1f})")

    if score >= 75 and h1_bullish and m15_bullish:
        direction = "BUY"
    
    # বেয়ারিশ লজিক
    elif h1_bearish or m15_bearish:
        bear_score = 0
        bear_reasons = []
        if h1_bearish: bear_score += 25; bear_reasons.append("H1 ম্যাক্রো ট্রেন্ড বেয়ারিশ")
        if m15_bearish: bear_score += 25; bear_reasons.append("M15 স্ট্রাকচার বেয়ারিশ")
        if curr_price < m5_ema9 and m5_ema9 < m5_ema21: bear_score += 20; bear_reasons.append("M5 এন্ট্রি ট্রিগার (EMA 9 < 21)")
        if bearish_fvg: bear_score += 15; bear_reasons.append("Bearish Fair Value Gap (FVG) কনফার্মড")
        if 35 <= rsi <= 60: bear_score += 15; bear_reasons.append(f"RSI নিরাপদ জোনে আছে ({rsi:.1f})")
        
        if bear_score >= 75:
            score = bear_score
            direction = "SELL"
            reasons = bear_reasons

    # ড্যাশবোর্ড রিপোর্ট তৈরি
    report = f"📊 *GOLD SMC & PRICE ACTION DASHBOARD*\n"
    report += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += f"🔹 Current Price: `${curr_price:.2f}`\n"
    report += f"🔥 Confluence Score: `{score}/100`\n"
    report += f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    if direction == "BUY":
        sl = curr_price - 3.0
        tp = curr_price + 6.0
        report += f"🟢 *SIGNAL: HIGH PROBABILITY BUY*\n"
        report += f"📍 Entry: `${curr_price:.2f}`\n"
        report += f"🛑 Stop Loss: `${sl:.2f}`\n"
        report += f"🎯 Take Profit: `${tp:.2f}`\n\n"
    elif direction == "SELL":
        sl = curr_price + 3.0
        tp = curr_price - 6.0
        report += f"🔴 *SIGNAL: HIGH PROBABILITY SELL*\n"
        report += f"📍 Entry: `${curr_price:.2f}`\n"
        report += f"🛑 Stop Loss: `${sl:.2f}`\n"
        report += f"🎯 Take Profit: `${tp:.2f}`\n\n"
    else:
        report += f"🟡 *SIGNAL: NO TRADE / WAIT*\n"
        report += f"বাজার বর্তমানে সাইডওয়েজ বা অনিশ্চিত অবস্থায় আছে। জোর করে ট্রেড নেওয়া বোকামি।\n\n"

    report += f"🧠 *লজিক ও কারণসমূহ:*\n"
    for r in reasons:
        report += f"• {r}\n"
        
    return report

# টেলিগ্রামে /start কমান্ড হ্যান্ডলার
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📊 লাইভ ড্যাশবোর্ড ও সিগন্যাল দেখুন", callback_data="get_dashboard")
    markup.add(btn)
    bot.send_message(message.chat.id, "স্বাগতম! এটি আপনার ফরেক্স গোল্ড ইনস্টিটিউশনাল ড্যাশবোর্ড বট। নিচের বোতামে চাপ দিয়ে যেকোনো সময় লাইভ এনালাইসিস দেখুন:", reply_markup=markup)

# বোতামে চাপ দিলে কাজ করার হ্যান্ডলার
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "get_dashboard":
        bot.answer_callback_query(call.id, "বাজার বিশ্লেষণ করা হচ্ছে...")
        dashboard_text = generate_institutional_analysis()
        
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("🔄 ড্যাশবোর্ড রিফ্রেশ করুন", callback_data="get_dashboard")
        markup.add(btn)
        
        bot.edit_message_text(chat_id=call.message.chat.id, 
                              message_id=call.message.message_id, 
                              text=dashboard_text, 
                              parse_mode="Markdown", 
                              reply_markup=markup)

if __name__ == "__main__":
    print("বট লাইভ পল্লিং শুরু হয়েছে...")
    bot.infinity_polling()
