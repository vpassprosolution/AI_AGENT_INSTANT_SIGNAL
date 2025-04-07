import asyncio
import websockets
import json
import time
import redis
import os

# ✅ Debug start
print("⚙️ websocket.py starting...")

# ✅ Redis connection (from Railway env var)
redis_url = os.environ.get("REDIS_URL")
if not redis_url:
    print("❌ REDIS_URL not found in environment!")
    exit(1)

redis_client = redis.StrictRedis.from_url(redis_url, decode_responses=True)
print("✅ Connected to Redis")

# ✅ TradingView credentials
SESSION_ID = os.environ.get("TV_SESSION_ID")
SESSION_SIGN = os.environ.get("TV_SESSION_SIGN")

if not SESSION_ID or not SESSION_SIGN:
    print("❌ TradingView session ID or sign missing!")
    exit(1)

print("✅ TradingView Session loaded")

# ✅ Constants
SYMBOL = "XAUUSD"
INTERVAL = 60  # 1-minute tick
CANDLE_GROUP = 5
REDIS_KEY = f"candle:{SYMBOL}:M5"
MAX_CANDLES = 30

tick_buffer = []

# ✅ Payload to subscribe WebSocket
def get_subscribe_payload():
    session = f"qs_{int(time.time() * 1000)}"
    return [
        {"m": "set_auth_token", "p": ["unauthorized_user_token"]},
        {"m": "chart_create_session", "p": [session, SESSION_ID]},
        {"m": "quote_create_session", "p": ["qs_1"]},
        {"m": "quote_add_symbols", "p": ["qs_1", f"{SYMBOL}"]},
        {"m": "resolve_symbol", "p": [session, "s1", f"={SYMBOL}"]},
        {"m": "create_series", "p": [session, "s1", "s1", "1", 300]}
    ]

# ✅ Convert tick buffer to OHLC
def convert_to_ohlc(ticks):
    if not ticks:
        return None
    return {
        "time": int(time.time()),
        "open": ticks[0],
        "high": max(ticks),
        "low": min(ticks),
        "close": ticks[-1]
    }

# ✅ Save to Redis
def save_to_redis(candle):
    candles = redis_client.get(REDIS_KEY)
    if candles:
        candles = json.loads(candles)
    else:
        candles = []

    candles.append(candle)
    if len(candles) > MAX_CANDLES:
        candles = candles[-MAX_CANDLES:]

    redis_client.set(REDIS_KEY, json.dumps(candles))
    print(f"✅ Saved candle to Redis | Total: {len(candles)}")

# ✅ Main WebSocket loop
async def tv_listener():
    print("📡 Connecting to TradingView WebSocket...")
    url = f"wss://data.tradingview.com/socket.io/websocket?session={SESSION_ID}&sign={SESSION_SIGN}"

    async with websockets.connect(url) as ws:
        print("✅ WebSocket connected")
        payloads = get_subscribe_payload()
        for item in payloads:
            await ws.send(json.dumps(item))

        last_group_time = time.time()

        async for message in ws:
            if "~m~" in message:
                parts = message.split("~m~")
                for part in parts:
                    if "s1" in part and "lp" in part:
                        try:
                            data_json = json.loads(part.split("~j~")[-1])
                            if "p" in data_json and "lp" in data_json["p"]:
                                price = float(data_json["p"]["lp"])
                                tick_buffer.append(price)

                                if time.time() - last_group_time >= INTERVAL * CANDLE_GROUP:
                                    candle = convert_to_ohlc(tick_buffer)
                                    if candle:
                                        save_to_redis(candle)
                                    tick_buffer.clear()
                                    last_group_time = time.time()
                        except Exception as e:
                            print(f"⚠️ Tick parsing error: {e}")

if __name__ == '__main__':
    print("🚀 Launching WebSocket listener...")
    asyncio.run(tv_listener())
