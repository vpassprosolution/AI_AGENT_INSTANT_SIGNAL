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


# === Get M5 Candle Data ===
def get_gold_m5_candles():
    try:
        df = yf.download("GC=F", interval="5m", period="2d", progress=False)
        if df.empty or "Close" not in df.columns:
            print("❌ Yahoo M5 candle empty")
            return None
        df = df.tail(120)
        df["close"] = df["Close"].astype(float)
        return df
    except Exception as e:
        print(f"❌ Error getting M5 candle: {e}")
        return None

def calculate_rsi(prices, period=14):
    delta = pd.Series(prices).diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices):
    exp1 = pd.Series(prices).ewm(span=12).mean()
    exp2 = pd.Series(prices).ewm(span=26).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=9).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

def detect_trend(prices):
    return (
        "bullish" if prices[-3] < prices[-2] < prices[-1]
        else "bearish" if prices[-3] > prices[-2] > prices[-1]
        else "neutral"
    )

def detect_snr(prices, sensitivity=0.003):
    mean_price = np.mean(prices[-20:])
    upper = mean_price * (1 + sensitivity)
    lower = mean_price * (1 - sensitivity)
    current = prices[-1]
    if current >= upper:
        return "resistance"
    elif current <= lower:
        return "support"
    return "middle"

def get_fixed_message(signal_type):
    return {
        "STRONG_BUY": "🔥 *STRONG BUY NOW!!* Naomi AI detects high-conviction bullish explosion forming at key support zone. Momentum, trend, and indicators are perfectly aligned. Ride the wave upward with confidence. 🚀",
        "WEAK_BUY": "🟢 *BUY SIGNAL DETECTED* - Bullish indicators align but trend is still forming. Naomi AI suggests a potential upside. Monitor closely for entry confirmation.",
        "STRONG_SELL": "🔻 *STRONG SELL NOW!!* Naomi AI sees heavy bearish pressure forming near resistance. Market is weakening sharply — execute with high conviction. ⚠️",
        "WEAK_SELL": "🟠 *SELL SIGNAL DETECTED* - Early signs of bearish reversal emerging. Naomi AI suggests caution — consider short if momentum confirms.",
    }.get(signal_type, "🤖 No signal available.")

# === MAIN SIGNAL GENERATOR ===
def generate_trade_signal():
    now = time.time()
    redis_key = "signal_cache:XAUUSD"
    cached = redis_client.hgetall(redis_key)

    if cached:
        try:
            if now - float(cached.get("timestamp", 0)) < 60:
                print(f"🔁 Cached Redis signal: {cached['signal_type']}")
                return get_fixed_message(cached["signal_type"])
        except:
            redis_client.delete(redis_key)

    df = get_gold_m5_candles()
    if df is None or len(df) < 30:
        return "⚠️ Failed to get data."

    # === Replace last price with Metals API
    try:
        metals_url = f"https://metals-api.com/api/latest?access_key={os.getenv('METALS_API_KEY')}&base=USD&symbols=XAU"
        res = requests.get(metals_url, timeout=10).json()
        real_price = round(res["rates"]["USDXAU"], 2)
        df.iloc[-1, df.columns.get_loc("close")] = real_price
        print(f"✅ Real price override: {real_price}")
    except:
        print("⚠️ Failed to get Metals API price")

    prices = df["close"].values
    rsi = calculate_rsi(prices).iloc[-1]
    macd, signal = calculate_macd(prices)
    trend = detect_trend(prices)
    snr = detect_snr(prices)

    print(f"RSI: {rsi:.2f} | MACD: {macd:.2f} | Signal: {signal:.2f} | Trend: {trend} | SNR: {snr}")

    # === DECISION TREE ===
    if snr == "support" and rsi < 40 and macd > signal and trend == "bullish":
        signal_type = "STRONG_BUY"
    elif snr == "resistance" and rsi > 60 and macd < signal and trend == "bearish":
        signal_type = "STRONG_SELL"
    elif trend == "bullish" and macd > signal:
        signal_type = "WEAK_BUY"
    elif trend == "bearish" and macd < signal:
        signal_type = "WEAK_SELL"
    else:
        signal_type = "WEAK_BUY" if rsi < 50 else "WEAK_SELL"  # Default fallback

    redis_client.hset(redis_key, mapping={
        "timestamp": now,
        "signal_type": signal_type
    })
    redis_client.expire(redis_key, 120)

    return get_fixed_message(signal_type)


# === API ENDPOINT ===
@app.route('/get_signal', methods=['GET'])
def get_signal():
    try:
        signal = generate_trade_signal()
        return jsonify({"instrument": "XAUUSD", "signal": signal})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === RUN ===
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
