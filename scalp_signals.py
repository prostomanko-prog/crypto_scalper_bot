import requests
from datetime import datetime

# ЧТО отслеживаем
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

# соответствие тикеров CoinGecko
SYMBOL_MAP = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "XRPUSDT": "ripple"
}

COINGECKO_URL = "https://api.coingecko.com/api/v3"

RSI_PERIOD = 14
FAST = 12
SLOW = 26
SIGNAL = 9


def get_prices(symbol_id, minutes=200):
    """Берём исторические цены с CoinGecko, интервал ~1 мин."""
    try:
        url = f"{COINGECKO_URL}/coins/{symbol_id}/market_chart"
        params = {"vs_currency": "usd", "days": 1}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()["prices"]

        closes = [float(p[1]) for p in data][-minutes:]
        return closes

    except Exception as e:
        print(f"Error fetching prices for {symbol_id}: {e}")
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
    if len(values) < period + 1:
        return None

    gains, losses = [], []

    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains.append(diff if diff > 0 else 0)
        losses.append(-diff if diff < 0 else 0)

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100

    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def macd(values):
    ef = ema(values, FAST)
    es = ema(values, SLOW)
    if not ef or not es:
        return None, None, None

    macd_line = ef - es

    macd_series = []
    for i in range(len(values)):
        ef_i = ema(values[: i + 1], FAST)
        es_i = ema(values[: i + 1], SLOW)
        if ef_i and es_i:
            macd_series.append(ef_i - es_i)

    if len(macd_series) < SIGNAL:
        return macd_line, None, None

    signal_line = ema(macd_series, SIGNAL)
    hist = macd_line - signal_line
    return macd_line, signal_line, round(hist, 4)


def trend(values):
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
    symbol_id = SYMBOL_MAP[symbol]
    closes = get_prices(symbol_id)

    if len(closes) < 50:
        return None

    last = closes[-1]

    r = rsi(closes)
    m_line, s_line, hist = macd(closes)
    tr = trend(closes)

    if None in (r, m_line, s_line, hist):
        return None

    direction = None

    if tr == "UP" and r > 40 and hist > 0 and m_line > s_line:
        direction = "LONG"

    if tr == "DOWN" and r < 60 and hist < 0 and m_line < s_line:
        direction = "SHORT"

    if not direction:
        return None

    sl, tp1, tp2 = levels(direction, last)

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": round(last, 2),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "leverage": 20 if symbol in ["BTCUSDT", "ETHUSDT"] else 10,
        "trend": tr,
        "rsi": r,
        "macd": hist,
        "vol_mult": 4,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_signals():
    results = []
    for sym in SYMBOLS:
        try:
            sig = analyze(sym)
            if sig:
                results.append(sig)
        except Exception as e:
            print(f"Signal error for {sym}: {e}")
    return results