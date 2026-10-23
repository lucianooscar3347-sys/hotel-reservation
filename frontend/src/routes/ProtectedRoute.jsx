import { useEffect } from 'react';
import { Navigate, useLocation, useNavigationType } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

let lastCheck = 0; // évite de revérifier plusieurs fois la session pour une même navigation (routes imbriquées)

export default function ProtectedRoute({ roles, children }) {
  const { user, loading, loadMe, endSession, home } = useAuth();
  const location = useLocation();
  const navType = useNavigationType();
  const hasToken = !!localStorage.getItem('access');

  // Bouton « Retour » / « Suivant » du navigateur (navigation POP) : la session est revérifiée auprès du serveur.
  useEffect(() => {
    if (navType === 'POP' && user && hasToken && Date.now() - lastCheck > 1000) { lastCheck = Date.now(); loadMe(); }
  }, [location.key]); // eslint-disable-line
  // Jeton disparu (déconnexion, autre onglet…) alors qu'un utilisateur est encore en mémoire : on nettoie.
  useEffect(() => { if (user && !hasToken) endSession(); }); // eslint-disable-line

  if (loading) return <div className="text-center p-5"><div className="spinner-border" /></div>;
  if (!user || !hasToken) return <Navigate to="/connexion" state={{ from: location, sessionEnded: true }} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={home} replace />;
  return children;
}
