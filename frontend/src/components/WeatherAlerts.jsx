import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { CloudSun, CloudRain, Wind, AlertTriangle, ThermometerSun, CheckCircle, RefreshCw } from 'lucide-react';
import { useLocation } from '../hooks/useLocation';
import { API_BASE_URL } from '../config/api';

export default function WeatherAlerts({ crop, condition }) {
  const { i18n } = useTranslation();
  const { location } = useLocation();
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isTamil = i18n.language === 'ta';

  const fetchWeatherForCoords = useCallback(async (lat, lon) => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = API_BASE_URL;
      let url = `${apiUrl}/api/weather/forecast?lat=${lat}&lon=${lon}`;
      if (crop) url += `&crop=${encodeURIComponent(crop)}`;
      if (condition) url += `&condition=${encodeURIComponent(condition)}`;

      const response = await fetch(url);
      if (!response.ok) throw new Error("Weather API failed");
      const data = await response.json();
      setWeatherData(data);
    } catch (err) {
      console.warn("WeatherAlerts fetch failed:", err);
      setError(isTamil ? "வானிலைத் தகவலைப் பெற முடியவில்லை." : "Weather information is temporarily unavailable.");
    } finally {
      setLoading(false);
    }
  }, [crop, condition, isTamil]);

  const handleRefresh = () => {
    const lat = location?.latitude || 11.0168;
    const lon = location?.longitude || 76.9558;
    fetchWeatherForCoords(lat, lon);
  };

  useEffect(() => {
    let isSubscribed = true;
    const lat = location?.latitude || 11.0168;
    const lon = location?.longitude || 76.9558;
    
    const timer = setTimeout(() => {
      if (isSubscribed) fetchWeatherForCoords(lat, lon);
    }, 0);

    const interval = setInterval(() => {
      if (isSubscribed) {
        fetchWeatherForCoords(lat, lon);
      }
    }, 3600000);
    return () => {
      isSubscribed = false;
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [location?.latitude, location?.longitude, fetchWeatherForCoords]);

  const getAlertIcon = (type) => {
    switch (type) {
      case 'rain': return <CloudRain size={24} />;
      case 'thunderstorm': return <AlertTriangle size={24} />;
      case 'wind': return <Wind size={24} />;
      case 'heat': return <ThermometerSun size={24} />;
      case 'humidity': return <CloudRain size={24} />;
      default: return <AlertTriangle size={24} />;
    }
  };

  const getAlertColors = (level, type) => {
    if (type === 'rain') return "bg-blue-50 border-blue-100 text-blue-800";
    if (type === 'wind') return "bg-orange-50 border-orange-100 text-orange-800";
    if (type === 'thunderstorm') return "bg-red-50 border-red-100 text-red-800";
    if (type === 'heat') return "bg-red-50 border-red-100 text-red-800";
    return "bg-agronex-soft border-agronex-primary text-agronex-deep"; // default advisory
  };

  const getIconColor = (level, type) => {
    if (type === 'rain') return "text-blue-600";
    if (type === 'wind') return "text-orange-600";
    if (type === 'thunderstorm') return "text-red-600";
    if (type === 'heat') return "text-red-600";
    return "text-agronex-primary";
  };

  const formatTime = (isoString) => {
    if (!isoString) return "";
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(isTamil ? 'ta-IN' : 'en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoString;
    }
  };


  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-agronex-deep flex items-center gap-2 uppercase tracking-wide text-sm">
          <CloudSun size={18} /> {isTamil ? "வானிலை எச்சரிக்கைகள்" : "WEATHER ALERTS"}
        </h3>
        <button onClick={handleRefresh} disabled={loading} className="text-gray-400 hover:text-agronex-primary transition-colors cursor-pointer" title="Refresh weather alerts">
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {loading && !weatherData ? (
        <div className="bg-white p-6 rounded-2xl border border-gray-100 text-center shadow-sm">
          <div className="w-8 h-8 border-4 border-agronex-soft border-t-agronex-primary rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-sm text-gray-500 font-medium">Checking local forecast...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 p-5 rounded-2xl border border-red-100 text-center">
          <p className="text-red-600 font-medium text-sm mb-3">{error}</p>
          <button 
            onClick={handleRefresh}
            className="bg-red-100 text-red-700 px-4 py-2 rounded-lg text-sm font-bold hover:bg-red-200 transition-colors cursor-pointer"
          >
            {isTamil ? "மீண்டும் முயற்சி செய்" : "Enable Location / Retry"}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {weatherData?.alerts && weatherData.alerts.length > 0 ? (
            weatherData.alerts.map((alert, idx) => (
              <div key={idx} className={`p-4 rounded-2xl border ${getAlertColors(alert.level, alert.type)} shadow-sm`}>
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 ${getIconColor(alert.level, alert.type)}`}>
                    {getAlertIcon(alert.type)}
                  </div>
                  <div className="flex-grow">
                    <h4 className="font-bold text-lg mb-1">{isTamil ? alert.title_ta : alert.title_en}</h4>
                    {alert.start && (
                      <p className="text-xs font-semibold opacity-75 mb-2">{formatTime(alert.start)}</p>
                    )}
                    <p className="text-sm leading-relaxed mb-3">{isTamil ? alert.message_ta : alert.message_en}</p>
                    
                    <div className="flex flex-wrap gap-2 text-xs">
                      {alert.probability !== undefined && (
                        <span className="bg-white/50 px-2 py-1 rounded font-semibold">Probability: {alert.probability}%</span>
                      )}
                      {alert.rain_mm !== undefined && (
                        <span className="bg-white/50 px-2 py-1 rounded font-semibold">Rainfall: {alert.rain_mm}mm</span>
                      )}
                      {alert.wind_speed !== undefined && (
                        <span className="bg-white/50 px-2 py-1 rounded font-semibold">Speed: {alert.wind_speed} km/h</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-black/5 text-[10px] text-right font-medium opacity-60">
                  {alert.source}
                </div>
              </div>
            ))
          ) : (
            <div className="bg-green-50 p-5 rounded-2xl border border-green-100 text-center shadow-sm">
              <CheckCircle size={28} className="text-green-500 mx-auto mb-2" />
              <h4 className="font-bold text-green-800 mb-1">{isTamil ? "குறிப்பிடத்தக்க வானிலை எச்சரிக்கைகள் இல்லை" : "No significant weather alerts"}</h4>
              <p className="text-sm text-green-600">Weather conditions look relatively normal for the forecast period.</p>
              <div className="mt-3 pt-3 border-t border-green-200/50 text-[10px] text-right font-medium text-green-600/60">
                Open-Meteo forecast
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
