import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, ArrowLeft, CheckCircle, Bot, ArrowRight, Volume2, VolumeX, Loader2, ChevronDown, ChevronUp, Activity } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import WeatherAlerts from '../components/WeatherAlerts';
import { API_BASE_URL } from '../config/api';

export default function Result() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const { result, imageUrl } = location.state || {};
  const isTamil = i18n.language === 'ta';
  const apiUrl = API_BASE_URL;

  const [copilotLoading, setCopilotLoading] = useState(false);
  const [copilotReply, setCopilotReply] = useState(null);
  const [copilotAudio, setCopilotAudio] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [activeQuestion, setActiveQuestion] = useState("");
  const [reportId] = useState(() => Math.floor(Date.now() / 1000).toString().slice(-6));
  const audioPlayerRef = useRef(null);

  if (!result) {
    return (
      <div className="text-center p-12 max-w-md mx-auto bg-white rounded-3xl shadow-xs border border-gray-100 my-8">
        <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
          <AlertTriangle size={32} />
        </div>
        <h3 className="text-lg font-bold text-gray-800 mb-1">
          {isTamil ? "முடிவுகள் எதுவும் இல்லை" : "No Analysis Results Found"}
        </h3>
        <p className="text-gray-500 text-xs mb-6">
          {isTamil ? "தயவுசெய்து முதலில் ஒரு பயிர் இலையை ஸ்கேன் செய்யவும்." : "Please scan or upload a crop leaf photo first."}
        </p>
        <Link 
          to="/crop" 
          className="inline-flex items-center justify-center gap-2 bg-agronex-primary text-white font-bold px-6 py-3 rounded-2xl shadow-xs hover:bg-agronex-deep transition-all text-xs"
        >
          <span>{isTamil ? "பயிரை ஸ்கேன் செய்க" : "Scan a Crop Leaf"}</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    );
  }

  const { crop, condition, confidence, is_healthy, top_predictions, status, quality_status, warning_message } = result;
  const confPercent = (confidence * 100).toFixed(1);
  const isUncertain = status === "Uncertain" || confidence < 0.60;
  const formattedCondition = (condition || '').replace(/_/g, ' ');

  const handleAskCopilot = async (questionText) => {
    setActiveQuestion(questionText);
    setCopilotLoading(true);
    setCopilotReply(null);
    setCopilotAudio(null);
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      setIsPlayingAudio(false);
    }

    try {
      const res = await fetch(`${apiUrl}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: questionText,
          crop_hint: crop,
          language: i18n.language || 'en',
          context: {
            crop: crop,
            condition: condition,
            confidence: confPercent,
            status: status,
            quality_status: quality_status || "Passed"
          }
        })
      });

      if (res.ok) {
        const data = await res.json();
        setCopilotReply(data);
        if (data.audio_base64) {
          setCopilotAudio(`data:audio/wav;base64,${data.audio_base64}`);
        }
      }
    } catch (err) {
      console.error("Copilot query failed:", err);
    } finally {
      setCopilotLoading(false);
    }
  };

  const toggleAudio = () => {
    if (!copilotAudio) return;
    if (isPlayingAudio && audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      setIsPlayingAudio(false);
    } else {
      const audio = new Audio(copilotAudio);
      audioPlayerRef.current = audio;
      setIsPlayingAudio(true);
      audio.onended = () => setIsPlayingAudio(false);
      audio.onerror = () => setIsPlayingAudio(false);
      audio.play().catch(() => setIsPlayingAudio(false));
    }
  };

  return (
    <div className="max-w-2xl mx-auto pb-12 space-y-6">
      {/* Top Bar with Back Button */}
      <div className="flex items-center justify-between">
        <Link 
          to="/dashboard" 
          className="inline-flex items-center text-xs font-bold text-gray-500 hover:text-agronex-deep transition-colors bg-white px-3 py-1.5 rounded-full border border-gray-100 shadow-xs"
        >
          <ArrowLeft size={14} className="mr-1" />
          <span>{isTamil ? "முகப்புக்குத் திரும்பு" : "Dashboard"}</span>
        </Link>
        <span className="text-[11px] font-semibold text-gray-400">
          ID: #{reportId}
        </span>
      </div>

      {/* Main Diagnostic Card */}
      <div className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100">
        {/* Status Header Banner */}
        <div className={`p-6 sm:p-8 text-center text-white relative overflow-hidden ${
          is_healthy 
            ? 'bg-gradient-to-br from-emerald-600 via-emerald-700 to-teal-800' 
            : isUncertain 
              ? 'bg-gradient-to-br from-amber-500 via-orange-600 to-amber-700' 
              : 'bg-gradient-to-br from-red-600 via-rose-700 to-amber-800'
        }`}>
          <div className="relative z-10">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 text-xs font-bold uppercase tracking-wider backdrop-blur-xs mb-3 border border-white/20">
              {is_healthy 
                ? (isTamil ? "ஆரோக்கியமான பயிர்" : "Healthy Crop") 
                : (isTamil ? "நோய் கண்டறியப்பட்டது" : "Condition Detected")}
            </span>

            <h2 className="text-2xl sm:text-3xl font-black font-display tracking-tight leading-snug">
              {crop}: {formattedCondition}
            </h2>
            <p className="text-white/80 text-xs mt-1 font-medium">
              {status} • {confPercent}% match
            </p>
          </div>
        </div>

        {/* Low Confidence Warning Box */}
        {isUncertain && (
          <div className="m-4 p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start gap-3 text-xs text-amber-900">
            <AlertTriangle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="font-bold">{isTamil ? "கவனிக்கவும்: குறைந்த நம்பிக்கை நிலை" : "Low Confidence Observation"}</strong>
              <p className="mt-0.5 text-amber-800 leading-relaxed">
                {warning_message || (isTamil 
                  ? "மாதிரி கணிப்பு உறுதிப்படுத்தப்பட்ட நோய் அல்ல. வேளாண்மை உதவி அலுவலர் அல்லது KVK மூலம் உறுதிப்படுத்துவது அவசியம்." 
                  : "Visual observation is not a clinical diagnosis. Ground verification by an agricultural extension officer (KVK) is strongly advised.")}
              </p>
            </div>
          </div>
        )}

        <div className="p-6 sm:p-8 space-y-6">
          {/* Diagnostic Snapshot with Uploaded Leaf Thumbnail */}
          {imageUrl && (
            <div className="flex items-center gap-4 bg-gray-50 p-3 rounded-2xl border border-gray-100">
              <img src={imageUrl} alt="Crop Leaf" className="w-16 h-16 object-cover rounded-xl border border-gray-200" />
              <div>
                <p className="text-xs font-bold text-gray-800">{crop} Leaf Analysis</p>
                <p className="text-[11px] text-gray-500">Quality: <span className="font-semibold text-emerald-700">{quality_status || "Passed"}</span></p>
                <p className="text-[11px] text-gray-500">Diagnosis Status: <span className="font-semibold">{status}</span></p>
              </div>
            </div>
          )}

          {/* Model Confidence Bar */}
          <div>
            <div className="flex justify-between text-xs font-bold text-gray-700 mb-1.5">
              <span>Model Prediction Confidence</span>
              <span className="text-agronex-deep">{confPercent}%</span>
            </div>
            <div className="w-full bg-gray-200 h-2.5 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-1000 ${
                  confidence > 0.85 ? 'bg-emerald-500' : confidence > 0.6 ? 'bg-amber-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(10, confidence * 100))}%` }}
              />
            </div>
          </div>

          {/* Differential Diagnoses / Alternative Possibilities */}
          {top_predictions && top_predictions.length > 1 && (
            <div className="bg-gray-50/90 p-4 rounded-2xl border border-gray-100 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-gray-700">
                <span>{isTamil ? "மாற்று கணிப்புகள் (Differential Diagnoses)" : "Differential Diagnoses"}</span>
                <span className="text-[11px] text-gray-400 font-normal">Top {top_predictions.length} ranked</span>
              </div>
              <div className="space-y-1.5">
                {top_predictions.slice(1, 4).map((pred, idx) => {
                  const pName = (pred.class_name || "").replace(/___/g, " — ").replace(/_/g, " ");
                  const pPct = ((pred.confidence || 0) * 100).toFixed(1);
                  return (
                    <div key={idx} className="flex justify-between items-center text-xs text-gray-600 bg-white p-2 rounded-xl border border-gray-100/80">
                      <span className="truncate pr-2 font-medium">{pName}</span>
                      <span className="font-bold text-gray-700 flex-shrink-0">{pPct}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Actionable Recommendations Checklist */}
          <div>
            <h3 className="font-bold text-sm text-agronex-deep mb-2 font-display">
              {t('what_to_do')}
            </h3>
            <div className="space-y-2 bg-gray-50 p-4 rounded-2xl border border-gray-100 text-xs text-gray-700">
              <div className="flex items-start gap-2.5">
                <CheckCircle size={15} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <span>
                  {is_healthy 
                    ? "Maintain standard drip irrigation and scheduled balanced fertilizer intervals." 
                    : "Isolate heavily affected foliage to prevent spore dispersal to adjacent plants."}
                </span>
              </div>
              <div className="flex items-start gap-2.5">
                <CheckCircle size={15} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <span>
                  Check regional rainfall forecast below before applying any protective spray.
                </span>
              </div>
            </div>
          </div>

          {/* ------------------------------------------------------------- */}
          {/* AgroNex AI Copilot Grounded Follow-up Section */}
          {/* ------------------------------------------------------------- */}
          <div className="bg-gradient-to-br from-emerald-50/70 via-teal-50/40 to-slate-50 p-5 rounded-3xl border border-emerald-200/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
                  <Bot size={18} />
                </div>
                <div>
                  <h4 className="font-bold text-agronex-deep text-sm font-display">
                    {t('copilot_title')}
                  </h4>
                  <p className="text-[11px] text-gray-500">
                    {t('copilot_subtitle')}
                  </p>
                </div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full">
                AgentFoundry v1.0
              </span>
            </div>

            {/* Quick Prompt Pills */}
            <div className="flex flex-wrap gap-2 pt-1">
              <button
                onClick={() => handleAskCopilot(t('ask_spray'))}
                disabled={copilotLoading}
                className="text-xs px-3 py-1.5 bg-white hover:bg-emerald-600 hover:text-white text-emerald-800 font-semibold rounded-full border border-emerald-200 shadow-2xs transition-all disabled:opacity-50"
              >
                💧 {t('ask_spray')}
              </button>
              <button
                onClick={() => handleAskCopilot(t('ask_organic'))}
                disabled={copilotLoading}
                className="text-xs px-3 py-1.5 bg-white hover:bg-emerald-600 hover:text-white text-emerald-800 font-semibold rounded-full border border-emerald-200 shadow-2xs transition-all disabled:opacity-50"
              >
                🌿 {t('ask_organic')}
              </button>
              <button
                onClick={() => handleAskCopilot(t('ask_prevention'))}
                disabled={copilotLoading}
                className="text-xs px-3 py-1.5 bg-white hover:bg-emerald-600 hover:text-white text-emerald-800 font-semibold rounded-full border border-emerald-200 shadow-2xs transition-all disabled:opacity-50"
              >
                🛡️ {t('ask_prevention')}
              </button>
            </div>

            {/* Loading Indicator */}
            {copilotLoading && (
              <div className="flex items-center gap-2 p-4 bg-white/80 rounded-2xl border border-emerald-100 text-xs text-emerald-800 font-medium animate-pulse">
                <Loader2 size={16} className="animate-spin text-emerald-600" />
                <span>AgroNex Agent is evaluating local weather and agricultural rules...</span>
              </div>
            )}

            {/* Copilot Result Box */}
            {copilotReply && (
              <div className="bg-white p-4 sm:p-5 rounded-2xl border border-emerald-100 shadow-xs space-y-3">
                <div className="flex items-start justify-between gap-2 border-b border-gray-100 pb-2">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-emerald-700 tracking-wider">
                      Agent Consultation
                    </span>
                    <p className="text-xs font-bold text-gray-800 mt-0.5">"{activeQuestion}"</p>
                  </div>
                  {copilotAudio && (
                    <button
                      onClick={toggleAudio}
                      className="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-full text-xs font-bold transition-colors"
                    >
                      {isPlayingAudio ? <VolumeX size={14} /> : <Volume2 size={14} />}
                      <span>{isPlayingAudio ? "Pause" : "Listen"}</span>
                    </button>
                  )}
                </div>

                {/* Spray Window Banner */}
                {copilotReply.spray_advisory && (
                  <div className={`p-2.5 rounded-xl text-xs font-bold flex items-center gap-2 ${
                    copilotReply.spray_advisory.includes("DO NOT") 
                      ? "bg-red-50 text-red-800 border border-red-200"
                      : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  }`}>
                    <span>⚡</span>
                    <span>{copilotReply.spray_advisory}</span>
                  </div>
                )}

                {/* Recommendation Text */}
                <p className="text-xs sm:text-sm text-gray-700 whitespace-pre-line leading-relaxed font-normal">
                  {copilotReply.recommendation}
                </p>

                {/* Collapsible Execution Trace for Hackathon Transparency */}
                {copilotReply.execution_trace && (
                  <div className="pt-2 border-t border-gray-100">
                    <button
                      onClick={() => setShowTrace(!showTrace)}
                      className="flex items-center justify-between w-full text-[11px] font-bold text-gray-500 hover:text-emerald-700"
                    >
                      <span className="flex items-center gap-1">
                        <Activity size={12} className="text-emerald-600" />
                        {t('workflow_trace')} ({copilotReply.total_latency_ms} ms)
                      </span>
                      {showTrace ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>

                    {showTrace && (
                      <div className="mt-2 p-3 bg-gray-50 rounded-xl space-y-1.5 text-[11px] text-gray-600 font-mono">
                        {copilotReply.execution_trace.map((step, idx) => (
                          <div key={idx} className="flex justify-between items-center border-b border-gray-200/50 pb-1 last:border-none">
                            <span className="font-semibold text-gray-800">{step.node}</span>
                            <span>{step.duration_ms} ms • {step.status}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* CTA: Full Conversational Voice Assistant */}
          <Link 
            to="/assistant" 
            state={{ initialCropContext: result }}
            className="flex items-center justify-between p-4 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-700 text-white transition-all shadow-md hover:shadow-lg group"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/20 text-white flex items-center justify-center shadow-xs">
                <Bot size={20} />
              </div>
              <div>
                <h4 className="font-bold text-sm leading-tight">
                  {isTamil ? "முழு குரல் வழிகாட்டலுக்கு அக்ரோநெக்ஸ் உதவியாளர்" : "Open Full Voice Copilot Assistant"}
                </h4>
                <p className="text-[11px] text-emerald-100/90 font-medium">
                  {isTamil ? "நேரடி தமிழ் குரல் உரையாடல் மற்றும் ஆலோசனைகள்" : "Speak naturally in Tamil or English with live microphone"}
                </p>
              </div>
            </div>
            <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
          </Link>

          {/* Weather Alerts Module */}
          <div className="pt-2">
            <WeatherAlerts crop={crop} condition={condition} />
          </div>
        </div>
      </div>
    </div>
  );
}
