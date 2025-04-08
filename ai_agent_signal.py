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
    logging.info(f"📅 GET {request.url}")

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

        # === Replace last candle with Metals API real price
        metals_url = f"https://metals-api.com/api/latest?access_key={os.getenv('METALS_API_KEY')}&base=USD&symbols=XAU"
        res = requests.get(metals_url, timeout=10).json()
        if "rates" in res and "USDXAU" in res["rates"]:
            real_price = round(res["rates"]["USDXAU"], 2)
            df.iloc[-1, df.columns.get_loc("close")] = real_price
            print(f"✅ Real price override: {real_price}")
        return df
    except Exception as e:
        print(f"❌ Error getting M5 candle: {e}")
        return None

# === Indicators ===
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

def calculate_bbands(prices, window=20):
    ma = pd.Series(prices).rolling(window).mean()
    std = pd.Series(prices).rolling(window).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    return upper.iloc[-1], lower.iloc[-1]

def detect_trend(prices):
    return (
        "bullish" if prices[-3] < prices[-2] < prices[-1] else
        "bearish" if prices[-3] > prices[-2] > prices[-1] else
        "neutral"
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

def calculate_ma_cross(prices):
    ma20 = pd.Series(prices).rolling(window=20).mean().iloc[-1]
    ma50 = pd.Series(prices).rolling(window=50).mean().iloc[-1]
    return "bullish" if ma20 > ma50 else "bearish"

def detect_volume_spike(df):
    if 'Volume' in df.columns:
        vol = df['Volume'].astype(float).tail(4).values
        return vol[-1] > np.mean(vol[:-1]) * 1.3
    return False

def calculate_ema200(prices):
    return pd.Series(prices).ewm(span=200).mean().iloc[-1]

# === Message ===
def get_fixed_message(signal_type):
    return {
        "STRONG_BUY": "🔥 *STRONG BUY NOW!!* Naomi AI detects powerful bullish confirmation from all indicators. SNR support zone + Trend + MA Cross + Volume confirmed. Ride the wave upward! 🚀",
        "WEAK_BUY": "🔹 *BUY SIGNAL DETECTED* - Some bullish indicators align, but caution advised. Monitor closely.",
        "STRONG_SELL": "🔻 *STRONG SELL NOW!!* Naomi AI detects dominant bearish signal. Resistance zone + Bearish MA Cross + MACD down. High conviction short.",
        "WEAK_SELL": "🔘 *SELL SIGNAL DETECTED* - Weak bearish signal forming. Partial confirmation. Monitor further."
    }.get(signal_type, "🤖 No signal available.")

# === Signal Engine ===
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

    prices = df["close"].values
    rsi = calculate_rsi(prices).iloc[-1]
    macd, macd_signal = calculate_macd(prices)
    upper_bb, lower_bb = calculate_bbands(prices)
    trend = detect_trend(prices)
    snr = detect_snr(prices)
    ma_trend = calculate_ma_cross(prices)
    ema200 = calculate_ema200(prices)
    volume_spike = detect_volume_spike(df)

    current_price = prices[-1]

    print(f"RSI: {rsi:.2f} | MACD: {macd:.2f} | BB: [{lower_bb:.2f}, {upper_bb:.2f}] | Trend: {trend} | MA20>50: {ma_trend} | EMA200: {ema200:.2f} | SNR: {snr} | Price: {current_price:.2f}")

    # === Decision Tree ===
    if (
        snr == "support" and rsi < 40 and macd > macd_signal and trend == "bullish"
        and ma_trend == "bullish" and current_price > ema200 and volume_spike
    ):
        signal_type = "STRONG_BUY"
    elif (
        snr == "resistance" and rsi > 60 and macd < macd_signal and trend == "bearish"
        and ma_trend == "bearish" and current_price < ema200 and volume_spike
    ):
        signal_type = "STRONG_SELL"
    elif trend == "bullish" and macd > macd_signal and current_price > ema200:
        signal_type = "WEAK_BUY"
    elif trend == "bearish" and macd < macd_signal and current_price < ema200:
        signal_type = "WEAK_SELL"
    else:
        signal_type = "WEAK_BUY" if rsi < 50 else "WEAK_SELL"

    redis_client.hset(redis_key, mapping={
        "timestamp": now,
        "signal_type": signal_type
    })
    redis_client.expire(redis_key, 120)

    return get_fixed_message(signal_type)

@app.route('/get_signal', methods=['GET'])
def get_signal():
    try:
        signal = generate_trade_signal()
        return jsonify({"instrument": "XAUUSD", "signal": signal})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
