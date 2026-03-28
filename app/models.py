from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    # Relationship: One user has many watchlist items
    watchlist_items = db.relationship('Watchlist', backref='owner', lazy='dynamic')

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    added_on = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # We will use this later for email alerts
    alert_enabled = db.Column(db.Boolean, default=True)

class StockHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    last_visited = db.Column(db.DateTime, default=datetime.utcnow)
    price_at_visit = db.Column(db.Float, nullable=True) # Price when they last checked
    visit_count = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))