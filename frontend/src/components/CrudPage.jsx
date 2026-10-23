import { useCallback, useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import api, { errMsg, parseApiError } from '../services/api';

const PAGE_SIZE = 10;

/** Page CRUD générique : liste + recherche + filtres + pagination + modal de formulaire. */
export default function CrudPage({ title, endpoint, columns, fields = [], canCreate = true, canEdit = true,
  canDelete = true, filters = [], rowActions, createLabel = 'Ajouter' }) {
  const [rows, setRows] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [filterVals, setFilterVals] = useState({});
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // { item }
  const [form, setForm] = useState({});
  const [error, setError] = useState('');
  const [fieldErrs, setFieldErrs] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [opts, setOpts] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, ...(search && { search }), ...Object.fromEntries(Object.entries(filterVals).filter(([, v]) => v)) };
      const { data } = await api.get(endpoint, { params });
      const list = data.results ?? data;
      setRows(list);
      setCount(data.count ?? list.length);
    } catch (e) { toast.error(errMsg(e)); } finally { setLoading(false); }
  }, [endpoint, page, search, filterVals]);
  useEffect(() => { load(); }, [load]);

  // options des <select> alimentés par l'API
  useEffect(() => {
    fields.filter((f) => f.optionsEndpoint).forEach(async (f) => {
      try {
        const { data } = await api.get(f.optionsEndpoint, { params: { page_size: 100 } });
        setOpts((o) => ({ ...o, [f.name]: (data.results ?? data).map((x) => ({ value: x.id, label: f.optionLabel(x) })) }));
      } catch { /* ignore */ }
    });
    // eslint-disable-next-line
  }, []);

  const openModal = (item = null) => {
    const f0 = {};
    fields.forEach((f) => {
      if (item) f0[f.name] = f.type === 'password' || f.type === 'file' ? '' : (item[f.name] ?? (f.type === 'multiselect' ? [] : ''));
      else f0[f.name] = f.default ?? (f.type === 'multiselect' ? [] : f.type === 'checkbox' ? true : '');
    });
    setForm(f0); setError(''); setFieldErrs({}); setModal({ item });
  };

  // Contrôle d'un champ : règle personnalisée (f.validate) sinon obligatoire / nombre / bornes.
  const checkField = (f, val, editing) => {
    const empty = val === '' || val == null || (Array.isArray(val) && val.length === 0) || (typeof val === 'string' && !val.trim());
    if (f.validate) { const m = f.validate(val, form); if (m) return m; }
    if (f.required && empty && !(editing && f.type === 'password') && f.type !== 'checkbox') return 'Ce champ est obligatoire.';
    if (empty) return '';
    if (f.type === 'number') {
      const n = Number(val);
      if (!Number.isFinite(n)) return 'Valeur numérique invalide.';
      if (f.min !== undefined && n < Number(f.min)) return `La valeur minimale est ${f.min}.`;
      if (f.max !== undefined && n > Number(f.max)) return `La valeur maximale est ${f.max}.`;
    }
    if (typeof val === 'string' && f.maxLength && val.trim().length > f.maxLength) return `${f.maxLength} caractères maximum.`;
    return '';
  };

  const submit = async (e) => {
    e.preventDefault(); setError('');
    if (submitting) return; // anti double envoi
    const editing = modal.item;
    const errs = {};
    fields.forEach((f) => { const m = checkField(f, form[f.name], editing); if (m) errs[f.name] = m; });
    setFieldErrs(errs);
    if (Object.keys(errs).length) { setTimeout(() => document.querySelector('.modal-body [aria-invalid="true"]')?.focus(), 0); return; }
    let payload;
    if (fields.some((f) => f.type === 'file')) {
      payload = new FormData();
      fields.forEach((f) => {
        const v = typeof form[f.name] === 'string' && f.type !== 'password' ? form[f.name].trim() : form[f.name];
        if (f.type === 'file') { if (v instanceof File) payload.append(f.name, v); }
        else if (f.type === 'multiselect') (v || []).forEach((x) => payload.append(f.name, x));
        else if (v !== '' && v != null) payload.append(f.name, v);
      });
    } else {
      payload = {};
      fields.forEach((f) => {
        let v = typeof form[f.name] === 'string' && f.type !== 'password' ? form[f.name].trim() : form[f.name];
        if (editing && f.type === 'password' && !v) return;
        if (v === '' && ['date', 'number', 'select'].includes(f.type)) v = null;
        payload[f.name] = v;
      });
    }
    setSubmitting(true);
    try {
      if (editing) await api.patch(`${endpoint}${editing.id}/`, payload);
      else await api.post(endpoint, payload);
      toast.success(editing ? 'Modification enregistrée.' : 'Élément créé.');
      setModal(null); load();
    } catch (err) {
      // erreurs du serveur rattachées au champ concerné ; les autres restent en haut du formulaire
      const { fields: fe, global } = parseApiError(err);
      const known = {}; const other = [];
      Object.entries(fe).forEach(([k, m]) => { if (fields.some((f) => f.name === k)) known[k] = m; else other.push(m); });
      setFieldErrs(known);
      setError([global, ...other].filter(Boolean).join(' '));
    } finally { setSubmitting(false); }
  };

  const remove = async (row) => {
    if (!window.confirm('Confirmer la suppression ?')) return;
    try { await api.delete(`${endpoint}${row.id}/`); toast.success('Supprimé.'); load(); }
    catch (err) { toast.error(errMsg(err)); }
  };

  const renderField = (f) => {
    const v = form[f.name] ?? '';
    const set = (val) => { setForm({ ...form, [f.name]: val }); if (fieldErrs[f.name]) setFieldErrs(({ [f.name]: _omit, ...r }) => r); };
    const err = fieldErrs[f.name];
    const common = { id: `crud-${f.name}`, 'aria-invalid': err ? 'true' : 'false', 'aria-describedby': err ? `crud-${f.name}-err` : undefined };
    const required = f.required && !(modal.item && f.type === 'password');
    const choices = f.options || opts[f.name] || [];
    switch (f.type) {
      case 'textarea': return <textarea {...common} rows="3" maxLength={f.maxLength} className={`form-control${err ? ' is-invalid' : ''}`} value={v} onChange={(e) => set(e.target.value)} />;
      case 'select': return (
        <select {...common} className={`form-select${err ? ' is-invalid' : ''}`} value={v} onChange={(e) => set(e.target.value)}>
          <option value="">— Choisir —</option>
          {choices.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>);
      case 'multiselect': return (
        <select {...common} multiple className="form-select" value={form[f.name] || []} onChange={(e) => set([...e.target.selectedOptions].map((o) => o.value))}>
          {choices.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>);
      case 'file': return <input {...common} type="file" accept="image/*" className={`form-control${err ? ' is-invalid' : ''}`} onChange={(e) => set(e.target.files[0])} />;
      case 'checkbox': return <div className="form-check"><input {...common} type="checkbox" className="form-check-input" checked={!!form[f.name]} onChange={(e) => set(e.target.checked)} /></div>;
      default: return <input {...common} type={f.type || 'text'} step={f.step} min={f.min} max={f.max} maxLength={f.maxLength}
        inputMode={f.inputMode || (f.type === 'number' ? 'decimal' : undefined)} pattern={f.pattern} placeholder={f.placeholder} title={f.title}
        autoComplete={f.type === 'password' ? 'new-password' : 'off'} className={`form-control${err ? ' is-invalid' : ''}`} aria-required={required ? 'true' : undefined}
        value={v} onChange={(e) => set(f.transform ? f.transform(e.target.value) : e.target.value)} />;
    }
  };

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE));

  return (
    <div>
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h4 className="mb-0">{title}</h4>
        {canCreate && <button className="btn btn-brand" onClick={() => openModal()}>+ {createLabel}</button>}
      </div>

      <div className="card mb-3"><div className="card-body">
        <form className="row g-2" onSubmit={(e) => { e.preventDefault(); setPage(1); setSearch(searchInput); }}>
          <div className="col-12 col-md-5"><input className="form-control" placeholder="Rechercher…" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} /></div>
          {filters.map((f) => (
            <div className="col-6 col-md-3" key={f.name}>
              <select className="form-select" value={filterVals[f.name] || ''} onChange={(e) => { setPage(1); setFilterVals({ ...filterVals, [f.name]: e.target.value }); }}>
                <option value="">{f.label}</option>
                {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>))}
          <div className="col-auto"><button className="btn btn-outline-secondary">Rechercher</button></div>
        </form>
      </div></div>

      <div className="card"><div className="table-responsive">
        <table className="table table-hover align-middle mb-0">
          <thead className="table-light"><tr>{columns.map((c) => <th key={c.label}>{c.label}</th>)}<th className="text-end">Actions</th></tr></thead>
          <tbody>
            {loading && <tr><td colSpan={columns.length + 1} className="text-center p-4"><div className="spinner-border spinner-border-sm" /></td></tr>}
            {!loading && rows.length === 0 && <tr><td colSpan={columns.length + 1} className="text-center text-muted p-4">Aucun résultat.</td></tr>}
            {!loading && rows.map((row) => (
              <tr key={row.id}>
                {columns.map((c) => <td key={c.label}>{c.render ? c.render(row) : row[c.key]}</td>)}
                <td className="text-end text-nowrap">
                  {rowActions && rowActions(row, load)}{' '}
                  {canEdit && <button className="btn btn-sm btn-outline-primary me-1" onClick={() => openModal(row)}>Modifier</button>}
                  {canDelete && <button className="btn btn-sm btn-outline-danger" onClick={() => remove(row)}>Supprimer</button>}
                </td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <div className="card-footer d-flex justify-content-between align-items-center">
        <small className="text-muted">{count} résultat(s)</small>
        <div className="btn-group btn-group-sm">
          <button className="btn btn-outline-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹</button>
          <button className="btn btn-outline-secondary" disabled>{page} / {pages}</button>
          <button className="btn btn-outline-secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>›</button>
        </div>
      </div></div>

      {modal && (
        <div className="modal-backdrop-custom" onMouseDown={(e) => e.target === e.currentTarget && setModal(null)}>
          <div className="modal-dialog modal-dialog-centered"><form className="modal-content" onSubmit={submit} noValidate>
            <div className="modal-header"><h5 className="modal-title">{modal.item ? 'Modifier' : createLabel}</h5>
              <button type="button" className="btn-close" onClick={() => setModal(null)} /></div>
            <div className="modal-body">
              {error && <div className="alert alert-danger py-2">{error}</div>}
              {fields.map((f) => (
                <div className="mb-3" key={f.name}>
                  <label className="form-label" htmlFor={`crud-${f.name}`}>{f.label}{f.required && <span className="text-danger"> *</span>}</label>
                  {renderField(f)}
                  {fieldErrs[f.name] ? <div id={`crud-${f.name}-err`} className="invalid-feedback d-block" role="alert">{fieldErrs[f.name]}</div>
                    : f.hint && <div className="form-text">{f.hint}</div>}
                </div>))}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-light" onClick={() => setModal(null)}>Annuler</button>
              <button className="btn btn-brand" disabled={submitting}>{submitting ? 'Enregistrement…' : 'Enregistrer'}</button>
            </div>
          </form></div>
        </div>)}
    </div>
  );
}
