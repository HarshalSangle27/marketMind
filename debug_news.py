import yfinance as yf
import json

ticker = "RELIANCE.NS"
print(f"--- Fetching News for {ticker} ---")

try:
    stock = yf.Ticker(ticker)
    news = stock.news
    
    if not news:
        print("❌ Result: Empty List [] (Yahoo gave no data)")
    else:
        print(f"✅ Found {len(news)} articles!")
        # Print the first article to see the keys
        print(json.dumps(news[0], indent=2))

except Exception as e:
    print(f"❌ Error: {e}")