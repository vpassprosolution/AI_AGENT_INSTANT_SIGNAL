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
    "🚨 ALERT! The market is showing explosive bullish momentum! BUY NOW! 💥💰",
    "🔥 Bulls have taken over! BUY NOW and dominate the move! 🟢📈",
    "📈 Unstoppable surge detected. BUY before it rockets! 💸🚀",
    "💣 Major reversal confirmed! BUY zones are live! 🔥",
    "💥 MACD + RSI = 🔥 BUY NOW before it flies!",
    "🧨 Bullish storm forming! BUY before breakout! 💵",
    "🟢 Market glowing green – BUY with confidence!",
    "📊 Technicals are aligned – BUY NOW and ride the wave!",
    "🚀 RSI reversal and MACD ignition! BUY THE BOOM!",
    "🔥 BUY SIGNAL CONFIRMED! Strike now! 💥"
]

STRONG_SELL_MESSAGES = [
    "🚨 SELL IMMEDIATELY! This market is turning! 📉💥",
    "⚠️ Top reached. SELL now before the drop hits!",
    "🔻 Overbought + MACD reversal = SELL IT ALL!",
    "💀 Charts scream SELL – protect your capital!",
    "🔥 SELL ZONE confirmed. Exit now or regret it.",
    "📉 Trend is dying. SELL BEFORE THE FALL!",
    "🩸 Big players exiting. SELL with them!",
    "🚫 Momentum dead. SELL while you can!",
    "🔺 Fake pump fading – SELL and secure profit!",
    "💣 Time to lock gains. SELL FAST!"
]

WEAK_BUY_MESSAGES = [
    "🟢 The bulls are waking up… This could be your early window. A subtle but solid **BUY** zone is emerging.",
    "📊 The market whispers... Not loud, but it leans **bullish**. A small **BUY** now might place you ahead of the crowd.",
    "⚠️ Conditions aren't perfect — but sometimes smart traders act before perfection. Think about a light **BUY**.",
    "🧠 The early signs of momentum are forming. A tactical **BUY** now could set you up for the next wave.",
    "🔄 It’s bending... not yet breaking out. A cautious **BUY** here could be the move others miss.",
    "💡 The bulls are poking the chart. No fireworks yet, but you don’t want to chase later. Strategic **BUY** zone.",
    "🟢 Calm before the surge? Some strength showing. It may not scream, but it points to a calculated **BUY**.",
    "📈 You're seeing what others will notice later. Quiet strength = early edge. A smart **BUY** now isn't crazy.",
    "🌱 This is how trends are born. You either wait… or you plant your flag. Early **BUY** opportunity.",
    "🧪 It's experimental — but the risk looks manageable. For those who know how to play it: **BUY** with intent."
]


WEAK_SELL_MESSAGES = [
    "🔻 SELL with caution – weakness appearing.",
    "📉 Momentum fading. Lighten your bag.",
    "⚠️ Sideways slide – SELL smart.",
    "🧠 Smart exit point forming. SELL partially.",
    "💀 Indicators dropping – SELL light.",
    "📊 Soft downtrend detected. Take profit.",
    "🩸 Losing strength. SELL if you're in.",
    "⚠️ Not crashing, but SELL safe.",
    "🔻 Cracks appearing – SELL small before break.",
    "🧯 Fire’s cooling off – SELL and wait."
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
