import { useCallback, useMemo, useState } from 'react';

/**
 * Formulaire validé : erreurs affichées après le départ du champ (blur) ou à la soumission, effacées dès que
 * l'utilisateur corrige, erreurs serveur rattachées au bon champ, soumission unique (anti double clic).
 * rules = { champ: (valeur, valeurs) => 'message' | '' }
 */
export default function useForm(initial, rules) {
  const [values, setValues] = useState(initial);
  const [touched, setTouched] = useState({});
  const [serverErrors, setServerErrors] = useState({});
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const clientErrors = useMemo(() => Object.fromEntries(
    Object.entries(rules).map(([k, fn]) => [k, fn(values[k], values)]).filter(([, m]) => m)), [values]); // eslint-disable-line

  const errors = {};
  Object.keys(rules).forEach((k) => { errors[k] = serverErrors[k] || ((attempted || touched[k]) ? clientErrors[k] || '' : ''); });

  const setValue = useCallback((k, v) => {
    setValues((o) => ({ ...o, [k]: v }));
    setServerErrors((s) => { if (!s[k]) return s; const { [k]: _omit, ...rest } = s; return rest; });
  }, []);

  const bind = (k) => ({
    name: k, value: values[k], error: errors[k],
    onChange: (e) => setValue(k, e.target.value),
    onBlur: () => setTouched((t) => ({ ...t, [k]: true })),
  });

  const handleSubmit = (fn) => async (e) => {
    e.preventDefault();
    if (submitting) return;
    setAttempted(true);
    if (Object.keys(clientErrors).length) {
      setTimeout(() => document.querySelector('[aria-invalid="true"]')?.focus(), 0);
      return;
    }
    setSubmitting(true);
    try { await fn(values); } finally { setSubmitting(false); }
  };

  return { values, setValue, setValues, errors, bind, handleSubmit, submitting, setServerErrors, valid: Object.keys(clientErrors).length === 0 };
}
