import { useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import StatusBadge from '../components/StatusBadge';
import AboutModal from '../components/AboutModal';

const CLIENT_MENU = [
  ['/espace', '📊 Tableau de bord', true], ['/espace/profil', '👤 Mon profil'], ['/espace/reservations', '📅 Mes réservations'],
  ['/espace/reservations/nouvelle', '➕ Nouvelle réservation'], ['/espace/paiements', '💳 Paiements'], ['/espace/factures', '🧾 Factures'],
];
const STAFF_MENU = [
  ['/admin', '📊 Dashboard', true, 'both'], ['/admin/chambres', '🛏️ Chambres', false, 'both'], ['/admin/categories', '🏷️ Catégories', false, 'admin'],
  ['/admin/equipements', '🧰 Équipements', false, 'admin'], ['/admin/services', '🛎️ Services', false, 'admin'], ['/admin/clients', '👥 Clients', false, 'both'],
  ['/admin/reservations', '📅 Réservations', false, 'both'], ['/admin/paiements', '💳 Paiements', false, 'both'],
  ['/admin/factures', '🧾 Factures', false, 'both'], ['/admin/utilisateurs', '🔐 Utilisateurs', false, 'admin'],
  ['/admin/statistiques', '📈 Statistiques', false, 'admin'], ['/admin/profil', '👤 Mon profil', false, 'both'],
];

export default function DashboardLayout() {
  const { user, signOut, isStaff, isAdmin } = useAuth();
  const [open, setOpen] = useState(false); // menu ouvert (mobile)
  const [about, setAbout] = useState(false); // fenêtre « À propos » (PDF du MPD)
  // Menu réduit (ordinateur) : le choix est mémorisé dans le navigateur
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebar-collapsed') === '1');
  const toggleCollapsed = (e) => {
    e.stopPropagation();
    setCollapsed((c) => {
      localStorage.setItem('sidebar-collapsed', c ? '0' : '1');
      return !c;
    });
  };
  const loc = useLocation();
  const menu = isStaff ? STAFF_MENU.filter((m) => m[3] === 'both' || isAdmin) : CLIENT_MENU;
  const crumbs = loc.pathname.split('/').filter(Boolean);

  return (
    <div className="d-flex">
      <aside className={`sidebar p-3 ${open ? 'open' : ''} ${collapsed ? 'collapsed' : ''}`} onClick={() => setOpen(false)}>
        <Link to="/" className="sidebar-brand d-block text-white fs-5 fw-bold text-decoration-none mb-4" title="Grand Hôtel">
          <span>🏨</span><span className="brand-text"> Grand Hôtel</span>
        </Link>
        <nav className="nav flex-column">
          {menu.map(([to, label, end]) => {
            const [icon, ...words] = label.split(' ');
            const text = words.join(' ');
            return (
              <NavLink key={to} to={to} end={end} className="nav-link" title={text}>
                <span className="nav-icon">{icon}</span><span className="nav-text">{text}</span>
              </NavLink>
            );
          })}
        </nav>
        <button
          type="button"
          className="sidebar-toggle"
          onClick={toggleCollapsed}
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Agrandir le menu' : 'Réduire le menu'}
          title={collapsed ? 'Agrandir le menu' : 'Réduire le menu'}
        >
          <span className="arrow" aria-hidden="true">{collapsed ? '›' : '‹'}</span>
          <span className="nav-text">Réduire le menu</span>
        </button>
      </aside>
      <div className="flex-grow-1" style={{ minWidth: 0 }}>
        <header className="navbar topbar px-3 justify-content-between">
          <button className="btn btn-outline-secondary d-lg-none" onClick={() => setOpen(!open)}>☰</button>
          <nav aria-label="breadcrumb" className="d-none d-md-block">
            <ol className="breadcrumb mb-0">
              {crumbs.map((c, i) => <li key={i} className={`breadcrumb-item text-capitalize ${i === crumbs.length - 1 ? 'active' : ''}`}>{c}</li>)}
            </ol>
          </nav>
          <div className="d-flex align-items-center gap-2">
            <button type="button" className="btn btn-sm btn-outline-brand" onClick={() => setAbout(true)} aria-haspopup="dialog">À propos</button>
            <span className="small text-muted d-none d-sm-inline">{user.first_name} {user.last_name}</span> <StatusBadge value={user.role} />
            <button className="btn btn-sm btn-outline-secondary" onClick={signOut}>Déconnexion</button>
          </div>
        </header>
        <main key={loc.pathname} className="page-enter p-3 p-md-4"><Outlet /></main>
      </div>
      {about && <AboutModal onClose={() => setAbout(false)} />}
    </div>
  );
}
