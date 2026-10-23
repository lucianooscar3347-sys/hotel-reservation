import { useEffect } from 'react';

// Éléments qui apparaissent en fondu au défilement (les cartes de chambres ont déjà leur propre animation).
const SELECTOR = 'main .card:not(.fade-in):not(.search-card), .empty-state';

/** Apparition progressive des cartes quand elles entrent à l'écran. Inactif si l'utilisateur préfère moins d'animations. */
export default function useReveal() {
  useEffect(() => {
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;

    const done = (el) => { el.classList.remove('reveal-target', 'reveal-in'); el.style.animationDelay = ''; };
    const io = new IntersectionObserver((entries) => {
      entries.filter((e) => e.isIntersecting).forEach((entry, i) => {
        const el = entry.target;
        io.unobserve(el);
        el.style.animationDelay = `${Math.min(i, 8) * 70}ms`; // cascade quand plusieurs cartes apparaissent ensemble
        el.classList.add('reveal-in');
        el.addEventListener('animationend', (ev) => { if (ev.target === el) done(el); }, { once: false });
        setTimeout(() => done(el), 1500); // filet de sécurité : l'élément ne reste jamais masqué
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });

    const watch = (el) => {
      if (el.classList.contains('reveal-in')) return;
      el.classList.add('reveal-target');
      io.observe(el);
    };
    const scan = (root) => {
      if (root.matches?.(SELECTOR)) watch(root);
      root.querySelectorAll?.(SELECTOR).forEach(watch);
    };
    scan(document.body);
    const mo = new MutationObserver((muts) => muts.forEach((m) => m.addedNodes.forEach((n) => n.nodeType === 1 && scan(n))));
    mo.observe(document.body, { childList: true, subtree: true });
    return () => {
      mo.disconnect(); io.disconnect();
      document.querySelectorAll('.reveal-target').forEach(done);
    };
  }, []);
}
