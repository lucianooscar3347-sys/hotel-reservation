import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AboutModal from '../components/AboutModal';

export default function PublicLayout() {
  const { user, signOut, home } = useAuth();
  const loc = useLocation();
  const [scrolled, setScrolled] = useState(false);
  const [about, setAbout] = useState(false);

  // Ombre de la barre de navigation dès que la page défile
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }); }, [loc.pathname]);

  return (
    <>
      <nav className={`navbar navbar-expand-md site-nav sticky-top${scrolled ? ' is-scrolled' : ''}`}>
        <div className="container">
          <Link className="navbar-brand" to="/">🏨 Grand Hôtel</Link>
          <div className="d-flex flex-wrap gap-2 align-items-center justify-content-end">
            <NavLink className="nav-link" to="/chambres">Chambres</NavLink>
            <NavLink className="nav-link" to="/disponibilite">Disponibilités</NavLink>
            <button type="button" className="nav-link nav-about" onClick={() => setAbout(true)} aria-haspopup="dialog">À propos</button>
            {user ? (<>
              <Link className="btn btn-brand btn-sm" to={home}>Mon espace</Link>
              <button className="btn btn-outline-brand btn-sm" onClick={signOut}>Déconnexion</button>
            </>) : (<>
              <Link className="btn btn-outline-brand btn-sm" to="/connexion">Connexion</Link>
              <Link className="btn btn-brand btn-sm" to="/inscription">Inscription</Link>
            </>)}
          </div>
        </div>
      </nav>
      <main key={loc.pathname} className="page-enter" style={{ minHeight: '70vh' }}><Outlet /></main>
      <footer className="site-footer py-4 mt-5 text-center small">© Grand Hôtel · Antananarivo — Tous les prix sont en ariary (Ar)</footer>
      {about && <AboutModal onClose={() => setAbout(false)} />}
    </>
  );
}
