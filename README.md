# Risk Engine

Fixed-income risk engine in Python.

## Architecture

- `src/risk_engine/instruments`: fixed-income instrument models such as bonds, treasuries, and swaps
- `src/risk_engine/marketdata`: market-data models, benchmark curves, and source adapters
- `src/risk_engine/services`: pricing, risk, and DV01 analytics
- `src/risk_engine/frontend`: GUI and presentation layer code

## Market Data First

The first build target is market data.

For a fixed-income project, the best starting point is a free, official source that can support Treasury curve work quickly. FRED is a strong choice because its API is free, official, and designed for programmatic retrieval of series observations and historical data. The first implementation will target Treasury curve-style rates from FRED, with room to add additional sources later.

## Build Style

This repository is being built incrementally:

- start with the smallest useful abstraction
- keep modules narrow and named after the business concept
- make extension easy without over-engineering early

