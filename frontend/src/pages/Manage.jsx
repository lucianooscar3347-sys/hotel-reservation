import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import CrudPage from '../components/CrudPage';
import StatusBadge from '../components/StatusBadge';
import api, { PRIX_MINIMUM_NUIT, errMsg, money } from '../services/api';
import { CIN_LENGTH, NB_VOYAGEURS_MAX, digitsOnly, validateCIN, validateEmail, validateName, validatePhone, validatePrixNuit } from '../lib/validators';
import { useAuth } from '../context/AuthContext';

const opt = (arr) => arr.map(([value, label]) => ({ value, label }));
const STATUT_RESA = opt([['EN_ATTENTE', 'En attente'], ['CONFIRMEE', 'Confirmée'], ['ANNULEE', 'Annulée'], ['TERMINEE', 'Terminée']]);
const STATUT_CH = opt([['DISPONIBLE', 'Disponible'], ['RESERVEE', 'Réservée'], ['OCCUPEE', 'Occupée'], ['NETTOYAGE', 'En nettoyage'], ['MAINTENANCE', 'Maintenance']]);

const call = async (url, ok, reload) => {
  try { await api.post(url); toast.success(ok); reload(); } catch (e) { toast.error(errMsg(e)); }
};

export function CategoriesPage() {
  return <CrudPage title="Catégories de chambres" endpoint="/categories/" createLabel="Nouvelle catégorie"
    columns={[{ label: 'Nom', key: 'nom' }, { label: 'Description', key: 'description' }]}
    fields={[{ name: 'nom', label: 'Nom', required: true }, { name: 'description', label: 'Description', type: 'textarea' }]} />;
}

export function EquipementsPage() {
  return <CrudPage title="Équipements" endpoint="/equipements/" createLabel="Nouvel équipement"
    columns={[{ label: 'Nom', key: 'nom' }, { label: 'Icône', key: 'icone' }]}
    fields={[{ name: 'nom', label: 'Nom', required: true }, { name: 'icone', label: 'Icône (texte)' }]} />;
}

export function ChambresPage() {
  const { isAdmin } = useAuth();
  const [cats, setCats] = useState([]);
  useEffect(() => { api.get('/categories/', { params: { page_size: 100 } }).then((r) => setCats(r.data.results.map((c) => ({ value: c.id, label: c.nom })))); }, []);
  return <CrudPage title="Chambres" endpoint="/chambres/" createLabel="Nouvelle chambre" canCreate={isAdmin} canEdit={isAdmin} canDelete={isAdmin}
    filters={[{ name: 'statut', label: 'Tous les statuts', options: STATUT_CH }, { name: 'categorie', label: 'Toutes catégories', options: cats }]}
    columns={[
      { label: 'Image', render: (r) => r.image ? <img src={r.image} alt="" width="56" height="40" style={{ objectFit: 'cover', borderRadius: 4 }} /> : '🛏️' },
      { label: 'N°', key: 'numero' }, { label: 'Catégorie', key: 'categorie_nom' }, { label: 'Type', key: 'type_chambre' },
      { label: 'Prix / nuit', render: (r) => money(r.prix_nuit) }, { label: 'Capacité', key: 'capacite' }, { label: 'Étage', key: 'etage' },
      { label: 'Statut', render: (r) => <StatusBadge value={r.statut} /> }]}
    rowActions={(r, reload) => r.statut === 'NETTOYAGE' && (
      <button className="btn btn-sm btn-outline-success me-1" onClick={async () => { try { await api.post(`/chambres/${r.id}/statut/`, { statut: 'DISPONIBLE' }); reload(); } catch (e) { toast.error(errMsg(e)); } }}>Rendre disponible</button>)}
    fields={[
      { name: 'numero', label: 'Numéro', required: true, maxLength: 10 },
      { name: 'categorie', label: 'Catégorie', type: 'select', required: true, optionsEndpoint: '/categories/', optionLabel: (c) => c.nom },
      { name: 'type_chambre', label: 'Type (ex. Vue mer)', required: true, maxLength: 50 },
      { name: 'prix_nuit', label: 'Prix par nuit (Ar)', type: 'number', step: '1', min: String(PRIX_MINIMUM_NUIT), required: true, validate: validatePrixNuit,
        hint: `Minimum ${money(PRIX_MINIMUM_NUIT)} par nuit. Le prix reflète la catégorie, le confort et les équipements.` },
      { name: 'capacite', label: 'Capacité', type: 'number', min: '1', max: String(NB_VOYAGEURS_MAX), required: true },
      { name: 'etage', label: 'Étage', type: 'number', min: '-5', max: '100', default: 0 },
      { name: 'statut', label: 'Statut', type: 'select', options: STATUT_CH, default: 'DISPONIBLE', required: true },
      { name: 'description', label: 'Description', type: 'textarea' },
      { name: 'image', label: 'Image', type: 'file' },
      { name: 'equipements', label: 'Équipements (Ctrl/Cmd pour plusieurs)', type: 'multiselect', optionsEndpoint: '/equipements/', optionLabel: (e) => e.nom }]} />;
}

export function ClientsPage() {
  const [hist, setHist] = useState(null);
  const [rows, setRows] = useState([]);
  const open = async (c) => { setHist(c); try { setRows((await api.get(`/clients/${c.id}/reservations/`)).data); } catch (e) { toast.error(errMsg(e)); } };
  const { isAdmin } = useAuth();
  return (<>
    <CrudPage title="Clients" endpoint="/clients/" createLabel="Nouveau client" canDelete={isAdmin}
      filters={[{ name: 'sexe', label: 'Tous sexes', options: opt([['M', 'Masculin'], ['F', 'Féminin']]) }]}
      columns={[{ label: 'Nom', key: 'nom' }, { label: 'Prénom', key: 'prenom' }, { label: 'Téléphone', key: 'telephone' }, { label: 'Email', key: 'email' }, { label: 'CIN', key: 'numero_piece_identite' }]}
      rowActions={(r) => <button className="btn btn-sm btn-outline-secondary me-1" onClick={() => open(r)}>Historique</button>}
      fields={[
        { name: 'nom', label: 'Nom', required: true, maxLength: 100, validate: (v) => validateName(v, 'Le nom') },
        { name: 'prenom', label: 'Prénom', required: true, maxLength: 100, validate: (v) => validateName(v, 'Le prénom') },
        { name: 'sexe', label: 'Sexe', type: 'select', required: true, options: opt([['M', 'Masculin'], ['F', 'Féminin']]) },
        { name: 'date_naissance', label: 'Date de naissance', type: 'date', validate: (v) => (v && v > new Date().toISOString().slice(0, 10) ? 'La date de naissance est dans le futur.' : '') },
        { name: 'adresse', label: 'Adresse', maxLength: 255 },
        { name: 'telephone', label: 'Téléphone', type: 'tel', required: true, maxLength: 30, validate: (v) => validatePhone(v), hint: 'Ex. 034 12 345 67 ou +261 34 12 345 67' },
        { name: 'email', label: 'Email', type: 'email', required: true, maxLength: 254, validate: validateEmail },
        { name: 'numero_piece_identite', label: 'N° CIN', maxLength: CIN_LENGTH, inputMode: 'numeric', pattern: `[0-9]{${CIN_LENGTH}}`,
          placeholder: `${CIN_LENGTH} chiffres`, title: `Exactement ${CIN_LENGTH} chiffres`, hint: `Exactement ${CIN_LENGTH} chiffres, sans espace.`,
          transform: digitsOnly, validate: (v) => validateCIN(v) }]} />
    {hist && <div className="modal-backdrop-custom" onMouseDown={(e) => e.target === e.currentTarget && setHist(null)}><div className="modal-dialog modal-lg modal-dialog-centered"><div className="modal-content">
      <div className="modal-header"><h5 className="modal-title">Historique – {hist.prenom} {hist.nom}</h5><button className="btn-close" onClick={() => setHist(null)} /></div>
      <div className="modal-body table-responsive">{rows.length === 0 ? <p className="text-muted">Aucune réservation.</p> : (
        <table className="table"><thead><tr><th>N°</th><th>Chambre</th><th>Séjour</th><th>Total</th><th>Statut</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.id}><td>{r.numero_reservation}</td><td>{r.chambre_numero}</td><td>{r.date_arrivee} → {r.date_depart}</td><td>{money(r.montant_total)}</td><td><StatusBadge value={r.statut} /></td></tr>)}</tbody></table>)}</div>
    </div></div></div>}
  </>);
}

export function ReservationsPage() {
  const { isStaff, isAdmin } = useAuth();
  return <CrudPage title={isStaff ? 'Réservations' : 'Mes réservations'} endpoint="/reservations/" createLabel="Nouvelle réservation"
    canCreate={isStaff} canEdit={isStaff} canDelete={isAdmin} filters={[{ name: 'statut', label: 'Tous les statuts', options: STATUT_RESA }]}
    columns={[
      { label: 'N°', render: (r) => isStaff ? r.numero_reservation : <Link to={`/espace/reservations/${r.id}`}>{r.numero_reservation}</Link> },
      ...(isStaff ? [{ label: 'Client', key: 'client_nom' }] : []),
      { label: 'Chambre', key: 'chambre_numero' }, { label: 'Arrivée', key: 'date_arrivee' }, { label: 'Départ', key: 'date_depart' },
      { label: 'Montant', render: (r) => money(r.montant_total) }, { label: 'Statut', render: (r) => <StatusBadge value={r.statut} /> }]}
    rowActions={(r, reload) => {
      const act = (a, ok, label, cls) => <button key={a} className={`btn btn-sm btn-outline-${cls} me-1`} onClick={() => call(`/reservations/${r.id}/${a}/`, ok, reload)}>{label}</button>;
      const active = ['EN_ATTENTE', 'CONFIRMEE'].includes(r.statut);
      return (<>
        {isStaff && r.statut === 'EN_ATTENTE' && act('confirmer', 'Réservation confirmée.', 'Confirmer', 'success')}
        {isStaff && r.statut === 'CONFIRMEE' && act('checkin', 'Check-in effectué.', 'Check-in', 'info')}
        {isStaff && r.statut === 'CONFIRMEE' && act('checkout', 'Check-out effectué.', 'Check-out', 'secondary')}
        {active && act('annuler', 'Réservation annulée.', 'Annuler', 'warning')}
      </>);
    }}
    fields={[
      { name: 'client', label: 'Client', type: 'select', required: true, optionsEndpoint: '/clients/', optionLabel: (c) => `${c.prenom} ${c.nom}` },
      { name: 'chambre', label: 'Chambre', type: 'select', required: true, optionsEndpoint: '/chambres/', optionLabel: (c) => `${c.numero} – ${c.categorie_nom} (${money(c.prix_nuit)})` },
      { name: 'date_arrivee', label: 'Date d\'arrivée', type: 'date', required: true }, { name: 'date_depart', label: 'Date de départ', type: 'date', required: true,
        validate: (v, form) => (v && form.date_arrivee && v <= form.date_arrivee ? "La date de départ doit être postérieure à l'arrivée." : '') },
      { name: 'nb_adultes', label: 'Adultes', type: 'number', min: '1', max: String(NB_VOYAGEURS_MAX), default: 1, required: true }, { name: 'nb_enfants', label: 'Enfants', type: 'number', min: '0', max: String(NB_VOYAGEURS_MAX), default: 0 }]} />;
}

export function ServicesPage() {
  const MODES = opt([['SEJOUR', 'Par séjour'], ['NUIT', 'Par nuit'], ['PERSONNE', 'Par personne'], ['PERSONNE_NUIT', 'Par personne et par nuit']]);
  return <CrudPage title="Services (prestations payantes)" endpoint="/services/" createLabel="Nouveau service"
    columns={[{ label: 'Service', key: 'nom' }, { label: 'Prix', render: (r) => money(r.prix) }, { label: 'Facturation', key: 'mode_libelle' },
      { label: 'Statut', render: (r) => <span className={`badge ${r.actif ? 'bg-success' : 'bg-secondary'}`}>{r.actif ? 'Proposé' : 'Désactivé'}</span> }]}
    fields={[
      { name: 'nom', label: 'Nom', required: true, maxLength: 80 },
      { name: 'description', label: 'Description', maxLength: 255 },
      { name: 'prix', label: 'Prix unitaire (Ar)', type: 'number', step: '1', min: '1', max: '10000000', required: true },
      { name: 'mode', label: 'Facturation', type: 'select', options: MODES, default: 'SEJOUR', required: true,
        hint: 'Seuls les services actifs choisis par le client sont facturés.' },
      { name: 'actif', label: 'Service actuellement proposé', type: 'checkbox' }]} />;
}

export function PaiementsPage() {
  const { isAdmin } = useAuth();
  return <CrudPage title="Paiements" endpoint="/paiements/" createLabel="Nouveau paiement" canEdit={false} canDelete={isAdmin}
    filters={[{ name: 'statut', label: 'Tous les statuts', options: opt([['PAYE', 'Payé'], ['PARTIEL', 'Partiel'], ['REMBOURSE', 'Remboursé']]) },
      { name: 'mode_paiement', label: 'Tous les modes', options: opt([['ESPECES', 'Espèces'], ['CARTE', 'Carte bancaire'], ['MOBILE_MONEY', 'Mobile Money'], ['VIREMENT', 'Virement']]) }]}
    columns={[{ label: 'Référence', key: 'reference' }, { label: 'Réservation', key: 'reservation_numero' }, { label: 'Montant', render: (r) => money(r.montant) },
      { label: 'Mode', key: 'mode_paiement' }, { label: 'Date', render: (r) => new Date(r.date_paiement).toLocaleString('fr-FR') }, { label: 'Statut', render: (r) => <StatusBadge value={r.statut} /> }]}
    rowActions={(r, reload) => isAdmin && r.statut !== 'REMBOURSE' && <button className="btn btn-sm btn-outline-warning me-1" onClick={() => window.confirm('Rembourser ce paiement ?') && call(`/paiements/${r.id}/rembourser/`, 'Paiement remboursé.', reload)}>Rembourser</button>}
    fields={[
      { name: 'reservation', label: 'Réservation', type: 'select', required: true, optionsEndpoint: '/reservations/', optionLabel: (r) => `${r.numero_reservation} – reste ${money(r.reste_a_payer)}` },
      { name: 'montant', label: 'Montant (Ar)', type: 'number', step: '1', min: '1', required: true },
      { name: 'mode_paiement', label: 'Mode de paiement', type: 'select', required: true, options: opt([['ESPECES', 'Espèces'], ['CARTE', 'Carte bancaire'], ['MOBILE_MONEY', 'Mobile Money'], ['VIREMENT', 'Virement']]) }]} />;
}

export function FacturesPage() {
  const { isStaff, isAdmin } = useAuth();
  const download = async (f) => {
    try {
      const { data } = await api.get(`/factures/${f.id}/pdf/`, { responseType: 'blob' });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a'); a.href = url; a.download = `${f.numero_facture}.pdf`; a.click(); URL.revokeObjectURL(url);
    } catch (e) { toast.error(errMsg(e)); }
  };
  return <CrudPage title={isStaff ? 'Factures' : 'Mes factures'} endpoint="/factures/" createLabel="Générer une facture" canEdit={false} canDelete={isAdmin}
    columns={[{ label: 'N° facture', key: 'numero_facture' }, { label: 'Réservation', key: 'reservation_numero' }, { label: 'Client', key: 'client_nom' },
      { label: 'Total', render: (r) => money(r.montant_total) }, { label: 'Payé', render: (r) => money(r.montant_paye) }, { label: 'Date', render: (r) => new Date(r.date_emission).toLocaleDateString('fr-FR') }]}
    rowActions={(r) => <button className="btn btn-sm btn-brand me-1" onClick={() => download(r)}>PDF</button>}
    fields={[{ name: 'reservation', label: 'Réservation confirmée', type: 'select', required: true, optionsEndpoint: '/reservations/?statut=CONFIRMEE', optionLabel: (r) => `${r.numero_reservation} – ${r.client_nom} (${money(r.montant_total)})` }]} />;
}

export function UsersPage() {
  return <CrudPage title="Utilisateurs" endpoint="/users/" createLabel="Nouvel utilisateur"
    filters={[{ name: 'role', label: 'Tous les rôles', options: opt([['ADMIN', 'Administrateur'], ['RECEPTIONNISTE', 'Réceptionniste'], ['CLIENT', 'Client']]) }]}
    columns={[{ label: 'Email', key: 'email' }, { label: 'Nom', render: (r) => `${r.first_name} ${r.last_name}` }, { label: 'Rôle', render: (r) => <StatusBadge value={r.role} /> },
      { label: 'Actif', render: (r) => (r.is_active ? '✅' : '⛔') }]}
    fields={[
      { name: 'email', label: 'Email', type: 'email', required: true }, { name: 'first_name', label: 'Prénom', required: true }, { name: 'last_name', label: 'Nom', required: true },
      { name: 'phone', label: 'Téléphone' }, { name: 'role', label: 'Rôle', type: 'select', required: true, default: 'CLIENT', options: opt([['ADMIN', 'Administrateur'], ['RECEPTIONNISTE', 'Réceptionniste'], ['CLIENT', 'Client']]) },
      { name: 'password', label: 'Mot de passe (8 caractères min.)', type: 'password', required: true }, { name: 'is_active', label: 'Compte actif', type: 'checkbox' }]} />;
}
