import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Bell, CloudRain, Wind, Building, CheckCheck, X } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function NotificationCenter() {
  const { i18n } = useTranslation();
  const isTamil = i18n.language === 'ta';
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const dropdownRef = useRef(null);

  useEffect(() => {
    // Generate active notifications from weather and scheme rules
    const loadNotifications = async () => {
      const items = [];

      // Farmer alert preferences from Profile
      let prefs = { notify_weather: true, notify_spray: true, notify_schemes: true };
      try {
        const storedPrefs = localStorage.getItem('agronex_alert_preferences');
        if (storedPrefs) prefs = { ...prefs, ...JSON.parse(storedPrefs) };
      } catch {
        // use default active alerts
      }

      try {
        // Fetch weather for regional default or cached location if weather or spray alerts enabled
        if (prefs.notify_weather || prefs.notify_spray) {
          const res = await fetch(`${API_BASE_URL}/api/weather?lat=11.0168&lon=76.9558`);
          if (res.ok) {
            const w = await res.json();

            // Weather alerts
            if (prefs.notify_weather) {
              const alerts = w.alerts || [];
              alerts.forEach((alert, idx) => {
                items.push({
                  id: `weather_${idx}`,
                  type: 'weather',
                  title: isTamil ? alert.title_ta || 'வானிலை எச்சரிக்கை' : alert.title_en || 'Weather Alert',
                  message: isTamil ? alert.message_ta : alert.message_en,
                  link: '/weather',
                  time: 'Active now',
                  read: false
                });
              });
            }

            // Spray safety alerts
            if (prefs.notify_spray) {
              const current = w.current || {};
              const precip = current.precipitation || 0;
              const wind = current.wind_speed || 0;
              if (precip > 2.0) {
                items.push({
                  id: 'spray_rain',
                  type: 'spray',
                  title: isTamil ? 'மருந்து தெளிக்க வேண்டாம்' : 'Do Not Spray Alert',
                  message: isTamil
                    ? 'தற்போதைய மழை காரணமாக பூச்சிக்கொல்லி தெளிப்பு உடனடியாக நிறுத்தப்பட வேண்டும்.'
                    : 'Active precipitation detected. Chemical spraying is restricted due to wash-off hazard.',
                  link: '/weather',
                  time: 'Urgent',
                  read: false
                });
              } else if (wind > 25) {
                items.push({
                  id: 'spray_wind',
                  type: 'spray',
                  title: isTamil ? 'தெளிப்பு எச்சரிக்கை' : 'Spray Drift Caution',
                  message: isTamil
                    ? 'அதிக காற்று (>25 கி.மீ/மணி) காரணமாக தெளிப்பு மருந்து வீணாக வாய்ப்புள்ளது.'
                    : 'High wind speed (>25 km/h) creates chemical drift hazard. Spray with caution.',
                  link: '/weather',
                  time: 'Notice',
                  read: false
                });
              }
            }
          }
        }
      } catch (e) {
        console.warn('Weather notification lookup:', e);
      }

      // Add a scheme notification if scheme alerts enabled
      if (prefs.notify_schemes) {
        items.push({
          id: 'scheme_pmkisan',
          type: 'scheme',
          title: isTamil ? 'பிஎம்-கிசான் eKYC நினைவூட்டல்' : 'PM-KISAN eKYC Notice',
          message: isTamil
            ? 'அடுத்த தவணைத் தொகையைப் பெற உங்கள் ஆதார் eKYC மற்றும் நில ஆவணங்களை சரிபார்க்கவும்.'
            : 'Ensure Aadhaar eKYC is active on pmkisan.gov.in for the upcoming Rs.2,000 installment.',
          link: '/schemes',
          time: 'Policy',
          read: false
        });
      }

      // Check if user previously dismissed
      const readIds = JSON.parse(localStorage.getItem('agronex_read_notifications') || '[]');
      const marked = items.map((it) => ({
        ...it,
        read: readIds.includes(it.id)
      }));

      setNotifications(marked);
      setUnreadCount(marked.filter((n) => !n.read).length);
    };

    loadNotifications();
  }, [isTamil]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const markAllRead = () => {
    const allIds = notifications.map((n) => n.id);
    localStorage.setItem('agronex_read_notifications', JSON.stringify(allIds));
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);
  };

  const getIcon = (type) => {
    switch (type) {
      case 'weather':
        return <CloudRain size={16} className="text-blue-600" />;
      case 'spray':
        return <Wind size={16} className="text-amber-600" />;
      default:
        return <Building size={16} className="text-emerald-600" />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-full hover:bg-gray-100 text-gray-600 hover:text-agronex-deep transition-all cursor-pointer"
        title="Notifications"
        aria-label="View notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 bg-emerald-600 text-white rounded-full text-[9px] font-black flex items-center justify-center animate-pulse">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-2xl shadow-xl border border-gray-100 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="p-3.5 bg-gray-50/80 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-extrabold text-gray-900 font-display">
                {isTamil ? 'அறிவிப்புகள்' : 'Notifications'}
              </span>
              {unreadCount > 0 && (
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-800">
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-[11px] font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 cursor-pointer"
              >
                <CheckCheck size={13} />
                <span>{isTamil ? 'அனைத்தும் படித்தவை' : 'Mark all read'}</span>
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-gray-100">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-xs text-gray-400">
                {isTamil ? 'புதிய அறிவிப்புகள் இல்லை' : 'No active notifications'}
              </div>
            ) : (
              notifications.map((item) => (
                <Link
                  key={item.id}
                  to={item.link}
                  onClick={() => setOpen(false)}
                  className={`p-3.5 flex items-start gap-3 hover:bg-emerald-50/50 transition-colors block ${
                    !item.read ? 'bg-emerald-50/20' : ''
                  }`}
                >
                  <div className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center shrink-0 mt-0.5">
                    {getIcon(item.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1 mb-0.5">
                      <h4 className="text-xs font-bold text-gray-900 truncate">{item.title}</h4>
                      <span className="text-[10px] text-gray-400 font-medium shrink-0">{item.time}</span>
                    </div>
                    <p className="text-[11px] text-gray-600 line-clamp-2 leading-relaxed">{item.message}</p>
                  </div>
                </Link>
              ))
            )}
          </div>

          <div className="p-2.5 bg-gray-50 border-t border-gray-100 flex justify-between items-center text-[11px]">
            <Link
              to="/profile"
              onClick={() => setOpen(false)}
              className="text-gray-500 hover:text-emerald-700 font-medium"
            >
              {isTamil ? 'அறிவிப்பு அமைப்புகள்' : 'Alert Preferences'}
            </Link>
            <button
              onClick={() => setOpen(false)}
              className="text-gray-400 hover:text-gray-600 font-medium flex items-center gap-1"
            >
              <X size={12} />
              <span>{isTamil ? 'மூடு' : 'Close'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
