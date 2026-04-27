# My Dark Sky

Beautiful Flask weather app inspired by Dark Sky, powered by OpenWeather.

## Features

- Current location weather with browser geolocation
- Search weather by specific city
- Today's live weather
- Forecast or historical weather for a chosen date
- SQLite cache for weather and geocoding responses with a 5-minute TTL
- Tailwind-based responsive UI

## Stack

- Python
- Flask
- SQLite with Flask-SQLAlchemy
- Tailwind CSS
- OpenWeather One Call 3.0 and Geocoding APIs

## Local Run

1. Install dependencies:
   `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Set `OPENWEATHER_API_KEY`
4. Start the app:
   `python app.py`

## Deployment

This project is ready for cloud deployment on platforms that support Flask apps.

- Production server: `gunicorn app:app`
- Procfile included
- Port binding handled with the `PORT` environment variable
- Render blueprint file included as `render.yaml`

After deployment, put only the live app URL inside `my_dark_sky_url.txt`.
