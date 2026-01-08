import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os

BITGET_API = "https://api.bitget.com/api/v2/mix/market/candles"

def get_candles(symbol: str):
    coin = symbol.replace("USDT", "")
    params = {
        "symbol": coin,
        "productType": "USDT-FUTURES",
        "granularity": "900",
        "limit": "96"
    }
    try:
        r = requests.get(BITGET_API, params=params, timeout=10)
        data = r.json()
        if data.get("code") != "00000":
            return None
        return data["data"][::-1]
    except:
        return None

def calculate_atr(candles):
    tr = []
    for i in range(1, len(candles)):
        high = float(candles[i][2])
        low = float(candles[i][3])
        prev_close = float(candles[i-1][4])
        tr.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return sum(tr) / len(tr) if len(tr) > 0 else 0

def calculate_ema(values, period):
    if len(values) < period:
        return values[-1]
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
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
    if not candles or len(candles) < 2:
        return None

    closes = [float(c[4]) for c in candles]
    atr = calculate_atr(candles)
    ema7 = calculate_ema(closes, 7)
    ema25 = calculate_ema(closes, 25)
    rsi = calculate_rsi(closes, 14)

    trend = "UP" if ema7 > ema25 else "DOWN"
    strong_trend = abs(ema7 - ema25) > atr * 0.4

    price = closes[-1]
    entry = round(price * 0.997, 6)
    tp = round(entry * 1.027, 6)
    sl = round(entry * 0.965, 6)

    if trend == "UP" and rsi < 42 and strong_trend:
        signal = "BUY"
        confidence = 78 + (42 - rsi)
    elif trend == "DOWN" and rsi > 58 and strong_trend:
        signal = "SELL"
        confidence = 75 + (rsi - 58)
    else:
        signal = "WAIT"
        confidence = 55

    confidence = min(max(confidence, 50), 95)

    return {
        "symbol": symbol,
        "price": price,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "trend": "Восходящий" if trend=="UP" else "Нисходящий",
        "atr": round(atr, 6),
        "rsi": round(rsi, 2),
        "strongTrend": strong_trend,
        "signal": signal,
        "confidence": round(confidence, 2)
    }

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет, Bekzod! Отправь монету для анализа, например:\nSOLUSDT, ARBUSDT, OPUSDT"
    )

async def handle_message(update: Update, context: CallbackContext):
    symbol = update.message.text.upper().strip()
    result = analyze(symbol)

    if not result:
        await update.message.reply_text(f"⚠️ Ошибка анализа для {symbol}\nПроверь символ и попробуй снова.")
        return

    msg = (
        f"💎 {symbol} — Анализ трейдера\n\n"
        f"💰 Текущая цена: {result['price']} USDT\n"
        f"📌 Entry: {result['entry']}\n"
        f"🎯 TP (+2.7%): {result['tp']}\n"
        f"🛑 SL (−3.5%): {result['sl']}\n\n"
        f"📊 Trend: {result['trend']}\n"
        f"⚡️ Strong Trend: {result['strongTrend']}\n"
        f"🔥 RSI14: {result['rsi']}\n"
        f"📐 ATR: {result['atr']}\n\n"
        f"🚦 Signal: {result['signal']}\n"
        f"📈 Уверенность: {result['confidence']}%"
    )

    await update.message.reply_text(msg)

def main():
    if not TELEGRAM_TOKEN:
        print("❌ Ошибка: TELEGRAM_TOKEN не установлен в переменных окружения!")
        returnapp = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
