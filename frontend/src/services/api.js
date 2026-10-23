import axios from 'axios';

export const CURRENCY = 'Ar';
// Doit rester identique à PRIX_MINIMUM_NUIT (backend/apps/common/constants.py) : le serveur reste l'autorité.
export const PRIX_MINIMUM_NUIT = 20000;
// Format unique « 20 000 Ar » (espaces insécables : le montant ne se coupe jamais en fin de ligne).
export const money = (v) => `${Math.round(Number(v || 0)).toLocaleString('fr-FR').replace(/[\u202f\u00a0]/g, '\u00a0')}\u00a0${CURRENCY}`;

// Supprime uniquement les jetons de connexion (les préférences d'affichage, comme le menu réduit, sont conservées).
export const clearSession = () => { localStorage.removeItem('access'); localStorage.removeItem('refresh'); };

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api' });

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('access');
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

let refreshing = null; // évite plusieurs refresh simultanés
api.interceptors.response.use((r) => r, async (err) => {
  const orig = err.config;
  const isAuthCall = orig?.url?.includes('/auth/login/') || orig?.url?.includes('/auth/refresh/');
  if (err.response?.status === 401 && !orig._retry && !isAuthCall && localStorage.getItem('refresh')) {
    orig._retry = true;
    try {
      refreshing = refreshing || axios.post(`${api.defaults.baseURL}/auth/refresh/`, { refresh: localStorage.getItem('refresh') });
      const { data } = await refreshing;
      refreshing = null;
      localStorage.setItem('access', data.access);
      if (data.refresh) localStorage.setItem('refresh', data.refresh);
      orig.headers.Authorization = `Bearer ${data.access}`;
      return api(orig);
    } catch (e) {
      refreshing = null;
      clearSession();
      // replace : la page protégée ne reste pas dans l'historique, le bouton « Retour » ne peut pas y revenir.
      window.location.replace('/connexion?session=expiree');
    }
  }
  return Promise.reject(err);
});

export const errMsg = (err) => {
  const d = err.response?.data;
  if (!err.response) return 'Erreur réseau : le serveur est injoignable. Vérifiez votre connexion puis réessayez.';
  if (err.response.status === 429) return 'Trop de tentatives. Patientez une minute avant de réessayer.';
  if (err.response.status >= 500 || !d || typeof d === 'string') return 'Erreur serveur : réessayez dans quelques instants.';
  if (d.detail) return d.detail;
  if (Array.isArray(d)) return d.join(' ');
  return Object.entries(d).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`).join(' | ');
};

const aplatir = (v) => (Array.isArray(v) ? v.map(aplatir).join(' ') : v && typeof v === 'object' ? Object.values(v).map(aplatir).join(' ') : String(v));

/** Sépare les erreurs DRF par champ { fields: {nom: message}, global: message } pour les afficher sous les champs. */
export const parseApiError = (err) => {
  const d = err.response?.data;
  if (!err.response || err.response.status >= 500 || err.response.status === 429 || !d || typeof d !== 'object' || Array.isArray(d)) {
    return { fields: {}, global: errMsg(err) };
  }
  const fields = {};
  let global = d.detail || '';
  Object.entries(d).forEach(([k, v]) => {
    if (k === 'detail') return;
    if (k === 'non_field_errors') global = [global, aplatir(v)].filter(Boolean).join(' ');
    else fields[k] = aplatir(v);
  });
  return { fields, global };
};

export default api;
