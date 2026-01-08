import requests
import math
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os

def get_candles(symbol: str):
    base = symbol.replace("USDT", "")
    url = "https://api.bitget.com/api/v2/mix/market/candles"
    params = {
        "symbol": base,
        "productType": "USDT-FUTURES",
        "granularity": "900",  # 15m
        "limit": "96"  # 96 свечей * 15m = 24 часа
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    if data.get("code") != "00000":
        return None
    return data["data"]

def calculate_atr(candles):
    tr_list = []
    for i in range(1, len(candles)):
        high = float(candles[i][2])
        low = float(candles[i][3])
        prev_close = float(candles[i-1][4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)
    return sum(tr_list) / len(tr_list)

def calculate_ema(values, period):
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema

def calculate_rsi(closes, period=14):
    gains, losses = 0, 0
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains += diff
        else:
            losses += abs(diff)
    avg_gain = gains / period
    avg_loss = losses / period if losses != 0 else 1
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def analyze(symbol: str):
    candles = get_candles(symbol)
    if not candles or len(candles) < 25:
        return None

    closes = [float(c[4]) for c in candles[::-1]]

    atr = round(calculate_atr([c for c in candles[::-1]]), 6)
    ema7 = round(calculate_ema(closes, 7), 6)
    ema25 = round(calculate_ema(closes, 25), 6)
    rsi = round(calculate_rsi(closes), 2)

    price = closes[-1]

    entry = round(price * 0.995, 6)
    tp = round(entry * 1.025, 6)
    sl = round(entry * 0.97, 6)

    if ema7 > ema25 and rsi < 40:
        signal = "BUY"
    elif ema7 < ema25 and rsi > 60:
        signal = "SELL"
    else:
        signal = "WAIT"

    return {
        "symbol": symbol,
        "price": price,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "atr": atr,
        "ema7": ema7,
        "ema25": ema25,
        "rsi": rsi,
        "signal": signal
    }

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Напиши монету, например: SOLUSDT или ARBUSDT")

async def handle_message(update: Update, context: CallbackContext):
    symbol = update.message.text.upper().strip()
    result = analyze(symbol)

    if not result:
        await update.message.reply_text(f"⚠ Ошибка анализа или данных недостаточно для {symbol}")
        return

    msg = (
        f"💎 {symbol} Анализ трейдера\n\n"
        f"💰 Текущая цена: {result['price']} USDT\n"
        f"📌 Вход (Entry): {result['entry']}\n"
        f"🎯 TP (+2.5%): {result['tp']}\n"
        f"🛑 SL (−3%): {result['sl']}\n\n"
        f"📊 EMA7: {result['ema7']} | EMA25: {result['ema25']}\n"
        f"📐 ATR: {result['atr']}\n"
        f"🔥 RSI14: {result['rsi']}\n\n"
        f"🚦 Сигнал: {result['signal']}"
    )

    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
