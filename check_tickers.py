import yfinance as yf

NIFTY_50_TICKERS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'BHARTIARTL.NS', 'SBIN.NS', 'INFY.NS', 
    'LICI.NS', 'ITC.NS', 'HINDUNILVR.NS', 'LT.NS', 'BAJFINANCE.NS', 'HCLTECH.NS', 'MARUTI.NS', 
    'SUNPHARMA.NS', 'ADANIENT.NS', 'KOTAKBANK.NS', 'TITAN.NS', 'ONGC.NS', 'TATAMOTORS.NS', 
    'NTPC.NS', 'AXISBANK.NS', 'DMART.NS', 'ADANIGREEN.NS', 'ADANIPORTS.NS', 'ULTRACEMCO.NS', 
    'ASIANPAINT.NS', 'COALINDIA.NS', 'BAJAJFINSV.NS', 'BAJAJ-AUTO.NS', 'POWERGRID.NS', 
    'NESTLEIND.NS', 'WIPRO.NS', 'M&M.NS', 'IOC.NS', 'JIOFIN.NS', 'HAL.NS', 'DLF.NS', 
    'ADANIPOWER.NS', 'JSWSTEEL.NS', 'TATASTEEL.NS', 'SIEMENS.NS', 'IRFC.NS', 'VBL.NS', 
    'ZOMATO.NS', 'PIDILITIND.NS', 'GRASIM.NS', 'SBILIFE.NS', 'BEL.NS', 'LTIM.NS'
]

print("Total tickers in list:", len(NIFTY_50_TICKERS))
data = yf.download(NIFTY_50_TICKERS, period="2d", interval="1d", progress=False)['Close']

missing = []
for ticker in NIFTY_50_TICKERS:
    if ticker not in data.columns or len(data[ticker].dropna()) < 2:
        missing.append(ticker)
        print(f"Missing {ticker}: Columns exist? {ticker in data.columns}")
        if ticker in data.columns:
            print(f"Length of data: {len(data[ticker].dropna())}")

print(f"\nMissing Tickers: {missing}")
