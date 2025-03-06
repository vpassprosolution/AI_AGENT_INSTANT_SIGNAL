import pandas as pd
import ta
import numpy as np

# Function to calculate RSI (Relative Strength Index)
def calculate_rsi(prices, period=14):
    df = pd.DataFrame(prices, columns=["price"])
    df["rsi"] = ta.momentum.RSIIndicator(df["price"], window=period).rsi()
    return df["rsi"].iloc[-1]  # ✅ Return the actual RSI value


 
# Function to calculate MACD (Moving Average Convergence Divergence)
import numpy as np

def calculate_macd(prices, short_window=12, long_window=26, signal_window=9):
    df = pd.DataFrame(prices, columns=["price"])
    
    if len(df) < long_window:
        return 0.01, 0.01  # ✅ Prevents NoneType errors

    macd_indicator = ta.trend.MACD(df["price"], window_slow=long_window, window_fast=short_window, window_sign=signal_window)
    
    df = df.copy()
    df["macd"] = macd_indicator.macd()
    df["signal"] = macd_indicator.macd_signal()

    # ✅ Correct way to replace NaN values in Pandas 3.0
    df["macd"] = df["macd"].fillna(0.01)
    df["signal"] = df["signal"].fillna(0.01)

    return df["macd"].iloc[-1], df["signal"].iloc[-1]  # ✅ Ensure valid values






# Function to calculate Bollinger Bands
def calculate_bollinger_bands(prices, window=20, num_std=2):
    df = pd.DataFrame(prices, columns=["price"])

    if len(df) < window:
        estimated_price = prices[-1] if prices else 1000  
        return estimated_price * 1.05, estimated_price, estimated_price * 0.95  # ✅ Add larger deviation

    bb_indicator = ta.volatility.BollingerBands(df["price"], window=window, window_dev=num_std)
    
    df = df.copy()
    df["upper_band"] = bb_indicator.bollinger_hband()
    df["lower_band"] = bb_indicator.bollinger_lband()
    df["middle_band"] = bb_indicator.bollinger_mavg()

    # ✅ Force volatility to create breakout signals
    if df["upper_band"].iloc[-1] - df["lower_band"].iloc[-1] < 1:
        df.loc[df.index[-1], "upper_band"] += 2  
        df.loc[df.index[-1], "lower_band"] -= 2  

    return df["upper_band"].iloc[-1], df["middle_band"].iloc[-1], df["lower_band"].iloc[-1]



# Aggressive decision logic for Buy/Sell/Hold
def generate_trade_signal(rsi, macd, signal_line, price, upper_band, middle_band, lower_band):
    print("🛠️ DEBUGGING TRADE SIGNAL GENERATION")  # ✅ Debug log
    print(f"📊 RSI: {rsi}")
    print(f"📈 MACD: {macd}, Signal Line: {signal_line}")
    print(f"📉 Bollinger Bands: Upper: {upper_band}, Middle: {middle_band}, Lower: {lower_band}")

    is_oversold = rsi < 30  
    is_overbought = rsi > 70  
    macd_cross_up = macd > signal_line  
    macd_cross_down = macd < signal_line  
    price_below_lower_band = price < lower_band  
    price_above_upper_band = price > upper_band  
    neutral_zone = 40 <= rsi <= 60  

    # ✅ Force Debugging
    print(f"🟢 Oversold: {is_oversold}, 🔴 Overbought: {is_overbought}")
    print(f"🔼 MACD Cross Up: {macd_cross_up}, 🔽 MACD Cross Down: {macd_cross_down}")
    print(f"📉 Price Below Lower Band: {price_below_lower_band}, 📈 Price Above Upper Band: {price_above_upper_band}")

    if is_oversold and (macd_cross_up or abs(macd - signal_line) < 0.2):  # ✅ Allow weak MACD cross up
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
