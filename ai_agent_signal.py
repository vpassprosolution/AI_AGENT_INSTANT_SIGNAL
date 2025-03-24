import requests
import yfinance as yf
from flask import Flask, jsonify, request
import os
import numpy as np
import logging
import pandas as pd
import time
import random

# Try importing 'ta' and provide a user-friendly message if not installed
try:
    import ta
except ModuleNotFoundError:
    raise ModuleNotFoundError("The 'ta' library is not installed. Please run 'pip install ta' to fix this error.")

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

last_signal_data = {}  # Store last signal per instrument for 15-min lock

@app.before_request
def log_request_info():
    logging.debug(f"📥 Incoming request: {request.method} {request.url}")
    print(f"📥 Incoming request: {request.method} {request.url}")

@app.route('/')
def home():
    return jsonify({"message": "AI Agent Instant Signal API is running!"})

# Price Source Mapping
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

# Indicator Calculations
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

# Signal Messages
STRONG_BUY_MESSAGES = [
    "🚨 ALERT! The market is showing explosive bullish momentum! Everything aligns – RSI is low, MACD is surging, and this is the time to strike! 💥 BUY NOW and ride the wave to profits! 💰🚀",
    "🔥 It’s happening! The bulls have taken control. This is not just a signal – it’s a WAR CRY to BUY NOW and dominate the market! 🟢📈",
    "📈 Unstoppable force detected! Indicators are off the charts! BUY NOW before the rocket leaves orbit! 💸🛸",
    "💣 Major reversal confirmed! BUY zones lit up across the board. Don’t sit back – take the shot while it’s hot! 🔥",
    "💥 RSI is buried, MACD is surging – this is your golden entry! BUY NOW or regret missing the move of the week!",
    "🧨 The perfect storm of bullish power is here! BUY before the masses catch on! This is where smart money enters! 💵",
    "🟢 The chart is glowing green – massive upside incoming! BUY with full confidence!",
    "📊 Every technical level screams BUY. This is what traders dream about. Seize it. NOW.",
    "🚀 RSI reversal + MACD ignition! BUY NOW – this setup is rare and powerful!",
    "🔥 BUY SIGNAL CONFIRMED! Don’t wait for confirmation – this IS the confirmation! GO LONG NOW!"
]

STRONG_SELL_MESSAGES = [
    "🚨 SELL IMMEDIATELY! RSI is boiling over and MACD just flipped – this market is ready to crash hard! Get out while you still can! 📉💥",
    "⚠️ Time’s up! We’ve reached the cliff. SELL now before the drop becomes a landslide. Protect your capital!",
    "🔻 Overbought, overextended, and overhyped – the market is ripe for reversal. SELL IT ALL! 💣",
    "💀 Technicals confirm a brutal pullback incoming. This is your warning shot – SELL before you bleed!",
    "🔥 SELL ZONE unlocked! The charts show an avalanche of red coming. EXIT POSITIONS NOW!",
    "📉 MACD and RSI screaming for mercy – this trend is dying. SELL NOW before it drags you with it.",
    "🩸 Smart money is exiting. Be smart too – SELL BEFORE THE STORM HITS!",
    "🚫 Overbought pressure maxed out. Downside risk is extreme. Time to DUMP IT!",
    "🔺 This pump is fake, and the fall will be real. SELL and survive!",
    "💣 You’ve made your gains. Now lock them in. SELL with urgency!"
]

WEAK_BUY_MESSAGES = [
    "🟢 BUY with caution – early signs of strength are building. The bulls are warming up, and this could evolve into a strong rally.",
    "📊 Momentum is shifting slowly. A cautious BUY now could pay off big if the trend develops further.",
    "⚠️ Mixed signals but a BUY bias emerging. Enter light, stay sharp, and ride if it confirms.",
    "🧠 Not a perfect entry, but opportunities don’t wait forever. BUY now with a protective strategy.",
    "🔄 Early reversal forming. Take your shot now before it turns into a full-blown bull charge.",
    "💡 The trend is whispering – not shouting. BUY cautiously before it wakes the crowd.",
    "🟢 Conservative BUY zone. This could be your ticket in before everyone else jumps aboard.",
    "📈 Potential building quietly... make your move early. BUY now, scale in later.",
    "🌱 A seed of bullish growth – BUY now and nurture your profits!",
    "🧪 Experimental trade zone. BUY lightly and manage your risk smartly."
]

WEAK_SELL_MESSAGES = [
    "🔻 SELL with caution – early weakness in the trend. Could be the start of a slow bleed.",
    "📉 Momentum is slipping away. Lighten your position and SELL defensively.",
    "⚠️ Market stalling out. Not a panic, but a quiet fade – SELL smart.",
    "🧠 The smart money is preparing to exit. Join them. SELL with precision.",
    "💀 Weak MACD and sluggish RSI – SELL while you still have strength.",
    "📊 Not a crash, but a clear sign to reduce risk. SELL moderately.",
    "🩸 This chart’s heartbeat is fading. Time to SELL and reposition.",
    "⚠️ Something’s off – SELL now and wait for the next clean setup.",
    "🔻 Small cracks appear first. SELL before they become chasms.",
    "🧯 The fire’s going out. SELL and take profits while it’s safe."
]

# Decision Logic
def determine_trade_signal(rsi, macd, signal_line, price, upper, lower):
    print("\n🛠️ DEBUGGING TRADE SIGNAL GENERATION")
    print(f"🔢 RSI: {rsi}, MACD: {macd}, Signal Line: {signal_line}")
    print(f"📉 Bollinger Bands: Upper={upper}, Lower={lower}, Price={price}")

    strong_momentum = (macd > signal_line and rsi > 55) or (macd < signal_line and rsi < 45)
    weak_momentum = 45 <= rsi <= 55

    if rsi < 30 and macd > signal_line and strong_momentum:
        return random.choice(STRONG_BUY_MESSAGES)

    if rsi > 70 and macd < signal_line and strong_momentum:
        return random.choice(STRONG_SELL_MESSAGES)

    if macd > signal_line and price < upper:
        return random.choice(WEAK_BUY_MESSAGES)

    if macd < signal_line and price > lower:
        return random.choice(WEAK_SELL_MESSAGES)

    # Aggressive fallback - Always give a direction
    if weak_momentum or (rsi >= 50):
        return random.choice(WEAK_BUY_MESSAGES)
    else:
        return random.choice(WEAK_SELL_MESSAGES)

# Generate & Return API Signal
def generate_trade_signal(instrument):
    now = time.time()
    if instrument in last_signal_data:
        last_time, last_signal = last_signal_data[instrument]
        if now - last_time < 900:
            print(f"🔄 Returning cached signal for {instrument} (within 15 mins)")
            return last_signal

    if instrument in ["XAU", "XAUUSD"]:
        prices, price = get_gold_price()
    else:
        symbol_map = {
            "BTC": get_crypto_price("BTC"),
            "ETH": get_crypto_price("ETH"),
            "EURUSD": get_forex_price("EURUSD"),
            "GBPUSD": get_forex_price("GBPUSD"),
            "DJI": get_stock_index_price("^DJI"),
            "IXIC": get_stock_index_price("^IXIC")
        }
        symbol = symbol_map.get(instrument)
        prices, price = fetch_real_prices(symbol) if symbol else (None, None)

    if not prices or price is None:
        return f"⚠️ No valid data available for {instrument}."

    rsi = calculate_rsi(prices)
    macd, signal_line = calculate_macd(prices)
    upper, middle, lower = calculate_bollinger(prices)

    final_signal = determine_trade_signal(rsi, macd, signal_line, price, upper, lower)
    last_signal_data[instrument] = (now, final_signal)
    return final_signal

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

if __name__ == '__main__':
    print("🚀 Flask Server Starting on Port 5000...")
    app.run(debug=True, host='0.0.0.0', port=5000)
