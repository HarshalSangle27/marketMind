from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.utils.fetcher import get_stock_data, get_market_health
from app.utils.ml_engine import analyze_stock, get_market_news, analyze_global_sentiment, analyze_mutual_fund
from app.utils.email_service import send_alert_email
from app.models import Watchlist, StockHistory
from app import db
import time
import concurrent.futures
from datetime import datetime

stocks_bp = Blueprint('stocks', __name__)

# --- GLOBAL CACHE ---
cache = {'data': [], 'news': [], 'health': None, 'last_updated': 0}

def _fetch_single_ticker_info(ticker):
    try:
        full_data = get_stock_data(ticker, period="5d")
        if full_data and 'info' in full_data:
            if ticker == 'BTC-USD':
                full_data['info']['name'] = 'Bitcoin'
            return full_data['info']
    except Exception as e:
        print(f"[WARNING] Failed to fetch {ticker}: {e}")
    return None

def _fetch_recent_stock_info(record):
    try:
        sd = get_stock_data(record.symbol, period="1d")
        if sd:
            new_price = sd['info']['raw_price']
            old_price = record.price_at_visit or new_price
            change = new_price - old_price
            pct_change = (change / old_price * 100) if old_price > 0 else 0
            
            return {
                'symbol': record.symbol,
                'name': sd['info']['name'],
                'current_price_str': sd['info']['price'],
                'old_price_str': f"{sd['info'].get('currency', 'INR')} {round(old_price, 2)}",
                'change': round(change, 2),
                'pct_change': round(pct_change, 2),
                'color': 'text-success' if change >= 0 else 'text-danger',
                'logo_url': sd['info'].get('logo_url', '')
            }
    except Exception as e:
        print(f"[WARNING] Failed to fetch recent stock {record.symbol}: {e}")
    return None

@stocks_bp.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        ticker = request.form.get('ticker')
        if ticker:
            return redirect(url_for('stocks.dashboard', ticker=ticker.upper()))
    
    # --- SMART CACHING LOGIC ---
    current_time = time.time()
    
    # Refresh if cache is empty OR older than 60 seconds
    if not cache['data'] or (current_time - cache['last_updated'] > 60):
        print("[INFO] Downloading Fresh Trending Data...")
        
        potential_tickers = [
            'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 
            'ICICIBANK.NS', 'TATAMOTORS.NS', 'SBIN.NS', 'ZOMATO.NS', 
            'AAPL', 'BTC-USD'
        ]
        
        # Parallel fetch for trending stocks
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            fetched = list(executor.map(_fetch_single_ticker_info, potential_tickers))
        
        fresh_data = [item for item in fetched if item is not None][:8]

        # Parallel fetch news & market health
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_news = executor.submit(get_market_news, limit=3)
            future_health = executor.submit(get_market_health)
            cache['news'] = future_news.result()
            cache['health'] = future_health.result()
        
        if len(fresh_data) > 0:
            cache['data'] = fresh_data
            cache['last_updated'] = current_time

    # Provide fallback health data if cache is empty
    market_health = cache.get('health', {'advances': 34, 'declines': 16, 'adv_pct': 68, 'dec_pct': 32})

    recent_stocks = []
    if current_user.is_authenticated:
        history_records = StockHistory.query.filter_by(user_id=current_user.id).order_by(StockHistory.last_visited.desc()).limit(8).all()
        if history_records:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(history_records), 8)) as executor:
                recent_results = list(executor.map(_fetch_recent_stock_info, history_records))
            recent_stocks = [r for r in recent_results if r is not None]

    return render_template('index.html', trending_stocks=cache['data'], market_news=cache['news'], market_health=market_health, recent_stocks=recent_stocks)

@stocks_bp.route('/dashboard/<ticker>')
def dashboard(ticker):
    ticker = ticker.upper().strip()
    
    # 1. Get Time Period (Default to 1mo)
    period = request.args.get('period', '1mo')
    
    # 2. Fetch Data
    stock_data = get_stock_data(ticker, period=period)
    
    if not stock_data:
        flash(f"Could not fetch data for {ticker}", "danger")
        return redirect(url_for('stocks.home'))

    # Sync fresh price to home page cache to ensure consistency
    for i, cached_item in enumerate(cache['data']):
        if cached_item.get('symbol') == ticker:
            cache['data'][i]['price'] = stock_data['info']['price']
            cache['data'][i]['change'] = stock_data['info']['change']
            cache['data'][i]['pct_change'] = stock_data['info']['pct_change']
            cache['data'][i]['color'] = stock_data['info']['color']
            break

    # Track view history for logged in users
    if current_user.is_authenticated:
        history = StockHistory.query.filter_by(user_id=current_user.id, symbol=ticker).first()
        if history:
            history.visit_count += 1
            history.last_visited = datetime.utcnow()
            history.price_at_visit = stock_data['info']['raw_price']
        else:
            history = StockHistory(user_id=current_user.id, symbol=ticker, price_at_visit=stock_data['info']['raw_price'])
            db.session.add(history)
        db.session.commit()

    return render_template('dashboard.html', 
                         stock_data=stock_data['info'], 
                         chart_data=stock_data['chart'],
                         current_period=period)

@stocks_bp.route('/remove_history/<ticker>', methods=['POST'])
@login_required
def remove_history(ticker):
    ticker = ticker.upper().strip()
    history = StockHistory.query.filter_by(user_id=current_user.id, symbol=ticker).first()
    if history:
        db.session.delete(history)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Not found'}), 404

@stocks_bp.route('/predict/<ticker>', methods=['GET', 'POST'])
@login_required
def predict(ticker):
    ticker = ticker.upper().strip()
    
    # 1. Get Period for AI
    period = request.args.get('period', '6mo') 

    # 2. Run Analysis
    analysis = analyze_stock(ticker, period=period)
    
    if not analysis:
        flash(f"Not enough data to generate prediction for {ticker} ({period})", "warning")
        return redirect(url_for('stocks.dashboard', ticker=ticker))
        
    # Append logo_url and name
    sd = get_stock_data(ticker, period="1d")
    if sd:
        analysis['name'] = sd['info']['name']
        analysis['logo_url'] = sd['info'].get('logo_url', '')
    else:
        analysis['name'] = ticker.replace('.NS', '')
        analysis['logo_url'] = ''

    # 3. Handle Subscription
    if request.method == 'POST':
        exists = Watchlist.query.filter_by(user_id=current_user.id, symbol=ticker).first()
        if not exists:
            new_alert = Watchlist(symbol=ticker, user_id=current_user.id)
            db.session.add(new_alert)
            db.session.commit()
            
            send_alert_email(current_user.email, current_user.username, ticker, analysis)
            flash(f'Success! Alert sent to {current_user.email}.', 'success')
        else:
            flash(f'You are already subscribed to {ticker}.', 'info')
        
        return redirect(url_for('stocks.predict', ticker=ticker, period=period))

    # 4. Check Subscription
    is_subscribed = False
    if current_user.is_authenticated:
        exists = Watchlist.query.filter_by(user_id=current_user.id, symbol=ticker).first()
        if exists: is_subscribed = True

    return render_template('prediction.html', data=analysis, is_subscribed=is_subscribed, current_period=period)

# --- GLOBAL AI PICKS CACHE ---
ai_cache = {'picks': [], 'last_updated': 0}

def _process_ai_pick(ticker):
    try:
        analysis = analyze_stock(ticker, period="6mo")
        if analysis:
            sd = get_stock_data(ticker, period="1d")
            if sd:
                analysis['name'] = sd['info']['name']
                analysis['logo_url'] = sd['info'].get('logo_url', '')
            else:
                analysis['name'] = ticker.replace('.NS', '')
                analysis['logo_url'] = ''
            return analysis
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
    return None

@stocks_bp.route('/ai-picks')
def ai_picks():
    current_time = time.time()
    
    if not ai_cache['picks'] or (current_time - ai_cache['last_updated'] > 3600):
        print("[INFO] Generating AI Top Picks...")
        tickers_to_analyze = ['TCS.NS', 'RELIANCE.NS', 'HDFCBANK.NS', 'LT.NS', 'ITC.NS', 'INFY.NS', 'TATAMOTORS.NS', 'SBIN.NS']
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            res = list(executor.map(_process_ai_pick, tickers_to_analyze))
        results = [r for r in res if r is not None]
                
        def verdict_score(v):
            if v == "STRONG BUY": return 4
            if v == "BUY": return 3
            if v == "HOLD": return 2
            if v == "SELL": return 1
            if v == "STRONG SELL": return 0
            return 0
            
        results.sort(key=lambda x: (verdict_score(x['verdict']), x['change_percent']), reverse=True)
        ai_cache['picks'] = results[:6]
        ai_cache['last_updated'] = current_time

    return render_template('ai_picks.html', top_picks=ai_cache['picks'])

# --- GLOBAL MUTUAL FUNDS CACHE ---
mf_cache = {'picks': [], 'last_updated': 0}

def _process_mf_pick(fund):
    try:
        analysis = analyze_mutual_fund(fund['ticker'])
        if analysis:
            fund_copy = fund.copy()
            fund_copy.update(analysis)
            return fund_copy
    except Exception as e:
        print(f"Error analyzing {fund['name']}: {e}")
    return None

@stocks_bp.route('/mutual-funds-picks')
def mutual_funds_picks():
    current_time = time.time()
    
    # Cache for 12 hours (43200 seconds) since MFs update daily
    if not mf_cache['picks'] or (current_time - mf_cache['last_updated'] > 43200):
        print("[INFO] Analyzing Mutual Funds data...")
        
        target_funds = [
            {'ticker': '0P0000YWL1.BO', 'name': 'Parag Parikh Flexi Cap Fund', 'category': 'Flexi Cap'},
            {'ticker': '0P0000XV99.BO', 'name': 'ICICI Pru Nifty 50 Index Fund', 'category': 'Index'},
            {'ticker': '0P0000XVUA.BO', 'name': 'SBI Contra Fund', 'category': 'Contra'},
            {'ticker': '0P0000XWAA.BO', 'name': 'SBI Small Cap Fund', 'category': 'Small Cap'},
            {'ticker': '0P0000XVWT.BO', 'name': 'Axis Bluechip Fund', 'category': 'Large Cap'},
            {'ticker': '0P0000XVKY.BO', 'name': 'Mirae Asset Large Cap Fund', 'category': 'Large Cap'},
            {'ticker': '0P0000XW7U.BO', 'name': 'HDFC Small Cap Fund', 'category': 'Small Cap'},
            {'ticker': '0P0000XVYZ.BO', 'name': 'Kotak Flexicap Fund', 'category': 'Flexi Cap'},
            {'ticker': 'NIFTYBEES.NS', 'name': 'Nippon India Nifty 50 ETF', 'category': 'Index ETF'},
            {'ticker': 'MON100.NS', 'name': 'Motilal Oswal Nasdaq 100 ETF', 'category': 'Intl ETF'}
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            res = list(executor.map(_process_mf_pick, target_funds))
        results = [r for r in res if r is not None]
                
        # Sort by highest CAGR
        results.sort(key=lambda x: x.get('cagr', 0), reverse=True)
        
        if results:
            mf_cache['picks'] = results
            mf_cache['last_updated'] = current_time

    return render_template('mutual_funds_picks.html', mf_picks=mf_cache['picks'])

# --- GLOBAL SENTIMENT CACHE ---
sentiment_cache = {'data': None, 'last_updated': 0}

@stocks_bp.route('/sentiment')
def sentiment():
    current_time = time.time()
    
    if not sentiment_cache['data'] or (current_time - sentiment_cache['last_updated'] > 3600):
        print("[INFO] Generating Global Sentiment Data...")
        sentiment_data = analyze_global_sentiment()
        
        # If fetch fails, keep old data if it exists, otherwise provide a neutral fallback
        if sentiment_data:
            sentiment_cache['data'] = sentiment_data
            sentiment_cache['last_updated'] = current_time
        elif not sentiment_cache['data']:
            # Fallback
            sentiment_cache['data'] = {
                'overall_score': 50,
                'top_factors': [],
                'positive_count': 0,
                'negative_count': 0
            }
            
    return render_template('sentiment.html', data=sentiment_cache['data'])

@stocks_bp.route('/strategies')
def strategies():
    return render_template('strategies.html')