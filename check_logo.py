import yfinance as yf

for ticker in ['HDFCBANK.NS', 'WIPRO.NS', 'AAPL']:
    try:
        info = yf.Ticker(ticker).info
        print(f"--- {ticker} ---")
        print("Website:", info.get('website'))
        print("Logo URL:", info.get('logo_url'))
    except Exception as e:
        print(f"Error for {ticker}: {e}")
