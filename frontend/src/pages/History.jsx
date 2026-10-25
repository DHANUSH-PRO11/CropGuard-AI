import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { 
  History as HistoryIcon, Search, ShieldCheck, AlertTriangle, 
  Trash2, Eye, Calendar, Sparkles, ArrowRight, RefreshCw, X, MessageSquare 
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function History() {
  const { i18n } = useTranslation();
  const isTamil = i18n.language === 'ta';
  const navigate = useNavigate();

  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL'); // ALL, HEALTHY, DISEASED, UNCERTAIN
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/crops/history`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRecords(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch analysis history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchHistory();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchHistory]);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm(isTamil ? 'இந்த பதிவை நீக்க விரும்புகிறீர்களா?' : 'Are you sure you want to delete this diagnosis record?')) {
      return;
    }
    setDeletingId(id);
    try {
      const res = await fetch(`${API_BASE_URL}/api/crops/history/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setRecords((prev) => prev.filter((r) => r.id !== id));
        if (selectedRecord && selectedRecord.id === id) {
          setSelectedRecord(null);
        }
      }
    } catch (err) {
      alert(err.message || 'Failed to delete record');
    } finally {
      setDeletingId(null);
    }
  };

  const handleAskCopilot = (record) => {
    // Navigate to Assistant with the context of this diagnosis
    navigate('/assistant', {
      state: {
        initialQuery: isTamil 
          ? `எனது ${record.crop} பயிரில் ${record.condition} கண்டறியப்பட்டது. என்ன செய்ய வேண்டும்?`
          : `My ${record.crop} had ${record.condition} detected. What management steps should I take now?`,
        context: {
          crop: record.crop,
          condition: record.condition,
          confidence: record.confidence,
          status: record.status,
          severity: record.severity,
          risk: record.risk
        }
      }
    });
  };

  // Filter calculations
  const filteredRecords = records.filter((r) => {
    const isHealthy = r.is_healthy || (r.condition && r.condition.toLowerCase().includes('healthy'));
    const isUncertain = r.status === 'Uncertain' || (r.confidence < 0.6);

    let matchesStatus = true;
    if (filterStatus === 'HEALTHY') matchesStatus = isHealthy;
    else if (filterStatus === 'DISEASED') matchesStatus = !isHealthy;
    else if (filterStatus === 'UNCERTAIN') matchesStatus = isUncertain;

    const q = searchQuery.toLowerCase().trim();
    if (!q) return matchesStatus;

    const matchesQuery = 
      (r.crop && r.crop.toLowerCase().includes(q)) ||
      (r.condition && r.condition.toLowerCase().includes(q)) ||
      (r.severity && r.severity.toLowerCase().includes(q));

    return matchesStatus && matchesQuery;
  });

  // Summary Metrics
  const totalScans = records.length;
  const healthyCount = records.filter((r) => r.is_healthy || (r.condition && r.condition.toLowerCase().includes('healthy'))).length;
  const diseasedCount = totalScans - healthyCount;
  const highConfCount = records.filter((r) => (r.confidence || 0) >= 0.7).length;
  const highConfRate = totalScans > 0 ? Math.round((highConfCount / totalScans) * 100) : 100;

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-gradient-to-br from-[#081c15] via-[#1b4332] to-[#2d6a4f] rounded-3xl p-6 sm:p-8 text-white shadow-md relative overflow-hidden">
        <div className="absolute -right-8 -bottom-8 w-48 h-48 bg-emerald-400/10 rounded-full blur-2xl pointer-events-none" />
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-emerald-200 text-xs font-semibold mb-3 border border-white/20">
            <HistoryIcon size={13} className="text-emerald-300" />
            <span>{isTamil ? 'முந்தைய பரிசோதனைகள்' : 'Diagnostic Audit Log'}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight font-display mb-2">
            {isTamil ? 'பயிர் நோய் பகுப்பாய்வு வரலாறு' : 'Crop Diagnosis History'}
          </h1>
          <p className="text-emerald-100/90 text-sm leading-relaxed">
            {isTamil
              ? 'உங்கள் நிலத்தில் மேற்கொள்ளப்பட்ட அனைத்து பயிர் இலை ஸ்கேன்கள், நோய் அறிகுறிகள், AI நம்பகத்தன்மை அளவுகள் மற்றும் பாதுகாப்பு வழிகாட்டல்களின் சேமிக்கப்பட்ட பதிவுகள்.'
              : 'Review your past plant health inspections, pathology observations, AI confidence scores, and follow-up agricultural advisories.'}
          </p>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-2xs">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block mb-1">
            {isTamil ? 'மொத்த ஸ்கேன்கள்' : 'Total Scans'}
          </span>
          <p className="text-2xl font-black text-gray-900 font-display">{totalScans}</p>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-emerald-100 shadow-2xs">
          <span className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider block mb-1">
            {isTamil ? 'ஆரோக்கியமானவை' : 'Healthy Leaves'}
          </span>
          <p className="text-2xl font-black text-emerald-600 font-display">{healthyCount}</p>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-amber-100 shadow-2xs">
          <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider block mb-1">
            {isTamil ? 'நோய் பாதிப்பு' : 'Diseased / At Risk'}
          </span>
          <p className="text-2xl font-black text-amber-600 font-display">{diseasedCount}</p>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-blue-100 shadow-2xs">
          <span className="text-[11px] font-bold text-blue-700 uppercase tracking-wider block mb-1">
            {isTamil ? 'உயர் நம்பிக்கை விகிதம்' : 'High Confidence'}
          </span>
          <p className="text-2xl font-black text-blue-700 font-display">{highConfRate}%</p>
        </div>
      </div>

      {/* Search & Status Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={isTamil ? 'பயிர் அல்லது நோயின் பெயரை தேடவும்...' : 'Filter by crop, disease name, or severity...'}
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 shadow-2xs"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          {[
            { id: 'ALL', labelEn: 'All', labelTa: 'அனைத்தும்' },
            { id: 'HEALTHY', labelEn: 'Healthy', labelTa: 'ஆரோக்கியம்' },
            { id: 'DISEASED', labelEn: 'Diseased', labelTa: 'பாதிப்பு' },
            { id: 'UNCERTAIN', labelEn: 'Uncertain', labelTa: 'உறுதியற்றவை' }
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setFilterStatus(pill.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                filterStatus === pill.id
                  ? 'bg-emerald-700 text-white shadow-xs'
                  : 'bg-white hover:bg-gray-100 text-gray-600 border border-gray-200/70'
              }`}
            >
              {isTamil ? pill.labelTa : pill.labelEn}
            </button>
          ))}
          <button
            onClick={fetchHistory}
            className="p-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-600 rounded-xl transition-all shadow-2xs"
            title="Refresh History"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin text-emerald-600' : 'text-gray-500'} />
          </button>
        </div>
      </div>

      {/* History Records List */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white p-5 rounded-2xl border border-gray-100 animate-pulse space-y-3">
              <div className="h-5 bg-gray-200 rounded-md w-1/2"></div>
              <div className="h-4 bg-gray-100 rounded-md w-3/4"></div>
              <div className="h-10 bg-gray-50 rounded-xl"></div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center space-y-3">
          <AlertTriangle size={32} className="text-red-500 mx-auto" />
          <h3 className="font-bold text-red-900">{isTamil ? 'பதிவுகளை ஏற்றுவதில் பிழை' : 'Failed to Load History'}</h3>
          <p className="text-xs text-red-700">{error}</p>
          <button
            onClick={fetchHistory}
            className="px-4 py-2 bg-red-600 text-white rounded-xl text-xs font-bold hover:bg-red-700"
          >
            {isTamil ? 'மீண்டும் முயற்சிக்கவும்' : 'Retry'}
          </button>
        </div>
      ) : filteredRecords.length === 0 ? (
        <div className="bg-white rounded-3xl border border-gray-200/80 p-10 text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <Sparkles size={28} />
          </div>
          <div>
            <h3 className="font-extrabold text-gray-800 text-base">
              {isTamil ? 'பரிசோதனை பதிவுகள் எதுவும் இல்லை' : 'No diagnosis records found'}
            </h3>
            <p className="text-xs text-gray-500 max-w-md mx-auto mt-1">
              {isTamil
                ? 'உங்கள் பயிரின் இலையை ஸ்கேன் செய்து முதல் பரிசோதனையை மேற்கொள்ளுங்கள்.'
                : 'Take a snapshot of a plant leaf using CropCheck to perform your first AI diagnosis.'}
            </p>
          </div>
          <Link
            to="/crop"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition-all"
          >
            <span>{isTamil ? 'புதிய பயிர் பரிசோதனை' : 'Scan New Crop Leaf'}</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredRecords.map((rec, idx) => {
            const isHealthy = rec.is_healthy || (rec.condition && rec.condition.toLowerCase().includes('healthy'));
            const confPct = Math.round((rec.confidence || 0) * (rec.confidence <= 1.0 ? 100 : 1));
            const formattedDate = rec.created_at ? new Date(rec.created_at).toLocaleDateString(isTamil ? 'ta-IN' : 'en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            }) : 'Recent';

            return (
              <div
                key={rec.id || `rec-${idx}`}
                onClick={() => setSelectedRecord(rec)}
                className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-2xs hover:shadow-md hover:border-emerald-300 transition-all flex flex-col justify-between space-y-3 cursor-pointer group"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-extrabold text-gray-900 group-hover:text-emerald-700 transition-colors flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                      <span>{rec.crop}</span>
                    </span>
                    <span className="text-[11px] font-medium text-gray-400 flex items-center gap-1">
                      <Calendar size={12} />
                      <span>{formattedDate}</span>
                    </span>
                  </div>

                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="text-base font-extrabold text-gray-900 leading-snug">
                        {rec.condition}
                      </h4>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {isHealthy ? (
                          <span className="text-emerald-700 font-semibold flex items-center gap-1">
                            <ShieldCheck size={13} /> {isTamil ? 'ஆரோக்கியமான பயிர்' : 'Healthy Foliage'}
                          </span>
                        ) : (
                          <span className="text-amber-700 font-semibold">
                            {rec.severity ? `${rec.severity} severity` : 'Affected condition'}
                          </span>
                        )}
                      </p>
                    </div>

                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-bold shrink-0 ${
                        isHealthy
                          ? 'bg-emerald-100 text-emerald-800'
                          : confPct >= 70
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {confPct}% {isTamil ? 'பொருத்தம்' : 'Match'}
                    </span>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="pt-2 border-t border-gray-100 flex items-center justify-between">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedRecord(rec);
                    }}
                    className="text-xs font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1.5"
                  >
                    <Eye size={14} />
                    <span>{isTamil ? 'விவரம் பார்க்க' : 'View Details'}</span>
                  </button>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAskCopilot(rec);
                      }}
                      className="text-xs font-bold text-gray-600 hover:text-blue-700 flex items-center gap-1 px-2.5 py-1 bg-gray-50 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Ask Copilot"
                    >
                      <MessageSquare size={13} />
                      <span className="hidden sm:inline">{isTamil ? 'ஆலோசகர்' : 'Copilot'}</span>
                    </button>
                    {rec.id && (
                      <button
                        onClick={(e) => handleDelete(rec.id, e)}
                        disabled={deletingId === rec.id}
                        className="text-gray-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                        title="Delete Record"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detailed Modal View */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-xl border border-gray-100 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-200/60">
                  {selectedRecord.crop}
                </span>
                <h3 className="text-xl font-extrabold text-gray-900 mt-1 font-display">
                  {selectedRecord.condition}
                </h3>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-100"
              >
                <X size={20} />
              </button>
            </div>

            <div className="bg-[#F8FAF9] p-4 rounded-2xl border border-gray-100 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500 font-semibold">{isTamil ? 'AI நம்பிக்கை:' : 'AI Confidence:'}</span>
                <strong className="text-gray-900 font-bold">
                  {Math.round((selectedRecord.confidence || 0) * (selectedRecord.confidence <= 1.0 ? 100 : 1))}%
                </strong>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 font-semibold">{isTamil ? 'மாதிரி நிலை:' : 'Evaluation Status:'}</span>
                <strong className="text-gray-900 font-bold">{selectedRecord.status || 'Verified'}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 font-semibold">{isTamil ? 'அபாய நிலை:' : 'Risk Assessment:'}</span>
                <strong className="text-gray-900 font-bold">{selectedRecord.risk || 'Normal'}</strong>
              </div>
            </div>

            <div className="p-3 bg-amber-50/80 border border-amber-200/80 rounded-xl text-xs text-amber-900 flex items-start gap-2">
              <AlertTriangle size={16} className="text-amber-700 shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                {isTamil
                  ? 'களத்தில் பூச்சிக்கொல்லி மருந்துகளை பயன்படுத்துவதற்கு முன்பு வேளாண் அலுவலர் பரிந்துரையை பெறவும்.'
                  : 'Always refer to product label instructions and local extension officer guidelines before spraying.'}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-2 pt-2">
              <button
                onClick={() => handleAskCopilot(selectedRecord)}
                className="flex-1 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-xs transition-all"
              >
                <MessageSquare size={15} />
                <span>{isTamil ? 'ஆலோசகரிடம் கேட்கவும்' : 'Consult Copilot with This Scan'}</span>
              </button>
              <button
                onClick={() => setSelectedRecord(null)}
                className="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-bold"
              >
                {isTamil ? 'மூடு' : 'Close'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
