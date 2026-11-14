from datetime import datetime
from typing import List, Dict, Any
from config import weather_thresholds as thresh

class WeatherAlertService:
    def generate_alerts(self, forecast: Dict[str, Any], crop: str = None, condition: str = None) -> List[Dict[str, Any]]:
        alerts = []
        
        # We look ahead for the next 24-48 hours
        hourly = forecast.get("hourly", {})
        times = hourly.get("time", [])
        
        if not times:
            return alerts
            
        precip_probs = hourly.get("precipitation_probability", [])
        precips = hourly.get("precipitation", [])
        weather_codes = hourly.get("weather_code", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        wind_gusts = hourly.get("wind_gusts_10m", [])
        temps = hourly.get("temperature_2m", [])
        humidities = hourly.get("relative_humidity_2m", [])
        
        # Only check the next 24 hours starting from current hour
        current = forecast.get("current", {})
        current_time_str = current.get("time", "")[:13]
        
        start_idx = 0
        for i, t in enumerate(times):
            if t.startswith(current_time_str) or t > current_time_str:
                start_idx = i
                break
                
        check_hours = min(start_idx + 24, len(times))
        
        def get_time_of_day(iso_time_str):
            if not iso_time_str:
                return "today"
            try:
                dt = datetime.fromisoformat(iso_time_str)
                hour = dt.hour
                if 5 <= hour < 12: return "morning"
                elif 12 <= hour < 17: return "afternoon"
                elif 17 <= hour < 21: return "evening"
                else: return "night"
            except:
                return "today"
                
        def get_time_of_day_ta(iso_time_str):
            if not iso_time_str:
                return "இன்று"
            try:
                dt = datetime.fromisoformat(iso_time_str)
                hour = dt.hour
                if 5 <= hour < 12: return "காலை"
                elif 12 <= hour < 17: return "பிற்பகல்"
                elif 17 <= hour < 21: return "மாலை"
                else: return "இரவு"
            except:
                return "இன்று"

        # 1. Rain Detection
        max_rain_prob = 0
        max_rain_prob_time = None
        
        for i in range(start_idx, check_hours):
            if precip_probs and precip_probs[i] > max_rain_prob:
                max_rain_prob = precip_probs[i]
                max_rain_prob_time = times[i]
                
        if max_rain_prob >= 70:
            tod_en = get_time_of_day(max_rain_prob_time)
            tod_ta = get_time_of_day_ta(max_rain_prob_time)
            alerts.append({
                "type": "rain",
                "level": "HIGH",
                "title_en": "High Chance of Rain",
                "title_ta": "மழை பெய்ய அதிக வாய்ப்பு உள்ளது",
                "message_en": f"Rain probability reaches {max_rain_prob}% during the forecast period. Consider planning irrigation and field activities accordingly.",
                "message_ta": f"முன்னறிவிப்பு காலத்தில் மழை வாய்ப்பு {max_rain_prob}% ஐ எட்டும். அதற்கேற்ப நீர்ப்பாசனம் மற்றும் களப்பணிகளைத் திட்டமிடுங்கள்.",
                "start": max_rain_prob_time,
                "probability": max_rain_prob,
                "source": "Open-Meteo forecast"
            })
            
        # 2. Thunderstorm Detection (Based strictly on WMO codes)
        storm_detected = False
        storm_time = None
        has_hail = False
        for i in range(start_idx, check_hours):
            code = weather_codes[i] if weather_codes else 0
            if code in [95, 96, 99]:
                storm_detected = True
                storm_time = times[i]
                if code in [96, 99]:
                    has_hail = True
                break
                
        if storm_detected:
            tod_en = get_time_of_day(storm_time)
            tod_ta = get_time_of_day_ta(storm_time)
            if has_hail:
                alerts.append({
                    "type": "thunderstorm",
                    "level": "HIGH",
                    "title_en": "Severe Weather Alert (Hail)",
                    "title_ta": "கடுமையான வானிலை (ஆலங்கட்டி மழை)",
                    "message_en": f"Hail and thunderstorms are indicated around {tod_en}. Protect vulnerable crops where possible.",
                    "message_ta": f"{tod_ta} நேரத்தில் ஆலங்கட்டி மற்றும் இடியுடன் கூடிய மழை பெய்யும். பலவீனமான பயிர்களைப் பாதுகாக்கவும்.",
                    "start": storm_time,
                    "source": "Open-Meteo forecast"
                })
            else:
                alerts.append({
                    "type": "thunderstorm",
                    "level": "WARNING",
                    "title_en": "Thunderstorm Warning",
                    "title_ta": "இடியுடன் கூடிய மழை எச்சரிக்கை",
                    "message_en": f"Thunderstorm conditions are forecast around {tod_en}. Avoid field work during the storm.",
                    "message_ta": f"{tod_ta} நேரத்தில் இடியுடன் கூடிய மழைக்கு வாய்ப்புள்ளது. வயல்வெளியில் வேலை செய்வதைத் தவிர்க்கவும்.",
                    "start": storm_time,
                    "source": "Open-Meteo forecast"
                })

        # 3. IMD Heavy Rainfall Risk (Cumulative 24h)
        total_24h_rain = sum(precips[start_idx:check_hours]) if precips else 0
        if total_24h_rain >= 64.5:
            alerts.append({
                "type": "heavy_rain",
                "level": "HIGH",
                "title_en": "IMD Heavy Rain Alert (Drainage Critical)",
                "title_ta": "கனமழை எச்சரிக்கை (வடிகால் வசதி அவசியம்)",
                "message_en": f"Heavy rainfall ({total_24h_rain:.1f} mm) forecast within 24h. Postpone all pesticide/fertilizer spraying, hold irrigation, and open drainage channels.",
                "message_ta": f"அடுத்த 24 மணி நேரத்தில் கனமழை ({total_24h_rain:.1f} மி.மீ) கணிக்கப்பட்டுள்ளது. மருந்து தெளிப்பதை ஒத்திவைத்து வடிகால் வசதியை உறுதி செய்யவும்.",
                "source": "Open-Meteo forecast"
            })
        elif total_24h_rain >= 35.0:
            alerts.append({
                "type": "moderate_rain",
                "level": "CAUTION",
                "title_en": "Moderate-to-Heavy Rain Caution",
                "title_ta": "மிதமான/கனமழை எச்சரிக்கை",
                "message_en": f"Accumulated rain ({total_24h_rain:.1f} mm) expected. Hold irrigation to conserve water and prevent waterlogging.",
                "message_ta": f"மழைப்பொழிவு ({total_24h_rain:.1f} மி.மீ) எதிர்பார்க்கப்படுகிறது. நீர்ப்பாசனத்தை நிறுத்தி வைக்கவும்.",
                "source": "Open-Meteo forecast"
            })

        # 4. Wind Gust Hazard (Spray Drift & Stalk Lodging)
        max_gust = max(wind_gusts[start_idx:check_hours]) if wind_gusts else 0
        if max_gust >= 50.0:
            alerts.append({
                "type": "strong_wind",
                "level": "HIGH",
                "title_en": "Severe Gale Wind Hazard",
                "title_ta": "கடுமையான பலத்த காற்று எச்சரிக்கை",
                "message_en": f"Wind gusts reaching {max_gust:.1f} km/h. Do not spray chemicals. Stake banana, sugarcane, and tall horticultural crops to prevent lodging.",
                "message_ta": f"காற்றின் வேகம் {max_gust:.1f} கி.மீ/மணி வரை வீசக்கூடும். மருந்து தெளிக்க வேண்டாம். வாழை, கரும்பு போன்ற பயிர்களுக்கு முட்டுக் கொடுக்கவும்.",
                "source": "Open-Meteo forecast"
            })
        elif max_gust >= 40.0:
            alerts.append({
                "type": "strong_wind",
                "level": "CAUTION",
                "title_en": "High Wind Spray Drift Warning",
                "title_ta": "பலத்த காற்று - தெளிப்பு எச்சரிக்கை",
                "message_en": f"Wind gusts up to {max_gust:.1f} km/h will cause severe spray drift and chemical loss. Postpone foliar spraying.",
                "message_ta": f"காற்றின் வேகம் {max_gust:.1f} கி.மீ/மணி வரை உள்ளதால் மருந்து காற்றில் அடித்துச் செல்லப்படும். தெளிப்பதைத் தவிர்க்கவும்.",
                "source": "Open-Meteo forecast"
            })

        # 5. Agronomic Disease Risk Indicators (Hutton Criteria & Micro-Climate Pathologies)
        crop_lower = (crop or "").lower()
        rh_90_hours = sum(1 for i in range(start_idx, check_hours) if humidities and humidities[i] >= 90)
        rh_85_hours = sum(1 for i in range(start_idx, check_hours) if humidities and humidities[i] >= 85)
        min_temp = min(temps[start_idx:check_hours]) if temps else 25.0
        max_temp = max(temps[start_idx:check_hours]) if temps else 30.0

        # Late Blight Risk (Tomato/Potato: Hutton/Smith criteria - min temp >= 10C and RH >= 90% for >= 6 hours)
        if ("tomato" in crop_lower or "potato" in crop_lower) and min_temp >= 10.0 and rh_90_hours >= 6:
            alerts.append({
                "type": "disease_risk",
                "level": "WARNING",
                "title_en": "Late Blight Environmental Risk (Hutton Criteria)",
                "title_ta": "இலைக்கருகல் நோய் சுற்றுச்சூழல் அபாயம்",
                "message_en": f"High humidity ({rh_90_hours}h above 90% RH) and mild temperatures ({min_temp:.1f}°C) favor Late Blight spore sporulation. Inspect lower canopy leaves.",
                "message_ta": f"அதிக ஈரப்பதம் ({rh_90_hours} மணிநேரம் >90%) இலைக்கருகல் பூஞ்சை பரவுவதற்கு சாதகமாக உள்ளது. இலைகளின் அடிப்பகுதியை ஆய்வு செய்யவும்.",
                "source": "Hutton Disease Risk Model"
            })

        # Blast Risk for Paddy / Rice (RH >= 85% for >= 8 hours and temp 20-30C)
        if ("paddy" in crop_lower or "rice" in crop_lower or "நெல்" in crop_lower) and 20.0 <= min_temp <= 30.0 and rh_85_hours >= 8:
            alerts.append({
                "type": "disease_risk",
                "level": "WARNING",
                "title_en": "Paddy Blast Fungal Threat Indicator",
                "title_ta": "நெல் குலை நோய் சாதக எச்சரிக்கை",
                "message_en": f"Prolonged leaf wetness ({rh_85_hours}h above 85% RH) creates optimal conditions for Pyricularia oryzae (Blast). Monitor leaf tips for spindle spots.",
                "message_ta": f"தொடர் ஈரப்பதம் குலை நோய் பரவ வாய்ப்பளிக்கிறது. இலை நுனிகளில் கண் வடிவ புள்ளிகள் உள்ளதா என கண்காணிக்கவும்.",
                "source": "Rice Blast Epidemiological Rule"
            })

        # Heat Stress (Tomato/Paddy flowering vulnerability at > 35C)
        if max_temp >= 35.0:
            alerts.append({
                "type": "heat_stress",
                "level": "CAUTION",
                "title_en": "Crop Heat Stress Alert",
                "title_ta": "பயிர் வெப்ப அலை எச்சரிக்கை",
                "message_en": f"High temperature peak of {max_temp:.1f}°C. Provide light afternoon irrigation to mitigate flower and fruit drop.",
                "message_ta": f"அதிகபட்ச வெப்பநிலை {max_temp:.1f}°C ஐ எட்டுகிறது. பூ மற்றும் பிஞ்சு உதிர்வதைத் தடுக்க மாலையில் லேசான பாசனம் செய்யவும்.",
                "source": "Open-Meteo forecast"
            })
                
        return alerts
