import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { 
  User, Phone, MapPin, Sprout, Globe, Bell, 
  Save, CheckCircle2, AlertCircle, Database, LogOut, Loader2 
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function Profile() {
  const { i18n } = useTranslation();
  const isTamil = i18n.language === 'ta';
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: '' }

  const [formData, setFormData] = useState({
    name: 'Arun Kumar',
    mobile: '9876543210',
    location: 'Coimbatore, Tamil Nadu',
    farm_size: 3.5,
    primary_crop: 'Paddy, Tomato',
    preferred_language: 'ta',
    notify_weather: true,
    notify_spray: true,
    notify_schemes: true
  });

  const token = localStorage.getItem('agronex_token');

  useEffect(() => {
    const fetchProfile = async () => {
      setLoading(true);
      try {
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE_URL}/api/profile`, { headers });
        if (res.ok) {
          const data = await res.json();
          const prefs = {
            notify_weather: data.notify_weather !== undefined ? Boolean(data.notify_weather) : true,
            notify_spray: data.notify_spray !== undefined ? Boolean(data.notify_spray) : true,
            notify_schemes: data.notify_schemes !== undefined ? Boolean(data.notify_schemes) : true
          };
          localStorage.setItem('agronex_alert_preferences', JSON.stringify(prefs));
          setFormData((prev) => ({
            ...prev,
            ...data,
            ...prefs
          }));
        }
      } catch (err) {
        console.warn('Profile fetch fallback to local defaults:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [token]);

  const handleChange = (field, val) => {
    setFormData((prev) => ({ ...prev, [field]: val }));
  };

  const handleToggle = (field) => {
    setFormData((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE_URL}/api/profile`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          name: formData.name,
          mobile: formData.mobile,
          location: formData.location,
          farm_size: parseFloat(formData.farm_size) || 0,
          primary_crop: formData.primary_crop,
          preferred_language: formData.preferred_language,
          notify_weather: formData.notify_weather,
          notify_spray: formData.notify_spray,
          notify_schemes: formData.notify_schemes
        })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const updated = await res.json();

      // Also sync language if changed
      if (formData.preferred_language && formData.preferred_language !== i18n.language) {
        i18n.changeLanguage(formData.preferred_language);
      }

      // Update local storage user profile name
      const stored = localStorage.getItem('agronex_user');
      if (stored) {
        try {
          const u = JSON.parse(stored);
          u.name = updated.name || formData.name;
          localStorage.setItem('agronex_user', JSON.stringify(u));
        } catch {
          // ignore
        }
      }

      // Cache alert preferences for real-time notification filtering
      localStorage.setItem('agronex_alert_preferences', JSON.stringify({
        notify_weather: updated.notify_weather !== undefined ? Boolean(updated.notify_weather) : formData.notify_weather,
        notify_spray: updated.notify_spray !== undefined ? Boolean(updated.notify_spray) : formData.notify_spray,
        notify_schemes: updated.notify_schemes !== undefined ? Boolean(updated.notify_schemes) : formData.notify_schemes
      }));

      setFeedback({
        type: 'success',
        message: isTamil ? 'சுயவிவர அமைப்புகள் வெற்றிகரமாக சேமிக்கப்பட்டன!' : 'Profile and preferences updated successfully!'
      });
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to update profile'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    if (window.confirm(isTamil ? 'கணக்கிலிருந்து வெளியேற விரும்புகிறீர்களா?' : 'Are you sure you want to log out?')) {
      localStorage.removeItem('agronex_token');
      localStorage.removeItem('agronex_user');
      navigate('/login');
    }
  };

  return (
    <div className="space-y-6 pb-12 max-w-3xl mx-auto">
      {/* Header Banner */}
      <div className="bg-gradient-to-br from-[#081c15] via-[#1b4332] to-[#2d6a4f] rounded-3xl p-6 sm:p-8 text-white shadow-md relative overflow-hidden">
        <div className="absolute -right-8 -bottom-8 w-48 h-48 bg-emerald-400/10 rounded-full blur-2xl pointer-events-none" />
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-emerald-200 text-xs font-semibold mb-2 border border-white/20">
              <User size={13} className="text-emerald-300" />
              <span>{isTamil ? 'விவசாயி கணக்கு' : 'Farmer Settings'}</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight font-display">
              {formData.name || (isTamil ? 'விவசாயி' : 'Farmer')}
            </h1>
            <p className="text-emerald-100/90 text-xs sm:text-sm mt-0.5">
              {formData.location || 'Tamil Nadu, India'}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="self-start sm:self-auto inline-flex items-center gap-1.5 px-3.5 py-2 bg-white/15 hover:bg-white/25 border border-white/20 rounded-xl text-xs font-bold text-white transition-all cursor-pointer"
          >
            <LogOut size={14} />
            <span>{isTamil ? 'வெளியேறு' : 'Log Out'}</span>
          </button>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-2xl border flex items-center gap-2.5 text-xs font-bold ${
            feedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          {feedback.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{feedback.message}</span>
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-3xl p-8 border border-gray-100 flex items-center justify-center">
          <Loader2 size={28} className="animate-spin text-emerald-600" />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Farm & Personal Information */}
          <div className="bg-white rounded-3xl border border-gray-200/80 p-6 shadow-2xs space-y-4">
            <h2 className="text-base font-extrabold text-gray-900 flex items-center gap-2 font-display">
              <Sprout size={18} className="text-emerald-600" />
              <span>{isTamil ? 'பண்ணை மற்றும் தொடர்பு தகவல்கள்' : 'Farm & Contact Details'}</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  {isTamil ? 'முழு பெயர்' : 'Full Name'}
                </label>
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    value={formData.name || ''}
                    onChange={(e) => handleChange('name', e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-2.5 bg-gray-50/50 border border-gray-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  {isTamil ? 'மொபைல் எண்' : 'Mobile Number'}
                </label>
                <div className="relative">
                  <Phone size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="tel"
                    value={formData.mobile || ''}
                    onChange={(e) => handleChange('mobile', e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-2.5 bg-gray-50/50 border border-gray-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  {isTamil ? 'பண்ணை இருப்பிடம் / மாவட்டம்' : 'Farm Location / District'}
                </label>
                <div className="relative">
                  <MapPin size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    value={formData.location || ''}
                    onChange={(e) => handleChange('location', e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-gray-50/50 border border-gray-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  {isTamil ? 'நிலப்பரப்பு (ஏக்கர்)' : 'Farm Size (Acres)'}
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={formData.farm_size || 0}
                  onChange={(e) => handleChange('farm_size', e.target.value)}
                  className="w-full px-4 py-2.5 bg-gray-50/50 border border-gray-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 font-medium"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  {isTamil ? 'முதன்மை பயிர்கள் (கமாவால் பிரிக்கவும்)' : 'Primary Crops (comma separated)'}
                </label>
                <input
                  type="text"
                  value={formData.primary_crop || ''}
                  onChange={(e) => handleChange('primary_crop', e.target.value)}
                  placeholder="e.g. Paddy, Tomato, Cotton, Sugarcane"
                  className="w-full px-4 py-2.5 bg-gray-50/50 border border-gray-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  {isTamil ? 'விருப்பமான மொழி' : 'Preferred Language'}
                </label>
                <div className="relative">
                  <Globe size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                  <select
                    value={formData.preferred_language || 'en'}
                    onChange={(e) => handleChange('preferred_language', e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-gray-50/50 border border-gray-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 font-medium cursor-pointer"
                  >
                    <option value="en">English (Indian English)</option>
                    <option value="ta">தமிழ் (Tamil)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* User-Configurable Notification Preferences */}
          <div className="bg-white rounded-3xl border border-gray-200/80 p-6 shadow-2xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-extrabold text-gray-900 flex items-center gap-2 font-display">
                <Bell size={18} className="text-emerald-600" />
                <span>{isTamil ? 'எச்சரிக்கை & அறிவிப்பு அமைப்புகள்' : 'Agricultural Alert Preferences'}</span>
              </h2>
              <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">
                {isTamil ? 'உள்-செயலி அறிவிப்புகள்' : 'In-App Alerts'}
              </span>
            </div>

            <div className="divide-y divide-gray-100">
              {/* Weather Alert Toggle */}
              <div className="py-3 flex items-center justify-between gap-4">
                <div>
                  <h4 className="text-xs sm:text-sm font-bold text-gray-900">
                    {isTamil ? 'வானிலை மற்றும் மழை அறிவிப்புகள்' : 'Weather & Rainfall Alerts'}
                  </h4>
                  <p className="text-[11px] text-gray-500">
                    {isTamil
                      ? 'அதிக மழை (>70%) அல்லது இடியுடன் கூடிய மழை முன்னறிவிப்புகளின் போது அறிவிக்கப்படும்.'
                      : 'Notify when high rain (>70%) or thunderstorm conditions are detected for your farm location.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleToggle('notify_weather')}
                  className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors cursor-pointer shrink-0 ${
                    formData.notify_weather ? 'bg-emerald-600 justify-end' : 'bg-gray-300 justify-start'
                  }`}
                >
                  <span className="w-4 h-4 rounded-full bg-white shadow-xs" />
                </button>
              </div>

              {/* Spray Window Caution Toggle */}
              <div className="py-3 flex items-center justify-between gap-4">
                <div>
                  <h4 className="text-xs sm:text-sm font-bold text-gray-900">
                    {isTamil ? 'தெளிப்பு கால பாதுகாப்பு எச்சரிக்கைகள்' : 'Pesticide / Fertilizer Spray Alerts'}
                  </h4>
                  <p className="text-[11px] text-gray-500">
                    {isTamil
                      ? 'கனமழை அல்லது அதிக காற்று (>25 கி.மீ/மணி) காரணமாக தெளிப்பு தடைபடும் போது எச்சரிக்கும்.'
                      : 'Alert when precipitation (>2mm, >60%) or high wind (>25 km/h) makes chemical application hazardous.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleToggle('notify_spray')}
                  className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors cursor-pointer shrink-0 ${
                    formData.notify_spray ? 'bg-emerald-600 justify-end' : 'bg-gray-300 justify-start'
                  }`}
                >
                  <span className="w-4 h-4 rounded-full bg-white shadow-xs" />
                </button>
              </div>

              {/* Government Schemes Toggle */}
              <div className="py-3 flex items-center justify-between gap-4">
                <div>
                  <h4 className="text-xs sm:text-sm font-bold text-gray-900">
                    {isTamil ? 'புதிய அரசு திட்டங்கள் & மானிய அறிவிப்புகள்' : 'Government Subsidy & Scheme Updates'}
                  </h4>
                  <p className="text-[11px] text-gray-500">
                    {isTamil
                      ? 'பிஎம்-கிசான், பயிர் காப்பீடு மற்றும் புதிய தமிழக அரசு மானியங்கள் குறித்த தகவல்கள்.'
                      : 'Highlight new subsidy openings, PMFBY insurance deadlines, and KCC institutional credit schemes.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleToggle('notify_schemes')}
                  className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors cursor-pointer shrink-0 ${
                    formData.notify_schemes ? 'bg-emerald-600 justify-end' : 'bg-gray-300 justify-start'
                  }`}
                >
                  <span className="w-4 h-4 rounded-full bg-white shadow-xs" />
                </button>
              </div>
            </div>
          </div>

          {/* Database & Offline Resilience Status */}
          <div className="bg-[#F8FAF9] rounded-2xl border border-gray-200/80 p-4 flex items-center justify-between text-xs text-gray-600">
            <div className="flex items-center gap-2">
              <Database size={16} className="text-emerald-700 shrink-0" />
              <div>
                <span className="font-bold text-gray-800">Storage Backend: </span>
                <span>Hybrid Supabase Cloud with SQLite Offline Fallback (`agronex.db`)</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
              Active
            </span>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-700 hover:bg-emerald-800 active:scale-95 text-white rounded-xl text-xs sm:text-sm font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              <span>{saving ? (isTamil ? 'சேமிக்கப்படுகிறது...' : 'Saving...') : (isTamil ? 'அமைப்புகளைச் சேமி' : 'Save Changes')}</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
