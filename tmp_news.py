import yfinance as yf
import json

news = yf.Ticker('^NSEI').news
with open('tmp_news.json', 'w') as f:
    json.dump(news[:2], f, indent=2)
print("Saved to tmp_news.json")
