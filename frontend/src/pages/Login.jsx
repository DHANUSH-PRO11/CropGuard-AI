import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Leaf, Eye, EyeOff, Lock, Mail, User, ArrowRight, ShieldCheck, AlertCircle, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { API_BASE_URL } from '../config/api';

export default function Login() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  const isRegister = location.pathname.includes('register');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    identifier: '',
    mobile: '',
    email: '',
    password: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);

    const endpoint = isRegister ? `${API_BASE_URL}/api/auth/register` : `${API_BASE_URL}/api/auth/login`;

    const cleanMobile = isRegister
      ? formData.mobile.trim()
      : formData.identifier.trim();

    const cleanEmail = isRegister && formData.email.trim()
      ? formData.email.trim().toLowerCase()
      : null;

    const payload = isRegister
      ? {
          name: formData.name.trim() || 'Farmer',
          mobile: cleanMobile,
          email: cleanEmail,
          password: formData.password,
          preferred_language: i18n.language || 'en'
        }
      : {
          username: formData.identifier.trim(),
          password: formData.password
        };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed. Please check your credentials.');
      }

      if (isRegister) {
        // Auto-login after successful registration
        const loginRes = await fetch(`${API_BASE_URL}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: cleanMobile,
            password: formData.password
          })
        });
        const loginData = await loginRes.json();
        if (loginData.access_token) {
          localStorage.setItem('agronex_token', loginData.access_token);
          localStorage.setItem('agronex_user', JSON.stringify(loginData.user || data));
        }
      } else {
        if (data.access_token) {
          localStorage.setItem('agronex_token', data.access_token);
        }
        if (data.user) {
          localStorage.setItem('agronex_user', JSON.stringify(data.user));
        }
      }

      navigate('/dashboard');
    } catch (err) {
      console.error('Auth error:', err);
      setErrorMsg(err.message || 'An error occurred during authentication.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] py-8 px-4">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/95 backdrop-blur-md p-7 sm:p-9 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 w-full max-w-md relative overflow-hidden"
      >
        {/* Decorative Top Accent */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-600"></div>

        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-inner">
            <Leaf size={30} className="text-emerald-600" />
          </div>

          <h2 className="text-2xl font-bold text-slate-900 tracking-tight font-display">
            {isRegister
              ? (i18n.language === 'ta' ? 'புதிய கணக்கை உருவாக்கவும்' : 'Create AgroNex Account')
              : (i18n.language === 'ta' ? 'மீண்டும் வருக!' : 'Welcome Back!')
            }
          </h2>

          <p className="text-slate-500 text-xs sm:text-sm mt-1">
            {isRegister
              ? (i18n.language === 'ta' ? 'உங்கள் பயிர்களை பாதுகாக்க இப்போதே இணையுங்கள்' : 'Join AgroNex to safeguard your farm and yield')
              : (i18n.language === 'ta' ? 'உங்கள் பயிர்களை பாதுகாக்க உள்நுழையவும்' : 'Log in to protect and monitor your crops')
            }
          </p>
        </div>

        {/* Error message banner */}
        {errorMsg && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-2 text-red-800 text-xs font-semibold animate-fadeIn">
            <AlertCircle size={16} className="text-red-600 flex-shrink-0" />
            <span className="flex-1">{errorMsg}</span>
            <button type="button" onClick={() => setErrorMsg(null)} className="text-red-500 hover:text-red-700 font-bold ml-1">✕</button>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Optional Name field if on register route */}
          {isRegister && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 ml-1">
                {i18n.language === 'ta' ? 'முழு பெயர்' : 'Full Name'}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User size={18} />
                </div>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={i18n.language === 'ta' ? "உங்கள் பெயர்" : "e.g. Ramesh Kumar"}
                  className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3.5 pl-10 pr-4 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-sm transition-all"
                  required
                />
              </div>
            </div>
          )}

          {/* Registration Mode: Distinct Mobile and Optional Email fields */}
          {isRegister ? (
            <>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 ml-1">
                  {i18n.language === 'ta' ? 'மொபைல் எண் (10 இலக்கங்கள்)' : 'Mobile Number (10 digits)'}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail size={18} />
                  </div>
                  <input
                    type="tel"
                    value={formData.mobile}
                    onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                    placeholder={i18n.language === 'ta' ? "எ.கா. 9876543210" : "e.g. 9876543210"}
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3.5 pl-10 pr-4 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-sm transition-all"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 ml-1">
                  {i18n.language === 'ta' ? 'மின்னஞ்சல் (விருப்பத்தேர்வு)' : 'Email Address (Optional)'}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail size={18} />
                  </div>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder={i18n.language === 'ta' ? "farmer@example.com" : "farmer@example.com"}
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3.5 pl-10 pr-4 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-sm transition-all"
                  />
                </div>
              </div>
            </>
          ) : (
            /* Login Mode: Single Identifier field */
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 ml-1">
                {t('mobile_or_email')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail size={18} />
                </div>
                <input
                  type="text"
                  value={formData.identifier}
                  onChange={(e) => setFormData({ ...formData, identifier: e.target.value })}
                  placeholder={t('mobile_or_email')}
                  className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3.5 pl-10 pr-4 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-sm transition-all"
                  required
                />
              </div>
            </div>
          )}

          {/* Password field */}
          <div>
            <div className="flex items-center justify-between mb-1.5 ml-1">
              <label className="block text-xs font-semibold text-slate-700">
                {t('password')}
              </label>
              {!isRegister && (
                <button
                  type="button"
                  onClick={() => alert(i18n.language === 'ta' ? 'கடவுச்சொல் மீட்டமைப்பு உங்கள் தொலைபேசி எண்ணிற்கு அனுப்பப்படும்.' : 'Password reset link will be sent to your mobile or email.')}
                  className="text-emerald-700 hover:text-emerald-800 text-xs font-semibold hover:underline"
                >
                  {i18n.language === 'ta' ? 'கடவுச்சொல் மறந்ததா?' : 'Forgot?'}
                </button>
              )}
            </div>

            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock size={18} />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder={t('password')}
                className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3.5 pl-10 pr-12 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-sm transition-all"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Submit CTA */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 active:scale-[0.98] text-white py-3.5 rounded-2xl font-bold flex justify-center items-center gap-2 mt-6 transition-all shadow-md shadow-emerald-600/20 text-sm disabled:opacity-60 cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 size={17} className="animate-spin" />
                <span>{isRegister ? (i18n.language === 'ta' ? 'பதிவாகிறது...' : 'Creating account...') : (i18n.language === 'ta' ? 'உள்நுழைகிறது...' : 'Logging in...')}</span>
              </>
            ) : (
              <>
                <span>{isRegister ? t('register') : t('login')}</span>
                <ArrowRight size={17} />
              </>
            )}
          </button>
        </form>

        {/* Toggle between Login and Register */}
        <div className="mt-7 text-center text-xs text-slate-500">
          {isRegister ? (
            <p>
              {i18n.language === 'ta' ? 'ஏற்கனவே கணக்கு உள்ளதா? ' : 'Already have an AgroNex account? '}
              <Link to="/login" className="text-emerald-700 font-bold hover:underline">
                {t('login')}
              </Link>
            </p>
          ) : (
            <p>
              {t('dont_have_account').split('?')[0]}?{' '}
              <Link to="/register" className="text-emerald-700 font-bold hover:underline">
                {t('dont_have_account').split('?')[1] || t('register')}
              </Link>
            </p>
          )}
        </div>

        {/* Security badge */}
        <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
          <ShieldCheck size={14} className="text-emerald-600" />
          <span>{i18n.language === 'ta' ? 'பாதுகாப்பான விவசாய தரவு குறியாக்கம்' : '256-bit encrypted farming data'}</span>
        </div>
      </motion.div>
    </div>
  );
}
