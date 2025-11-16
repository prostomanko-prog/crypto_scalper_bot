import os
import time
import telegram
from scalp_signals import generate_signals

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telegram.Bot(token=TOKEN)

def send_signal(sig):
    text = (
        f"⚡ SCALP SIGNAL\n\n"
        f"Монета: {sig['symbol']}\n"
        f"Направление: {sig['direction']}\n\n"
        f"Вход: {sig['entry']}\n"
        f"SL: {sig['sl']}\n"
        f"TP1: {sig['tp1']}\n"
        f"TP2: {sig['tp2']}\n\n"
        f"Плечо: x{sig['leverage']}\n"
        f"Тренд (5m): {sig['trend']}\n"
        f"RSI: {sig['rsi']}\n"
        f"MACD: {sig['macd']}\n"
        f"Объём: x{sig['vol_mult']}\n"
        f"Время: {sig['time']}"
    )
    bot.send_message(chat_id=CHAT_ID, text=text)

def main():
    sent = set()

    while True:
        signals = generate_signals()

        for sig in signals:
            key = f"{sig['symbol']}-{sig['time']}"
            if key not in sent:
                send_signal(sig)
                sent.add(key)

        time.sleep(20)

if __name__ == "__main__":
    main()
