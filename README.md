# My Dark Sky

My Dark Sky is a Flask weather application inspired by the original Dark Sky product. It provides a polished interface for checking today's conditions, searching by city, using the browser's current location, and viewing weather for a specific past or future date.

## Features

- Current location weather using browser geolocation
- City search using geocoding
- Today's live weather conditions
- Date-based weather lookup for both past and future dates
- SQLite cache with a five-minute expiration window
- Responsive Tailwind CSS interface

## Tech Stack

- Python 3
- Flask
- Flask-SQLAlchemy with SQLite
- Tailwind CSS
- Open-Meteo forecast, archive, and geocoding APIs

## Project Structure

- `app.py`: Flask routes, template rendering, and app startup
- `models.py`: SQLAlchemy cache model
- `services/weather_service.py`: weather lookup, geocoding, normalization, and caching
- `templates/`: Jinja templates for the UI
- `static/js/script.js`: browser geolocation logic

## Installation

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`
5. Optionally change `FLASK_SECRET` in `.env`
6. Run the application:
   `python app.py`

## Environment Variables

This project no longer requires a paid weather API key.

Supported environment variables:

- `FLASK_SECRET`: secret key for Flask sessions
- `FLASK_DEBUG`: set to `true` for local debugging
- `PORT`: hosting platform port, used automatically in production

## Caching

Weather responses and geocoding results are cached in SQLite for five minutes. This reduces repeated external API requests and satisfies the project caching requirement.

## Deployment

The application is ready to deploy on platforms such as Render, Railway, or similar Flask-compatible hosts.

- Production server: `gunicorn app:app`
- `Procfile` included
- `render.yaml` included
- `PORT` environment variable supported

After deployment, place only the live application URL in `my_dark_sky_url.txt`.
