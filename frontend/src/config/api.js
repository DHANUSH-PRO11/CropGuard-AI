/**
 * API configuration for AgroNex
 *
 * In Vercel multi-service deployment, the frontend and backend share the same domain:
 * - Production: API_BASE_URL defaults to '' (same-origin relative path /api/*).
 * - Development: API_BASE_URL defaults to 'http://localhost:8000' (or proxied via Vite dev server).
 * - Override anytime by defining the VITE_API_URL environment variable.
 */
export const API_BASE_URL =
  import.meta.env.VITE_API_URL !== undefined && import.meta.env.VITE_API_URL !== ''
    ? import.meta.env.VITE_API_URL
    : import.meta.env.DEV
      ? 'http://localhost:8000'
      : '';

export default API_BASE_URL;
