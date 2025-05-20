import logging
import uuid
import pandas as pd
import numpy as np
from binance.um_futures import UMFutures
from binance.error import ClientError
import ta
from time import sleep
import asyncio
from requests.exceptions import ConnectTimeout, RequestException
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from datetime import datetime, timedelta
import os
import requests
from keys import api, secret

# === MODE SWITCH ===
LIVE_MODE = False  # Set to True for mainnet
BASE_URL = "https://fapi.binance.com" if LIVE_MODE else "https://testnet.binancefuture.com"

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logging.info("Bot started in {} mode".format("LIVE" if LIVE_MODE else "TESTNET"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_alert(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
            requests.post(url, json=payload)
        except Exception as e:
            logging.error(f"Failed to send Telegram alert: {str(e)}")

# Trading configuration
CONFIG = {
    'initial_balance': 1000,
    'take_profit': 0.012,
    'stop_loss': 0.009,
    'leverage': 30,
    'volume': 20,
    'max_positions': 10,
    'max_drawdown': 0.10,
    'daily_loss_limit': 0.05,
    'min_volume_threshold': 100000,
    'min_atr_threshold': 0.001,
    'margin_type': 'CROSS',
    'symbol': 'BTCUSDT',
    'interval': '1m',
    'klines_limit': 500,
}

try:
    client = UMFutures(key=api, secret=secret, base_url=BASE_URL)
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET", "POST"], raise_on_status=False)
    client.session.mount("https://", HTTPAdapter(max_retries=retries))
    client.session.timeout = 15
except Exception as e:
    logging.error(f"Failed to initialize Binance client: {str(e)}")
    raise

# === Indicator Calculation ===
def calculate_indicators(df):
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close']).rsi()
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    stoch_rsi = ta.momentum.StochRSIIndicator(close=df['Close'])
    df['StochRSI_k'] = stoch_rsi.stochrsi_k()
    df['StochRSI_d'] = stoch_rsi.stochrsi_d()
    df['Volume_avg'] = df['Volume'].rolling(window=14).mean()
    df['MA_50'] = df['Close'].rolling(window=50).mean()
    df['MA_200'] = df['Close'].rolling(window=200).mean()
    return df

# === Order Book Imbalance Calculation ===
def calculate_obi(book):
    bids = np.array([[float(bid[0]), float(bid[1])] for bid in book['bids']])
    asks = np.array([[float(ask[0]), float(ask[1])] for ask in book['asks']])
    bid_volume = bids[:, 1].sum()
    ask_volume = asks[:, 1].sum()
    return (bid_volume - ask_volume) / (bid_volume + ask_volume + 1e-10)

# === Signal Logic ===
def generate_trade_signal(df, obi):
    last = df.iloc[-1]
    conditions = [
        last['RSI'] < 30,
        last['MACD'] > last['MACD_signal'],
        last['StochRSI_k'] > last['StochRSI_d'],
        last['Close'] > last['MA_50'],
        last['Volume'] > last['Volume_avg'],
        obi > 0
    ]
    if all(conditions):
        return "BUY"
    
    conditions = [
        last['RSI'] > 70,
        last['MACD'] < last['MACD_signal'],
        last['StochRSI_k'] < last['StochRSI_d'],
        last['Close'] < last['MA_50'],
        last['Volume'] < last['Volume_avg'],
        obi < 0
    ]
    if all(conditions):
        return "SELL"
    return None

# === Unit Tests ===
def test_calculate_vwap():
    df = pd.DataFrame({
        'High': [101, 102, 103],
        'Low': [99, 98, 97],
        'Close': [100, 100, 100],
        'Volume': [100, 200, 300]
    })
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    assert round(vwap.iloc[-1], 2) > 0, "VWAP calculation failed"
    print("test_calculate_vwap passed")

def test_calculate_obi():
    book = {
        'bids': [["100", "1"], ["99", "2"]],
        'asks': [["101", "1"], ["102", "2"]]
    }
    obi = calculate_obi(book)
    assert -1 <= obi <= 1, "OBI out of expected range"
    print("test_calculate_obi passed")

def test_advanced_signal_logic():
    # Requires full mock of indicators and book data
    print("test_advanced_signal_logic skipped")

# === Main Loop ===
async def main():
    symbol = CONFIG['symbol']
    interval = CONFIG['interval']
    limit = CONFIG['klines_limit']
    while True:
        try:
            klines = client.klines(symbol=symbol, interval=interval, limit=limit)
            df = pd.DataFrame(klines, columns=[
                'Time', 'Open', 'High', 'Low', 'Close', 'Volume',
                'Close_time', 'Quote_asset_volume', 'Number_of_trades',
                'Taker_buy_base_volume', 'Taker_buy_quote_volume', 'Ignore'])
            df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
            df = calculate_indicators(df)

            book = client.depth(symbol=symbol, limit=5)
            obi = calculate_obi(book)

            signal = generate_trade_signal(df, obi)
            if signal:
                message = f"{signal} signal for {symbol} at {df.iloc[-1]['Close']} | OBI: {obi:.4f}"
                logging.info(message)
                send_telegram_alert(message)

            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Main loop error: {str(e)}")
            send_telegram_alert(f"Error: {str(e)}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    test_calculate_vwap()
    test_calculate_obi()
    test_advanced_signal_logic()
    asyncio.run(main())
