import os
import time
import logging
import requests
import numpy as np
import pandas as pd
import redis
import json
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


# ✅ GOLD Candle: Yahoo + replace final price with Metals API real-time
def get_gold_candles_combined():
    try:
        df = yf.download("GC=F", interval="1m", period="2d", progress=False)
        if df.empty or "Close" not in df.columns:
            print("❌ Yahoo Gold candle empty")
            return None
        df = df.tail(120)
        df["close"] = df["Close"].astype(float)

        # Replace last price with Metals API
        url = f"https://metals-api.com/api/latest?access_key={os.getenv('METALS_API_KEY')}&base=USD&symbols=XAU"
        res = requests.get(url, timeout=10).json()
        if "rates" in res and "USDXAU" in res["rates"]:
            df.iloc[-1, df.columns.get_loc("close")] = round(res["rates"]["USDXAU"], 2)
            print("✅ GOLD candle from Yahoo + real-time Metals price (last candle)")
            return df
        else:
            print("⚠️ Metals API failed, fallback to Yahoo candle only")
            return df
    except Exception as e:
        print(f"❌ Gold candle error: {e}")
        return None


# ✅ TwelveData for others
def get_twelvedata_history(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=30&apikey={os.getenv('TWELVE_API_KEY')}"
    try:
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df["close"] = df["close"].astype(float)
        return df[::-1]
    except Exception as e:
        print(f"❌ Error TwelveData {symbol}: {e}")
        return None


# ✅ Indicators
def detect_trend_direction(prices):
    return (
        "bullish" if prices[-3] < prices[-2] < prices[-1]
        else "bearish" if prices[-3] > prices[-2] > prices[-1]
        else "neutral"
    )

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

def calculate_bollinger_bands(prices, window=20):
    ma = pd.Series(prices).rolling(window).mean()
    std = pd.Series(prices).rolling(window).std()
    return ma.iloc[-1] + 2 * std.iloc[-1], ma.iloc[-1] - 2 * std.iloc[-1]

def detect_volume_spike(df):
    if 'volume' in df.columns:
        vol = df['volume'].astype(float).tail(4).values
        return vol[-1] > np.mean(vol[:-1]) * 1.3
    return False

def get_fixed_message(signal_type):
    return {
        "STRONG_BUY": "🔥 STRONG BUY NOW!! Naomi AI detects aggressive bullish explosion forming. Enter with confidence. 🚀",
        "WEAK_BUY": "🟢 BUY NOW !! - Subtle bullish strength detected by Naomi Assist. Possible upside incoming.",
        "STRONG_SELL": "🔻 STRONG SELL NOW!! Naomi AI sees powerful bearish crash developing. High confidence short! ⚠️",
        "WEAK_SELL": "🟠 SELL NOW !! - Mild bearish movement detected. Momentum shifting lower.",
    }.get(signal_type, "⚠️ Naomi AI unable to detect clear signal. Market is neutral.")


# ✅ Main Logic
def generate_trade_signal(instrument):
    now = time.time()
    redis_key = f"signal_cache:{instrument}"
    cached = redis_client.hgetall(redis_key)
    if cached and now - float(cached.get("timestamp", 0)) < 60:
        print(f"🔁 Cached Redis signal: {cached['signal_type']}")
        return get_fixed_message(cached["signal_type"])

    tw_symbols = {
        "BTC": "BTC/USD", "ETH": "ETH/USD",
        "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD",
        "DJI": "DIA", "IXIC": "QQQ"
    }

    if instrument in ["XAU", "XAUUSD"]:
        df = get_gold_candles_combined()
        if df is None or len(df) < 30:
            return "⚠️ Failed to get GOLD data."
        df["close"] = df["close"].astype(float)
        prices = df["close"].values
        price = round(prices[-1], 2)
        volume_spike = True
    elif instrument in tw_symbols:
        df = get_twelvedata_history(tw_symbols[instrument])
        if df is None or len(df) < 30:
            return f"⚠️ No data for {instrument}"
        prices = df["close"].values
        price = round(prices[-1], 2)
        volume_spike = detect_volume_spike(df)
    else:
        return f"⚠️ Invalid instrument: {instrument}"

    trend = detect_trend_direction(prices)
    rsi_series = calculate_rsi(prices)
    rsi_value = rsi_series.iloc[-1] if not rsi_series.isna().all() else 50
    macd, signal = calculate_macd(prices)
    boll_upper, boll_lower = calculate_bollinger_bands(prices)

    # ✅ Handle BBand NaN fallback
    if np.isnan(boll_upper) or np.isnan(boll_lower):
        boll_upper, boll_lower = price + 2, price - 2

    print(f"📊 {instrument} | Price: {price}, Trend: {trend}, RSI: {rsi_value:.2f}, MACD: {macd:.2f}, Signal: {signal:.2f}, BBands: [{boll_lower:.2f}, {boll_upper:.2f}], Volume Spike: {volume_spike}")

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
        signal = generate_trade_signal(selected_instrument.upper())
        return jsonify({"instrument": selected_instrument, "signal": signal})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ Run
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
