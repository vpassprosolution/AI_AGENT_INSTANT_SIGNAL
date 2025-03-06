import requests
import yfinance as yf
import technical_analysis  # Import technical functions
from flask import Flask, jsonify
import os

app = Flask(__name__)

# Home Route to check if API is running
@app.route('/')
def home():
    return jsonify({"message": "AI Agent Instant Signal API is running!"})

# Function to fetch real-time price for each instrument
def get_crypto_price(symbol):
    # Convert symbol to Yahoo Finance format
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

import requests

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
    print(f"📡 Receiving Instrument: {selected_instrument}")  # ✅ Debug log

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
    elif selected_instrument in ["XAU", "XAUUSD"]:  # ✅ Ensure "XAUUSD" is correctly mapped
        print("🟡 Gold selected, fetching price...")  # ✅ Debug
        price = get_gold_price()
        print(f"✅ Gold Price Fetched: {price}")  # ✅ Debug

    if price is None:
        print(f"⚠️ No price found for {selected_instrument}!")  # ✅ Debug
        return "⚠️ No valid data available."

    print(f"✅ Final Price Used in Signal Calculation: {price}")  # ✅ Debug

    # ✅ Now passing Gold price correctly to technical indicators
    return f"Current {selected_instrument} price: {price}"



# API endpoint for trade signal
@app.route('/get_signal/<string:selected_instrument>', methods=['GET'])
def get_signal(selected_instrument):
    trade_signal = generate_trade_signal(selected_instrument)

    return jsonify({"instrument": selected_instrument, "signal": trade_signal})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Read PORT from environment variables
    app.run(host='0.0.0.0', port=port)
