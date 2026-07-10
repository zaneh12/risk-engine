# Risk Engine

Practice project for building a fixed-income risk engine in Python.

## Layout

- `src/risk_engine/instruments`: instrument definitions such as bonds, treasuries, and swaps
- `src/risk_engine/services`: pricing and risk services such as price, risk, and DV01
- `src/risk_engine/marketdata`: curves, rates, and other market data objects
- `src/risk_engine/frontend`: GUI or other presentation layer code

## Philosophy

This repo is being built with a "why you need it" approach:

- start with the smallest useful abstraction
- keep modules narrow and named after the business concept
- make extension easy without over-engineering early

