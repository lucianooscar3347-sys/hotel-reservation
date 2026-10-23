// Validation côté navigateur : retour immédiat à l'utilisateur. Le serveur applique les MÊMES règles (backend/apps/common/validators.py).
// Chaque fonction retourne '' si la valeur est valide, sinon le message à afficher sous le champ.
import { PRIX_MINIMUM_NUIT } from '../services/api';

export const NB_NUITS_MAX = 60;
export const NB_VOYAGEURS_MAX = 20;

export const clean = (v) => String(v ?? '').trim().replace(/\s+/g, ' ');
const hasControlChars = (v) => /[\u0000-\u001f\u007f-\u009f]/.test(v);

const pad = (n) => String(n).padStart(2, '0');
export const toISO = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const todayISO = () => toISO(new Date());
export const addDays = (iso, n) => { const d = new Date(`${iso}T00:00:00`); d.setDate(d.getDate() + n); return toISO(d); };
export const nightsBetween = (a, b) => Math.round((new Date(`${b}T00:00:00`) - new Date(`${a}T00:00:00`)) / 86400000);

export const required = (v, label = 'Ce champ') => (clean(v) ? '' : `${label} est obligatoire.`);

export function validateName(v, label = 'Ce champ') {
  const s = clean(v);
  if (!s) return `${label} est obligatoire.`;
  if (hasControlChars(s)) return 'Caractères non autorisés.';
  if (s.length < 2) return `${label} doit contenir au moins 2 caractères.`;
  if (s.length > 100) return `${label} ne peut pas dépasser 100 caractères.`;
  if (!/^\p{L}+(?:[ '’-]\p{L}+)*$/u.test(s)) return "Utilisez uniquement des lettres, espaces, apostrophes et traits d'union.";
  return '';
}

export function validateEmail(v) {
  const s = clean(v);
  if (!s) return "L'adresse e-mail est obligatoire.";
  if (s.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@.]{2,}$/.test(s) || s.includes('..')) return 'Adresse e-mail invalide (ex. nom@exemple.com).';
  return '';
}

export function validatePhone(v, { optional = false } = {}) {
  const s = clean(v);
  if (!s) return optional ? '' : 'Le numéro de téléphone est obligatoire.';
  let n = s.replace(/[ .\-()]/g, '');
  if (n.startsWith('00')) n = `+${n.slice(2)}`;
  if (/^0\d{9}$/.test(n)) return '';
  if (/^\+[1-9]\d{7,14}$/.test(n)) return n.startsWith('+261') && n.length !== 13 ? 'Un numéro malgache doit contenir 9 chiffres après +261.' : '';
  return 'Numéro invalide. Exemples : 034 12 345 67 ou +261 34 12 345 67.';
}

// CIN : exactement 14 chiffres (même règle que backend/apps/common/validators.py : valider_cin).
export const CIN_LENGTH = 14;
export const digitsOnly = (v, max = CIN_LENGTH) => String(v ?? '').replace(/\D/g, '').slice(0, max);
export function validateCIN(v, { optional = true } = {}) {
  const s = clean(v);
  if (!s) return optional ? '' : 'Le numéro de CIN est obligatoire.';
  if (!/^[0-9]+$/.test(s)) return 'Le CIN ne doit contenir que des chiffres (sans espace ni lettre).';
  if (s.length !== CIN_LENGTH) return `Le CIN doit contenir exactement ${CIN_LENGTH} chiffres (${s.length} saisi${s.length > 1 ? 's' : ''}).`;
  return '';
}

export function validatePassword(v) {
  if (!v) return 'Le mot de passe est obligatoire.';
  if (v.length < 10) return 'Au moins 10 caractères.';
  if (v.length > 128) return '128 caractères maximum.';
  if (!/\p{L}/u.test(v) || !/\d/.test(v)) return 'Ajoutez au moins une lettre et un chiffre.';
  return '';
}

export function validateInt(v, { min, max, label = 'Cette valeur' }) {
  if (v === '' || v == null) return `${label} est obligatoire.`;
  if (!/^-?\d+$/.test(String(v).trim())) return `${label} doit être un nombre entier.`;
  const n = Number(v);
  if (n < min) return `${label} doit être au moins ${min}.`;
  if (n > max) return `${label} ne peut pas dépasser ${max}.`;
  return '';
}

export function validatePrixNuit(v) {
  if (v === '' || v == null) return 'Le prix par nuit est obligatoire.';
  const n = Number(v);
  if (!Number.isFinite(n)) return 'Prix invalide.';
  if (n < PRIX_MINIMUM_NUIT) return `Le prix minimum par nuit est de ${PRIX_MINIMUM_NUIT.toLocaleString('fr-FR')} Ar.`;
  if (n > 99999999) return 'Prix trop élevé.';
  return '';
}

export function validateArrivee(a) {
  if (!a) return "La date d'arrivée est obligatoire.";
  if (a < todayISO()) return "La date d'arrivée ne peut pas être dans le passé.";
  return '';
}

export function validateDepart(a, d) {
  if (!d) return 'La date de départ est obligatoire.';
  if (a && d <= a) return "La date de départ doit être postérieure à la date d'arrivée.";
  if (a && nightsBetween(a, d) > NB_NUITS_MAX) return `Un séjour ne peut pas dépasser ${NB_NUITS_MAX} nuits.`;
  return '';
}
