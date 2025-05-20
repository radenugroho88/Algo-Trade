🧠 Summary of HFT Bot

*✅ Core Features*

'Live/Testnet Mode': Controlled via a LIVE_MODE switch with correct BASE_URL.

Exchange API: Uses Binance's UMFutures REST API with retry handling via urllib3 + HTTPAdapter.

Leverage Trading: Automatically sets up trades with leverage and a fixed volume per order.

Signal Generation:

Indicators used:

- RSI

- MACD & MACD Signal

- 20-period Moving Average

- Volume average (10-period)

- Order Book Imbalance (OBI) is used to improve trade signal reliability.

- Threshold-based logic determines if a BUY or SELL signal is valid.

*Order Execution:*

Places market orders on signal.

Automatically sets Take Profit (TP) and Stop Loss (SL) orders using TAKE_PROFIT_MARKET and STOP_MARKET.

Risk Controls:

Configurable stop loss, take profit, trailing stop (unused for now), leverage, volume, drawdown, and daily loss limits.

Real-Time Operation:

Uses asyncio loop for live trading every second (await asyncio.sleep(1)).

Signal Statistics Tracking:

Maintains a count of BUY, SELL, and NONE signals triggered for monitoring performance.

🧪 Tech Stack
Binance Futures API

Pandas for data manipulation

NumPy for numeric processing

TA-Lib (via ta) for indicator computation

Scipy (though norm is imported but unused)

Logging module for structured logging

Asyncio for non-blocking execution loop

Retry logic with requests for resilient network behavior

🚧 Incomplete or Unused Components
trailing_stop: Configured but not used.

min_volume_threshold & min_atr_threshold: Not yet implemented in signal logic.

scipy.stats.norm: Imported but unused (possibly for later enhancements like confidence intervals or Gaussian filters).

🎯 Bot Workflow (Simplified)
Fetch latest klines (1m and 1h).

Calculate indicators.

Fetch order book depth, calculate OBI.

Generate trading signal based on:

RSI level

MACD crossover

OBI threshold

If a valid signal:

Calculate position size.

Place a market order.

Set TP and SL orders.

Log all activity.

Wait 1 second and repeat.
