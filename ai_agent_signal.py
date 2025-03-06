import requests
import yfinance as yf
import technical_analysis  # Import technical functions
from flask import Flask, jsonify
import os
import numpy as np
from flask import Flask, jsonify

app = Flask(__name__)

# Home Route to check if API is running
@app.route('/')
def home():
    return jsonify({"message": "AI Agent Instant Signal API is running!"})

# Function to fetch real-time price for each instrument
def get_crypto_price(symbol):
    symbol_map = {"BTC": "BTC-USD", "ETH": "ETH-USD"}
    yahoo_symbol = symbol_map.get(symbol, None)

    if yahoo_symbol:
        data = yf.Ticker(yahoo_symbol).history(period="1d")
        if not data.empty:
            return round(data["Close"].iloc[-1], 2)

    print(f"❌ No price found for {symbol} using Yahoo Finance")
    return None

def get_forex_price(pair):
    symbol = f"{pair[:3]}{pair[3:]}=X"
    data = yf.Ticker(symbol).history(period="1d")
    
    if not data.empty:
        return round(data["Close"].iloc[-1], 4)
    return None

def get_stock_index_price(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="1d")
    
    if not data.empty:
        return round(data["Close"].iloc[-1], 2)
    return None

def get_gold_price():
    url = "https://metals-api.com/api/latest?access_key=cflqymfx6mzfe1pw3p4zgy13w9gj12z4aavokqd5xw4p8xeplzlwyh64fvrv&base=USD&symbols=XAU"
    response = requests.get(url)
    data = response.json()

    print("🔍 Metal API Response:", data)  

    if "rates" in data:
        if "USDXAU" in data["rates"]:  
            return round(data["rates"]["USDXAU"], 2)  
        elif "XAU" in data["rates"]:  
            return round(1 / data["rates"]["XAU"], 2)  

    print("⚠️ No Gold price found in API response!")
    return None

def generate_trade_signal(selected_instrument):
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
        return "⚠️ No valid data available."

    test_prices = [price] * 30  

    rsi = technical_analysis.calculate_rsi(test_prices)
    macd, signal_line = technical_analysis.calculate_macd(test_prices)
    upper_band, middle_band, lower_band = technical_analysis.calculate_bollinger_bands(test_prices)

    is_oversold = rsi < 30  
    is_overbought = rsi > 70  
    macd_cross_up = macd > signal_line  
    macd_cross_down = macd < signal_line  
    price_below_lower_band = price < lower_band  
    price_above_upper_band = price > upper_band  
    neutral_zone = 40 <= rsi <= 60  

    if is_oversold and (macd_cross_up or abs(macd - signal_line) < 0.2):  
        return "🚀 The market is heating up! 🔥 It's time to take action – **BUY now** before the move starts!"

    elif is_overbought and macd_cross_down:
        return "⚠️ Warning! Overbought conditions detected. 📉 **SELL now** before it's too late!"

    elif macd_cross_up and price < upper_band:
        return "📈 Momentum is shifting upwards! **A bullish crossover detected** – buyers are stepping in!"

    elif macd_cross_down and price > middle_band:
        return "📉 Bearish pressure is building! **A downward move is forming** – caution is advised!"

    elif neutral_zone:
        return "🧐 The market is in a tricky zone. No action needed for now – **HOLD your position.**"

    return "⚠️ No strong trade signal detected. Stay alert for market changes."




# API endpoint for trade signal
@app.route('/get_signal/<string:selected_instrument>', methods=['GET'])
def get_signal(selected_instrument):
    trade_signal = generate_trade_signal(selected_instrument)
    return jsonify({"instrument": selected_instrument, "signal": trade_signal})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  
    app.run(host='0.0.0.0', port=port)
