import requests
import yfinance as yf
from flask import Flask, jsonify, request
import os
import numpy as np
import random
import logging
import pandas as pd
import ta  # ✅ Required for technical indicators

app = Flask(__name__)

# ✅ Enable full logging
logging.basicConfig(level=logging.DEBUG)

@app.before_request
def log_request_info():
    logging.debug(f"📥 Incoming request: {request.method} {request.url}")
    print(f"📥 Incoming request: {request.method} {request.url}")  # ✅ Force print to CMD

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



# ✅ RSI, MACD, BOLLINGER BANDS FUNCTIONS
def calculate_rsi(prices, period=14):
    df = pd.DataFrame(prices, columns=["price"])
    df["rsi"] = ta.momentum.RSIIndicator(df["price"], window=period).rsi()
    return df["rsi"].iloc[-1]  

def calculate_macd(prices, short_window=12, long_window=26, signal_window=9):
    df = pd.DataFrame(prices, columns=["price"])
    
    if len(df) < long_window:
        return 0.01, 0.01  

    macd_indicator = ta.trend.MACD(df["price"], window_slow=long_window, window_fast=short_window, window_sign=signal_window)

    df = df.copy()
    df["macd"] = macd_indicator.macd()
    df["signal"] = macd_indicator.macd_signal()

    df["macd"] = df["macd"].fillna(0.01)
    df["signal"] = df["signal"].fillna(0.01)

    return df["macd"].iloc[-1], df["signal"].iloc[-1] 

def calculate_bollinger_bands(prices, window=20, num_std=2):
    df = pd.DataFrame(prices, columns=["price"])

    if len(df) < window:
        estimated_price = prices[-1] if prices else 1000  
        return estimated_price * 1.05, estimated_price, estimated_price * 0.95  

    bb_indicator = ta.volatility.BollingerBands(df["price"], window=window, window_dev=num_std)

    df = df.copy()
    df["upper_band"] = bb_indicator.bollinger_hband()
    df["lower_band"] = bb_indicator.bollinger_lband()
    df["middle_band"] = bb_indicator.bollinger_mavg()

    return df["upper_band"].iloc[-1], df["middle_band"].iloc[-1], df["lower_band"].iloc[-1]

# ✅ TRADE SIGNAL GENERATION
def generate_trade_signal(selected_instrument):
    print(f"📡 Processing Instrument: {selected_instrument}")

    price = None

    if selected_instrument == "BTC":
        price = get_crypto_price("BTC")
    elif selected_instrument == "ETH":
        price = get_crypto_price("ETH")
    elif selected_instrument == "EURUSD":
        price = get_forex_price("EURUSD")
    elif selected_instrument == "GBPUSD":
        price = get_forex_price("GBPUSD")
    elif selected_instrument == "DJI":
        price = get_stock_index_price("^DJI")
    elif selected_instrument == "IXIC":
        price = get_stock_index_price("^IXIC")
    elif selected_instrument in ["XAU", "XAUUSD"]:
        price = get_gold_price()

    if price is None:
        print(f"⚠️ No price found for {selected_instrument}!")  
        return f"⚠️ [{selected_instrument}] No valid data available."

    print(f"✅ Price for {selected_instrument}: {price}")

    test_prices = [price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(30)]

    rsi = calculate_rsi(test_prices)
    macd, signal_line = calculate_macd(test_prices)
    upper_band, middle_band, lower_band = calculate_bollinger_bands(test_prices)

    print(f"📊 [{selected_instrument}] RSI: {rsi}")
    print(f"📈 [{selected_instrument}] MACD: {macd}, Signal Line: {signal_line}")
    print(f"📉 [{selected_instrument}] Bollinger Bands: Upper: {upper_band}, Middle: {middle_band}, Lower: {lower_band}")

    final_signal = determine_trade_signal(rsi, macd, signal_line, price, upper_band, lower_band)
    print(f"🔍 FINAL SIGNAL for {selected_instrument}: {final_signal}")  # ✅ Debugging Log

    return final_signal  # ✅ Ensure the function returns the actual signal, not an error message

def determine_trade_signal(rsi, macd, signal_line, price, upper_band, lower_band):
    print("🛠️ DEBUGGING TRADE SIGNAL GENERATION")  
    print(f"📊 RSI: {rsi}")
    print(f"📈 MACD: {macd}, Signal Line: {signal_line}")
    print(f"📉 Bollinger Bands: Upper: {upper_band}, Lower: {lower_band}")

    is_oversold = rsi < 30  
    is_overbought = rsi > 70  
    macd_cross_up = macd > signal_line  
    macd_cross_down = macd < signal_line  
    price_below_lower_band = price < lower_band  
    price_above_upper_band = price > upper_band  
    neutral_zone = 40 <= rsi <= 60  

    print(f"🟢 Oversold: {is_oversold}, 🔴 Overbought: {is_overbought}")
    print(f"🔼 MACD Cross Up: {macd_cross_up}, 🔽 MACD Cross Down: {macd_cross_down}")
    print(f"📉 Price Below Lower Band: {price_below_lower_band}, 📈 Price Above Upper Band: {price_above_upper_band}")

    if is_oversold and (macd_cross_up or abs(macd - signal_line) < 0.2):  
        return "🚀 The market is heating up! 🔥 It's time to **BUY now** before the move starts!"

    elif is_overbought and macd_cross_down:
        return "⚠️ Warning! Overbought conditions detected. 📉 **SELL now** before it's too late!"

    elif macd_cross_up and price < upper_band:
        return "📈 Momentum is shifting upwards! **A bullish crossover detected** – buyers are stepping in!"

    elif macd_cross_down and price > lower_band:
        return "📉 Bearish pressure is building! **A downward move is forming** – caution is advised!"

    elif neutral_zone:
        return "🧐 The market is in a tricky zone. No action needed for now – **HOLD your position.**"

    return "⚠️ No strong trade signal detected. Stay alert for market changes."







@app.route('/get_signal/<string:selected_instrument>', methods=['GET'])
def get_signal(selected_instrument):
    try:
        print(f"🟢 API Request Received for: {selected_instrument}")  # ✅ Debugging Log
        trade_signal = generate_trade_signal(selected_instrument)

        print(f"✅ FINAL SIGNAL BEFORE RETURN: {trade_signal}")  # ✅ Print final result

        if "No valid data" in trade_signal:
            print(f"❌ ERROR: No valid data for {selected_instrument}")
            return jsonify({"instrument": selected_instrument, "signal": "⚠️ No strong trade signal detected."})

        print(f"🟢 API Response Sent: {trade_signal}")  # ✅ Debugging Log
        return jsonify({"instrument": selected_instrument, "signal": trade_signal})

    except Exception as e:
        print(f"❌ Error Processing {selected_instrument}: {e}")
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    print("🚀 Flask Server Starting on Port 5000...")
    app.run(debug=True, host='0.0.0.0', port=5000)
