import requests
import yfinance as yf
from flask import Flask, jsonify, request
import os
import numpy as np
import logging
import pandas as pd
import time

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

def get_crypto_price(symbol):
    symbol_map = {"BTC": "BTC-USD", "ETH": "ETH-USD"}
    return symbol_map.get(symbol, None)

def get_forex_price(pair):
    return f"{pair}=X"

def get_stock_index_price(symbol):
    return symbol

def get_gold_price():
    url = "https://metals-api.com/api/latest?access_key=cflqymfx6mzfe1pw3p4zgy13w9gj12z4aavokqd5xw4p8xeplzlwyh64fvrv&base=USD&symbols=XAU"
    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print(f"❌ Error fetching Gold price: {e}")
        return None, None

    print("🔍 FULL METAL API RESPONSE:", data)

    if "rates" in data and "USDXAU" in data["rates"]:
        price = round(data["rates"]["USDXAU"], 2)
        print(f"✅ GOLD PRICE FROM API: {price}")
        return [price] * 30, price

    print("⚠️ No Gold price found in API response!")
    return None, None

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

def determine_trade_signal(rsi, macd, signal_line, price, upper, lower):
    print("\n🛠️ DEBUGGING TRADE SIGNAL GENERATION")
    print(f"🔢 RSI: {rsi}, MACD: {macd}, Signal Line: {signal_line}")
    print(f"📉 Bollinger Bands: Upper={upper}, Lower={lower}, Price={price}")

    strong_momentum = (macd > signal_line and rsi > 55) or (macd < signal_line and rsi < 45)

    if rsi < 30 and macd > signal_line and strong_momentum:
        return "🚨 **WHAT'S UP TRADERS!**\n🔥 **MARKET ALERT**\n📈 **Strong Bullish Signal! BUY NOW!** 🚀"

    if rsi > 70 and macd < signal_line and strong_momentum:
        return "🚨 **SELL ZONE DETECTED!**\n📉 **Overbought + Bearish Crossover! SELL NOW!** 💥"

    if 40 <= rsi <= 60:
        return "⚠️ **Neutral Zone**\n🧐 Market is undecided. HOLD. Wait for clarity."

    return "⚠️ No strong signal detected. Stay alert."

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
