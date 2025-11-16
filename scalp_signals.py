import requests
from datetime import datetime
import math

BINANCE_URL = "https://api.binance.com"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
INTERVAL = "1m"     # таймфрейм
LIMIT = 200         # сколько свечей брать (для индикаторов)

# настройки стратегии
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9


def get_klines(symbol: str, interval: str = INTERVAL, limit: int = LIMIT):
    """Получаем свечи с Binance. Возвращаем список закрытий."""
    url = f"{BINANCE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    closes = [float(candle[4]) for candle in data]  # close price = index 4
    return closes


def ema(values, period):
    """Простая EMA без сторонних библиотек."""
    if len(values) < period:
        return None

    k = 2 / (period + 1)
    ema_val = sum(values[:period]) / period  # SMA старт

    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)

    return ema_val


def rsi(values, period=RSI_PERIOD):
    """RSI по классической формуле."""
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-diff)

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = diff if diff > 0 else 0.0
        loss = -diff if diff < 0 else 0.0

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values, fast=MACD_FAST, slow=MACD_SLOW, signal_period=MACD_SIGNAL):
    """MACD: возвращаем (macd_line, signal_line, hist)."""
    if len(values) < slow + signal_period:
        return None, None, None

    ema_fast_val = ema(values, fast)
    ema_slow_val = ema(values, slow)

    if ema_fast_val is None or ema_slow_val is None:
        return None, None, None

    macd_line = ema_fast_val - ema_slow_val

    # грубая оценка signal: считаем MACD на последних (slow + signal_period*2) свечах
    macd_series = []
    for i in range(len(values) - (slow + signal_period * 2), len(values)):
        chunk = values[: i + 1]
        ef = ema(chunk, fast)
        es = ema(chunk, slow)
        if ef is not None and es is not None:
            macd_series.append(ef - es)

    if len(macd_series) < signal_period:
        return macd_line, None, None

    signal_line = ema(macd_series, signal_period)
    hist = macd_line - signal_line if signal_line is not None else None

    return macd_line, signal_line, hist


def define_trend(close_prices):
    """Определяем тренд по EMA 50/200."""
    ema_fast_trend = ema(close_prices, 50)
    ema_slow_trend = ema(close_prices, 200)

    if ema_fast_trend is None or ema_slow_trend is None:
        return "SIDE"

    if ema_fast_trend > ema_slow_trend * 1.001:
        return "UP"
    elif ema_fast_trend < ema_slow_trend * 0.999:
        return "DOWN"
    else:
        return "SIDE"


def build_levels(direction, price):
    """Считаем SL / TP для LONG/SHORT."""
    if direction == "LONG":
        sl = price * 0.995    # -0.5%
        tp1 = price * 1.003   # +0.3%
        tp2 = price * 1.006   # +0.6%
    else:
        sl = price * 1.005    # +0.5% против нас
        tp1 = price * 0.997   # -0.3%
        tp2 = price * 0.994   # -0.6%

    # округление до разумного количества знаков
    def rnd(x):
        # если цена большая — меньше знаков
        if x > 1000:
            return round(x, 2)
        elif x > 100:
            return round(x, 3)
        else:
            return round(x, 4)

    return rnd(sl), rnd(tp1), rnd(tp2)


def generate_signal_for_symbol(symbol):
    closes = get_klines(symbol)
    last_price = closes[-1]

    trend = define_trend(closes)
    rsi_val = rsi(closes)
    macd_line, signal_line, hist = macd(closes)

    if rsi_val is None or macd_line is None or signal_line is None or hist is None:
        return None  # данных мало

    direction = None

    # Условия для LONG
    if (
        trend == "UP"
        and 40 <= rsi_val <= 65
        and macd_line > signal_line
        and hist > 0
    ):
        direction = "LONG"

    # Условия для SHORT
    if (
        trend == "DOWN"
        and 35 <= rsi_val <= 60
        and macd_line < signal_line
        and hist < 0
    ):
        direction = "SHORT"

    if direction is None:
        return None

    sl, tp1, tp2 = build_levels(direction, last_price)

    # простое плечо и объём, можешь поменять как хочешь
    leverage = 20 if symbol in ("BTCUSDT", "ETHUSDT") else 10
    vol_mult = 4

    sig = {
        "symbol": symbol,
        "direction": direction,
        "entry": last_price,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "leverage": leverage,
        "trend": trend,
        "rsi": round(rsi_val, 2),
        "macd": round(hist, 4),  # гистограмма — сила сигнала
        "vol_mult": vol_mult,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return sig


def generate_signals():
    """
    Главная функция, которую вызывает bot.py
    Возвращает список сигналов (0, 1 или несколько).
    """
    signals = []
    for symbol in SYMBOLS:
        try:
            sig = generate_signal_for_symbol(symbol)
            if sig:
                signals.append(sig)
        except Exception as e:
            # чтобы ошибка по одному символу не завалила весь бот
            print(f"Error while generating signal for {symbol}: {e}")

    return signals