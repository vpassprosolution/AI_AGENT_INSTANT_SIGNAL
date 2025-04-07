import requests
import yfinance as yf
from flask import Flask, jsonify, request
import os
import numpy as np
import logging
import pandas as pd
import time
import redis
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ✅ Redis connection from Railway ENV
redis_client = redis.StrictRedis.from_url(
    os.getenv("REDIS_URL"),
    decode_responses=True
)

@app.before_request
def log_request_info():
    logging.info(f"📥 {request.method} {request.url}")

@app.route('/')
def home():
    return jsonify({"message": "AI Agent Instant Signal API is running!"})

# ✅ Get Gold Price
def get_gold_price():
    api_key = os.getenv("METALS_API_KEY")
    url = f"https://metals-api.com/api/latest?access_key={api_key}&base=USD&symbols=XAU"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        print(f"❌ Error fetching Gold price: {e}")
        return None

    if "rates" in data and "USDXAU" in data["rates"]:
        price = round(data["rates"]["USDXAU"], 2)
        print(f"✅ GOLD PRICE: {price}")
        return price

    print("⚠️ No Gold price found in API response.")
    return None

# ✅ Indicator Calculations
def detect_trend_direction(prices):
    if len(prices) < 3:
        return "neutral"
    if prices[-3] < prices[-2] < prices[-1]:
        return "bullish"
    if prices[-3] > prices[-2] > prices[-1]:
        return "bearish"
    return "neutral"

def calculate_rsi(prices, period=14):
    delta = pd.Series(prices).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices):
    exp1 = pd.Series(prices).ewm(span=12, adjust=False).mean()
    exp2 = pd.Series(prices).ewm(span=26, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

def calculate_bollinger_bands(prices, window=20):
    series = pd.Series(prices)
    ma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    upper_band = ma + (std * 2)
    lower_band = ma - (std * 2)
    return upper_band.iloc[-1], lower_band.iloc[-1]

def detect_volume_spike(data):
    if 'Volume' in data:
        vol = data['Volume'].tail(4).values
        return vol[-1] > np.mean(vol[:-1]) * 1.3
    return False

def get_fixed_message(signal_type):
    messages = {
        "STRONG_BUY": "🔥 STRONG BUY SIGNAL - Naomi AI confirms aggressive upward momentum. All indicators aligned. 📈",
        "STRONG_SELL": "📉 STRONG SELL SIGNAL - Naomi AI confirms strong bearish breakdown. Indicators confirm reversal. 🔻",
        "WEAK_BUY": "⚠️ BUY SIGNAL - Early bullish signs detected. Watch closely for confirmation. 🟢",
        "WEAK_SELL": "⚠️ SELL SIGNAL - Mild bearish shift forming. Possible fade incoming. 🔸",
    }
    return messages.get(signal_type, "⚠️ Unable to determine signal.")

# ✅ Main Signal Logic
def generate_trade_signal(instrument):
    now = time.time()
    redis_key = f"signal_cache:{instrument}"

    cached = redis_client.hgetall(redis_key)
    if cached:
        timestamp = float(cached.get("timestamp", 0))
        if now - timestamp < 60:
            return get_fixed_message(cached["signal_type"])

    symbol_map = {
        "BTC": "BTC-USD", "ETH": "ETH-USD", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
        "DJI": "^DJI", "IXIC": "^IXIC"
    }

    if instrument in ["XAU", "XAUUSD"]:
        price = get_gold_price()
        if price is None:
            return "⚠️ Failed to get gold price."
        prices = [price] * 30
        trend = "neutral"
        rsi_value = 50
        macd = 0
        signal = 0
        boll_upper, boll_lower = price + 2, price - 2
        volume_spike = False
    else:
        symbol = symbol_map.get(instrument)
        if not symbol:
            return f"⚠️ Invalid instrument: {instrument}"
        try:
            data = yf.Ticker(symbol).history(period="1d", interval="1m")
            if data.empty or len(data) < 30:
                return f"⚠️ No valid price data for {instrument}"
        except Exception as e:
            return f"⚠️ Error fetching data: {e}"

        prices = list(data["Close"].values[-30:])
        price = round(prices[-1], 2)
        trend = detect_trend_direction(prices)
        rsi_series = calculate_rsi(prices)
        rsi_value = rsi_series.iloc[-1] if not rsi_series.isna().all() else 50
        macd, signal = calculate_macd(prices)
        boll_upper, boll_lower = calculate_bollinger_bands(prices)
        volume_spike = detect_volume_spike(data)

    if trend == "bullish" and rsi_value < 70 and macd > signal and price < boll_upper and volume_spike:
        signal_type = "STRONG_BUY"
    elif trend == "bearish" and rsi_value > 30 and macd < signal and price > boll_lower and volume_spike:
        signal_type = "STRONG_SELL"
    elif trend == "bullish" and rsi_value < 70:
        signal_type = "WEAK_BUY"
    elif trend == "bearish" and rsi_value > 30:
        signal_type = "WEAK_SELL"
    else:
        signal_type = "WEAK_BUY" if rsi_value < 50 else "WEAK_SELL"

    redis_client.hset(redis_key, mapping={
        "timestamp": now,
        "price": price,
        "signal_type": signal_type
    })
    redis_client.expire(redis_key, 120)

    return get_fixed_message(signal_type)

# ✅ API Endpoint
@app.route('/get_signal/<string:selected_instrument>', methods=['GET'])
def get_signal(selected_instrument):
    try:
        signal = generate_trade_signal(selected_instrument)
        return jsonify({"instrument": selected_instrument, "signal": signal})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Run Server
if __name__ == '__main__':
    print("🚀 AI Agent Signal API Running...")
    app.run(debug=False, host='0.0.0.0', port=5000)
