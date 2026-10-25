import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ChevronLeft, MapPin, Search, CloudRain, Wind, ThermometerSun, AlertTriangle, CloudSun, Droplets } from 'lucide-react';
import { useLocation } from '../hooks/useLocation';
import { API_BASE_URL } from '../config/api';

export default function Weather() {
  const { i18n } = useTranslation();
  const { location, loading: locLoading, error: locError, requestLocation, updateLocationManually } = useLocation();
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [searchMode, setSearchMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const isTamil = i18n.language === 'ta';

  const fetchWeather = useCallback(async (lat, lon) => {
    setWeatherLoading(true);
    try {
      const apiUrl = API_BASE_URL;
      const response = await fetch(`${apiUrl}/api/weather/forecast?lat=${lat}&lon=${lon}`);
      if (response.ok) {
        setWeather(await response.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setWeatherLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!location?.latitude || !location?.longitude) return;
    const timer = setTimeout(() => {
      fetchWeather(location.latitude, location.longitude);
    }, 0);
    return () => clearTimeout(timer);
  }, [location?.latitude, location?.longitude, fetchWeather]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    try {
      const res = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(searchQuery)}&count=1&language=en&format=json`);
      const data = await res.json();
      if (data.results && data.results.length > 0) {
        const place = data.results[0];
        updateLocationManually(place.latitude, place.longitude, place.name, place.admin1, place.country);
        setSearchMode(false);
      } else {
        alert("Location not found");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'rain': return <CloudRain size={24} />;
      case 'thunderstorm': return <AlertTriangle size={24} />;
      case 'wind': return <Wind size={24} />;
      case 'heat': return <ThermometerSun size={24} />;
      case 'humidity': return <Droplets size={24} />;
      default: return <AlertTriangle size={24} />;
    }
  };

  const getAlertColors = (type) => {
    if (type === 'rain') return "bg-blue-50 border-blue-200 text-blue-900";
    if (type === 'wind') return "bg-orange-50 border-orange-200 text-orange-900";
    if (type === 'thunderstorm' || type === 'heat') return "bg-red-50 border-red-200 text-red-900";
    return "bg-green-50 border-green-200 text-green-900";
  };

  return (
    <div className="pb-16 max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link 
          to="/dashboard" 
          className="inline-flex items-center text-xs font-bold text-gray-500 hover:text-agronex-deep transition-colors bg-white px-3 py-1.5 rounded-full border border-gray-100 shadow-xs"
        >
          <ChevronLeft size={16} className="mr-0.5" />
          <span>{isTamil ? "முகப்பு" : "Dashboard"}</span>
        </Link>
        <h1 className="text-xl font-extrabold text-agronex-deep font-display">
          {isTamil ? "பண்ணை வானிலை முன்னறிவிப்பு" : "Farm Weather Radar"}
        </h1>
        <div className="w-16"></div>
      </div>

      <div>
        {/* Location Section */}
        <div className="bg-white rounded-3xl p-5 shadow-xs border border-gray-100 mb-5">
          {!searchMode ? (
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
                  <MapPin size={20} />
                </div>
                <div>
                  <p className="text-[10px] font-extrabold text-gray-400 uppercase tracking-wider">
                    {isTamil ? "கண்காணிக்கப்படும் பண்ணை" : "MONITORED LOCATION"}
                  </p>
                  <h3 className="font-bold text-base text-agronex-deep">
                    {locLoading ? "Detecting location..." : location ? `${location.city}, ${location.state}` : "Unknown"}
                  </h3>
                </div>
              </div>
              <button 
                onClick={() => setSearchMode(true)} 
                className="text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200/50 px-3.5 py-2 rounded-xl transition-all"
              >
                {isTamil ? "மாற்று" : "Change City"}
              </button>
            </div>
          ) : (
            <form onSubmit={handleSearch} className="flex gap-2">
              <input 
                type="text" 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder={isTamil ? "நகரத்தின் பெயரை தட்டச்சு செய்க..." : "Search Indian city or district..."} 
                className="flex-grow bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500"
                autoFocus
              />
              <button 
                type="submit" 
                className="bg-agronex-primary hover:bg-agronex-deep text-white px-4 rounded-xl font-bold flex items-center justify-center transition-colors"
              >
                <Search size={18} />
              </button>
              <button 
                type="button" 
                onClick={() => setSearchMode(false)} 
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 rounded-xl text-xs font-bold transition-colors"
              >
                {isTamil ? "ரத்து" : "Cancel"}
              </button>
            </form>
          )}

          {/* Quick Regional Agricultural District Presets */}
          <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider shrink-0 mr-1">
              {isTamil ? "முக்கிய பகுதிகள்:" : "Agri Hubs:"}
            </span>
            {[
              { name: "Coimbatore", ta: "கோயம்புத்தூர்", lat: 11.0168, lon: 76.9558 },
              { name: "Thanjavur", ta: "தஞ்சாவூர்", lat: 10.7870, lon: 79.1378 },
              { name: "Madurai", ta: "மதுரை", lat: 9.9252, lon: 78.1198 },
              { name: "Salem", ta: "சேலம்", lat: 11.6643, lon: 78.1460 },
              { name: "Trichy", ta: "திருச்சி", lat: 10.7905, lon: 78.7047 }
            ].map((dist) => (
              <button
                key={dist.name}
                type="button"
                onClick={() => updateLocationManually(dist.lat, dist.lon, dist.name, "Tamil Nadu", "India")}
                className="px-2.5 py-1 bg-gray-50 hover:bg-emerald-50 hover:text-emerald-800 text-gray-600 rounded-lg font-medium whitespace-nowrap border border-gray-200/60 transition-all text-[11px] cursor-pointer"
              >
                {isTamil ? dist.ta : dist.name}
              </button>
            ))}
          </div>
        </div>

        {locError && (
          <div className="bg-amber-50 p-4 rounded-2xl border border-amber-200 flex items-center justify-between mb-5 text-xs text-amber-800">
            <span>{locError}</span>
            <button
              onClick={requestLocation}
              className="bg-amber-100 hover:bg-amber-200 text-amber-900 px-3 py-1.5 rounded-xl font-bold transition-colors cursor-pointer"
            >
              {isTamil ? "மீண்டும் முயற்சி" : "Retry GPS"}
            </button>
          </div>
        )}

        {weatherLoading ? (
          <div className="text-center py-12 bg-white rounded-3xl border border-gray-100 shadow-xs">
            <div className="w-10 h-10 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin mx-auto mb-3"></div>
            <p className="font-semibold text-gray-600 text-sm">
              {isTamil ? "நேரலை வானிலை தரவு பெறப்படுகிறது..." : "Fetching live agricultural weather radar..."}
            </p>
          </div>
        ) : weather && weather.current ? (
          <div className="space-y-6">
            {/* Current Weather Card */}
            <div className="bg-gradient-to-br from-[#0B5D3B] via-[#0f7249] to-[#16A36A] rounded-3xl p-6 sm:p-8 text-white shadow-lg relative overflow-hidden">
              <div className="relative z-10 flex justify-between items-start">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-white/15 text-emerald-100 inline-block mb-3 border border-white/20">
                    Live Farm Atmosphere
                  </span>
                  <div className="flex items-baseline gap-2">
                    <p className="text-5xl sm:text-6xl font-black font-display tracking-tight">
                      {Math.round(weather.current.temperature)}°
                    </p>
                    <span className="text-xl font-semibold opacity-70">C</span>
                  </div>
                  <p className="text-xl font-bold mt-1 text-emerald-100 font-display">
                    {isTamil && weather.condition_ta ? weather.condition_ta : weather.condition_en}
                  </p>
                </div>

                <div className="text-right">
                  <div className="w-14 h-14 rounded-2xl bg-white/15 backdrop-blur-md flex items-center justify-center text-white ml-auto mb-2 border border-white/20">
                    <CloudSun size={32} />
                  </div>
                  <p className="text-xs font-medium text-emerald-100">
                    Feels like {Math.round(weather.current.temperature + 2)}°C
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-white/15 relative z-10 text-xs">
                <div className="bg-black/15 backdrop-blur-xs p-2.5 rounded-xl border border-white/10">
                  <span className="opacity-70 text-[10px] uppercase font-bold block mb-0.5">Humidity</span>
                  <div className="flex items-center gap-1.5 font-bold text-sm">
                    <Droplets size={14} className="text-blue-300" />
                    <span>{weather.current.humidity}%</span>
                  </div>
                </div>

                <div className="bg-black/15 backdrop-blur-xs p-2.5 rounded-xl border border-white/10">
                  <span className="opacity-70 text-[10px] uppercase font-bold block mb-0.5">Wind Speed</span>
                  <div className="flex items-center gap-1.5 font-bold text-sm">
                    <Wind size={14} className="text-teal-300" />
                    <span>{weather.current.wind_speed} km/h</span>
                  </div>
                </div>

                <div className="bg-black/15 backdrop-blur-xs p-2.5 rounded-xl border border-white/10">
                  <span className="opacity-70 text-[10px] uppercase font-bold block mb-0.5">Spray Status</span>
                  <div className="flex items-center gap-1.5 font-bold text-sm">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    <span>{weather.current.wind_speed < 15 ? "Suitable" : "Careful"}</span>
                  </div>
                </div>

                <div className="bg-black/15 backdrop-blur-xs p-2.5 rounded-xl border border-white/10">
                  <span className="opacity-70 text-[10px] uppercase font-bold block mb-0.5">Updated</span>
                  <div className="font-semibold text-[11px] text-emerald-100 truncate">
                    {new Date(weather.last_updated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
              
              <CloudSun size={200} className="absolute -bottom-16 -right-16 opacity-10 pointer-events-none text-white" />
            </div>

            {/* Configured Agricultural Spray Safety Rule Engine */}
            {(() => {
              const precip = weather.current.precipitation || 0;
              const wind = weather.current.wind_speed || 0;
              let maxRainProb = 0;
              if (weather.hourly && weather.hourly.length > 0) {
                maxRainProb = Math.max(...weather.hourly.slice(0, 24).map(h => h.precipitation_probability || 0));
              }

              const isRainRisk = maxRainProb > 60 || precip > 2.0;
              const isWindRisk = wind > 25;

              let badgeColor = "bg-emerald-50 border-emerald-200 text-emerald-900";
              let badgeTitle = isTamil ? "தெளிப்புக்கு சாதகமான நேரம் (Safe Window)" : "Favorable Spray Window";
              let badgeMsg = isTamil 
                ? "அடுத்த 24 மணி நேரத்தில் குறைந்த காற்று மற்றும் குறைந்த மழை வாய்ப்பு (<60%)."
                : "Wind is moderate and rain probability is below 60% in the immediate 24-hour forecast.";

              if (isRainRisk) {
                badgeColor = "bg-red-50 border-red-200 text-red-900";
                badgeTitle = isTamil ? "தெளிக்க வேண்டாம் (Do Not Spray)" : "Unfavorable Spray Window (Rain Hazard)";
                badgeMsg = isTamil
                  ? `மழை வாய்ப்பு ${maxRainProb}% (>60%) அல்லது மழை அளவு >2 மி.மீ. மருந்து அடித்துச் செல்லப்படும் அபாயம்.`
                  : `Rain probability reaches ${maxRainProb}% (>60%) or precipitation >2mm. High chemical wash-off and runoff risk.`;
              } else if (isWindRisk) {
                badgeColor = "bg-amber-50 border-amber-200 text-amber-900";
                badgeTitle = isTamil ? "எச்சரிக்கையுடன் தெளிக்கவும் (Caution Spraying)" : "Caution Spraying (Drift Hazard)";
                badgeMsg = isTamil
                  ? `காற்றின் வேகம் ${wind} கி.மீ/மணி (>25 கி.மீ/மணி). மருந்து காற்றில் பரவி வீணாகும் அபாயம்.`
                  : `Wind speed is ${wind} km/h (>25 km/h). Significant risk of chemical drift to non-target areas.`;
              }

              return (
                <div className={`p-4 sm:p-5 rounded-3xl border ${badgeColor} space-y-2.5 shadow-2xs`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-white/70 border border-current">
                      {isTamil ? "தானியங்கி தெளிப்பு விதிமுறைகள்" : "Configured Agricultural Spray Rules"}
                    </span>
                    <span className="text-[10px] text-gray-500 font-medium">
                      {weather.offline_fallback ? "Offline Fallback" : "Live Open-Meteo Data"}
                    </span>
                  </div>
                  <div>
                    <h4 className="font-extrabold text-sm">{badgeTitle}</h4>
                    <p className="text-xs leading-relaxed opacity-90 mt-0.5">{badgeMsg}</p>
                  </div>
                  <div className="pt-2 border-t border-black/5 text-[11px] opacity-75 leading-relaxed">
                    <strong>{isTamil ? "முக்கிய அறிவிப்பு:" : "Regulatory Notice:"} </strong>
                    {isTamil
                      ? "வானிலை கணிப்புகள் எதிர்கால நிலைக்கு முழு உத்தரவாதம் அளிக்காது. பூச்சிக்கொல்லி லேபிளில் உள்ள வழிகாட்டுதல்கள், பாதுகாப்பு ஆடைகள் மற்றும் வட்டார வேளாண்மை அலுவலர் ஆலோசனைகளுக்கே முதன்மையான முன்னுரிமை."
                      : "Forecasts do not guarantee future conditions. Registered pesticide label instructions, safety buffer zones, and agricultural university guidelines supersede automated mathematical thresholds."}
                  </div>
                </div>
              );
            })()}

            {/* Today Hourly Forecast */}
            {weather.hourly && weather.hourly.length > 0 && (
              <div>
                <h3 className="font-extrabold text-base text-agronex-deep mb-3 font-display">
                  {isTamil ? "இன்றைய மணிநேர முன்னறிவிப்பு" : "Hourly Rain & Temperature Radar"}
                </h3>
                <div className="bg-white rounded-3xl border border-gray-100 shadow-xs overflow-hidden divide-y divide-gray-100">
                  {[weather.hourly[0], weather.hourly[3], weather.hourly[6], weather.hourly[9], weather.hourly[12]].filter(Boolean).map((hourData, idx) => {
                    const timeObj = new Date(hourData.time);
                    const timeStr = timeObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    return (
                      <div key={idx} className="flex items-center justify-between p-3.5 px-5 hover:bg-gray-50/60 transition-colors">
                        <span className="w-20 font-bold text-xs text-gray-700">{timeStr}</span>
                        <div className="flex items-center gap-1.5 text-blue-600 font-semibold text-xs">
                          <CloudRain size={15} />
                          <span>{hourData.precipitation_probability}% {isTamil ? "மழை" : "Rain"}</span>
                        </div>
                        <div className="w-16 text-right font-extrabold text-sm text-agronex-deep">
                          {Math.round(hourData.temperature)}°C
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Agricultural Weather Alerts */}
            <div>
              <h3 className="font-extrabold text-base text-agronex-deep mb-3 flex items-center gap-2 font-display">
                <AlertTriangle size={18} className="text-amber-500" />
                <span>{isTamil ? "வேளாண் வானிலை எச்சரிக்கைகள்" : "Farming Weather Advisories"}</span>
              </h3>
              
              <div className="space-y-3">
                {weather.alerts && weather.alerts.length > 0 ? (
                  weather.alerts.map((alert, idx) => (
                    <div key={idx} className={`p-4 rounded-2xl border ${getAlertColors(alert.type)} flex items-start gap-3.5 shadow-xs`}>
                      <div className="mt-1 text-emerald-700">{getAlertIcon(alert.type)}</div>
                      <div>
                        <h4 className="font-bold text-sm mb-0.5">{isTamil ? alert.title_ta : alert.title_en}</h4>
                        <p className="text-xs font-medium opacity-90 leading-relaxed mb-2">
                          {isTamil ? alert.message_ta : alert.message_en}
                        </p>
                        {alert.probability && (
                          <span className="inline-block bg-white/60 px-2 py-0.5 rounded-md text-[11px] font-bold">
                            {alert.probability}% Probability
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="bg-emerald-50/70 p-4 rounded-2xl border border-emerald-100 flex items-center gap-3 shadow-xs">
                    <div className="bg-emerald-100 p-2 rounded-xl text-emerald-700">
                      <CloudSun size={20} />
                    </div>
                    <div>
                      <h4 className="font-bold text-emerald-900 text-xs">
                        {isTamil ? "தற்போது குறிப்பிடத்தக்க வானிலை எச்சரிக்கைகள் இல்லை." : "✓ Normal weather conditions for crops."}
                      </h4>
                      <p className="text-[11px] text-emerald-700 font-medium">
                        {isTamil ? "பயிர்களுக்கு உகந்த வானிலை நிலவுகிறது." : "Forecast indicates favorable conditions for farming operations."}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 7 Day Forecast */}
            <div>
              <h3 className="font-extrabold text-base text-agronex-deep mb-3 font-display">
                {isTamil ? "அடுத்த 7 நாட்கள் முன்னறிவிப்பு" : "7-Day Regional Forecast"}
              </h3>
              <div className="bg-white rounded-3xl border border-gray-100 shadow-xs overflow-hidden divide-y divide-gray-100">
                {weather.forecast?.map((day, idx) => {
                  const dateObj = new Date(day.date);
                  const dayName = idx === 0 ? (isTamil ? 'இன்று' : 'Today') : dateObj.toLocaleDateString('en-US', { weekday: 'short' });
                  return (
                    <div key={idx} className="flex items-center justify-between p-3.5 px-5 hover:bg-gray-50/60 transition-colors">
                      <span className="w-18 font-bold text-xs text-gray-700">{dayName}</span>
                      <div className="flex items-center gap-1.5 text-blue-600 font-semibold text-xs">
                        <CloudRain size={14} />
                        <span>{day.precipitation_probability_mean}%</span>
                      </div>
                      <div className="w-24 text-right font-extrabold text-xs text-gray-800">
                        {Math.round(day.temperature_max)}° <span className="text-gray-400 font-medium ml-1">{Math.round(day.temperature_min)}°</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : weather && !weather.success ? (
          <div className="bg-red-50 p-6 rounded-3xl border border-red-100 text-center">
            <AlertTriangle className="text-red-400 mx-auto mb-3" size={32} />
            <h3 className="text-red-800 font-bold mb-1">
              {isTamil ? "நேரடி வானிலைத் தரவைப் பெற முடியவில்லை." : "Unable to fetch live weather data."}
            </h3>
            <p className="text-red-600 text-sm font-medium">
              {weather.error || (isTamil ? "தரவு இல்லை" : "Data unavailable")}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
