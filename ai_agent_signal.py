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
    url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": "your_coinmarketcap_api_key"}
    params = {"symbol": symbol, "convert": "USD"}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    if "data" in data and symbol in data["data"]:
        return round(data["data"][symbol]["quote"]["USD"]["price"], 2)
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
    url = "https://metals-api.com/api/latest?access_key=your_metal_api_key&base=USD&symbols=XAU"
    response = requests.get(url)
    data = response.json()
    
    if "rates" in data and "USDXAU" in data["rates"]:
        return round(data["rates"]["USDXAU"], 2)
    return None

# Function to generate trade signal (calls `technical_analysis.py`)
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
    elif selected_instrument == "XAU":
        price = get_gold_price()
    else:
        return "⚠️ No valid instrument selected."

    if price is None:
        return "⚠️ No valid data available."

    # Example price data (using real-time price in a dummy dataset)
    test_prices = [price] * 30

    # Call technical analysis functions
    rsi = technical_analysis.calculate_rsi(test_prices)
    macd, signal_line = technical_analysis.calculate_macd(test_prices)
    upper_band, middle_band, lower_band = technical_analysis.calculate_bollinger_bands(test_prices)

    # Generate trade signal based on indicators
    trade_signal = technical_analysis.generate_trade_signal(rsi, macd, signal_line, price, upper_band, lower_band)

    return trade_signal

# API endpoint for trade signal
@app.route('/get_signal/<string:selected_instrument>', methods=['GET'])
def get_signal(selected_instrument):
    trade_signal = generate_trade_signal(selected_instrument)

    return jsonify({"instrument": selected_instrument, "signal": trade_signal})



if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Read PORT from environment variables
    app.run(host='0.0.0.0', port=port)

