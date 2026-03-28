import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import yfinance as yf # Ensure this is imported if used, though strict yfinance usage is in ml_engine.py

def send_alert_email(user_email, username, ticker, prediction_data):
    """
    Sends a formatted HTML email with the stock prediction.
    """
    # 1. Load Credentials securely
    sender_email = os.environ.get('SMTP_EMAIL')
    sender_password = os.environ.get('SMTP_PASSWORD')

    # 2. Check if credentials exist
    if not sender_email or not sender_password:
        print("❌ Error: SMTP credentials missing in .env file")
        return False

    # 3. Create Email Subject & Content
    subject = f"MarketMind Alert: {ticker} Prediction"
    
    # Determine color for email
    color = "green" if prediction_data['trend'] == "RISE" else "red"
    
    # HTML Template
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #0b1121; padding: 20px; text-align: center; color: white;">
                <h2>MarketMind AI</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd;">
                <h3>Hello {username},</h3>
                <p>Here is your daily AI outlook for <strong>{ticker}</strong>.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="font-size: 18px; margin: 0;">Verdict: <strong>{prediction_data['verdict']}</strong></p>
                    <p style="font-size: 24px; color: {color}; font-weight: bold; margin: 10px 0;">
                        Predicted to {prediction_data['trend']}
                    </p>
                    <p>Target Price: <strong>{prediction_data['predicted_price']}</strong></p>
                </div>
                
                <p style="color: #666; font-size: 12px;">
                    Disclaimer: This is an AI-generated prediction for educational purposes. 
                    Investments are subject to market risks.
                </p>
            </div>
        </body>
    </html>
    """

    # 4. Construct Message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = user_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))

    # 5. Send via Gmail SMTP
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent successfully to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False