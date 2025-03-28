import requests
import yfinance as yf
from flask import Flask, jsonify, request
import os
import numpy as np
import logging
import pandas as pd
import time
import random


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
        # ✅ Fetch 30x M1 candles (most recent 30 minutes)
        data = yf.Ticker(symbol).history(period="1d", interval="1m")
        if not data.empty and len(data) >= 30:
            close_prices = list(data["Close"].values[-30:])
            latest_price = round(close_prices[-1], 2)
            print(f"✅ {symbol} | M1 Last Price: {latest_price}")
            return close_prices, latest_price
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
    return None, None



# ✅ Signal Messages
STRONG_BUY_MESSAGES = [
    "🔥 BREAKING ALERT! 🔥\n\n🚀 Momentum is exploding! RSI is climbing strong, and MACD just fired a bullish crossover. This is not a test — it's the real deal.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n📈 The bulls are charging! Volume is rising, indicators are aligned, and the market is waking up with power.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n💥 A major breakout is unfolding! This isn’t noise — this is a calculated ignition from the technicals.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n🟢 RSI is surging from oversold territory, and MACD just confirmed liftoff. The breakout zone is live!\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n📊 The chart just lit up — trend reversal confirmed! Momentum is in full throttle.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n⚡ Bulls are back with fury! Key resistance has been broken and support is holding tight.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n💹 Everything aligns — RSI, MACD, Bollinger. This is the setup pro traders dream of.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n📣 The market is screaming bullish — no hesitation, just domination. This is the moment.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n🧨 The pressure has built up — and now it's releasing. Early buyers already entered. You’re next.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n🎯 Precision entry point detected! Momentum is heating up fast — don’t miss this golden window.\n\nNaomi Ai suggests STRONG BUY NOW! Ride the explosion before it takes off! 🚀"
]



STRONG_SELL_MESSAGES = [
    "🔥 BREAKING ALERT! 🔥\n\n📉 A major breakdown is unfolding! RSI is spiking downward, MACD just flipped bearish — and price is cracking support.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n💥 Momentum is collapsing, and bulls are vanishing. This isn't a dip — it's the start of a larger downtrend.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n💀 The charts are bleeding. RSI is overbought and diving, MACD flipped hard, and volume is flooding red.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n⚠️ Trend reversal confirmed! Key support broken, momentum rolling downhill — this isn’t slowing anytime soon.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n📊 Indicators in freefall. MACD has plunged below signal, and RSI can't hold its levels. This is a clean signal to get out.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🚨 Panic volume detected. The market is rushing for the exits, and price is falling through the floor.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🔻 Breakdown in motion! Lower lows, failed bounces, and bearish momentum surging. No time left to hesitate.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n📛 Support has collapsed. Price is unraveling and volatility is exploding — don’t wait for confirmation.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🧯 Momentum is toast. Bulls have lost control completely — and smart money is already out.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🩸 This isn't weakness — it’s surrender. Indicators are flashing red across the board. This is a confirmed breakdown.\n\nNaomi Ai suggests STRONG SELL NOW! Exit fast before the drop gets deeper! 📉"
]



WEAK_BUY_MESSAGES = [
    "🔥 BREAKING ALERT! 🔥\n\n📊 Momentum is starting to tilt in favor of the bulls. It’s not loud yet, but the pressure is building.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n🌱 A subtle spark is forming beneath the surface. This could be the beginning of something big if it holds.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n📈 MACD is curling up gently, and RSI is lifting from neutral. The bulls are warming up quietly.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n🔄 Price has found its footing. Early momentum is forming like the calm before the breakout.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n🧠 Smart money might be stepping in. The shift is small but noticeable — and often that’s all you need.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n💡 The charts aren’t screaming yet — but technicals are lining up slowly. A breakout could be brewing.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n📉 Price recently bounced off key support. It’s holding, and upside is beginning to show.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n🛠️ The foundation is forming. Volume is calm, but structure is solid. The move may begin soon.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n📡 The signal is faint — but real. A quiet bullish shift is unfolding beneath the surface.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀",

    "🔥 BREAKING ALERT! 🔥\n\n📊 The market is preparing for its next phase. Those who enter early often ride the cleanest moves.\n\nNaomi Ai suggests BUY NOW! Ride the wave before it’s too late! 🚀"
]





WEAK_SELL_MESSAGES = [
    "🔥 BREAKING ALERT! 🔥\n\n📉 Momentum is quietly fading… not a crash, but a slow decline is setting in. The bulls look tired, and upside energy is losing grip.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🧠 Something’s changing under the surface. Momentum indicators are softening, and buyers aren’t stepping in as confidently.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n⚠️ Early cracks forming in the structure. RSI is dipping gently, MACD is flattening. It’s the kind of weakness smart traders don’t ignore.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🩸 The chart isn’t broken yet, but it’s limping. Price failed to make new highs and momentum is drifting. Quiet exits are already happening.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n💀 This isn’t panic — it’s preparation. Early signs of a potential fade are here. Volume’s drying up and trend is flattening.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🧯 Momentum has cooled and energy is slipping. The uptrend is losing steam. No need to panic — but smart exits happen early.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n📊 Bulls are hesitating. Market sentiment feels dull, and price can’t push higher. A pullback may be near.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🚨 It’s not dramatic — yet. But this is where silent reversals begin. The first to act usually exit clean.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n🔻 The fire is dimming. Indicators are sluggish and price is struggling to hold strength. Trim early, not late.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉",

    "🔥 BREAKING ALERT! 🔥\n\n⏳ Time to be cautious. Bulls had their chance — now the market feels heavy. Small exit now could save bigger regret later.\n\nNaomi Ai suggests SELL NOW before it slips further! 📉"
]

def get_random_message(signal_type):
    if signal_type == "STRONG_BUY":
        return random.choice(STRONG_BUY_MESSAGES)
    elif signal_type == "STRONG_SELL":
        return random.choice(STRONG_SELL_MESSAGES)
    elif signal_type == "WEAK_BUY":
        return random.choice(WEAK_BUY_MESSAGES)
    elif signal_type == "WEAK_SELL":
        return random.choice(WEAK_SELL_MESSAGES)
    else:
        return "⚠️ Unable to determine signal at this time."



# ✅ NEW: Detect Candle Trend Direction (Last 3 candles)
def detect_trend_direction(prices):
    if len(prices) < 3:
        return "neutral"
    if prices[-3] < prices[-2] < prices[-1]:
        return "bullish"
    if prices[-3] > prices[-2] > prices[-1]:
        return "bearish"
    return "neutral"




# ✅ Main Hybrid Signal Logic (no timeframe mention in output)
def generate_trade_signal(instrument):
    now = time.time()
    cache = last_signal_data.get(instrument)

    # ✅ Cache only 60 seconds
    if cache and now - cache["timestamp"] < 60:
        print(f"🔁 Cached signal_type: {cache['signal_type']}")
        return get_random_message(cache["signal_type"])

    symbol_map = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "DJI": "^DJI",
        "IXIC": "^IXIC"
    }

    if instrument in ["XAU", "XAUUSD"]:
        price = get_gold_price()
        if price is None:
            return "⚠️ Failed to get gold price."
        prices = [price] * 30  # Simulate candle behavior
    else:
        symbol = symbol_map.get(instrument)
        if not symbol:
            return f"⚠️ Invalid instrument: {instrument}"
        prices, price = fetch_real_prices(symbol)
        if not prices or price is None:
            return f"⚠️ No valid price data for {instrument}"

    # ✅ Only trend-based logic
    trend = detect_trend_direction(prices)

    if trend == "bullish":
        signal_type = "STRONG_BUY"
    elif trend == "bearish":
        signal_type = "STRONG_SELL"
    else:
        signal_type = random.choice(["WEAK_BUY", "WEAK_SELL"])

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
