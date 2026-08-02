// In dev, this stays "/api" and Vite's proxy (see vite.config.ts) forwards
// it to http://localhost:8000. In production, frontend and backend are
// deployed separately (e.g. Vercel + Render) with no shared origin to
// proxy through, so VITE_API_BASE_URL must be set at build time to the
// deployed backend's full URL -- see frontend/.env.example.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
