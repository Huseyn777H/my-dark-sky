from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class WeatherCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_key = db.Column(db.String(100), unique=True, nullable=False)
    data = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
