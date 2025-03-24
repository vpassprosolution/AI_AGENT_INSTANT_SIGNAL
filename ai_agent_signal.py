import requests
import yfinance as yf
from flask import Flask, jsonify, request
import os
import numpy as np
import logging
import pandas as pd
import time
import random

# Try importing 'ta'
try:
    import ta
except ModuleNotFoundError:
    raise ModuleNotFoundError("The 'ta' library is not installed. Please run 'pip install ta'")

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# 5-minute signal lock structure
last_signal_data = {}

@app.before_request
def log_request_info():
    logging.debug(f"📥 Incoming request: {request.method} {request.url}")
    print(f"📥 Incoming request: {request.method} {request.url}")

@app.route('/')
def home():
    return jsonify({"message": "AI Agent Instant Signal API is running!"})

# ✅ FETCHING PRICE FUNCTIONS
def get_crypto_price(symbol):
    symbol_map = {"BTC": "BTC-USD", "ETH": "ETH-USD"}
    yahoo_symbol = symbol_map.get(symbol, None)

    if yahoo_symbol:
        data = yf.Ticker(yahoo_symbol).history(period="1d")
        if not data.empty:
            price = round(data["Close"].iloc[-1], 2)
            print(f"✅ Fetched {symbol} price: {price}")  # ✅ Debugging Log
            return price

    print(f"❌ No price found for {symbol} using Yahoo Finance")
    return None

def get_forex_price(pair):
    symbol = f"{pair[:3]}{pair[3:]}=X"
    data = yf.Ticker(symbol).history(period="1d")
    
    if not data.empty:
        price = round(data["Close"].iloc[-1], 4)
        print(f"✅ Fetched {pair} price: {price}")  # ✅ Debugging Log
        return price
    return None

def get_stock_index_price(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="1d")
    
    if not data.empty:
        price = round(data["Close"].iloc[-1], 2)
        print(f"✅ Fetched {symbol} price: {price}")  # ✅ Debugging Log
        return price
    return None

def get_gold_price():
    url = "https://metals-api.com/api/latest?access_key=cflqymfx6mzfe1pw3p4zgy13w9gj12z4aavokqd5xw4p8xeplzlwyh64fvrv&base=USD&symbols=XAU"

    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print(f"❌ Error fetching Gold price: {e}")
        return None

    print("🔍 FULL METAL API RESPONSE:", data)  # ✅ Print full API response in CMD

    if "rates" in data and "USDXAU" in data["rates"]:
        price = round(data["rates"]["USDXAU"], 2)
        print(f"✅ GOLD PRICE FROM API: {price}")  # ✅ Print fetched price
        return price

    print("⚠️ No Gold price found in API response!")
    return None

def fetch_real_prices(symbol):
    try:
        data = yf.Ticker(symbol).history(period="2d", interval="5m")
        if not data.empty and len(data) >= 30:
            close_prices = list(data["Close"].values[-30:])
            latest_price = round(close_prices[-1], 2)
            return close_prices, latest_price
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
    return None, None

# ✅ Indicator Calculations
def calculate_rsi(prices):
    df = pd.DataFrame(prices, columns=["price"])
    return ta.momentum.RSIIndicator(df["price"], window=14).rsi().iloc[-1]

def calculate_macd(prices):
    df = pd.DataFrame(prices, columns=["price"])
    macd_obj = ta.trend.MACD(df["price"])
    macd = macd_obj.macd().iloc[-1]
    signal = macd_obj.macd_signal().iloc[-1]
    return macd, signal

def calculate_bollinger(prices):
    df = pd.DataFrame(prices, columns=["price"])
    bb = ta.volatility.BollingerBands(df["price"])
    upper = bb.bollinger_hband().iloc[-1]
    middle = bb.bollinger_mavg().iloc[-1]
    lower = bb.bollinger_lband().iloc[-1]
    return upper, middle, lower

# ✅ Signal Messages
STRONG_BUY_MESSAGES = [
    "🚀 This is it. RSI is buried, MACD just lit a fire, and price is loading up like a rocket about to launch. Every technical light is green. The window won’t stay open long — **BUY NOW** and ride this breakout with conviction! 💥📈",

    "🔥 Bulls are in full control. This is not a test. This is what traders wait weeks for — momentum, structure, and sentiment all aligned. You miss this, you’ll chase it later. **BUY NOW** while it’s fresh and flying. 🚀",

    "💣 The setup is undeniable. Volume’s rising, indicators are screaming bullish, and the move is brewing beneath the surface. You either react now or regret it later. No hesitation. **BUY NOW** and own the edge. 🧨",

    "📈 You’re watching a textbook bullish explosion in progress. The kind of move that starts slow and then leaves everyone behind. This is the type of signal that doesn’t come often. **BUY NOW**, or watch it run without you. ⏱️",

    "🟢 This is no ordinary bounce — this is a power shift. Bulls have taken the reins, and they’re not letting go. The breakout energy is real. Stop overthinking. **BUY NOW** before the stampede begins. 🐂🔥",

    "💥 Trend reversal confirmed. This isn’t guesswork. Momentum is aligned, structure is clean, and confidence is building. Traders are entering heavily. Don’t be last. **BUY NOW**, or stay sidelined. Your call. 📊",

    "🚨 Breakout confirmation. RSI is reversing from oversold, MACD crossover is clean, and price just reclaimed key levels. The storm is here — but this time, you’re the lightning. **BUY NOW** with power. ⚡",

    "🔥 Every signal that matters is flashing bullish. Momentum? ✅ Volume? ✅ Price structure? ✅ This is not the time to hesitate. The market is giving you a gift. **BUY NOW**, and hold on tight. 🎯",

    "📊 It’s one of those rare moments where everything lines up. Charts don’t lie — and they’re saying one thing loud and clear: **BUY NOW**. This is your shot to catch the move before the masses see it. 🧠",

    "🚀 Entry point of the week just showed up. The kind that sets the tone for the whole session. Early buyers are loading. Smart traders are ready. This is your chance to be first. **BUY NOW**, and don’t look back. 🏁"
]


STRONG_SELL_MESSAGES = [
    "💣 This isn’t a dip — it’s the start of a full-blown meltdown. Indicators are collapsing, buyers are vanishing, and momentum is falling off a cliff. Protect what’s yours. **SELL NOW** before the floor drops out. 📉",

    "🚨 It’s all breaking down. RSI is screaming overbought, MACD flipped hard, and price just cracked support. There’s no time to debate. **SELL NOW**, or get caught in the collapse. 🛑",

    "⚠️ The market just hit a turning point — and not the good kind. Distribution is obvious, and the bulls are trapped. Exit before they drag you down. This is serious. **SELL NOW**, aggressively. 💥",

    "💀 This chart looks like a disaster in progress. Uptrend is gone, momentum is dead, and fear is starting to spread. Traders are bailing. You should too. **SELL NOW**, and live to trade another day. 🩸",

    "📉 This is your final warning. Overbought reversal confirmed. Volume is fading, and weakness is taking over fast. Waiting any longer? That’s called gambling. **SELL NOW**, while you still have control. ⏳",

    "🔥 Everything is flashing red. You’re not being paranoid — you’re being smart. Bulls are losing control, and this thing is tipping hard. There’s one move left: **SELL NOW**, fast and clean. 🧯",

    "🔻 Breakdown in progress. MACD flipped, RSI is tanking, and support zones are shattered. Hope is not a strategy. Lock your gains. Cut your losses. **SELL NOW**, before it’s too late. 📊",

    "🚫 The rally is fake. The drop is real. Buyers are exhausted, and price action is telling the truth. Exit now or watch it all bleed out. **SELL NOW**, no hesitation. 💣",

    "📛 This setup is beyond dangerous. It’s not just fading — it’s crashing. Volume spike on the downside, MACD diving, RSI screaming exit. Be smart. Be fast. **SELL NOW**, and don’t look back. 💔",

    "🧠 If you’ve been waiting for a sign, this is it. Market is cracking, technicals are cooked, and sentiment is turning cold. This isn’t time to analyze — it’s time to act. **SELL NOW**, aggressively. 🔥"
]


WEAK_BUY_MESSAGES = [
    "📊 The chart is whispering opportunity. Early momentum is taking shape, and the bulls are stretching. It's not explosive — yet. But for those watching closely, this is the kind of moment where calculated risk becomes reward. *BUY NOW*, slowly and smartly.",
    
    "🧠 Smart money isn’t waiting for fireworks. They’re stepping in quietly, before the crowd catches on. This isn’t hype — it’s precision. A subtle shift is underway. If you know, you know. *BUY NOW* with calm confidence.",
    
    "🌱 Every rally starts somewhere… and this could be the seed. It’s quiet, but the ground is shifting. No one’s yelling yet — which is exactly why it matters. Slowly scale in. *BUY NOW* before it gets noticed.",
    
    "🟢 The signs aren’t loud — but they’re there. Support is holding, pressure is building. Traders with patience are already making their move. Want in early? This is the zone. *BUY NOW*... don’t chase later.",
    
    "💡 Opportunity rarely announces itself. But when you know how to read the market, you feel the buildup. It’s subtle, but undeniable. Slow and steady is the game here. *BUY NOW*, before the wave builds.",
    
    "🔄 Market rotation is starting to show. Price is stabilizing, and the path upward is quietly forming. No rush. No panic. Just calculated positioning. This is where legends scale in. *BUY NOW*, gradually.",
    
    "🧪 It’s not a breakout. Not yet. But it’s the kind of setup that turns into one. If you’re waiting for perfection, you’ll miss the real edge. The pros are already easing in. *BUY NOW*, with strategy.",
    
    "📈 The upside is whispering — not shouting. And that’s when the best entries happen. Get in early, get in light, and ride the momentum before it becomes obvious. *BUY NOW* while it’s still calm.",
    
    "🧠 This is how early trades feel — uncertain, but full of potential. A perfect storm is slowly brewing. You don’t need to go all in. But if you wait too long… you’ll be chasing. *BUY NOW*, one step at a time.",
    
    "🚀 The energy is building under the surface. Price structure is holding firm, buyers are testing the waters. It’s early, yes. But real traders know — this is when the best plays are made. *BUY NOW*, quietly and confidently."
]



WEAK_SELL_MESSAGES = [
    "📉 Momentum is quietly slipping. No panic yet — but the strength is fading fast. It’s not a full collapse, but smart traders are trimming. **SELL NOW**, lightly but deliberately.",

    "🧠 It’s not chaos — it’s calculated deterioration. RSI is weakening, and buyers are getting tired. If you’ve been holding, now’s the time to reduce risk. **SELL NOW**, with control.",

    "⚠️ Signs of exhaustion are everywhere. Price action looks soft, and momentum is barely breathing. You don’t need to run — but don’t stand still either. **SELL NOW**, step by step.",

    "🩸 The uptrend is wounded. It’s limping, not dead — but weakness is creeping in. Don’t wait for confirmation of a crash. Scale out slowly. **SELL NOW**, while the door’s still open.",

    "💀 It's not dramatic... yet. But the cracks are forming. A stealthy reversal is brewing, and smart money is already adjusting. Play it like a pro. **SELL NOW**, no emotion.",

    "🧯 The fire’s going out. Momentum cooled, volume dropped, and upside looks tired. Time to secure gains or minimize exposure. **SELL NOW**, tactically.",

    "📊 The chart still looks okay — but you know better. The vibe has shifted. Support is being tested and momentum is fading. Don’t wait for it to break. **SELL NOW**, cautiously.",

    "🚨 Market’s not crashing — but it’s not climbing either. You’re entering a zone of slow bleed. Stay ahead of it. **SELL NOW**, gently but with purpose.",

    "🔻 Subtle weakness often turns into sharp drops. Don’t get caught sleeping. This is your heads-up. **SELL NOW**, wisely.",

    "⏳ Time’s ticking, and the edge is disappearing. The longer you hold, the thinner your profits get. Be proactive. **SELL NOW**, before it’s obvious to everyone else."
]


# ✅ Detect signal type (used in cache)
def detect_signal_type(rsi, macd, signal_line, price, upper, lower):
    strong_momentum = (macd > signal_line and rsi > 55) or (macd < signal_line and rsi < 45)
    weak_momentum = 45 <= rsi <= 55

    if rsi < 30 and macd > signal_line and strong_momentum:
        return "STRONG_BUY"
    if rsi > 70 and macd < signal_line and strong_momentum:
        return "STRONG_SELL"
    if macd > signal_line and price < upper:
        return "WEAK_BUY"
    if macd < signal_line and price > lower:
        return "WEAK_SELL"
    return "WEAK_BUY" if rsi >= 50 else "WEAK_SELL"

# ✅ Get message by signal type
def get_random_message(signal_type):
    if signal_type == "STRONG_BUY":
        return random.choice(STRONG_BUY_MESSAGES)
    elif signal_type == "STRONG_SELL":
        return random.choice(STRONG_SELL_MESSAGES)
    elif signal_type == "WEAK_SELL":
        return random.choice(WEAK_SELL_MESSAGES)
    return random.choice(WEAK_BUY_MESSAGES)

# ✅ Main Hybrid Signal Logic
def generate_trade_signal(instrument):
    now = time.time()
    cache = last_signal_data.get(instrument)

    # ✅ Return cached signal type within 5 minutes
    if cache and now - cache["timestamp"] < 300:
        print(f"🔁 Cached signal_type: {cache['signal_type']}")
        return get_random_message(cache["signal_type"])

    # ✅ Instrument symbol map
    symbol_map = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "DJI": "^DJI",
        "IXIC": "^IXIC"
    }

    # ✅ Gold (XAU) via Metals API
    if instrument in ["XAU", "XAUUSD"]:
        price = get_gold_price()
        if price is None:
            return "⚠️ Failed to get gold price."
        prices = [price] * 30
    else:
        symbol = symbol_map.get(instrument)
        if not symbol:
            return f"⚠️ Invalid instrument: {instrument}"
        prices, price = fetch_real_prices(symbol)
        if not prices or price is None:
            return f"⚠️ No valid price data for {instrument}"

    # ✅ Indicators
    rsi = calculate_rsi(prices)
    macd, signal_line = calculate_macd(prices)
    upper, middle, lower = calculate_bollinger(prices)

    # ✅ Signal logic
    signal_type = detect_signal_type(rsi, macd, signal_line, price, upper, lower)
    last_signal_data[instrument] = {
        "timestamp": now,
        "price": price,
        "signal_type": signal_type
    }
    return get_random_message(signal_type)

# ✅ Flask API
@app.route('/get_signal/<string:selected_instrument>', methods=['GET'])
def get_signal(selected_instrument):
    try:
        print(f"🟢 API Request Received for: {selected_instrument}")
        signal = generate_trade_signal(selected_instrument)
        print(f"✅ FINAL SIGNAL: {signal}")
        return jsonify({"instrument": selected_instrument, "signal": signal})
    except Exception as e:
        print(f"❌ Error Processing {selected_instrument}: {e}")
        return jsonify({"error": str(e)}), 500

# ✅ Start Flask App
if __name__ == '__main__':
    print("🚀 Flask Server Starting on Port 5000...")
    app.run(debug=True, host='0.0.0.0', port=5000)
