// Use a relative same-origin path in production, and an env var or default local URL in development
export const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://127.0.0.1:8000');
