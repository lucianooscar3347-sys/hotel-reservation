import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import api, { errMsg, money, parseApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import StatusBadge from '../components/StatusBadge';
import Field from '../components/Field';
import PriceBreakdown from '../components/PriceBreakdown';
import useForm from '../lib/useForm';
import {
  NB_VOYAGEURS_MAX, addDays, todayISO, validateArrivee, validateDepart, validateInt, validateName, validatePassword,
  validatePhone,
} from '../lib/validators';

const MODES = { SEJOUR: 'par séjour', NUIT: 'par nuit', PERSONNE: 'par personne', PERSONNE_NUIT: 'par personne et par nuit' };
const SERVER_TO_FORM = { date_arrivee: 'arrivee', date_depart: 'depart', nb_adultes: 'adultes', nb_enfants: 'enfants', chambre: 'chambre', services_demandes: 'services', montant_attendu: 'montant' };
const fmtDate = (d) => new Date(`${d}T00:00:00`).toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'long', year: 'numeric' });
const STATUT_NOTE = {
  EN_ATTENTE: "Votre demande est enregistrée. Elle n'est pas encore confirmée : l'hôtel la validera prochainement.",
  CONFIRMEE: "Votre réservation est confirmée par l'hôtel.",
  ANNULEE: 'Cette réservation a été annulée.',
  TERMINEE: 'Séjour terminé.',
};

export function NewReservation() {
  const nav = useNavigate();
  const [p] = useSearchParams();
  const today = todayISO();
  const [f, setF] = useState({ arrivee: p.get('arrivee') || '', depart: p.get('depart') || '', adultes: p.get('adultes') || '1', enfants: '0', chambre: p.get('chambre') || '' });
  const [touched, setTouched] = useState({});
  const [attempted, setAttempted] = useState(false);
  const [fieldErr, setFieldErr] = useState({});
  const [err, setErr] = useState('');
  const [rooms, setRooms] = useState([]);
  const [roomsLoaded, setRoomsLoaded] = useState(false);
  const [services, setServices] = useState([]);
  const [picked, setPicked] = useState({}); // { idService: quantité }
  const [quote, setQuote] = useState(null);
  const [quoteErr, setQuoteErr] = useState('');
  const [quoting, setQuoting] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const change = (k, v) => {
    setF((o) => ({ ...o, [k]: v }));
    setFieldErr((o) => { const { [k]: _omit, ...rest } = o; return rest; });
  };
  const errs = {
    arrivee: validateArrivee(f.arrivee),
    depart: validateDepart(f.arrivee, f.depart),
    adultes: validateInt(f.adultes, { min: 1, max: NB_VOYAGEURS_MAX, label: "Le nombre d'adultes" }),
    enfants: validateInt(f.enfants, { min: 0, max: NB_VOYAGEURS_MAX, label: "Le nombre d'enfants" }),
  };
  const datesOk = !errs.arrivee && !errs.depart;
  const peopleOk = !errs.adultes && !errs.enfants;
  const room = rooms.find((r) => String(r.id) === String(f.chambre));
  errs.chambre = !f.chambre ? 'Choisissez une chambre.'
    : roomsLoaded && !room ? "Cette chambre n'est pas disponible pour ces dates ou ce nombre de voyageurs." : '';
  const show = (k) => fieldErr[k] || ((attempted || touched[k]) ? errs[k] : '');
  const blur = (k) => () => setTouched((t) => ({ ...t, [k]: true }));

  // Chambres réellement disponibles (le serveur re-vérifie à la confirmation)
  useEffect(() => {
    if (!datesOk) { setRooms([]); setRoomsLoaded(false); return undefined; }
    let alive = true;
    setRoomsLoaded(false);
    const t = setTimeout(() => {
      const personnes = peopleOk ? Number(f.adultes) + Number(f.enfants) : undefined;
      api.get('/chambres/disponibles/', { params: { arrivee: f.arrivee, depart: f.depart, ...(personnes && { personnes }) } })
        .then((r) => { if (alive) { setRooms(r.data); setRoomsLoaded(true); } })
        .catch((e) => { if (alive) setErr(errMsg(e)); });
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [f.arrivee, f.depart, f.adultes, f.enfants, datesOk, peopleOk]);

  useEffect(() => { api.get('/services/', { params: { page_size: 100 } }).then((r) => setServices(r.data.results || r.data)).catch(() => {}); }, []);

  const lignes = useMemo(() => Object.entries(picked).map(([id, q]) => ({ service: Number(id), quantite: Math.max(1, Math.min(10, Number(q) || 1)) })), [picked]);
  const canQuote = datesOk && peopleOk && !!room;

  // Devis calculé PAR LE SERVEUR : mis à jour à chaque changement de dates, chambre, voyageurs ou services
  useEffect(() => {
    if (!canQuote) { setQuote(null); setQuoteErr(''); setQuoting(false); return undefined; }
    let alive = true;
    setQuoting(true);
    const t = setTimeout(async () => {
      try {
        const { data } = await api.post('/reservations/devis/', {
          chambre: Number(f.chambre), date_arrivee: f.arrivee, date_depart: f.depart,
          nb_adultes: Number(f.adultes), nb_enfants: Number(f.enfants), services_demandes: lignes,
        });
        if (alive) { setQuote(data); setQuoteErr(''); }
      } catch (e) {
        if (alive) { const { fields, global } = parseApiError(e); setQuote(null); setQuoteErr([global, ...Object.values(fields)].filter(Boolean).join(' ')); }
      } finally { if (alive) setQuoting(false); }
    }, 300);
    return () => { alive = false; clearTimeout(t); };
  }, [canQuote, f.chambre, f.arrivee, f.depart, f.adultes, f.enfants, lignes, refresh]);

  const toggleService = (s) => setPicked((o) => { const { [s.id]: had, ...rest } = o; return had ? rest : { ...o, [s.id]: 1 }; });

  const submit = async (e) => {
    e.preventDefault();
    if (submitting) return; // anti double envoi
    setErr(''); setAttempted(true);
    if (Object.values(errs).some(Boolean) || !quote) {
      setTimeout(() => document.querySelector('[aria-invalid="true"]')?.focus(), 0);
      if (!Object.values(errs).some(Boolean) && !quote) setErr(quoteErr || 'Le récapitulatif de prix est en cours de calcul, patientez un instant.');
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post('/reservations/', {
        chambre: Number(f.chambre), date_arrivee: f.arrivee, date_depart: f.depart, nb_adultes: Number(f.adultes), nb_enfants: Number(f.enfants),
        services_demandes: lignes, montant_attendu: quote.montant_total, // contrôle : le serveur refuse si le tarif a changé
      });
      toast.success('Réservation enregistrée.');
      nav(`/espace/reservations/${data.id}`, { state: { nouvelle: true } });
    } catch (er) {
      const { fields, global } = parseApiError(er);
      const mapped = {}; const others = [];
      Object.entries(fields).forEach(([k, m]) => { if (SERVER_TO_FORM[k] && !['services', 'montant'].includes(SERVER_TO_FORM[k])) mapped[SERVER_TO_FORM[k]] = m; else others.push(m); });
      setFieldErr(mapped);
      setErr([global, ...others].filter(Boolean).join(' '));
      if (fields.montant_attendu || fields.chambre) setRefresh((r) => r + 1); // recharge le prix / les disponibilités
    } finally { setSubmitting(false); }
  };

  const ready = canQuote;
  return (
    <div className="fade-in">
      <h3 className="section-title mb-3">Nouvelle réservation</h3>
      <form onSubmit={submit} noValidate>
        <div className="row g-4">
          <div className="col-lg-7"><div className="card card-body">
            {err && <div className="alert alert-danger py-2" role="alert">{err}</div>}
            <div className="row">
              <Field className="col-md-6 mb-3" name="arrivee" label="Arrivée" type="date" required min={today} value={f.arrivee} error={show('arrivee')}
                onChange={(e) => { change('arrivee', e.target.value); if (f.depart && f.depart <= e.target.value) change('depart', ''); }} onBlur={blur('arrivee')} />
              <Field className="col-md-6 mb-3" name="depart" label="Départ" type="date" required min={f.arrivee ? addDays(f.arrivee, 1) : addDays(today, 1)} value={f.depart}
                error={show('depart')} onChange={(e) => change('depart', e.target.value)} onBlur={blur('depart')} />
              <Field className="col-md-6 mb-3" name="adultes" label="Adultes" type="number" required min="1" max={NB_VOYAGEURS_MAX} inputMode="numeric" value={f.adultes}
                error={show('adultes')} onChange={(e) => change('adultes', e.target.value)} onBlur={blur('adultes')} />
              <Field className="col-md-6 mb-3" name="enfants" label="Enfants" type="number" min="0" max={NB_VOYAGEURS_MAX} inputMode="numeric" value={f.enfants}
                error={show('enfants')} onChange={(e) => change('enfants', e.target.value)} onBlur={blur('enfants')} />
              <Field className="col-12 mb-2" name="chambre" label="Chambre disponible" as="select" required value={f.chambre} disabled={!datesOk} error={show('chambre')}
                onChange={(e) => change('chambre', e.target.value)} onBlur={blur('chambre')}
                >
                <option value="">{datesOk ? '— Choisir une chambre —' : "Sélectionnez d'abord des dates valides"}</option>
                {rooms.map((r) => <option key={r.id} value={r.id}>Ch. {r.numero} – {r.categorie_nom} – {r.capacite} pers. – {money(r.prix_nuit)}/nuit</option>)}
              </Field>
              {datesOk && roomsLoaded && rooms.length === 0 && <div className="col-12"><div className="alert alert-warning py-2 mb-2">Aucune chambre disponible pour ces critères. Essayez d'autres dates.</div></div>}
            </div>

            {services.length > 0 && (
              <fieldset className="mt-3">
                <legend className="h6">Services supplémentaires <small className="text-muted fw-normal">(facultatif)</small></legend>
                <div className="service-list">
                  {services.map((s) => {
                    const on = picked[s.id] !== undefined;
                    return (
                      <div key={s.id} className={`service-item ${on ? 'on' : ''}`}>
                        <div className="form-check mb-0 flex-grow-1">
                          <input className="form-check-input" type="checkbox" id={`svc-${s.id}`} checked={on} onChange={() => toggleService(s)} />
                          <label className="form-check-label" htmlFor={`svc-${s.id}`}>
                            <strong>{s.nom}</strong>
                            <small className="d-block text-muted">{money(s.prix)} {MODES[s.mode]}{s.description ? ` · ${s.description}` : ''}</small>
                          </label>
                        </div>
                        {on && s.mode === 'SEJOUR' && (
                          <input type="number" min="1" max="10" className="form-control form-control-sm qty" aria-label={`Quantité pour ${s.nom}`} value={picked[s.id]}
                            onChange={(e) => setPicked((o) => ({ ...o, [s.id]: e.target.value }))} />)}
                      </div>);
                  })}
                </div>
              </fieldset>)}
          </div></div>

          <div className="col-lg-5"><div className="card card-body summary-card">
            <h5 className="mb-3">Récapitulatif</h5>
            {!ready && <p className="text-muted mb-0">Choisissez vos dates, le nombre de voyageurs et une chambre : le prix détaillé s'affichera ici.</p>}
            {ready && quoting && <div aria-busy="true"><div className="skeleton mb-2" style={{ height: 18 }} /><div className="skeleton mb-2" style={{ height: 18 }} /><div className="skeleton" style={{ height: 28 }} /></div>}
            {ready && !quoting && quoteErr && <div className="alert alert-warning py-2 mb-0" role="alert">{quoteErr}</div>}
            {ready && !quoting && quote && (
              <>
                <p className="small text-muted mb-2">Chambre {room.numero} · {room.categorie_nom} · {fmtDate(f.arrivee)} → {fmtDate(f.depart)} · {quote.nb_personnes} voyageur(s)</p>
                <PriceBreakdown prixNuit={quote.prix_nuit} nuits={quote.nb_nuits} hebergement={quote.hebergement_montant} reduction={quote.reduction_montant}
                  lignes={quote.services.map((s) => ({ label: s.nom, detail: `${money(s.prix_unitaire)} × ${s.unites} ${MODES[s.mode]}`, montant: s.montant }))}
                  taxes={quote.taxes} total={quote.montant_total} />
                <p className="small text-muted mt-3 mb-0">Le montant définitif est recalculé et vérifié par le serveur au moment de la validation.</p>
              </>)}
            <button className="btn btn-brand btn-lg mt-3" disabled={submitting || quoting || !quote}>
              {submitting ? <><span className="spinner-border spinner-border-sm me-2" />Enregistrement…</> : 'Valider la réservation'}
            </button>
          </div></div>
        </div>
      </form>
    </div>
  );
}

export function ReservationDetail() {
  const { id } = useParams();
  const { state } = useLocation();
  const [r, setR] = useState(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const load = () => api.get(`/reservations/${id}/`).then((x) => setR(x.data)).catch((e) => { setFailed(true); toast.error(errMsg(e)); });
  useEffect(() => { load(); }, [id]); // eslint-disable-line
  if (failed) return <div className="empty-state"><h5>Réservation introuvable</h5><Link to="/espace/reservations" className="btn btn-brand mt-2">Mes réservations</Link></div>;
  if (!r) return <div className="text-center p-5"><div className="spinner-border text-secondary" role="status"><span className="visually-hidden">Chargement…</span></div></div>;
  const cancel = async () => {
    if (busy || !window.confirm('Annuler cette réservation ?')) return;
    setBusy(true);
    try { await api.post(`/reservations/${id}/annuler/`); toast.success('Réservation annulée.'); await load(); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const rows = [['Numéro', r.numero_reservation], ['Chambre', `${r.chambre_numero}${r.chambre_categorie ? ` · ${r.chambre_categorie}` : ''}`],
    ['Arrivée', fmtDate(r.date_arrivee)], ['Départ', fmtDate(r.date_depart)], ['Durée', `${r.nb_nuits} nuit(s)`],
    ['Voyageurs', `${r.nb_adultes} adulte(s), ${r.nb_enfants} enfant(s)`], ['Déjà payé', money(r.montant_paye)], ['Reste à payer', money(r.reste_a_payer)]];
  return (
    <div className="fade-in" style={{ maxWidth: 760 }}>
      {state?.nouvelle && <div className="alert alert-success" role="status">Votre réservation a bien été enregistrée par le serveur.</div>}
      <h4 className="section-title">Réservation {r.numero_reservation} <StatusBadge value={r.statut} /></h4>
      <p className="text-muted">{STATUT_NOTE[r.statut]}</p>
      <div className="row g-3">
        <div className="col-md-6"><div className="card h-100"><table className="table mb-0"><tbody>{rows.map(([k, v]) => <tr key={k}><th className="fw-semibold text-muted" style={{ width: 130 }}>{k}</th><td>{v}</td></tr>)}</tbody></table></div></div>
        <div className="col-md-6"><div className="card card-body h-100"><h6 className="mb-3">Détail du prix</h6>
          <PriceBreakdown prixNuit={r.prix_nuit} nuits={r.nb_nuits} hebergement={r.hebergement_montant} reduction={r.reduction_montant}
            lignes={(r.lignes || []).map((l) => ({ label: l.nom, detail: `${money(l.prix_unitaire)} ${MODES[l.mode]}${l.mode === 'SEJOUR' && l.quantite > 1 ? ` × ${l.quantite}` : ''}`, montant: l.montant }))}
            taxes={Number(r.taxes_montant) > 0 ? [{ libelle: 'Taxes et frais', montant: r.taxes_montant }] : []} total={r.montant_total} />
        </div></div>
      </div>
      <div className="mt-3 d-flex flex-wrap gap-2">
        <Link to="/espace/reservations" className="btn btn-light">← Mes réservations</Link>
        {['EN_ATTENTE', 'CONFIRMEE'].includes(r.statut) && <button className="btn btn-outline-danger" onClick={cancel} disabled={busy}>Annuler</button>}
        {r.statut !== 'ANNULEE' && Number(r.reste_a_payer) > 0 && <Link to="/espace/paiements" className="btn btn-brand">Payer</Link>}
      </div>
    </div>
  );
}

export function Profile() {
  const { user, loadMe } = useAuth();
  const [err, setErr] = useState('');
  const [pwErr, setPwErr] = useState('');
  const form = useForm({ first_name: user.first_name || '', last_name: user.last_name || '', phone: user.phone || '' }, {
    first_name: (v) => validateName(v, 'Le prénom'),
    last_name: (v) => validateName(v, 'Le nom'),
    phone: (v) => validatePhone(v, { optional: true }),
  });
  const pw = useForm({ old_password: '', new_password: '' }, {
    old_password: (v) => (v ? '' : "L'ancien mot de passe est obligatoire."),
    new_password: (v, all) => validatePassword(v) || (v === all.old_password ? "Le nouveau mot de passe doit être différent de l'ancien." : ''),
  });
  const save = form.handleSubmit(async (v) => {
    setErr('');
    try { await api.patch('/auth/me/', { first_name: v.first_name.trim(), last_name: v.last_name.trim(), phone: v.phone.trim() }); await loadMe(); toast.success('Profil mis à jour.'); }
    catch (er) { const { fields, global } = parseApiError(er); form.setServerErrors(fields); setErr(global); }
  });
  const change = pw.handleSubmit(async (v) => {
    setPwErr('');
    try { await api.post('/auth/change-password/', v); pw.setValues({ old_password: '', new_password: '' }); toast.success('Mot de passe modifié.'); }
    catch (er) { const { fields, global } = parseApiError(er); pw.setServerErrors(fields); setPwErr(global); }
  });
  return (
    <div className="row g-4 fade-in" style={{ maxWidth: 900 }}>
      <form className="col-md-6" onSubmit={save} noValidate><div className="card card-body">
        <h5>Mon profil</h5>
        {err && <div className="alert alert-danger py-2" role="alert">{err}</div>}
        <Field name="email" label="Email" value={user.email} disabled readOnly />
        <Field label="Prénom" required maxLength={100} {...form.bind('first_name')} />
        <Field label="Nom" required maxLength={100} {...form.bind('last_name')} />
        <Field label="Téléphone" type="tel" hint="Ex. 034 12 345 67 ou +261 34 12 345 67" {...form.bind('phone')} />
        <button className="btn btn-brand" disabled={form.submitting}>{form.submitting ? 'Enregistrement…' : 'Enregistrer'}</button>
      </div></form>
      <form className="col-md-6" onSubmit={change} noValidate><div className="card card-body">
        <h5>Changer le mot de passe</h5>
        {pwErr && <div className="alert alert-danger py-2" role="alert">{pwErr}</div>}
        <Field label="Ancien mot de passe" type="password" autoComplete="current-password" required {...pw.bind('old_password')} />
        <Field label="Nouveau mot de passe" type="password" autoComplete="new-password" hint="10 caractères min., lettre + chiffre" required {...pw.bind('new_password')} />
        <button className="btn btn-brand" disabled={pw.submitting}>{pw.submitting ? 'Modification…' : 'Modifier'}</button>
      </div></form>
    </div>
  );
}
