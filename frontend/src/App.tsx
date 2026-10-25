import { FormEvent, useEffect, useState } from "react";
import { api, Case } from "./api";

type Page = "dashboard" | "cases" | "new-case" | "case-detail" | "upload";

function go(page: Page, id?: number) {
  window.location.hash = id ? `${page}/${id}` : page;
}

function route(): { page: Page; id?: number } {
  const [page, id] = window.location.hash.slice(1).split("/");
  const valid: Page[] = ["dashboard", "cases", "new-case", "case-detail", "upload"];
  return { page: valid.includes(page as Page) ? page as Page : "dashboard", id: id ? Number(id) : undefined };
}

function AuthScreen({ register }: { register: boolean }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (register && password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      if (register) {
        await api.register(username, password);
        window.location.hash = "login";
      } else {
        const response = await api.login(username, password);
        localStorage.setItem("dermai_access_token", response.access_token);
        window.location.hash = "dashboard";
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to complete request.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="brand-mark">D</div>
        <p className="eyebrow">DERMAI WORKSPACE</p>
        <h1>{register ? "Create your workspace" : "Welcome back"}</h1>
        <p className="muted">{register ? "Start organizing skin-image cases securely." : "Sign in to continue to your cases."}</p>
        <form onSubmit={submit} className="form-stack">
          <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} minLength={3} required /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required /></label>
          {register && <label>Confirm password<input type="password" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} minLength={8} required /></label>}
          {error && <p className="error" role="alert">{error}</p>}
          <button disabled={busy}>{busy ? "Please wait…" : register ? "Create account" : "Sign in"}</button>
        </form>
        <button className="link-button" onClick={() => { window.location.hash = register ? "login" : "register"; }}>
          {register ? "Already have an account? Sign in" : "Need an account? Register"}
        </button>
      </section>
    </main>
  );
}

function Layout({ children, current }: { children: React.ReactNode; current: Page }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="wordmark" onClick={() => go("dashboard")}>DERMAI <span>WORKSPACE</span></button>
        <nav>
          <button className={current === "dashboard" ? "active" : ""} onClick={() => go("dashboard")}>Overview</button>
          <button className={current === "cases" ? "active" : ""} onClick={() => go("cases")}>Cases</button>
          <button className={current === "upload" ? "active" : ""} onClick={() => go("upload")}>Upload image</button>
          <button onClick={() => { localStorage.removeItem("dermai_access_token"); window.location.hash = "login"; }}>Log out</button>
        </nav>
      </header>
      <main className="content">{children}</main>
    </div>
  );
}

function Dashboard() {
  return <><div className="hero"><p className="eyebrow">CASE WORKSPACE</p><h1>Prepare each case with clarity.</h1><p className="muted">Upload and organize images for future analysis. DermAI does not provide predictions in this milestone.</p><div className="actions"><button onClick={() => go("new-case")}>Create a case</button><button className="secondary" onClick={() => go("upload")}>Upload image</button></div></div><div className="grid two"><article className="panel"><p className="eyebrow">01 / CASES</p><h2>Keep patient work separated</h2><p className="muted">Create cases, track status, and associate validated images without mixing them with prediction history.</p></article><article className="panel"><p className="eyebrow">02 / PREPROCESSING</p><h2>Ready for the next milestone</h2><p className="muted">Validated uploads can later feed the existing 224 × 224 RGB preprocessing pipeline.</p></article></div></>;
}

function CaseList() {
  const [cases, setCases] = useState<Case[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api.cases().then(setCases).catch((e) => setError(e.message)); }, []);
  return <section><div className="section-heading"><div><p className="eyebrow">CASE MANAGEMENT</p><h1>Your cases</h1></div><button onClick={() => go("new-case")}>New case</button></div>{error && <p className="error">{error}</p>}{!error && cases.length === 0 && <div className="empty panel"><h2>No cases yet</h2><p className="muted">Create your first case to organize validated skin images.</p><button onClick={() => go("new-case")}>Create a case</button></div>}<div className="case-grid">{cases.map((item) => <button className="case-card" key={item.id} onClick={() => go("case-detail", item.id)}><span className={`status ${item.status}`}>{item.status.replace("_", " ")}</span><h2>{item.title}</h2><p className="muted">{item.description || "No description"}</p><small>Updated {new Date(item.updated_at).toLocaleDateString()}</small></button>)}</div></section>;
}

function CaseForm({ existing, onSaved }: { existing?: Case; onSaved: (item: Case) => void }) {
  const [title, setTitle] = useState(existing?.title || "");
  const [description, setDescription] = useState(existing?.description || "");
  const [status, setStatus] = useState<Case["status"]>(existing?.status || "open");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { const item = existing ? await api.updateCase(existing.id, { title, description, status }) : await api.createCase({ title, description, status }); onSaved(item); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to save case."); } finally { setBusy(false); }
  }
  return <form className="panel form-stack" onSubmit={submit}><label>Case title<input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={120} /></label><label>Description<textarea value={description} onChange={(e) => setDescription(e.target.value)} maxLength={2000} rows={5} /></label><label>Status<select value={status} onChange={(e) => setStatus(e.target.value as Case["status"])}><option value="open">Open</option><option value="in_progress">In progress</option><option value="closed">Closed</option></select></label>{error && <p className="error">{error}</p>}<button disabled={busy}>{busy ? "Saving…" : existing ? "Save changes" : "Create case"}</button></form>;
}

function NewCase() { return <section className="narrow"><p className="eyebrow">CASE MANAGEMENT</p><h1>Create a case</h1><CaseForm onSaved={(item) => go("case-detail", item.id)} /></section>; }

function CaseDetail({ id }: { id: number }) {
  const [item, setItem] = useState<Case | null>(null); const [editing, setEditing] = useState(false); const [error, setError] = useState("");
  useEffect(() => { api.getCase(id).then(setItem).catch((e) => setError(e.message)); }, [id]);
  async function remove() { if (!confirm("Delete this case and its image associations?")) return; try { await api.deleteCase(id); go("cases"); } catch (e) { setError(e instanceof Error ? e.message : "Unable to delete case."); } }
  if (error) return <p className="error">{error}</p>; if (!item) return <p className="muted">Loading case…</p>;
  return <section className="narrow"><button className="back-button" onClick={() => go("cases")}>← All cases</button>{editing ? <><h1>Edit case</h1><CaseForm existing={item} onSaved={(saved) => { setItem(saved); setEditing(false); }} /></> : <div className="panel"><span className={`status ${item.status}`}>{item.status.replace("_", " ")}</span><h1>{item.title}</h1><p className="muted">{item.description || "No description"}</p><div className="detail-meta"><span>Created {new Date(item.created_at).toLocaleString()}</span><span>Images: {Array.isArray(item.images) ? item.images.length : item.images}</span></div><div className="actions"><button onClick={() => setEditing(true)}>Edit case</button><button className="danger" onClick={remove}>Delete case</button></div></div>}</section>;
}

function UploadPage() {
  const [cases, setCases] = useState<Case[]>([]); const [caseId, setCaseId] = useState(""); const [file, setFile] = useState<File | null>(null); const [preview, setPreview] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { api.cases().then(setCases).catch(() => undefined); }, []);
  function choose(selected: File | undefined) { setMessage(""); setError(""); if (!selected) return; if (!["image/jpeg", "image/png"].includes(selected.type) || selected.size > 10 * 1024 * 1024) { setError("Choose a JPG, JPEG, or PNG image up to 10 MB."); return; } setFile(selected); setPreview(URL.createObjectURL(selected)); }
  async function submit(event: FormEvent) { event.preventDefault(); if (!file) { setError("Choose an image first."); return; } setBusy(true); setError(""); try { const result = await api.upload(file, caseId ? Number(caseId) : undefined); setMessage(`${result.image.filename} was validated successfully.`); } catch (e) { setError(e instanceof Error ? e.message : "Upload failed."); } finally { setBusy(false); } }
  return <section className="narrow"><p className="eyebrow">IMAGE INTAKE</p><h1>Upload an image</h1><p className="muted">Validation only for now—no disease prediction is generated.</p><form className="panel form-stack" onSubmit={submit}><label className="dropzone"><input type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" onChange={(e) => choose(e.target.files?.[0])} />{preview ? <img src={preview} alt="Selected skin image preview" /> : <><strong>Choose an image</strong><span>JPG, JPEG, or PNG · maximum 10 MB</span></>}</label><label>Associate with case (optional)<select value={caseId} onChange={(e) => setCaseId(e.target.value)}><option value="">No case association</option>{cases.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>{error && <p className="error">{error}</p>}{message && <p className="success" role="status">{message}</p>}<button disabled={busy}>{busy ? "Validating…" : "Validate image"}</button></form></section>;
}

export default function App() {
  const [current, setCurrent] = useState(route());
  useEffect(() => { const update = () => setCurrent(route()); window.addEventListener("hashchange", update); if (!window.location.hash) window.location.hash = "dashboard"; return () => window.removeEventListener("hashchange", update); }, []);
  const authenticated = Boolean(localStorage.getItem("dermai_access_token"));
  if (!authenticated) return <AuthScreen register={window.location.hash === "#register"} />;
  let page: React.ReactNode = current.page === "dashboard" ? <Dashboard /> : current.page === "cases" ? <CaseList /> : current.page === "new-case" ? <NewCase /> : current.page === "case-detail" && current.id ? <CaseDetail id={current.id} /> : <UploadPage />;
  return <Layout current={current.page}>{page}</Layout>;
}
