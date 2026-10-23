/** Champ de formulaire accessible : libellé lié, message d'erreur sous le champ, état invalide visible. */
export default function Field({ label, name, error, hint, required, as: As = 'input', className = 'mb-3', children, ...rest }) {
  const id = `f-${name}`;
  const described = error ? `${id}-err` : hint ? `${id}-hint` : undefined;
  const base = As === 'select' ? 'form-select' : 'form-control';
  return (
    <div className={className}>
      <label htmlFor={id} className="form-label">{label}{required && <span className="text-danger" aria-hidden="true"> *</span>}</label>
      <As id={id} name={name} className={`${base}${error ? ' is-invalid' : ''}`} aria-invalid={error ? 'true' : 'false'}
        aria-describedby={described} aria-required={required ? 'true' : undefined} {...rest}>{children}</As>
      {error
        ? <div id={`${id}-err`} className="invalid-feedback d-block" role="alert">{error}</div>
        : hint && <div id={`${id}-hint`} className="form-text">{hint}</div>}
    </div>
  );
}
