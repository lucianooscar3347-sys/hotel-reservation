const MAP = {
  EN_ATTENTE: ['warning text-dark', 'En attente'], CONFIRMEE: ['success', 'Confirmée'], ANNULEE: ['danger', 'Annulée'],
  TERMINEE: ['secondary', 'Terminée'], DISPONIBLE: ['success', 'Disponible'], RESERVEE: ['info text-dark', 'Réservée'],
  OCCUPEE: ['danger', 'Occupée'], NETTOYAGE: ['warning text-dark', 'En nettoyage'], MAINTENANCE: ['dark', 'Maintenance'],
  PAYE: ['success', 'Payé'], PARTIEL: ['info text-dark', 'Partiel'], REMBOURSE: ['secondary', 'Remboursé'],
  ADMIN: ['danger', 'Administrateur'], RECEPTIONNISTE: ['primary', 'Réceptionniste'], CLIENT: ['secondary', 'Client'],
};
export default function StatusBadge({ value }) {
  const [cls, label] = MAP[value] || ['light text-dark', value];
  return <span className={`badge bg-${cls}`}>{label}</span>;
}
