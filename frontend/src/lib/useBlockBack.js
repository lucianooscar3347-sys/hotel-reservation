import { useEffect } from 'react';

/**
 * Empêche le bouton « Retour » du navigateur de quitter la page tant que `active` est vrai
 * (utilisé sur la page de connexion juste après une déconnexion : impossible de revenir en arrière).
 * Principe : on ajoute une entrée à l'historique (history.pushState) et on la ré-ajoute à chaque retour (popstate).
 * L'utilisateur reste libre de naviguer avec les liens du site ; le blocage disparaît en quittant la page.
 */
export default function useBlockBack(active) {
  useEffect(() => {
    if (!active) return undefined;
    const lock = () => window.history.pushState(window.history.state, '', window.location.href);
    lock();
    window.addEventListener('popstate', lock);
    return () => window.removeEventListener('popstate', lock);
  }, [active]);
}
