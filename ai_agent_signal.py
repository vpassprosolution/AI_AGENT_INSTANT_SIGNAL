import os
import time
import logging
import requests
import numpy as np
import pandas as pd
import redis
import yfinance as yf

from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

redis_client = redis.StrictRedis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

@app.before_request
def log_request_info():
    logging.info(f"📥 GET {request.url}")

@app.route('/')
def home():
    return jsonify({"message": "AI Agent Instant Signal API is running!"})


# === CANDLE SOURCES ===
def get_gold_candles():
    try:
        df = yf.download("GC=F", interval="5m", period="2d", progress=False)
        if df.empty or "Close" not in df.columns:
            return None
        df = df.tail(120)
        df["close"] = df["Close"].astype(float)

        # Override last candle with Metals API
        url = f"https://metals-api.com/api/latest?access_key={os.getenv('METALS_API_KEY')}&base=USD&symbols=XAU"
        res = requests.get(url, timeout=10).json()
        if "rates" in res and "USDXAU" in res["rates"]:
            real_price = round(res["rates"]["USDXAU"], 2)
            df.iloc[-1, df.columns.get_loc("close")] = real_price
            print(f"✅ GOLD real price override: {real_price}")
        else:
            print("⚠️ Metals API failed")
        return df
    except:
        return None

def get_twelvedata_candles(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=120&apikey={os.getenv('TWELVE_API_KEY')}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df["close"] = df["close"].astype(float)
        return df[::-1]  # reverse order
    except:
        return None


# === INDICATORS ===
def calculate_rsi(prices, period=14):
    delta = pd.Series(prices).diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices):
    exp1 = pd.Series(prices).ewm(span=12).mean()
    exp2 = pd.Series(prices).ewm(span=26).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=9).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

def detect_trend(prices):
    return "bullish" if prices[-3] < prices[-2] < prices[-1] else \
           "bearish" if prices[-3] > prices[-2] > prices[-1] else "neutral"

def detect_snr(prices, sensitivity=0.003):
    mean = np.mean(prices[-20:])
    upper = mean * (1 + sensitivity)
    lower = mean * (1 - sensitivity)
    price = prices[-1]
    if price >= upper:
        return "resistance"
    elif price <= lower:
        return "support"
    return "middle"


# === FIXED MESSAGE ===
def get_fixed_message(signal_type):
    return {
        "STRONG_BUY": "🔥 *STRONG BUY NOW!!* Naomi AI detects high-conviction bullish explosion forming at key support zone. Ride the wave upward with confidence 🚀",
        "WEAK_BUY": "🟢 *BUY SIGNAL DETECTED* - Bullish indicators align. Potential upside forming.",
        "STRONG_SELL": "🔻 *STRONG SELL NOW!!* Naomi AI detects major bearish crash forming near resistance. Execute confidently ⚠️",
        "WEAK_SELL": "🟠 *SELL SIGNAL DETECTED* - Early signs of bearish pressure emerging. Be cautious and watch momentum closely.",
    }.get(signal_type, "🤖 No signal available.")


# === GENERATE SIGNAL ===
def generate_trade_signal(instrument):
    now = time.time()
    redis_key = f"signal_cache:{instrument}"
    cached = redis_client.hgetall(redis_key)

    if cached:
        try:
            if now - float(cached.get("timestamp", 0)) < 60:
                print(f"🔁 Cached Redis signal: {cached['signal_type']}")
                return get_fixed_message(cached["signal_type"])
        except:
            redis_client.delete(redis_key)

    # ✅ Get Candle Data
    if instrument == "XAUUSD":
        df = get_gold_candles()
    else:
        mapping = {
            "BTC": "BTC/USD", "ETH": "ETH/USD",
            "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD",
            "DJI": "DIA", "IXIC": "QQQ"
        }
        if instrument not in mapping:
            return f"⚠️ Invalid instrument: {instrument}"
        df = get_twelvedata_candles(mapping[instrument])

    if df is None or len(df) < 30:
        return "⚠️ Failed to get data."

    prices = df["close"].values
    rsi = calculate_rsi(prices).iloc[-1]
    macd, signal = calculate_macd(prices)
    trend = detect_trend(prices)
    snr = detect_snr(prices)

    print(f"{instrument} | RSI: {rsi:.2f} | MACD: {macd:.2f} | Signal: {signal:.2f} | Trend: {trend} | SNR: {snr}")

    # ✅ Decision Tree
    if snr == "support" and rsi < 40 and macd > signal and trend == "bullish":
        signal_type = "STRONG_BUY"
    elif snr == "resistance" and rsi > 60 and macd < signal and trend == "bearish":
        signal_type = "STRONG_SELL"
    elif trend == "bullish" and macd > signal:
        signal_type = "WEAK_BUY"
    elif trend == "bearish" and macd < signal:
        signal_type = "WEAK_SELL"
    else:
        signal_type = "WEAK_BUY" if rsi < 50 else "WEAK_SELL"

    redis_client.hset(redis_key, mapping={
        "timestamp": now,
        "signal_type": signal_type
    })
    redis_client.expire(redis_key, 120)

    return get_fixed_message(signal_type)


# === ENDPOINT ===
@app.route('/get_signal/<string:instrument>', methods=['GET'])
def get_signal(instrument):
    try:
        signal = generate_trade_signal(instrument.upper())
        return jsonify({"instrument": instrument.upper(), "signal": signal})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === RUN ===
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
