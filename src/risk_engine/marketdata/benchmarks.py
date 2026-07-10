"""Reference market-data mappings used by the pricing stack.

The toy curve is intentionally small so the first demo stays readable.
The full Treasury curve is here for later once we want a broader shape.
"""

TOY_TREASURY_CURVE_SERIES: dict[str, str] = {
    "2Y": "DGS2",
    "10Y": "DGS10",
}

DEFAULT_TREASURY_CURVE_SERIES: dict[str, str] = {
    "1M": "DGS1MO",
    "3M": "DGS3MO",
    "6M": "DGS6MO",
    "1Y": "DGS1",
    "2Y": "DGS2",
    "3Y": "DGS3",
    "5Y": "DGS5",
    "7Y": "DGS7",
    "10Y": "DGS10",
    "20Y": "DGS20",
    "30Y": "DGS30",
}
