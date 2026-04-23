"""
fetch_data.py
-------------
Fetches stock price data using yfinance (free, no rate limits, recent data).

Strategy:
  - 25 symbols x 5 years of daily data = ~32,000 rows
  - Run once, takes < 2 minutes, no API key needed
  - Data is current up to today

Outputs:
  - data/raw_stock_prices.csv   (~32,000+ rows)
  - data/company_metadata.csv   (25 companies)

Run: .\\venv\\Scripts\\python.exe etl\\fetch_data.py
"""

import os
import yfinance as yf
import pandas as pd
from tqdm import tqdm

# ── Symbols: 80 stocks across 8 sectors (80 x 1255 rows = 100,400 rows) ─────
SYMBOLS = {
    "Technology":      ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "TSLA",
                        "AMD",  "INTC", "CRM",   "ORCL", "ADBE", "QCOM"],
    "Healthcare":      ["JNJ",  "PFE",  "UNH",  "ABBV", "MRK",
                        "TMO",  "ABT",  "DHR",  "BMY",  "AMGN"],
    "Finance":         ["JPM",  "BAC",  "GS",   "WFC",  "C",
                        "MS",   "BLK",  "SCHW", "AXP",  "USB"],
    "Energy":          ["XOM",  "CVX",  "SLB",  "COP",
                        "EOG",  "PXD",  "MPC",  "VLO"],
    "Consumer":        ["AMZN", "WMT",  "PG",   "KO",   "PEP",
                        "MCD",  "SBUX", "NKE",  "HD",   "LOW"],
    "Industrials":     ["CAT",  "BA",   "HON",  "UPS",  "LMT",
                        "RTX",  "DE",   "MMM",  "GE",   "EMR"],
    "Communication":   ["T",    "VZ",   "DIS",  "NFLX", "CMCSA"],
    "RealEstate":      ["AMT",  "PLD",  "CCI",  "EQIX", "SPG"],
    "Utilities":       ["NEE",  "DUK",  "SO",   "D",    "AEP",
                        "EXC",  "SRE",  "PCG",  "ED",   "ETR",  "AWK"],
}

# Flat list
ALL_SYMBOLS = [s for syms in SYMBOLS.values() for s in syms]

# Date range: 5 years of recent data (today minus 5 years)
PERIOD = "5y"   # yfinance period string: max / 5y / 2y / 1y


def fetch_prices():
    """Download OHLCV data for all symbols using yfinance bulk download."""
    print("\n[INFO] Downloading price data via yfinance...")
    print(f"   Symbols : {len(ALL_SYMBOLS)}")
    print(f"   Period  : {PERIOD} (up to today)")
    print(f"   Expected: ~{len(ALL_SYMBOLS) * 252 * 5:,} rows (5 yrs x 252 trading days)\n")

    # Bulk download - much faster than one-by-one
    raw = yf.download(
        tickers=ALL_SYMBOLS,
        period=PERIOD,
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        threads=True,
        progress=True,
    )

    # Reshape from wide multi-index format to long format
    all_rows = []
    for symbol in tqdm(ALL_SYMBOLS, desc="Reshaping data"):
        try:
            df = raw[symbol].copy()
            df = df.dropna(subset=["Close"])
            df = df.reset_index()
            df["symbol"] = symbol
            df = df.rename(columns={
                "Date":   "date",
                "Open":   "open",
                "High":   "high",
                "Low":    "low",
                "Close":  "close",
                "Volume": "volume",
                "Adj Close": "adj_close",
            })
            # Select and reorder columns
            df = df[["symbol", "date", "open", "high", "low", "close", "adj_close", "volume"]]
            all_rows.append(df)
        except Exception as e:
            print(f"  [WARN] {symbol}: {e}")

    price_df = pd.concat(all_rows, ignore_index=True)

    # Add derived columns
    price_df["price_change"]     = (price_df["close"] - price_df["open"]).round(4)
    price_df["daily_return_pct"] = ((price_df["close"] - price_df["open"]) / price_df["open"] * 100).round(4)
    price_df["high_low_spread"]  = (price_df["high"] - price_df["low"]).round(4)

    price_df = price_df.sort_values(["symbol", "date"]).reset_index(drop=True)

    return price_df


def fetch_metadata():
    """Fetch company info (sector, industry, exchange, etc.) via yfinance."""
    print("\n[INFO] Fetching company metadata...")

    rows = []
    for symbol in tqdm(ALL_SYMBOLS, desc="Fetching metadata"):
        try:
            info = yf.Ticker(symbol).info
            rows.append({
                "symbol":       symbol,
                "company_name": info.get("longName", ""),
                "exchange":     info.get("exchange", ""),
                "currency":     info.get("currency", "USD"),
                "country":      info.get("country", ""),
                "sector":       info.get("sector", ""),
                "industry":     info.get("industry", ""),
                "market_cap":   info.get("marketCap", None),
                "ipo_date":     info.get("ipoExpectedDate", ""),
                "website":      info.get("website", ""),
                "employees":    info.get("fullTimeEmployees", None),
                "description":  info.get("longBusinessSummary", "")[:300],
            })
            tqdm.write(f"  [OK] {symbol}: {info.get('longName', 'N/A')} | {info.get('sector', 'N/A')}")
        except Exception as e:
            tqdm.write(f"  [FAIL] {symbol}: {e}")

    return pd.DataFrame(rows)


def main():
    os.makedirs("data", exist_ok=True)

    # ── Phase 1: Prices ───────────────────────────────────────────────────────
    price_df = fetch_prices()
    price_df.to_csv("data/raw_stock_prices.csv", index=False)

    print(f"\n[SAVED] data/raw_stock_prices.csv")
    print(f"   Total rows   : {len(price_df):,}")
    print(f"   Symbols      : {price_df['symbol'].nunique()}")
    print(f"   Date range   : {price_df['date'].min().date()} -> {price_df['date'].max().date()}")

    if len(price_df) >= 100000:
        print(f"   [TARGET MET] 100K+ rows achieved!")
    else:
        print(f"   [NOTE] {len(price_df):,} rows. Will supplement with more symbols if needed.")

    # ── Phase 2: Metadata ─────────────────────────────────────────────────────
    meta_df = fetch_metadata()
    meta_df.to_csv("data/company_metadata.csv", index=False)

    print(f"\n[SAVED] data/company_metadata.csv")
    print(f"   Companies : {len(meta_df)}")
    print(f"\n   Sector breakdown:")
    for sector, count in meta_df["sector"].value_counts().items():
        print(f"     {sector}: {count} companies")

    print("\n[DONE] Data collection complete! Ready for ETL.")
    print("   Next step: run etl/load_dimensions.py")


if __name__ == "__main__":
    main()
