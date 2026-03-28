import requests

try:
    s = requests.Session()
    # 1. Signup
    print("Signing up...")
    s.post('http://127.0.0.1:5000/signup', data={'username':'testuser1', 'email':'t1@example.com', 'password':'password123'})
    
    # 2. Login
    print("Logging in...")
    s.post('http://127.0.0.1:5000/login', data={'email':'t1@example.com', 'password':'password123'})
    
    # 3. Visit AAPL Dashboard
    print("Visiting AAPL...")
    r_dash = s.get('http://127.0.0.1:5000/dashboard/AAPL')
    if r_dash.status_code == 200:
        print("AAPL Dashboard Loaded.")
    
    # 4. Check Home Page
    print("Checking Home Page...")
    r_home = s.get('http://127.0.0.1:5000/')
    if 'Your Recently Viewed Stocks' in r_home.text:
        print("SUCCESS! 'Your Recently Viewed Stocks' is visible.")
        if 'AAPL' in r_home.text:
            print("SUCCESS! 'AAPL' is inside the history section.")
    else:
        print("FAIL: 'Your Recently Viewed Stocks' not found.")
        
except Exception as e:
    print(f"Error: {e}")
