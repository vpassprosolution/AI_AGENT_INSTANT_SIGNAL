import requests
import pandas as pd
import ta
import yfinance as yf
import config
import technical_analysis  # Import AI signal logic

# Function to fetch real-time gold price from Metal API (USD per ounce)
def get_gold_price():
    url = f"https://metals-api.com/api/latest?access_key={config.METAL_API_KEY}&base=USD&symbols=XAU"
    response = requests.get(url)
    data = response.json()
    
    if "rates" in data and "USDXAU" in data["rates"]:  # Correct calculation
        return round(data["rates"]["USDXAU"], 2)  # USD per ounce of gold
    return None

# Function to fetch real-time Forex price from Yahoo Finance
def get_forex_price(pair):
    symbol = f"{pair[:3]}{pair[3:]}=X"  # Format like EURUSD=X for Yahoo Finance
    data = yf.Ticker(symbol).history(period="1d")
    
    if not data.empty:
        return round(data["Close"].iloc[-1], 4)  # Get the latest closing price
    return None

# Function to fetch real-time crypto price from CoinMarketCap API
def get_crypto_price(symbol):
    url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": config.COINMARKETCAP_API_KEY}
    params = {"symbol": symbol, "convert": "USD"}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    if "data" in data and symbol in data["data"]:
        return round(data["data"][symbol]["quote"]["USD"]["price"], 2)  # Price rounded to 2 decimals
    return None

# Function to fetch real-time stock index prices (Dow Jones, Nasdaq) from Yahoo Finance
def get_stock_index_price_yahoo(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="1d")
    
    if not data.empty:
        return round(data["Close"].iloc[-1], 2)  # Get the latest closing price
    return None

# Aggressive decision logic for Buy/Sell/Hold
def generate_trade_signal(rsi, macd, signal_line, price, upper_band, lower_band):
    # Market conditions
    is_oversold = rsi < 50  # Buy earlier when RSI is below 50 (less strict)
    is_overbought = rsi > 50  # Sell earlier when RSI is above 50 (less strict)
    macd_cross_up = macd > signal_line  # Bullish MACD crossover
    macd_cross_down = macd < signal_line  # Bearish MACD crossover
    price_below_lower_band = price < lower_band
    price_above_upper_band = price > upper_band
    neutral_zone = 40 <= rsi <= 60  # No clear trend, neutral zone

    # Aggressive trade decisions
    if is_oversold and macd_cross_up and price_below_lower_band:
        return "🚀 **AGGRESSIVE BUY Signal** - Market is oversold, MACD is bullish, and price is undervalued!"

    elif is_overbought and macd_cross_down and price_above_upper_band:
        return "⚠️ **AGGRESSIVE SELL Signal** - Market is overbought, MACD is bearish, and price is too high!"

    elif neutral_zone or (macd_cross_up and macd_cross_down):  # Mixed signals
        return "🤔 **HOLD Position** - No strong signal, market is in a neutral zone."

    else:
        return "⚠️ **NO TRADE** - Indicators do not align for a confident trade."

# Fetch and analyze real-time market data for the selected instrument
if __name__ == "__main__":
    # Let's assume the user selects the instrument (for now, use 'BTC' as an example)
    selected_instrument = "BTC"  # This would be set dynamically based on user input (e.g., through Telegram)

    # Print the selected instrument
    print(f"\nSelected Instrument: {selected_instrument}")

    # Fetch real-time data for the selected instrument
    if selected_instrument == "BTC":
        price = get_crypto_price("BTC")
        print(f"Bitcoin Price (BTC/USDT): {price}")
    elif selected_instrument == "ETH":
        price = get_crypto_price("ETH")
        print(f"Ethereum Price (ETH/USDT): {price}")
    elif selected_instrument == "EURUSD":
        price = get_forex_price("EURUSD")
        print(f"EUR/USD Exchange Rate: {price}")
    elif selected_instrument == "GBPUSD":
        price = get_forex_price("GBPUSD")
        print(f"GBP/USD Exchange Rate: {price}")
    elif selected_instrument == "DJI":
        price = get_stock_index_price_yahoo("^DJI")
        print(f"Dow Jones Index (DJI): {price}")
    elif selected_instrument == "IXIC":
        price = get_stock_index_price_yahoo("^IXIC")
        print(f"Nasdaq Index (IXIC): {price}")
    elif selected_instrument == "XAU":
        price = get_gold_price()
        print(f"Gold Price (XAU/USD): {price}")
    
    # AI SIGNAL PROCESSING for the selected instrument
    print("\n🔍 Analyzing market conditions...")

    # Example price data (this will now be real-time prices)
    test_prices = [price] * 30  # Just as an example, you can use the actual data over time for better analysis

    # Calculate indicators for the selected instrument
    rsi_value = technical_analysis.calculate_rsi(test_prices)
    macd_value, signal_value = technical_analysis.calculate_macd(test_prices)
    upper_band, middle_band, lower_band = technical_analysis.calculate_bollinger_bands(test_prices)
    
    # Assume the latest price is the last value in test_prices
    latest_price = test_prices[-1]

    # Generate trade signal
    trade_signal = technical_analysis.generate_trade_signal(
        rsi_value, macd_value, signal_value, latest_price, upper_band, lower_band
    )

    # Print the final trade signal for the selected instrument
    print(f"\nTrade Decision for {selected_instrument}: {trade_signal}")
