# Risk Engine

Fixed-income pricing and risk engine in Python.

## Overview

This repository implements the core building blocks of a fixed-income analytics stack:

- market data ingestion from FRED Treasury series
- curve construction and interpolation
- bond pricing from discounted cash flows
- curve visualization for analysis and review

The code is organized to separate market data, instrument models, analytics services, and presentation logic. That makes it straightforward to extend the engine from a local prototype into a service-backed application later.

## What It Demonstrates

The current implementation covers a minimal but realistic workflow:

1. pull Treasury curve data from FRED
2. build a `YieldCurve` object from tenor/rate points
3. interpolate spot rates across the curve
4. price a plain fixed-rate bond
5. visualize the curve with a dashboard-style plot

## Core Math

The bond pricer uses standard discounted cash-flow logic:

```text
Price = sum_{t=1..N} CF_t / (1 + r_t)^t
```

Where:

- `CF_t` is the cash flow at time `t`
- `r_t` is the curve-implied spot rate for that maturity
- `N` is the final payment period

Curve values are interpolated between known tenors using linear interpolation:

```text
r(x) = r_1 + (x - x_1) / (x_2 - x_1) * (r_2 - r_1)
```

This is intentionally simple for the first version. It is a good baseline for learning, testing, and later replacing with a more sophisticated curve framework if needed.

## Architecture

```text
src/risk_engine/
  instruments/   # fixed-income instrument models
  marketdata/    # curve models, benchmark series, source adapters
  services/      # pricing, risk, and DV01 logic
  frontend/      # plotting and presentation utilities
```

`main.py` is the working entry point used for local development, smoke tests, and quick experiments.

## Current Instrument Coverage

- Fixed-rate bond
- Treasury curve from FRED

## Current Analytics

- curve interpolation
- bond pricing
- spread calculation on the demo curve

## Run It

Set a local FRED API key in `.env`:

```env
FRED_API_KEY=your_key_here
```

Then run:

```bash
python main.py
```

The demo loads Treasury data, prints a curve summary, prices a sample bond, and opens the curve plot.

## Design Principles

- Keep domain models small and explicit.
- Separate market data, pricing logic, and visualization.
- Start with the simplest implementation that can still be extended cleanly.
- Favor readable code over abstraction for its own sake.

## Next Steps

- add clean price vs. dirty price
- add DV01 for bonds and curve shifts
- support semiannual coupon bonds and day-count conventions
- expose the engine through an API layer for a future web application

