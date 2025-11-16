import random
import time
from datetime import datetime

def generate_signals():
    """
    Генерирует тестовые сигналы, чтобы бот всегда работал.
    Здесь можно подключить реальную логику позже.
    """

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    directions = ["LONG", "SHORT"]

    signals = []

    # делаем случайно: будет 1 сигнал или 0
    if random.random() < 0.7:
        symbol = random.choice(symbols)
        direction = random.choice(directions)

        entry = round(random.uniform(100, 60000), 2)
        sl = round(entry * (0.99 if direction == "LONG" else 1.01), 2)
        tp1 = round(entry * (1.01 if direction == "LONG" else 0.99), 2)
        tp2 = round(entry * (1.02 if direction == "LONG" else 0.98), 2)

        leverage = random.choice([10, 15, 20, 25])
        trend = random.choice(["UP", "DOWN", "SIDE"])
        rsi = random.randint(20, 80)
        macd = random.uniform(-5, 5)
        vol_mult = random.randint(1, 5)

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "leverage": leverage,
            "trend": trend,
            "rsi": rsi,
            "macd": macd,
            "vol_mult": vol_mult,
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })

    return signals