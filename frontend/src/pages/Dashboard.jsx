import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { toast } from 'react-toastify';
import api, { errMsg, money } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import CountUp from '../components/CountUp';

const COLORS = ['#1f3a5f', '#c9a24d', '#198754', '#dc3545', '#6f42c1', '#20c997'];
const Stat = ({ label, value }) => (
  <div className="col-6 col-lg-3"><div className="card stat-card"><div className="card-body"><div className="text-muted small">{label}</div><div className="fs-4 fw-bold">{typeof value === 'number' ? <CountUp value={value} /> : value}</div></div></div></div>
);
const Chart = ({ title, children }) => (
  <div className="col-12 col-lg-6"><div className="card h-100"><div className="card-body"><h6>{title}</h6><div style={{ height: 260 }}><ResponsiveContainer>{children}</ResponsiveContainer></div></div></div></div>
);

export default function DashboardPage({ view = 'overview' }) {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/dashboard/').then((r) => setD(r.data)).catch((e) => toast.error(errMsg(e))); }, []);
  if (!d) return <div className="text-center p-5"><div className="spinner-border" /></div>;

  if (d.role === 'CLIENT') return (
    <div><h4 className="mb-3">Bienvenue</h4>
      <div className="row g-3 mb-3"><Stat label="Mes réservations" value={d.mes_reservations} /><Stat label="En attente" value={d.en_attente} />
        <Stat label="Confirmées" value={d.confirmees} /><Stat label="Total payé" value={money(d.total_paye)} /></div>
      <Link className="btn btn-brand" to="/espace/reservations/nouvelle">Réserver une chambre</Link></div>
  );

  let cumul = 0;
  const evolution = d.reservations_par_mois.map((x) => ({ mois: x.mois, valeur: (cumul += x.valeur) }));
  const occ = [{ name: 'Occupées', value: d.taux_occupation }, { name: 'Libres', value: 100 - d.taux_occupation }];
  const stats = view === 'stats';

  return (
    <div>
      <h4 className="mb-3">{stats ? 'Statistiques' : 'Tableau de bord'}</h4>
      {!stats && <div className="row g-3 mb-4">
        <Stat label="Chambres" value={d.total_chambres} /><Stat label="Disponibles" value={d.chambres_disponibles} />
        <Stat label="Occupées" value={d.chambres_occupees} /><Stat label="Réservées" value={d.chambres_reservees} />
        <Stat label="Clients" value={d.total_clients} /><Stat label="Réservations" value={d.total_reservations} />
        <Stat label="En attente" value={d.reservations_en_attente} /><Stat label="Chiffre d'affaires" value={money(d.chiffre_affaires)} />
      </div>}
      <div className="row g-3 mb-4">
        <Chart title="Réservations par mois"><BarChart data={d.reservations_par_mois}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="mois" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="valeur" name="Réservations" fill="#1f3a5f" /></BarChart></Chart>
        <Chart title="Revenus par mois"><BarChart data={d.revenus_par_mois}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="mois" /><YAxis width={74} /><Tooltip formatter={(v) => money(v)} /><Bar dataKey="valeur" name="Revenus" fill="#c9a24d" /></BarChart></Chart>
        {stats && <>
          <Chart title={`Taux d'occupation : ${d.taux_occupation} %`}><PieChart><Pie data={occ} dataKey="value" innerRadius={55} outerRadius={90}>{occ.map((_, i) => <Cell key={i} fill={['#dc3545', '#e9ecef'][i]} />)}</Pie><Tooltip formatter={(v) => `${v} %`} /><Legend /></PieChart></Chart>
          <Chart title="Répartition des types de chambres"><PieChart><Pie data={d.repartition_types} dataKey="valeur" nameKey="nom" outerRadius={90} label>{d.repartition_types.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart></Chart>
          <Chart title="Évolution cumulée des réservations"><LineChart data={evolution}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="mois" /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="valeur" name="Cumul" stroke="#198754" strokeWidth={2} /></LineChart></Chart>
        </>}
      </div>
      {!stats && <div className="card"><div className="card-header">Dernières réservations</div><div className="table-responsive"><table className="table mb-0">
        <thead><tr><th>Client</th><th>Chambre</th><th>Date</th><th>Montant</th><th>Statut</th></tr></thead>
        <tbody>{d.dernieres_reservations.map((r) => <tr key={r.id}><td>{r.client_nom}</td><td>{r.chambre_numero}</td><td>{r.date_arrivee} → {r.date_depart}</td><td>{money(r.montant_total)}</td><td><StatusBadge value={r.statut} /></td></tr>)}</tbody>
      </table></div></div>}
    </div>
  );
}
