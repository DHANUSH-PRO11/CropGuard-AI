/**
 * API configuration for AgroNex
 *
 * Robust URL normalization:
 * - Trims whitespace
 * - Strips trailing slashes
 * - Strips accidental trailing '/api'
 * - Defaults to same-origin relative path in production or localhost:8000 in dev
 */
const getSanitizedBaseUrl = () => {
  const raw = import.meta.env.VITE_API_URL;
  if (raw !== undefined && raw !== null && typeof raw === 'string') {
    let clean = raw.trim().replace(/\/+$/, '');
    if (clean.toLowerCase().endsWith('/api')) {
      clean = clean.slice(0, -4).replace(/\/+$/, '');
    }
    return clean;
  }
  return import.meta.env.DEV ? 'http://localhost:8000' : '';
};

export const API_BASE_URL = getSanitizedBaseUrl();

export default API_BASE_URL;
