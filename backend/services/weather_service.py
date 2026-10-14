import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Tuple
from datetime import datetime
from services.weather_alert_service import WeatherAlertService

class WeatherService:
    def __init__(self):
        self.alert_service = WeatherAlertService()
        self._cache: Dict[str, Any] = {}
        
    def get_weather(self, lat: float, lon: float, crop: str = None, condition: str = None) -> Dict[str, Any]:
        base_url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
            "timezone": "auto",
            "forecast_days": 7
        }
        
        query_string = urllib.parse.urlencode(params, doseq=True)
        url = f"{base_url}?{query_string}"
        
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AgroNex/1.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            current = data.get("current", {})
            hourly = data.get("hourly", {})
            daily = data.get("daily", {})
            alerts = self.alert_service.generate_alerts(data, crop, condition)

            # Map weather code
            code = current.get("weather_code", 0)
            condition_en = "Clear"
            condition_ta = "தெளிவான"
            if code in [1, 2, 3]:
                condition_en, condition_ta = "Partly Cloudy", "பகுதி மேகமூட்டம்"
            elif code in [45, 48]:
                condition_en, condition_ta = "Foggy", "மூடுபனி"
            elif code in [51, 53, 55, 56, 57]:
                condition_en, condition_ta = "Drizzle", "தூறல்"
            elif code in [61, 63, 65, 66, 67, 80, 81, 82]:
                condition_en, condition_ta = "Rain", "மழை"
            elif code in [95, 96, 99]:
                condition_en, condition_ta = "Thunderstorm", "இடியுடன் கூடிய மழை"
            
            # Format 7-day forecast
            forecast = []
            if "time" in daily:
                for i in range(len(daily["time"])):
                    forecast.append({
                        "date": daily["time"][i],
                        "temperature_max": daily["temperature_2m_max"][i],
                        "temperature_min": daily["temperature_2m_min"][i],
                        "precipitation_probability_mean": daily["precipitation_probability_max"][i],
                    })
                    
            # Format 24-hour forecast starting from current hour
            hourly_forecast = []
            if "time" in hourly:
                current_time_str = current.get("time", "")[:13] # e.g. "2026-10-04T20"
                start_idx = 0
                for i, t in enumerate(hourly["time"]):
                    if t.startswith(current_time_str) or t > current_time_str:
                        start_idx = i
                        break
                        
                end_idx = min(start_idx + 24, len(hourly["time"]))
                for i in range(start_idx, end_idx):
                    hourly_forecast.append({
                        "time": hourly["time"][i],
                        "temperature": hourly["temperature_2m"][i],
                        "precipitation_probability": hourly["precipitation_probability"][i],
                    })
            
            result = {
                "success": True,
                "location": {
                    "latitude": lat,
                    "longitude": lon
                },
                "last_updated": current.get("time", datetime.now().isoformat()),
                "condition_en": condition_en,
                "condition_ta": condition_ta,
                "current": {
                    "temperature": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "precipitation": current.get("precipitation"),
                    "weather_code": code
                },
                "hourly": hourly_forecast,
                "forecast": forecast,
                "alerts": alerts
            }
            cache_key = f"{round(lat, 2)}_{round(lon, 2)}"
            self._cache[cache_key] = result
            self._cache["_last"] = result
            return result
        except (urllib.error.URLError, Exception) as e:
            cache_key = f"{round(lat, 2)}_{round(lon, 2)}"
            cached = self._cache.get(cache_key) or self._cache.get("_last")
            if cached:
                fallback = dict(cached)
                fallback["cached"] = True
                return fallback
            now_iso = datetime.now().isoformat()
            today_str = now_iso[:10]
            return {
                "success": True,
                "offline_fallback": True,
                "location": {
                    "latitude": lat,
                    "longitude": lon
                },
                "last_updated": now_iso,
                "condition_en": "Partly Cloudy",
                "condition_ta": "பகுதி மேகமூட்டம்",
                "current": {
                    "temperature": 28.5,
                    "humidity": 68.0,
                    "wind_speed": 12.0,
                    "precipitation": 0.0,
                    "weather_code": 1
                },
                "hourly": [
                    {
                        "time": f"{today_str}T{hour:02d}:00",
                        "temperature": 28.0 + (hour % 5),
                        "precipitation_probability": 10
                    }
                    for hour in range(24)
                ],
                "forecast": [
                    {
                        "date": today_str,
                        "temperature_max": 31.0,
                        "temperature_min": 23.0,
                        "precipitation_probability_mean": 15
                    }
                ],
                "alerts": []
            }
