import time
import telebot
import os
from scalp_signals import generate_signals

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

sent = set()

def send_signal(sig):
    msg = (
        f"⚡ SCALP x20 SIGNAL\n\n"
        f"Монета: {sig['symbol']}\n"
        f"Сторона: {sig['direction']}\n\n"
        f"Вход: {sig['entry']}\n"
        f"SL: {sig['sl']}\n"
        f"TP1: {sig['tp1']}\n"
        f"TP2: {sig['tp2']}\n\n"
        f"Плечо: {sig['leverage']}\n"
        f"Тренд: {sig['trend']}\n"
        f"RSI: {sig['rsi']}\n"
        f"MACD: {sig['macd']}\n"
        f"Объём: x{sig['vol_mult']}\n"
        f"Время: {sig['time']}"
    )

    bot.send_message(CHAT_ID, msg)

while True:
    signals = generate_signals()

    for sig in signals:
        key = f"{sig['symbol']}_{sig['time']}"
        if key not in sent:
            send_signal(sig)
            sent.add(key)

    time.sleep(20)