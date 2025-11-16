import time
import os
import telebot
from scalp_signals import generate_signals

# Берём токен и чат из переменных окружения Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("ERROR: TELEGRAM_TOKEN или CHAT_ID не заданы в переменных окружения!")
    raise SystemExit(1)

bot = telebot.TeleBot(TOKEN)

# здесь храним уже отправленные сигналы, чтобы не дублировать
sent = set()

def send_signal(sig: dict):
    msg = (
        f"⚡ SCALP x20 SIGNAL\n\n"
        f"Монета: {sig['symbol']}\n"
        f"Сторона: {sig['direction']}\n"
        f"Вход: {sig['entry']}\n"
        f"SL: {sig['sl']}\n"
        f"TP1: {sig['tp1']}\n"
        f"TP2: {sig['tp2']}\n"
        f"Плечо: {sig['leverage']}\n"
        f"Тренд: {sig['trend']}\n"
        f"RSI: {sig['rsi']}\n"
        f"MACD: {sig['macd']}\n"
        f"Объём: x{sig['vol_mult']}\n"
        f"Время: {sig['time']}\n"
    )

    print(f"Sending signal: {sig['symbol']} {sig['direction']} {sig['entry']}")
    bot.send_message(CHAT_ID, msg)


print("Bot started and running...")

while True:
    try:
        print("Checking signals...")
        signals = generate_signals()
        print(f"Signals found: {len(signals)}")

        for sig in signals:
            key = f"{sig['symbol']}_{sig['time']}"
            if key not in sent:
                send_signal(sig)
                sent.add(key)

    except Exception as e:
        # чтобы бот не падал от одной ошибки
        print(f"Error in main loop: {e}")

    # пауза, чтобы не долбить Binance и не ловить бан
    time.sleep(60)   # 60 секунд, можешь сделать 120