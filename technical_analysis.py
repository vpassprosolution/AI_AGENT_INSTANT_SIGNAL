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
        return 0, 0  # Prevents NoneType errors
    
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
        estimated_price = prices[-1] if prices else 1000  # Default price to prevent NoneType errors
        return estimated_price * 1.05, estimated_price, estimated_price * 0.95

    bb_indicator = ta.volatility.BollingerBands(df["price"], window=window, window_dev=num_std)
    
    df = df.copy()  # Avoid chained assignment warnings
    df["upper_band"] = bb_indicator.bollinger_hband()
    df["lower_band"] = bb_indicator.bollinger_lband()
    df["middle_band"] = bb_indicator.bollinger_mavg()

    return df["upper_band"].iloc[-1], df["middle_band"].iloc[-1], df["lower_band"].iloc[-1]



# Aggressive decision logic for Buy/Sell/Hold
def generate_trade_signal(rsi, macd, signal_line, price, upper_band, lower_band):
    # Market conditions
    is_oversold = rsi < 30  # Buy when RSI is below 30 (stronger signal)
    is_overbought = rsi > 70  # Sell when RSI is above 70 (stronger signal)
    macd_cross_up = macd > signal_line  # Bullish MACD crossover
    macd_cross_down = macd < signal_line  # Bearish MACD crossover
    price_below_lower_band = price < lower_band
    price_above_upper_band = price > upper_band
    neutral_zone = 40 <= rsi <= 60  # No clear trend, neutral zone

    # ✅ Storyline-Based Trade Signals
    if is_oversold and macd_cross_up and price_below_lower_band:
        return "🚀 The market is heating up! 🔥 It's time to take action – **BUY now** before the move starts!"

    elif is_overbought and macd_cross_down and price_above_upper_band:
        return "⚠️ Warning! Overbought conditions detected. 📉 **SELL now** before it's too late!"

    elif macd_cross_up and price < middle_band:
        return "📈 Momentum is shifting upwards! **A bullish crossover detected** – buyers are stepping in!"

    elif macd_cross_down and price > middle_band:
        return "📉 Bearish pressure is building! **A downward move is forming** – caution is advised!"

    elif neutral_zone:
        return "🧐 The market is in a tricky zone. No action needed for now – **HOLD your position.**"

    else:
        return "⚠️ No strong trade signal detected. Stay alert for market changes."


