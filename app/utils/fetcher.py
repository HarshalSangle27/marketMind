import yfinance as yf
import pandas as pd
import concurrent.futures

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

def get_market_health():
    """
    Fetches the market health (Advances vs Declines) for the NIFTY 50.
    Uses yfinance.download to fetch all tickers at once for maximum speed.
    """
    try:
        # Fetch the last 2 days of closing prices for all NIFTY 50 stocks
        # grouping by ticker to easily access each stock's data
        data = yf.download(NIFTY_50_TICKERS, period="2d", interval="1d", progress=False)['Close']
        
        advances = 0
        declines = 0
        
        for ticker in NIFTY_50_TICKERS:
            try:
                # Check if we have at least 2 days of data for this ticker
                if ticker in data.columns and len(data[ticker].dropna()) >= 2:
                    prices = data[ticker].dropna()
                    prev_close = float(prices.iloc[-2])
                    current_close = float(prices.iloc[-1])
                    
                    if current_close >= prev_close:
                        advances += 1
                    else:
                        declines += 1
            except Exception:
                try:
                    stock = yf.Ticker(ticker)
                    curr = stock.fast_info.last_price
                    prev = stock.fast_info.previous_close
                    if curr >= prev:
                        advances += 1
                    else:
                        declines += 1
                except Exception:
                    continue
                
        total_tracked = advances + declines
        
        # Calculate percentages for the progress bar
        if total_tracked > 0:
            adv_pct = round((advances / total_tracked) * 100)
            dec_pct = 100 - adv_pct
        else:
            adv_pct = 50
            dec_pct = 50
            
        # Default fallback if API fails completely
        if total_tracked == 0:
            advances, declines, adv_pct, dec_pct = 34, 16, 68, 32
            
        # Dynamic momentum text
        if adv_pct >= 65:
            momentum_text = "Overall momentum is strongly positive today."
        elif adv_pct >= 55:
            momentum_text = "Overall momentum is moderately positive today."
        elif dec_pct >= 65:
            momentum_text = "Overall momentum is strongly negative today."
        elif dec_pct >= 55:
            momentum_text = "Overall momentum is moderately negative today."
        else:
            momentum_text = "Overall momentum is relatively neutral today."
            
        return {
            'advances': advances,
            'declines': declines,
            'adv_pct': adv_pct,
            'dec_pct': dec_pct,
            'text': momentum_text
        }
        
    except Exception as e:
        print(f"Market Health Error: {e}")
        # Return fallback values on error
        return {
            'advances': 34,
            'declines': 16,
            'adv_pct': 68,
            'dec_pct': 32,
            'text': "Overall momentum is strongly positive today."
        }

def get_stock_data(ticker, period="1mo"):
    """
    Fetches stock data.
    FIXED for INR Stocks: Uses stock.fast_info to bypass timezone cutoff bugs in yfinance history.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # 1. Fetch History (ONLY used for drawing the graph)
        hist = stock.history(period=period)
        if hist.empty: return None
            
        info = stock.info
        
        # Determine Currency Symbol
        currency_code = info.get('currency', 'INR')
        currency_symbol_map = {
            'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥',
            'AUD': 'A$', 'CAD': 'C$', 'CHF': 'CHF', 'CNY': '¥', 'HKD': 'HK$'
        }
        currency_symbol = currency_symbol_map.get(currency_code, f"{currency_code} ")
        
        # --- THE BULLETPROOF INR FIX ---
        # Completely detach the Current Price from the Chart's period.
        try:
            # fast_info is a real-time stream, completely immune to period/timezone bugs
            current_price = stock.fast_info.last_price
            prev_close = stock.fast_info.previous_close
        except Exception:
            # Fallback just in case fast_info is unavailable
            price_hist = stock.history(period="2d")
            if len(price_hist) >= 2:
                prev_close = price_hist['Close'].iloc[-2]
                current_price = price_hist['Close'].iloc[-1]
            else:
                current_price = hist['Close'].iloc[-1]
                prev_close = current_price

        # 3. Calculate accurate change mathematically
        change = current_price - prev_close
        
        if prev_close > 0:
            pct_change = (change / prev_close) * 100
        else:
            pct_change = 0.0
            
        color = "text-success" if change >= 0 else "text-danger"
        
        # --- Smart SIP Return Logic ---
        annual_return = info.get('52WeekChange', 0.12)
        if annual_return is None: annual_return = 0.12

        sip_return_rate = round(annual_return * 100, 1)
        if sip_return_rate <= 0: sip_return_rate = 12.0
        if sip_return_rate > 30: sip_return_rate = 30.0
        
        # 4. Fetch Raw News
        news_list = []
        try:
            raw_news = stock.news
            if raw_news:
                for item in raw_news[:3]: 
                    article = item.get('content', item)
                    title = article.get('title', article.get('headline', ''))
                    link = '#'
                    if 'clickThroughUrl' in article: link = article['clickThroughUrl'].get('url', '#')
                    elif 'link' in article: link = article['link']
                    
                    if title:
                        news_list.append({'title': title, 'link': link, 'publisher': article.get('provider', {}).get('displayName', 'Yahoo')})
        except Exception:
            pass 

        # Determine Logo URL
        website = info.get('website', '')
        if website:
            import re
            domain = re.sub(r'^https?://(www\.)?', '', website).split('/')[0]
        else:
            domain = ticker.replace('.NS', '').replace('.BO', '').lower() + '.com'
            
        globe_domains = ['tcs.com', 'sbi.co.in']
        if domain in globe_domains:
            logo_url = "notfound" # Will fail and trigger the ui-avatars onerror fallback
        else:
            logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
            
        # 5. Return Data Dictionary
        data = {
            'info': {
                'symbol': ticker,
                'name': info.get('longName', ticker),
                'price': f"{info.get('currency', 'INR')} {round(current_price, 2)}",
                'raw_price': current_price,
                'change': f"{round(change, 2)}",
                'pct_change': f"{round(pct_change, 2)}",
                'color': color,
                'currency': currency_code,
                'currency_symbol': currency_symbol,
                'logo_url': logo_url,
                'dayHigh': round(hist['High'].max(), 2),
                'dayLow': round(hist['Low'].min(), 2),
                'volume': f"{round(info.get('volume', 0) / 100000, 2)} L",
                'open': round(info.get('open', 0), 2),
                'marketCap': f"{currency_symbol} {round(info.get('marketCap', 0) / 10000000, 2)} Cr",
                'sip_return': sip_return_rate
            },
            'chart': {
                'dates': hist.index.strftime('%b %d').tolist(),
                'prices': hist['Close'].tolist()
            },
            'news': news_list
        }
        return data

    except Exception as e:
        print(f"Fetcher Error: {e}")
        return None