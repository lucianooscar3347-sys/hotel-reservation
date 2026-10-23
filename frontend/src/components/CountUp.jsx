import { useEffect, useState } from 'react';

/** Compteur animé (0 → valeur) pour les chiffres du tableau de bord. Les valeurs non numériques sont affichées telles quelles. */
export default function CountUp({ value, duration = 900 }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!Number.isFinite(value) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setN(value); return undefined; }
    let raf; const t0 = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / duration);
      setN(Math.round(value * (1 - (1 - p) ** 3))); // décélération douce
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{Number.isFinite(n) ? n.toLocaleString('fr-FR') : n}</>;
}
