import requests
from datetime import datetime

# Binance US — НЕ блокирует Railway
BASE_URL = "https://api.binance.us"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

RSI_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
EMA_SIGNAL = 9


def get_klines(symbol, interval="1m", limit=200):
    """Загрузка свечей безопасно"""
    try:
        url = f"{BASE_URL}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        r = requests.get(url, params=params, timeout=7)
        data = r.json()
        return [float(x[4]) for x in data]  # close prices
    except Exception as e:
        print(f"Error fetching klines for {symbol}: {e}")
        return []


def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = sum(values[:period]) / period
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


def rsi(values, period=RSI_PERIOD):
    if len(values) < period + 2:
        return None

    gains, losses = [], []

    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-diff)

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = diff if diff > 0 else 0
        loss = -diff if diff < 0 else 0

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def macd(values):
    ef = ema(values, EMA_FAST)
    es = ema(values, EMA_SLOW)
    if ef is None or es is None:
        return None, None, None

    macd_line = ef - es

    # строим серию МАСД, чтобы брать сигнальную EMA
    macd_series = []
    for i in range(len(values)):
        ef_i = ema(values[: i + 1], EMA_FAST)
        es_i = ema(values[: i + 1], EMA_SLOW)
        if ef_i and es_i:
            macd_series.append(ef_i - es_i)

    if len(macd_series) < EMA_SIGNAL:
        return macd_line, None, None

    signal_line = ema(macd_series, EMA_SIGNAL)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def get_trend(values):
    ema50 = ema(values, 50)
    ema200 = ema(values, 200)
    if not ema50 or not ema200:
        return "SIDE"
    if ema50 > ema200:
        return "UP"
    if ema50 < ema200:
        return "DOWN"
    return "SIDE"


def levels(direction, price):
    if direction == "LONG":
        sl = price * 0.995
        tp1 = price * 1.003
        tp2 = price * 1.006
    else:
        sl = price * 1.005
        tp1 = price * 0.997
        tp2 = price * 0.994

    return round(sl, 2), round(tp1, 2), round(tp2, 2)


def analyze(symbol):
    closes = get_klines(symbol)
    if not closes:
        return None

    last = closes[-1]
    rsi_val = rsi(closes)
    macd_line, signal_line, hist = macd(closes)
    trend = get_trend(closes)

    if None in (rsi_val, macd_line, signal_line, hist):
        return None

    direction = None

    # Условия LONG
    if trend == "UP" and rsi_val > 40 and hist > 0 and macd_line > signal_line:
        direction = "LONG"

    # Условия SHORT
    if trend == "DOWN" and rsi_val < 60 and hist < 0 and macd_line < signal_line:
        direction = "SHORT"

    if not direction:
        return None

    sl, tp1, tp2 = levels(direction, last)

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": last,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "leverage": 20 if symbol in ["BTCUSDT", "ETHUSDT"] else 10,
        "trend": trend,
        "rsi": rsi_val,
        "macd": round(hist, 4),
        "vol_mult": 4,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_signals():
    final = []
    for s in SYMBOLS:
        try:
            sig = analyze(s)
            if sig:
                final.append(sig)
        except Exception as e:
            print(f"Signal error for {s}: {e}")
    return final