import { useEffect, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import api, { errMsg, money, parseApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Field from '../components/Field';
import useForm from '../lib/useForm';
import useBlockBack from '../lib/useBlockBack';
import {
  NB_VOYAGEURS_MAX, addDays, todayISO, validateArrivee, validateDepart, validateEmail, validateInt, validateName,
  validatePassword, validatePhone,
} from '../lib/validators';

const RoomImage = ({ room }) => (
  <div className="room-media">
    {room.image ? <img src={room.image} alt={`Chambre ${room.numero}`} loading="lazy" /> : <div className="room-placeholder" aria-hidden="true">🛏️</div>}
    <span className="price-tag">{money(room.prix_nuit)}<small> / nuit</small></span>
  </div>
);

function RoomCard({ room, qs = '', reserveQs = '' }) {
  const equip = room.equipements_detail || [];
  return (
    <div className="card room-card h-100 fade-in">
      <RoomImage room={room} />
      <div className="card-body d-flex flex-column">
        <div className="d-flex justify-content-between align-items-start gap-2">
          <h5 className="mb-1">Chambre {room.numero}</h5>
          <span className="badge badge-soft">{room.categorie_nom}</span>
        </div>
        <p className="text-muted small mb-2">{room.type_chambre} · {room.capacite} pers. · étage {room.etage}</p>
        <div className="chips mb-3">
          {equip.slice(0, 4).map((e) => <span key={e.id} className="chip">{e.nom}</span>)}
          {equip.length > 4 && <span className="chip">+{equip.length - 4}</span>}
        </div>
        <div className="mt-auto d-flex gap-2">
          <Link to={`/chambres/${room.id}${qs}`} className="btn btn-outline-brand btn-sm flex-fill">Détails</Link>
          <Link to={`/espace/reservations/nouvelle?chambre=${room.id}${reserveQs}`} className="btn btn-brand btn-sm flex-fill">Réserver</Link>
        </div>
      </div>
    </div>
  );
}

const RoomSkeletons = () => (
  <div className="row g-4" aria-busy="true" aria-label="Chargement des chambres">
    {[1, 2, 3].map((i) => <div className="col-12 col-md-6 col-lg-4" key={i}><div className="card room-card"><div className="skeleton" style={{ height: 200 }} /><div className="card-body"><div className="skeleton mb-2" style={{ height: 22, width: '60%' }} /><div className="skeleton" style={{ height: 16, width: '90%' }} /></div></div></div>)}
  </div>
);

export function Home() {
  const nav = useNavigate();
  const today = todayISO();
  const [q, setQ] = useState({ arrivee: '', depart: '', personnes: '2' });
  const [touched, setTouched] = useState(false);
  const [featured, setFeatured] = useState([]);
  const errs = {
    arrivee: validateArrivee(q.arrivee),
    depart: validateDepart(q.arrivee, q.depart),
    personnes: validateInt(q.personnes, { min: 1, max: NB_VOYAGEURS_MAX, label: 'Le nombre de voyageurs' }),
  };
  const invalid = Object.values(errs).some(Boolean);

  useEffect(() => {
    api.get('/chambres/', { params: { page_size: 3, ordering: 'prix_nuit' } })
      .then((r) => setFeatured((r.data.results || []).filter((c) => c.statut !== 'MAINTENANCE')))
      .catch(() => {});
  }, []);

  const submit = (e) => {
    e.preventDefault(); setTouched(true);
    if (invalid) return;
    nav(`/disponibilite?arrivee=${q.arrivee}&depart=${q.depart}&personnes=${q.personnes}`);
  };
  const show = (k) => (touched ? errs[k] : '');
  return (
    <>
      <section className="hero"><div className="container">
        <p className="eyebrow">Grand Hôtel · Antananarivo</p>
        <h1 className="display-5">Séjournez dans le confort</h1>
        <p className="lead mb-4">Trouvez et réservez votre chambre en quelques clics, à partir de {money(20000)} la nuit.</p>
        <form className="search-card" onSubmit={submit} noValidate>
          <div className="row g-3 align-items-start">
            <Field className="col-12 col-md-3" name="s-arrivee" label="Arrivée" type="date" min={today} value={q.arrivee} error={show('arrivee')}
              onChange={(e) => setQ({ ...q, arrivee: e.target.value, depart: q.depart && q.depart <= e.target.value ? '' : q.depart })} />
            <Field className="col-12 col-md-3" name="s-depart" label="Départ" type="date" min={q.arrivee ? addDays(q.arrivee, 1) : addDays(today, 1)} value={q.depart}
              error={show('depart')} onChange={(e) => setQ({ ...q, depart: e.target.value })} />
            <Field className="col-6 col-md-2" name="s-personnes" label="Voyageurs" type="number" min="1" max={NB_VOYAGEURS_MAX} inputMode="numeric" value={q.personnes}
              error={show('personnes')} onChange={(e) => setQ({ ...q, personnes: e.target.value })} />
            <div className="col-6 col-md-4 d-flex align-items-end search-btn-col"><button className="btn btn-accent w-100 btn-lg">Rechercher</button></div>
          </div>
        </form>
      </div></section>

      <section className="container py-5"><div className="row g-4">
        {[['🔒', 'Réservation sécurisée', 'Prix calculés et contrôlés par nos serveurs.'], ['⚡', 'Disponibilités en direct', 'Aucune double réservation possible.'], ['🧾', 'Facture PDF', 'Récapitulatif détaillé et facture instantanée.']].map(([i, t, d]) => (
          <div className="col-md-4" key={t}><div className="card feature-card h-100 p-4 text-center"><div className="feature-icon">{i}</div><h5>{t}</h5><p className="text-muted mb-0">{d}</p></div></div>))}
      </div></section>

      {featured.length > 0 && (
        <section className="container pb-5">
          <div className="d-flex justify-content-between align-items-end mb-3"><h2 className="section-title mb-0">Nos chambres</h2><Link to="/chambres">Tout voir →</Link></div>
          <div className="row g-4">{featured.map((r) => <div className="col-12 col-md-6 col-lg-4" key={r.id}><RoomCard room={r} /></div>)}</div>
        </section>)}
    </>
  );
}

export function Rooms() {
  const [params] = useSearchParams();
  const [f, setF] = useState({ arrivee: params.get('arrivee') || '', depart: params.get('depart') || '', categorie: '', personnes: params.get('personnes') || '' });
  const [cats, setCats] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const withDates = !!(f.arrivee && f.depart);
  const dateErr = f.arrivee && f.depart ? validateDepart(f.arrivee, f.depart) : '';
  const arrErr = f.arrivee ? validateArrivee(f.arrivee) : '';
  const persErr = f.personnes ? validateInt(f.personnes, { min: 1, max: NB_VOYAGEURS_MAX, label: 'Le nombre de voyageurs' }) : '';
  const blocked = !!(dateErr || arrErr || persErr || (f.arrivee && !f.depart) || (!f.arrivee && f.depart));

  useEffect(() => { api.get('/categories/', { params: { page_size: 100 } }).then((r) => setCats(r.data.results)).catch(() => {}); }, []);
  useEffect(() => {
    if (blocked) { setRooms([]); return undefined; }
    let alive = true;
    (async () => {
      setLoading(true); setLoadError('');
      try {
        if (withDates) {
          const { data } = await api.get('/chambres/disponibles/', { params: { arrivee: f.arrivee, depart: f.depart, ...(f.categorie && { categorie: f.categorie }), ...(f.personnes && { personnes: f.personnes }) } });
          if (alive) setRooms(data);
        } else {
          const { data } = await api.get('/chambres/', { params: { page_size: 100, ...(f.categorie && { categorie: f.categorie }) } });
          if (alive) setRooms(data.results.filter((r) => r.statut !== 'MAINTENANCE' && (!f.personnes || r.capacite >= Number(f.personnes))));
        }
      } catch (e) { if (alive) { setRooms([]); setLoadError(errMsg(e)); } } finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [f.arrivee, f.depart, f.categorie, f.personnes, blocked, withDates]);

  const qs = withDates ? `?arrivee=${f.arrivee}&depart=${f.depart}` : '';
  const reserveQs = withDates ? `&arrivee=${f.arrivee}&depart=${f.depart}${f.personnes ? `&adultes=${f.personnes}` : ''}` : '';
  const today = todayISO();
  return (
    <div className="container py-4">
      <h2 className="section-title mb-3">{withDates ? 'Chambres disponibles' : 'Nos chambres'}</h2>
      <div className="card filter-card mb-4"><div className="card-body row g-3">
        <Field className="col-6 col-md-3 mb-0" name="r-arrivee" label="Arrivée" type="date" min={today} value={f.arrivee} error={arrErr}
          onChange={(e) => setF({ ...f, arrivee: e.target.value, depart: f.depart && f.depart <= e.target.value ? '' : f.depart })} />
        <Field className="col-6 col-md-3 mb-0" name="r-depart" label="Départ" type="date" min={f.arrivee ? addDays(f.arrivee, 1) : today} value={f.depart}
          error={dateErr || (f.arrivee && !f.depart ? 'Choisissez une date de départ.' : '')} onChange={(e) => setF({ ...f, depart: e.target.value })} />
        <Field className="col-6 col-md-3 mb-0" name="r-categorie" label="Catégorie" as="select" value={f.categorie} onChange={(e) => setF({ ...f, categorie: e.target.value })}>
          <option value="">Toutes</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
        </Field>
        <Field className="col-6 col-md-3 mb-0" name="r-personnes" label="Voyageurs" type="number" min="1" max={NB_VOYAGEURS_MAX} inputMode="numeric" value={f.personnes} error={persErr}
          onChange={(e) => setF({ ...f, personnes: e.target.value })} />
      </div></div>

      {loadError && <div className="alert alert-danger" role="alert">{loadError}</div>}
      {loading ? <RoomSkeletons /> : (
        <div className="row g-4">
          {!blocked && !loadError && rooms.length === 0 && (
            <div className="col-12"><div className="empty-state"><div className="fs-1">🛏️</div><h5>Aucune chambre ne correspond à votre recherche</h5>
              <p className="text-muted mb-3">Essayez d'autres dates, une autre catégorie ou moins de voyageurs.</p>
              <button className="btn btn-outline-brand" onClick={() => setF({ arrivee: '', depart: '', categorie: '', personnes: '' })}>Réinitialiser les filtres</button></div></div>)}
          {rooms.map((r) => <div className="col-12 col-md-6 col-lg-4" key={r.id}><RoomCard room={r} qs={qs} reserveQs={reserveQs} /></div>)}
        </div>)}
    </div>
  );
}

export function RoomDetail() {
  const { id } = useParams();
  const { search } = useLocation();
  const [room, setRoom] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { api.get(`/chambres/${id}/`).then((r) => setRoom(r.data)).catch((e) => { setFailed(true); toast.error(errMsg(e)); }); }, [id]);
  if (failed) return <div className="container py-5"><div className="empty-state"><h5>Chambre introuvable</h5><Link to="/chambres" className="btn btn-brand mt-2">Voir toutes les chambres</Link></div></div>;
  if (!room) return <div className="text-center p-5"><div className="spinner-border text-secondary" role="status"><span className="visually-hidden">Chargement…</span></div></div>;
  const extra = search ? `&${search.slice(1)}` : '';
  return (
    <div className="container py-4"><div className="row g-4">
      <div className="col-md-6">{room.image ? <img src={room.image} className="img-fluid rounded-4 shadow-sm" alt={`Chambre ${room.numero}`} /> : <div className="room-placeholder rounded-4" style={{ height: 320 }} aria-hidden="true">🛏️</div>}</div>
      <div className="col-md-6">
        <h2 className="section-title">Chambre {room.numero}</h2>
        <p><span className="badge badge-soft me-1">{room.categorie_nom}</span><span className="badge bg-light text-dark">{room.type_chambre}</span></p>
        <h3 className="text-brand">{money(room.prix_nuit)} <small className="text-muted fs-6">/ nuit</small></h3>
        <p>{room.description || 'Chambre confortable et bien équipée.'}</p>
        <p className="text-muted">Capacité : {room.capacite} personne(s) · Étage : {room.etage}</p>
        <div className="chips mb-4">{room.equipements_detail.map((e) => <span key={e.id} className="chip">{e.nom}</span>)}</div>
        <Link className="btn btn-brand btn-lg" to={`/espace/reservations/nouvelle?chambre=${room.id}${extra}`}>Réserver cette chambre</Link>
        <p className="small text-muted mt-3 mb-0">Le prix final (nuits, services, taxes éventuelles) vous est détaillé avant confirmation.</p>
      </div>
    </div></div>
  );
}

export function Login() {
  const { login, user, home } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [params] = useSearchParams();
  const [err, setErr] = useState('');
  const loggedOut = !!loc.state?.loggedOut;
  const expired = !loggedOut && (params.get('session') === 'expiree' || !!loc.state?.sessionEnded);
  const alreadyIn = !!user && !!localStorage.getItem('access');
  // Juste après une déconnexion : le bouton « Retour » du navigateur ne peut plus ramener vers les pages protégées.
  useBlockBack(loggedOut && !alreadyIn);
  const form = useForm({ email: '', password: '' }, {
    email: validateEmail,
    password: (v) => (v ? '' : 'Le mot de passe est obligatoire.'),
  });
  const submit = form.handleSubmit(async (v) => {
    setErr('');
    try {
      const u = await login(v.email.trim().toLowerCase(), v.password);
      toast.success('Bienvenue !');
      nav(loc.state?.from?.pathname || (['ADMIN', 'RECEPTIONNISTE'].includes(u.role) ? '/admin' : '/espace'), { replace: true });
    } catch (er) { setErr(er.response?.status === 401 ? 'Email ou mot de passe incorrect.' : errMsg(er)); }
  });
  // Déjà connecté : inutile de revoir la page de connexion (ex. bouton « Retour » après connexion).
  if (alreadyIn) return <Navigate to={home} replace />;
  return (
    <div className="container py-5" style={{ maxWidth: 440 }}><div className="card auth-card"><form className="card-body p-4" onSubmit={submit} noValidate>
      <h3 className="mb-3 section-title">Connexion</h3>
      {loggedOut && <div className="alert alert-success py-2" role="status">Vous avez été déconnecté en toute sécurité.</div>}
      {expired && <div className="alert alert-warning py-2" role="status">Votre session a expiré ou n'est plus valide. Veuillez vous reconnecter.</div>}
      {err && <div className="alert alert-danger py-2" role="alert">{err}</div>}
      <Field label="Email" type="email" autoComplete="email" required {...form.bind('email')} />
      <Field label="Mot de passe" type="password" autoComplete="current-password" required {...form.bind('password')} />
      <button className="btn btn-brand w-100" disabled={form.submitting}>{form.submitting ? <><span className="spinner-border spinner-border-sm me-2" />Connexion…</> : 'Se connecter'}</button>
      <p className="mt-3 mb-0 small">Pas de compte ? <Link to="/inscription">Inscrivez-vous</Link></p>
    </form></div></div>
  );
}

export function Register() {
  const nav = useNavigate();
  const { user, home } = useAuth();
  const [err, setErr] = useState('');
  const form = useForm({ first_name: '', last_name: '', email: '', phone: '', password: '', confirm: '' }, {
    first_name: (v) => validateName(v, 'Le prénom'),
    last_name: (v) => validateName(v, 'Le nom'),
    email: validateEmail,
    phone: (v) => validatePhone(v),
    password: validatePassword,
    confirm: (v, all) => (!v ? 'Veuillez confirmer le mot de passe.' : v !== all.password ? 'Les mots de passe ne correspondent pas.' : ''),
  });
  const submit = form.handleSubmit(async (v) => {
    setErr('');
    const { confirm, ...body } = v;
    try {
      await api.post('/auth/register/', { ...body, first_name: body.first_name.trim(), last_name: body.last_name.trim(), email: body.email.trim().toLowerCase(), phone: body.phone.trim() });
      toast.success('Compte créé, connectez-vous.'); nav('/connexion');
    } catch (er) {
      const { fields, global } = parseApiError(er);
      form.setServerErrors(fields);
      setErr(global);
    }
  });
  if (user && localStorage.getItem('access')) return <Navigate to={home} replace />;
  return (
    <div className="container py-5" style={{ maxWidth: 540 }}><div className="card auth-card"><form className="card-body p-4" onSubmit={submit} noValidate>
      <h3 className="mb-3 section-title">Créer un compte</h3>
      {err && <div className="alert alert-danger py-2" role="alert">{err}</div>}
      <div className="row">
        <Field className="col-6 mb-3" label="Prénom" autoComplete="given-name" maxLength={100} required {...form.bind('first_name')} />
        <Field className="col-6 mb-3" label="Nom" autoComplete="family-name" maxLength={100} required {...form.bind('last_name')} />
      </div>
      <Field label="Email" type="email" autoComplete="email" required {...form.bind('email')} />
      <Field label="Téléphone" type="tel" autoComplete="tel" hint="Ex. 034 12 345 67 ou +261 34 12 345 67" required {...form.bind('phone')} />
      <div className="row">
        <Field className="col-6 mb-3" label="Mot de passe" type="password" autoComplete="new-password" hint="10 caractères min., lettre + chiffre" required {...form.bind('password')} />
        <Field className="col-6 mb-3" label="Confirmation" type="password" autoComplete="new-password" required {...form.bind('confirm')} />
      </div>
      <button className="btn btn-brand w-100 mt-2" disabled={form.submitting}>{form.submitting ? <><span className="spinner-border spinner-border-sm me-2" />Création…</> : "S'inscrire"}</button>
    </form></div></div>
  );
}
