import { createContext, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { clearSession } from '../services/api';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

const PROTECTED_PATH = /^\/(espace|admin)(\/|$)/;

export function AuthProvider({ children }) {
  const nav = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!localStorage.getItem('access'));

  const loadMe = async () => {
    try { setUser((await api.get('/auth/me/')).data); }
    catch { clearSession(); setUser(null); }
    finally { setLoading(false); }
  };
  useEffect(() => { if (localStorage.getItem('access')) loadMe(); }, []);

  // Session terminée (jeton absent, expiré ou invalide) : on oublie l'utilisateur et, sur une page protégée,
  // on redirige vers la connexion en REMPLAÇANT l'entrée d'historique (le bouton « Retour » ne la retrouve pas).
  const endSession = () => {
    setUser(null);
    if (PROTECTED_PATH.test(window.location.pathname)) nav('/connexion', { replace: true, state: { sessionEnded: true } });
  };

  // Sécurité du bouton « Retour » : page restaurée depuis le cache avant/arrière du navigateur, ou déconnexion dans un autre onglet.
  useEffect(() => {
    const onPageShow = (e) => { if (e.persisted) (localStorage.getItem('access') ? loadMe() : endSession()); };
    const onStorage = (e) => { if ((e.key === 'access' || e.key === null) && !localStorage.getItem('access')) endSession(); };
    window.addEventListener('pageshow', onPageShow);
    window.addEventListener('storage', onStorage);
    return () => { window.removeEventListener('pageshow', onPageShow); window.removeEventListener('storage', onStorage); };
  }, []); // eslint-disable-line

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login/', { email, password });
    localStorage.setItem('access', data.access);
    localStorage.setItem('refresh', data.refresh);
    setUser(data.user);
    return data.user;
  };
  const logout = async () => {
    try { await api.post('/auth/logout/', { refresh: localStorage.getItem('refresh') }); } catch { /* ignore */ }
    clearSession();
    setUser(null);
  };
  // Déconnexion complète : jeton révoqué côté serveur, session effacée du navigateur, puis page de connexion
  // sans possibilité de revenir en arrière (l'entrée d'historique est remplacée, voir useBlockBack sur la page Connexion).
  const signOut = async () => {
    await logout();
    nav('/connexion', { replace: true, state: { loggedOut: true } });
  };
  const isStaff = user && ['ADMIN', 'RECEPTIONNISTE'].includes(user.role);
  const isAdmin = user?.role === 'ADMIN';
  const home = isStaff ? '/admin' : '/espace';

  return <AuthContext.Provider value={{ user, loading, login, logout, signOut, endSession, loadMe, isStaff, isAdmin, home }}>{children}</AuthContext.Provider>;
}
