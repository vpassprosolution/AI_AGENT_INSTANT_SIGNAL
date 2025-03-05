import pandas as pd
import ta

# Function to calculate RSI (Relative Strength Index)
def calculate_rsi(prices, period=14):
    df = pd.DataFrame(prices, columns=["price"])  # Convert price list to DataFrame
    df["rsi"] = ta.momentum.RSIIndicator(df["price"], window=period).rsi()
    return df["rsi"].iloc[-1]  # Return the latest RSI value
 
# Function to calculate MACD (Moving Average Convergence Divergence)
def calculate_macd(prices, short_window=12, long_window=26, signal_window=9):
    df = pd.DataFrame(prices, columns=["price"])
    
    # Ensure we have enough data points
    if len(df) < long_window:
        return None, None  # Not enough data
    
    macd_indicator = ta.trend.MACD(df["price"], window_slow=long_window, window_fast=short_window, window_sign=signal_window)
    
    df = df.copy()  # Avoid chained assignment warnings
    df["macd"] = macd_indicator.macd()
    df["signal"] = macd_indicator.macd_signal()
    
    # Handle NaN values by replacing them properly
    df.loc[:, "macd"] = df["macd"].fillna(0)
    df.loc[:, "signal"] = df["signal"].fillna(0)

    return df["macd"].iloc[-1], df["signal"].iloc[-1]  # Return latest MACD & Signal Line values

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(prices, window=20, num_std=2):
    df = pd.DataFrame(prices, columns=["price"])

    # Ensure we have enough data points
    if len(df) < window:
        return None, None, None  # Not enough data
    
    bb_indicator = ta.volatility.BollingerBands(df["price"], window=window, window_dev=num_std)
    
    df = df.copy()  # Avoid chained assignment warnings
    df["upper_band"] = bb_indicator.bollinger_hband()
    df["lower_band"] = bb_indicator.bollinger_lband()
    df["middle_band"] = bb_indicator.bollinger_mavg()

    return df["upper_band"].iloc[-1], df["middle_band"].iloc[-1], df["lower_band"].iloc[-1]

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



