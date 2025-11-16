import requests
from datetime import datetime

# Монеты, которые скальпим
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Таймфреймы
TF_SMALL = "1m"   # вход (скальп)
TF_BIG = "5m"     # тренд

# Параметры под плечо x20
SL_PCT = 0.002     # 0.2%
TP1_PCT = 0.003    # 0.3%
TP2_PCT = 0.005    # 0.5%
LEVERAGE = 20

# Фильтр объёма
VOLUME_MULT = 1.4   # всплеск объёма

BASE_URL = "https://api.binance.com/api/v3/klines"


def get_klines(symbol: str, interval: str, limit: int = 200):
    url = f"{BASE_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()

    closes = [float(c[4]) for c in data]
    volumes = [float(c[5]) for c in data]

    return closes, volumes


def ema(values, period):
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def rsi(values, period=14):
    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(values) - 1):
        diff = values[i + 1] - values[i]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def macd(values):
    ema12 = ema(values, 12)
    ema26 = ema(values, 26)
    macd_line = ema12 - ema26
    signal_line = ema(values[-35:], 9)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def generate_signals():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    output = []

    for symbol in SYMBOLS:
        try:
            closes_s, volumes_s = get_klines(symbol, TF_SMALL, 150)
            closes_b, _ = get_klines(symbol, TF_BIG, 150)
        except:
            continue

        # Тренд 5m
        ema20_big = ema(closes_b, 20)
        ema50_big = ema(closes_b, 50)
        big_trend = "LONG" if ema20_big > ema50_big else "SHORT"

        ema9_prev = ema(closes_s[:-1], 9)
        ema20_prev = ema(closes_s[:-1], 20)
        ema9_curr = ema(closes_s, 9)
        ema20_curr = ema(closes_s, 20)

        rsi_val = rsi(closes_s, 14)
        if rsi_val is None:
            continue

        macd_line, signal_line, hist = macd(closes_s)

        avg_vol = sum(volumes_s[:-1]) / len(volumes_s[:-1])
        vol_ok = volumes_s[-1] > avg_vol * VOLUME_MULT

        price = closes_s[-1]
        direction = None

        # LONG
        if (
            big_trend == "LONG" and
            ema9_prev < ema20_prev and ema9_curr > ema20_curr and
            price > ema20_curr and
            52 < rsi_val < 80 and
            hist > 0 and macd_line > signal_line and
            vol_ok
        ):
            direction = "LONG"

        # SHORT
        if (
            big_trend == "SHORT" and
            ema9_prev > ema20_prev and ema9_curr < ema20_curr and
            price < ema20_curr and
            20 < rsi_val < 48 and
            hist < 0 and macd_line < signal_line and
            vol_ok
        ):
            direction = "SHORT"

        if direction is None:
            continue

        entry = price

        if direction == "LONG":
            sl = entry * (1 - SL_PCT)
            tp1 = entry * (1 + TP1_PCT)
            tp2 = entry * (1 + TP2_PCT)
        else:
            sl = entry * (1 + SL_PCT)
            tp1 = entry * (1 - TP1_PCT)
            tp2 = entry * (1 - TP2_PCT)

        output.append({
            "symbol": symbol,
            "direction": direction,
            "entry": round(entry, 4),
            "sl": round(sl, 4),
            "tp1": round(tp1, 4),
            "tp2": round(tp2, 4),
            "leverage": LEVERAGE,
            "rsi": round(rsi_val, 2),
            "macd": round(hist, 4),
            "vol_mult": round(volumes_s[-1] / avg_vol, 2),
            "trend": big_trend,
            "time": now
        })

    return output
