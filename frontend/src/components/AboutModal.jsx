import { useEffect, useRef, useState } from 'react';

// Le PDF est servi par le frontend : frontend/public/docs/mpd.pdf (remplacez ce fichier par votre propre MPD si besoin).
const PDF_URL = `${import.meta.env.BASE_URL}docs/mpd.pdf`;
const VIEW_URL = `${PDF_URL}#toolbar=1&navpanes=0&view=FitH`;

/** Fenêtre « À propos » : lecteur PDF intégré du MPD, avec téléchargement, ouverture dans un onglet et agrandissement. */
export default function AboutModal({ onClose }) {
  const [full, setFull] = useState(false);
  const [ready, setReady] = useState(false);
  const dialogRef = useRef(null);
  const closeRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  // Certains navigateurs (mobiles, option « télécharger les PDF ») n'annoncent jamais la fin du chargement : on retire l'écran d'attente.
  useEffect(() => { const t = setTimeout(() => setReady(true), 2500); return () => clearTimeout(t); }, []);

  useEffect(() => {
    const previous = document.activeElement;
    const { overflow } = document.body.style;
    document.body.style.overflow = 'hidden'; // la page derrière ne défile plus
    closeRef.current?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') { onCloseRef.current(); return; }
      if (e.key !== 'Tab') return;
      const items = dialogRef.current?.querySelectorAll('a[href], button:not([disabled]), iframe');
      if (!items?.length) return;
      const first = items[0]; const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = overflow; previous?.focus?.(); };
  }, []);

  return (
    <div className="modal-backdrop-custom" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={dialogRef} className={`modal-dialog modal-dialog-centered about-dialog${full ? ' is-full' : ''}`}
        role="dialog" aria-modal="true" aria-labelledby="about-title">
        <div className="modal-content">
          <div className="modal-header about-header">
            <div>
              <h5 className="modal-title" id="about-title">À propos · Modèle Physique des Données</h5>
              <p className="about-sub mb-0">Grand Hôtel — structure de la base de données PostgreSQL (MPD).</p>
            </div>
            <div className="about-actions">
              <a className="btn btn-sm btn-outline-brand" href={PDF_URL} download="MPD-Grand-Hotel.pdf">⬇ Télécharger</a>
              <a className="btn btn-sm btn-outline-brand" href={PDF_URL} target="_blank" rel="noopener noreferrer">↗ Nouvel onglet</a>
              <button type="button" className="btn btn-sm btn-outline-brand" onClick={() => setFull(!full)} aria-pressed={full}>
                {full ? '⤡ Réduire' : '⤢ Agrandir'}
              </button>
              <button type="button" ref={closeRef} className="btn-close" onClick={onClose} aria-label="Fermer la fenêtre" />
            </div>
          </div>
          <div className="modal-body about-body">
            {!ready && <div className="about-loading"><div className="spinner-border spinner-border-sm" /><span>Chargement du document…</span></div>}
            <iframe title="Modèle Physique des Données (PDF)" src={VIEW_URL} className="about-frame" onLoad={() => setReady(true)} />
          </div>
          <div className="modal-footer about-footer">
            <small className="text-muted">
              Le document ne s'affiche pas ? <a href={PDF_URL} target="_blank" rel="noopener noreferrer">Ouvrez-le dans un nouvel onglet</a> ou téléchargez-le.
            </small>
          </div>
        </div>
      </div>
    </div>
  );
}
