import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta

def analyze_stock(ticker, period="6mo"):
    """
    Runs Linear Regression on price history (variable period) and Sentiment Analysis.
    """
    try:
        # 1. FETCH DATA (Dynamic Period + Fix for Empty/NaN Data)
        stock = yf.Ticker(ticker)
        
        # Extract currency
        info = stock.info
        currency_code = info.get('currency', 'INR')
        currency_symbol_map = {
            'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥',
            'AUD': 'A$', 'CAD': 'C$', 'CHF': 'CHF', 'CNY': '¥', 'HKD': 'HK$'
        }
        currency_symbol = currency_symbol_map.get(currency_code, f"{currency_code} ")
        
        # .dropna() removes rows with missing data (crucial for stocks like AAPL)
        hist = stock.history(period=period).dropna()
        
        # Determine minimum data points needed
        min_days = 15 if period == "1mo" else 30
        if len(hist) < min_days:
            return None 

        # 2. FEATURE ENGINEERING (Technical Indicators + Lags)
        # Calculate moving averages and past prices to capture trends
        hist['Close_Lag1'] = hist['Close'].shift(1)
        hist['Close_Lag2'] = hist['Close'].shift(2)
        hist['Close_Lag3'] = hist['Close'].shift(3)
        hist['Open_Lag'] = hist['Open'].shift(1)
        hist['MA_5'] = hist['Close'].rolling(window=5).mean()
        hist['MA_10'] = hist['Close'].rolling(window=10).mean()
        hist['Daily_Return'] = hist['Close'].pct_change()
        
        # Drop rows with NaN values created by rolling/shift
        hist = hist.dropna()
        hist = hist.reset_index()

        # 3. PREPARE DATA FOR REGRESSION
        features_close = ['Close_Lag1', 'Close_Lag2', 'Close_Lag3', 'MA_5', 'MA_10', 'Daily_Return']
        features_open = ['Open_Lag', 'Close_Lag1', 'MA_5']
        
        X_close = hist[features_close]
        y_close = hist['Close']
        
        X_open = hist[features_open]
        y_open = hist['Open']

        # 4. TRAIN MODELS (Gradient Boosting Regressor)
        # Using Gradient Boosting for higher accuracy and handling non-linear relationships
        model_close = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
        model_close.fit(X_close, y_close)
        
        model_open = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
        model_open.fit(X_open, y_open)

        # 5. PREDICT TOMORROW
        last_close = y_close.iloc[-1]
        
        # Build features for tomorrow based on today's closing metrics
        next_day_features_close = pd.DataFrame([{
            'Close_Lag1': last_close,
            'Close_Lag2': X_close['Close_Lag1'].iloc[-1],
            'Close_Lag3': X_close['Close_Lag2'].iloc[-1],
            'MA_5': np.mean(y_close.iloc[-4:].tolist() + [last_close]),
            'MA_10': np.mean(y_close.iloc[-9:].tolist() + [last_close]),
            'Daily_Return': (last_close - X_close['Close_Lag1'].iloc[-1]) / X_close['Close_Lag1'].iloc[-1] if X_close['Close_Lag1'].iloc[-1] != 0 else 0
        }])
        
        next_day_features_open = pd.DataFrame([{
            'Open_Lag': y_open.iloc[-1],
            'Close_Lag1': last_close,
            'MA_5': np.mean(y_close.iloc[-4:].tolist() + [last_close])
        }])
        
        predicted_close = model_close.predict(next_day_features_close)[0]
        predicted_open = model_open.predict(next_day_features_open)[0]
        
        current_price = y_close.iloc[-1]
        
        # Calculate Trend based on Close price
        price_change = predicted_close - current_price
        price_trend = "RISE" if price_change > 0 else "FALL"
        trend_color = "success" if price_change > 0 else "danger"

        # 5. SENTIMENT ANALYSIS (Robust)
        analyzer = SentimentIntensityAnalyzer()
        news_list = []
        total_score = 0
        count = 0
        
        try:
            news_data = stock.news
            if news_data:
                for item in news_data[:5]:
                    # Handle nested structure
                    if 'content' in item:
                        article = item['content']
                    else:
                        article = item 
                    
                    title = article.get('title', '')
                    
                    # Robust link finding
                    link = '#'
                    if 'clickThroughUrl' in article and article['clickThroughUrl']:
                        link = article['clickThroughUrl'].get('url', '#')
                    elif 'link' in article:
                        link = article['link']
                    elif 'url' in article:
                        link = article['url']

                    if not title: continue 

                    # Analyze Sentiment
                    score = analyzer.polarity_scores(title)['compound']
                    total_score += score
                    
                    if score >= 0.05: s_tag = "Positive"
                    elif score <= -0.05: s_tag = "Negative"
                    else: s_tag = "Neutral"
                    
                    news_list.append({'title': title, 'link': link, 'tag': s_tag})
                    count += 1
        except Exception as e:
            print(f"News Parsing Error: {e}")

        # --- FALLBACK NEWS ---
        if count == 0:
            context_tag = "Positive" if price_trend == "RISE" else "Negative"
            news_list.append({
                'title': f"Market trend analysis suggests {context_tag.lower()} momentum.",
                'link': '#',
                'tag': context_tag + " (AI Context)"
            })
            final_sentiment_score = 65.0 if price_trend == "RISE" else 35.0
        else:
            avg_score = total_score / count
            final_sentiment_score = round((avg_score + 1) * 50, 1)

        # 6. FINAL VERDICT
        verdict = "HOLD"
        verdict_color = "warning"
        
        if price_trend == "RISE" and final_sentiment_score > 60:
            verdict = "STRONG BUY"
            verdict_color = "success"
        elif price_trend == "FALL" and final_sentiment_score < 40:
            verdict = "STRONG SELL"
            verdict_color = "danger"
        elif price_trend == "RISE":
            verdict = "BUY"
            verdict_color = "primary"
        elif price_trend == "FALL":
            verdict = "SELL"
            verdict_color = "danger"

        # Chart Data
        regression_line = model_close.predict(X_close)
        
        return {
            'symbol': ticker,
            'current_price': round(current_price, 2),
            'predicted_price': round(predicted_close, 2),
            'predicted_open': round(predicted_open, 2),
            'change_percent': round((price_change / current_price) * 100, 2),
            'trend': price_trend,
            'trend_color': trend_color,
            'currency_symbol': currency_symbol,
            'sentiment_score': final_sentiment_score,
            'news': news_list,
            'verdict': verdict,
            'verdict_color': verdict_color,
            'dates': hist['Date'].dt.strftime('%Y-%m-%d').tolist(),
            'actual_prices': y_close.tolist(),
            'trend_prices': regression_line.tolist()
        }

    except Exception as e:
        print(f"AI Engine Error: {e}")
        return None

def get_market_news(limit=3):
    """
    Fetches real-time market news (NIFTY 50 index used as proxy) via yfinance.
    """
    try:
        index = yf.Ticker('^NSEI')
        raw_news = index.news
        formatted_news = []
        
        if not raw_news: return formatted_news
        
        for item in raw_news[:limit]:
            # Handle variable yfinance nested structure
            content = item.get('content', item)
            title = content.get('title', 'Market Update')
            
            # Extract Link
            link = '#'
            if 'clickThroughUrl' in content and content['clickThroughUrl']:
                link = content['clickThroughUrl'].get('url', '#')
            elif 'link' in content:
                link = content['link']
            elif 'url' in content:
                link = content['url']
                
            # Extract Publisher/Source
            publisher = content.get('provider', {}).get('displayName', 'Financial News')
            if not isinstance(publisher, str): publisher = 'Financial News'

            formatted_news.append({
                'title': title,
                'link': link,
                'publisher': publisher
            })
            
        return formatted_news
    except Exception as e:
        print(f"Error fetching market news: {e}")
        return []

def analyze_global_sentiment():
    """
    Fetches news from major global indices and commodities to calculate an overall
    macro-economic sentiment score. Extracts the top 5 strongest polarizing headlines
    as influencing factors.
    """
    try:
        analyzer = SentimentIntensityAnalyzer()
        
        # Major indices and indicators to represent "Global Market"
        # S&P 500, Nasdaq, NIFTY 50, Gold, Bitcoin
        symbols = ['^GSPC', '^IXIC', '^NSEI', 'GC=F', 'BTC-USD']
        
        all_news = []
        
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                news = ticker.news
                if news:
                    all_news.extend(news[:5]) # Get top 5 from each to have a mix
            except Exception as e:
                print(f"Failed to fetch news for {sym}: {e}")
                
        if not all_news:
            return None
            
        processed_factors = []
        positive_count = 0
        negative_count = 0
        
        # Keep track of unique titles
        seen_titles = set()
        
        for item in all_news:
            content = item.get('content', item)
            # Some responses use just 'title' directly
            if not isinstance(content, dict):
                content = item
                
            title = content.get('title', '')
            
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            
            # Source/Publisher
            publisher = content.get('provider', {}).get('displayName', 'Market News')
            if not isinstance(publisher, str): publisher = 'Market News'
            
            # Analysis
            score = analyzer.polarity_scores(title)['compound']
            
            # Categorize
            if score >= 0.05:
                direction = "up"
                tag_color = "success"
                positive_count += 1
            elif score <= -0.05:
                direction = "down"
                tag_color = "danger"
                negative_count += 1
            else:
                continue # Skip neutral for factors
                
            processed_factors.append({
                'title': title,
                'source': publisher,
                'direction': direction,
                'color': tag_color,
                'abs_score': abs(score) # For sorting later
            })
            
        total_eval = positive_count + negative_count
        
        if total_eval == 0:
            target_score = 50
        else:
            target_score = int((positive_count / total_eval) * 100)
            
        # Sort factors by strongest absolute sentiment to find the "Top Influencing Factors"
        processed_factors.sort(key=lambda x: x['abs_score'], reverse=True)
        top_factors = processed_factors[:5]
        
        return {
            'overall_score': target_score,
            'top_factors': top_factors,
            'positive_count': positive_count,
            'negative_count': negative_count
        }

    except Exception as e:
        print(f"Error in global sentiment analysis: {e}")
        return None

def analyze_mutual_fund(ticker):
    """
    Analyzes a mutual fund using yfinance history.
    Calculates 1-Year CAGR, Risk Level (via volatility), and AI Conviction (momentum).
    """
    try:
        mf = yf.Ticker(ticker)
        # Get 1 year of history
        hist = mf.history(period="1y").dropna()
        
        if len(hist) < 50: # Need sufficient data
            return None
            
        current_nav = hist['Close'].iloc[-1]
        start_nav_1y = hist['Close'].iloc[0]
        
        # Calculate 1Y CAGR
        cagr_1y = ((current_nav / start_nav_1y) - 1) * 100
        
        # Calculate Risk Level (Annualized Volatility of daily returns)
        daily_returns = hist['Close'].pct_change().dropna()
        # roughly 252 trading days in a year
        annual_volatility = daily_returns.std() * np.sqrt(252) * 100 
        
        if annual_volatility < 12:
            risk_level = "Low"
            risk_color = "success"
        elif annual_volatility < 20:
            risk_level = "Moderate"
            risk_color = "warning"
        else:
            risk_level = "High"
            risk_color = "danger"
            
        # Calculate AI Conviction (1-month vs 6-month momentum)
        try:
            hist_6mo = mf.history(period="6mo").dropna()
            hist_1mo = mf.history(period="1mo").dropna()
            
            ret_6mo = ((hist_6mo['Close'].iloc[-1] / hist_6mo['Close'].iloc[0]) - 1)
            ret_1mo = ((hist_1mo['Close'].iloc[-1] / hist_1mo['Close'].iloc[0]) - 1)
            
            # Simple heuristic: strong short-term momentum relative to long-term
            if ret_1mo > (ret_6mo / 6) * 1.5:
                conviction = "Very High"
            elif ret_1mo > (ret_6mo / 6) * 1.0:
                conviction = "High"
            else:
                conviction = "Medium"
        except:
            conviction = "High" # Fallback
            
        return {
            'cagr': round(cagr_1y, 2),
            'risk': risk_level,
            'risk_color': risk_color,
            'conviction': conviction
        }
            
    except Exception as e:
        print(f"Error analyzing mutual fund {ticker}: {e}")
        return None