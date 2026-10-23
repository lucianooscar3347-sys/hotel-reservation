import { money } from '../services/api';

/**
 * Récapitulatif de prix. Affiche uniquement ce que le serveur a calculé (devis ou réservation enregistrée).
 * lignes : [{ label, detail, montant }]  ·  taxes : [{ libelle, montant }]
 */
export default function PriceBreakdown({ prixNuit, nuits, hebergement, lignes = [], reduction = 0, taxes = [], total }) {
  return (
    <dl className="price-list mb-0">
      <div><dt>Tarif par nuit</dt><dd>{money(prixNuit)}</dd></div>
      <div><dt>Hébergement <small className="text-muted">({nuits} nuit{nuits > 1 ? 's' : ''} × {money(prixNuit)})</small></dt><dd>{money(hebergement)}</dd></div>
      {lignes.map((l) => (
        <div key={l.label}><dt>{l.label}{l.detail && <small className="text-muted d-block">{l.detail}</small>}</dt><dd>{money(l.montant)}</dd></div>))}
      {Number(reduction) > 0 && <div className="text-success"><dt>Réduction long séjour</dt><dd>− {money(reduction)}</dd></div>}
      {taxes.map((t) => <div key={t.libelle}><dt>{t.libelle}</dt><dd>{money(t.montant)}</dd></div>)}
      <div className="price-total"><dt>Total à payer</dt><dd>{money(total)}</dd></div>
    </dl>
  );
}
