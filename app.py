import os
from datetime import date, datetime

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

from models import db
from services.weather_service import (
    WeatherServiceError,
    build_location_name,
    classify_date,
    geocode_location,
    get_current_weather,
    get_weather_for_date,
    reverse_geocode,
)

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///weather_cache.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.getenv("FLASK_SECRET", "my-dark-sky-dev-secret")

db.init_app(app)

with app.app_context():
    db.create_all()


def _safe_float(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise WeatherServiceError(f"Invalid {field_name}.")


def _build_context(error=None):
    return {
        "error": error,
        "weather": None,
        "selected_date": date.today().isoformat(),
        "mode": "today",
        "location_name": None,
        "lat": None,
        "lon": None,
    }


@app.template_filter("datetimeformat")
def datetimeformat(value, format_string="%A, %b %d"):
    return datetime.fromtimestamp(value).strftime(format_string)


@app.route("/")
def index():
    context = _build_context()
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not lat or not lon:
        return render_template("index.html", **context)

    try:
        lat_value = _safe_float(lat, "latitude")
        lon_value = _safe_float(lon, "longitude")
        weather = get_current_weather(lat_value, lon_value)
        location_data = reverse_geocode(lat_value, lon_value)

        context.update(
            weather=weather,
            location_name=build_location_name(location_data, lat_value, lon_value),
            lat=lat_value,
            lon=lon_value,
        )
    except WeatherServiceError as exc:
        context["error"] = str(exc)
    except Exception:
        context["error"] = "Unable to load weather data right now."

    return render_template("index.html", **context)


@app.route("/search", methods=["POST"])
def search():
    city = request.form.get("city", "")

    try:
        location = geocode_location(city)
        return redirect(
            url_for("index", lat=location["lat"], lon=location["lon"], city=build_location_name(location))
        )
    except WeatherServiceError as exc:
        context = _build_context(error=str(exc))
        return render_template("index.html", **context), 400
    except Exception:
        context = _build_context(error="Unable to search for that location right now.")
        return render_template("index.html", **context), 500


@app.route("/date-weather")
def date_weather():
    context = _build_context()
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    date_str = request.args.get("date")

    try:
        if not lat or not lon:
            raise WeatherServiceError("Choose a location first.")
        if not date_str:
            raise WeatherServiceError("Choose a date first.")

        lat_value = _safe_float(lat, "latitude")
        lon_value = _safe_float(lon, "longitude")
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        weather = get_weather_for_date(lat_value, lon_value, selected_date)
        location_data = reverse_geocode(lat_value, lon_value)

        context.update(
            weather=weather,
            selected_date=selected_date.isoformat(),
            mode=classify_date(selected_date),
            location_name=build_location_name(location_data, lat_value, lon_value),
            lat=lat_value,
            lon=lon_value,
        )
    except ValueError:
        context["error"] = "Use a valid date."
    except WeatherServiceError as exc:
        context["error"] = str(exc)
    except Exception:
        context["error"] = "Unable to load weather for that date right now."

    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "true").lower() == "true",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
