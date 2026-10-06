import React from "react";
import { createRoot } from "react-dom/client";
import { AnimatePresence, motion } from "motion/react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  Database,
  Download,
  Eye,
  EyeOff,
  FileSearch,
  Filter,
  FlaskConical,
  Grid2X2,
  LogOut,
  Mic,
  MicOff,
  Network,
  Play,
  Plus,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Square,
  Trash2,
  Upload,
  Users,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import "./styles.css";

const LoginNetwork3D = React.lazy(() => import("./LoginNetwork3D"));

// Production is deployed as one Vercel origin, so API calls stay same-origin and
// authentication cookies never need to cross sites. Local Vite development still
// talks to the FastAPI dev server unless an explicit URL is provided.
const API =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8000" : "");
type User = { id: number; name: string; email: string; role: string };
type Dataset = {
  id: number;
  name: string;
  transaction_count: number;
  account_count: number;
  created_at: string;
};
type Score = {
  id: number;
  account_id: string;
  score: number;
  severity: string;
  breakdown: Record<string, number>;
  finding_ids: number[];
  review_status: string;
};
const csrf = () =>
  document.cookie
    .split("; ")
    .find((x) => x.startsWith("muletrace_csrf="))
    ?.split("=")[1] || "";
async function api(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (init.method && init.method !== "GET") headers.set("X-CSRF-Token", csrf());
  if (init.body instanceof FormData === false && init.body)
    headers.set("Content-Type", "application/json");
  const r = await fetch(API + path, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!r.ok) {
    let e;
    try {
      e = await r.json();
    } catch {
      e = { detail: r.statusText };
    }
    throw new Error(
      typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail),
    );
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r.text();
}
const money = (n: number, c = "") =>
  `${c} ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(n)}`;
const statusLabel = (s: string) =>
  ({
    unreviewed: "Unreviewed",
    under_review: "Under review",
    confirmed_suspicious: "Confirmed suspicious",
    cleared: "Cleared",
  })[s] || s;

function AmbientScene() {
  return (
    <div className="ambient-scene" aria-hidden="true">
      <div className="perspective-grid" />
      <div className="aurora aurora-a" />
      <div className="aurora aurora-b" />
      <div className="data-particle p1" />
      <div className="data-particle p2" />
      <div className="data-particle p3" />
    </div>
  );
}

function ThreatSphere({ score = 0 }: { score?: number }) {
  return (
    <div className="threat-sphere" aria-label={`${score} high-risk accounts`}>
      <div className="sphere-core">
        <span>{score}</span>
        <small>HIGH RISK</small>
      </div>
      <div className="orbit orbit-one"><i /><i /></div>
      <div className="orbit orbit-two"><i /></div>
      <div className="orbit orbit-three" />
      <div className="scan-plane" />
    </div>
  );
}

class SceneBoundary extends React.Component<
  { children: React.ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? null : this.props.children; }
}

function AuthScreen({ mode, onAuthenticated, navigate }: { mode: "login" | "signup"; onAuthenticated: (u: User) => void; navigate: (path: string) => void }) {
  const signingUp = mode === "signup";
  const [email, setEmail] = React.useState(signingUp ? "" : "supervisor@muletrace.local"),
    [password, setPassword] = React.useState(signingUp ? "" : "DemoPass!123"),
    [name, setName] = React.useState(""),
    [workspaceName, setWorkspaceName] = React.useState(""),
    [showPassword, setShowPassword] = React.useState(false),
    [error, setError] = React.useState(""),
    [busy, setBusy] = React.useState(false);
  const supportsWebGL = React.useMemo(() => {
    try {
      const canvas = document.createElement("canvas");
      return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
    } catch {
      return false;
    }
  }, []);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onAuthenticated(
        await api(signingUp ? "/api/auth/register" : "/api/auth/login", {
          method: "POST",
          body: JSON.stringify(signingUp ? { email, password, name, workspace_name: workspaceName } : { email, password }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login">
      <section className="login-brand">
        <div className="login-logo">
          <strong className="mads-wordmark">MADs</strong>
          <span>Mule Account<br />Detection System</span>
        </div>
        <div className="login-copy">
          <span className="eyebrow"><i /> FINANCIAL CRIME INTELLIGENCE</span>
          <h1>
            See the money.
            <br />
            <b>Trace the network.</b>
          </h1>
          <p>
            Spot suspicious money movement with explainable risk scoring and
            connected-account analysis—before the trail goes cold.
          </p>
          <div className="login-actions">
            <a href="#login-form" className="reference-button lilac">Explore dashboard</a>
            <a href="#network-preview" className="reference-button lime">View network <Network /></a>
          </div>
        </div>
        <div className="analyst-note">
          <div className="avatar-stack"><i>SM</i><i>AI</i><i>↗</i></div>
          <p><b>Designed for analyst-led investigation</b><span>Explainable signals. Human decisions.</span></p>
        </div>
        <div id="network-preview" className="login-network" aria-label="Decorative preview of connected account activity">
          <div className="network-fallback" aria-hidden="true"><Network /></div>
          {supportsWebGL && <SceneBoundary><React.Suspense fallback={null}><LoginNetwork3D /></React.Suspense></SceneBoundary>}
        </div>
      </section>
      <section className="login-panel">
        <form id="login-form" onSubmit={submit}>
          <div className="mobile-logo">
            <div className="brand-mark">M</div>MADs
          </div>
          <span className="eyebrow teal">ANALYST WORKSPACE</span>
          <h2>{signingUp ? "Create your workspace" : "Welcome back"}</h2>
          <p>{signingUp ? "Start a secure analyst-led investigation workspace." : "Sign in to continue your investigation."}</p>
          {signingUp && <div className="auth-pair">
            <label>Your name<input value={name} onChange={(e) => setName(e.target.value)} minLength={2} required autoComplete="name" /></label>
            <label>Workspace<input value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} minLength={2} required autoComplete="organization" /></label>
          </div>}
          <label>
            Email
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
              autoComplete="username"
            />
          </label>
          <label className="password-field">
            <span>Password</span>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type={showPassword ? "text" : "password"}
              required
              autoComplete={signingUp ? "new-password" : "current-password"}
              minLength={signingUp ? 10 : undefined}
            />
            <button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)}>
              {showPassword ? <EyeOff /> : <Eye />}
            </button>
          </label>
          {error && (
            <div className="error">
              <AlertTriangle /> {error}
            </div>
          )}
          <button className="primary wide" disabled={busy}>
            {busy ? (signingUp ? "Creating workspace…" : "Authenticating…") : (signingUp ? "Create account" : "Enter workspace")}
            <ChevronRight />
          </button>
          <button className="auth-switch" type="button" onClick={() => navigate(signingUp ? "/login" : "/signup")}>
            {signingUp ? "Already have an account? Sign in" : "New to MADs? Create an account"}
          </button>
          <small>
            Sessions expire automatically. State-changing actions are CSRF
            protected.
          </small>
        </form>
      </section>
    </main>
  );
}

function NotFound({ navigate }: { navigate: (path: string) => void }) {
  return <main className="not-found">
    <div className="error-orbit" aria-hidden="true"><span>4</span><i><Network /></i><span>4</span></div>
    <span className="eyebrow">LOST CONNECTION</span>
    <h1>This trail goes nowhere.</h1>
    <p>The page you requested is outside the investigation network.</p>
    <button className="reference-button lime" onClick={() => navigate("/")}>Return to MADs <ChevronRight /></button>
  </main>;
}

function App() {
  const [user, setUser] = React.useState<User | null>(null),
    [loading, setLoading] = React.useState(true),
    [path, setPath] = React.useState(window.location.pathname);
  const navigate = React.useCallback((next: string) => {
    window.history.pushState({}, "", next); setPath(next);
  }, []);
  React.useEffect(() => {
    api("/api/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  React.useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const known = ["/", "/login", "/signup", "/app"].includes(path);
  if (loading)
    return (
      <div className="boot">
        MADs <span>initializing secure workspace…</span>
      </div>
    );
  if (!known) return <NotFound navigate={navigate} />;
  if (user) return <Console user={user} onLogout={() => { setUser(null); navigate("/login"); }} />;
  return <AuthScreen key={path} mode={path === "/signup" ? "signup" : "login"} navigate={navigate} onAuthenticated={(nextUser) => { setUser(nextUser); navigate("/app"); }} />;
}

type AssistantContext = {
  domain: "bank" | "elliptic";
  dataset_id?: number;
  run_id?: number;
  wallet_id?: string;
};
type AssistantAction = {
  type: string;
  wallet_id?: string;
  severity?: string;
  status?: string;
  transaction_ids?: string[];
  relationship_ids?: number[];
};
type AssistantEvidence = { kind: string; id: string; label: string; wallet_id?: string };
type AssistantMessage = {
  id: string;
  role: "analyst" | "assistant";
  text: string;
  evidence?: AssistantEvidence[];
  choices?: { id: string; label: string; score: number; severity: string }[];
};

function VoiceAssistant({ context, resetKey, onAction, autoOpen = false, autoSpeak = false, welcomeText }: { context: AssistantContext; resetKey: string; onAction: (action: AssistantAction) => void | Promise<void>; autoOpen?: boolean; autoSpeak?: boolean; welcomeText?: string }) {
  const [open, setOpen] = React.useState(autoOpen), [input, setInput] = React.useState(""), [messages, setMessages] = React.useState<AssistantMessage[]>([]), [state, setState] = React.useState<"idle" | "listening" | "transcribing" | "processing" | "speaking" | "error">("idle"), [error, setError] = React.useState(""), [muted, setMuted] = React.useState(false), [speechStatus, setSpeechStatus] = React.useState<any>();
  const recorder = React.useRef<MediaRecorder | null>(null), stream = React.useRef<MediaStream | null>(null), chunks = React.useRef<Blob[]>([]), timeout = React.useRef<number | undefined>(undefined), pending = React.useRef<AbortController | undefined>(undefined), requestVersion = React.useRef(0), contextRef = React.useRef(context), audio = React.useRef<HTMLAudioElement | null>(null), audioUrl = React.useRef<string | null>(null), welcomed = React.useRef(false);
  contextRef.current = context;
  const stopTracks = React.useCallback(() => { stream.current?.getTracks().forEach(track => track.stop()); stream.current = null; }, []);
  const stopPlayback = React.useCallback(() => { audio.current?.pause(); audio.current = null; if (audioUrl.current) URL.revokeObjectURL(audioUrl.current); audioUrl.current = null; window.speechSynthesis?.cancel(); }, []);
  React.useEffect(() => { requestVersion.current += 1; pending.current?.abort(); }, [context.domain, context.dataset_id, context.run_id, context.wallet_id]);
  React.useEffect(() => { setMessages([]); setInput(""); setError(""); pending.current?.abort(); stopPlayback(); }, [resetKey]);
  React.useEffect(() => { api("/api/assistant/status").then(setSpeechStatus).catch(() => setSpeechStatus({ speech_available: false, voice_available: false, max_recording_seconds: 60 })); return () => { pending.current?.abort(); recorder.current?.state === "recording" && recorder.current.stop(); stopTracks(); stopPlayback(); }; }, [stopTracks, stopPlayback]);
  const cancel = React.useCallback(() => { requestVersion.current += 1; pending.current?.abort(); if (timeout.current) window.clearTimeout(timeout.current); if (recorder.current?.state === "recording") recorder.current.stop(); stopTracks(); stopPlayback(); setState("idle"); }, [stopTracks, stopPlayback]);
  async function transcribe(blob: Blob) {
    if (!speechStatus?.speech_available) { setState("error"); setError("Live speech transcription is not configured. Type the command instead; no transcript was simulated."); return; }
    if (blob.size > (speechStatus.max_audio_bytes || 8 * 1024 * 1024)) { setState("error"); setError("Recording exceeded the configured upload limit."); return; }
    setState("transcribing"); setError("");
    const form = new FormData(); form.append("file", blob, "investigation.webm");
    try { const result = await api("/api/assistant/transcribe", { method: "POST", body: form }); setInput(result.text); setState("idle"); }
    catch (e) { setState("error"); setError((e as Error).message); }
  }
  async function startRecording() {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") { setState("error"); setError("This browser does not support secure microphone recording. Use the typed command input."); return; }
    if (!speechStatus?.speech_available) { setState("error"); setError("Speech transcription is not configured on the server. Typed commands are fully available."); return; }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true }); chunks.current = [];
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
      const next = new MediaRecorder(stream.current, { mimeType: mime }); recorder.current = next;
      next.ondataavailable = event => { if (event.data.size) chunks.current.push(event.data); };
      next.onstop = () => { if (timeout.current) window.clearTimeout(timeout.current); const blob = new Blob(chunks.current, { type: mime }); stopTracks(); if (blob.size) void transcribe(blob); else { setState("error"); setError("No audio was captured."); } };
      next.onerror = () => { stopTracks(); setState("error"); setError("Recording failed. Check microphone access and try again."); };
      next.start(500); setState("listening");
      timeout.current = window.setTimeout(() => next.state === "recording" && next.stop(), (speechStatus.max_recording_seconds || 60) * 1000);
    } catch (e) { stopTracks(); setState("error"); setError((e as DOMException).name === "NotAllowedError" ? "Microphone permission was denied. Enable it for this site or use typed commands." : "The microphone could not be started."); }
  }
  async function speak(text: string) {
    if (muted) return;
    stopPlayback();
    if (speechStatus?.voice_available) {
      try {
        setState("speaking");
        const response = await fetch(`${API}/api/assistant/speak`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() }, body: JSON.stringify({ text }) });
        if (!response.ok) throw new Error("ElevenLabs voice generation failed");
        const url = URL.createObjectURL(await response.blob()); audioUrl.current = url;
        const next = new Audio(url); audio.current = next;
        next.onended = () => { stopPlayback(); setState("idle"); };
        next.onerror = () => { stopPlayback(); setState("idle"); };
        await next.play(); return;
      } catch { stopPlayback(); }
    }
    if (speechStatus?.speech_provider === "elevenlabs") { setState("idle"); return; }
    if (!window.speechSynthesis) { setState("idle"); return; }
    const utterance = new SpeechSynthesisUtterance(text); utterance.rate = 1.02;
    utterance.onstart = () => setState("speaking"); utterance.onend = () => setState("idle"); utterance.onerror = () => setState("idle"); window.speechSynthesis.speak(utterance);
  }
  React.useEffect(() => { if (autoSpeak && welcomeText && speechStatus !== undefined && !welcomed.current) { welcomed.current = true; if (autoOpen) setOpen(true); void speak(welcomeText); } }, [autoOpen, autoSpeak, welcomeText, speechStatus]);
  async function submit(command = input) {
    const text = command.trim(); if (!text || !context.dataset_id) return;
    const version = ++requestVersion.current; pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    const messageId = crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`;
    setMessages(old => [...old, { id: `${messageId}-user`, role: "analyst", text }]); setInput(""); setState("processing"); setError("");
    try {
      const result = await api("/api/assistant/command", { method: "POST", signal: controller.signal, body: JSON.stringify({ request_id: messageId, text, context: contextRef.current }) });
      if (version !== requestVersion.current || controller.signal.aborted) return;
      await onAction(result.action || { type: "none" });
      if (version !== requestVersion.current) return;
      setMessages(old => [...old, { id: `${messageId}-assistant`, role: "assistant", text: result.answer, evidence: result.evidence, choices: result.choices }]); setState("idle"); speak(result.spoken_answer || result.answer);
    } catch (e) { if ((e as Error).name !== "AbortError" && version === requestVersion.current) { setState("error"); setError((e as Error).message); } }
  }
  function choose(id: string) { void onAction({ type: "select_wallet", wallet_id: id }); setMessages(old => [...old, { id: `${Date.now()}-choice`, role: "assistant", text: `Selected ${id}. You can now ask why it was flagged or expand its network.`, evidence: [{ kind: "wallet", id, label: id }] }]); }
  function closePanel() { cancel(); setOpen(false); }
  return <div className={`voice-assistant ${open ? "open" : ""}`}>
    {!open ? <button className="assistant-launch" onClick={() => setOpen(true)} aria-label="Open voice investigation assistant"><Mic/><span>Voice assistant</span></button> : <section className="assistant-panel" aria-label="Voice investigation assistant">
      <header><div><span className="assistant-orb"><Mic/></span><p><b>MADs Investigation Copilot</b><small>{state === "idle" ? "Evidence-grounded commands" : state}</small></p></div><div><button onClick={() => setMuted(x => !x)} aria-label={muted ? "Unmute spoken responses" : "Mute spoken responses"}>{muted ? <VolumeX/> : <Volume2/>}</button><button onClick={closePanel} aria-label="Close assistant"><X/></button></div></header>
      <div className="assistant-privacy"><ShieldCheck/><span>{speechStatus?.voice_available ? "Narration and push-to-talk use ElevenLabs; MADs does not retain raw audio." : speechStatus?.speech_available ? `Audio is processed by ${speechStatus.speech_provider} and not retained by MADs.` : "ElevenLabs is awaiting a server key; secure browser narration and typed commands remain available."}</span></div>
      <div className="assistant-history" aria-live="polite">{messages.length ? messages.map(message => <article key={message.id} className={message.role}><span>{message.role === "assistant" ? "MADs" : "You"}</span><p>{message.text}</p>{message.choices?.length ? <div className="assistant-choices">{message.choices.map(choice => <button key={choice.id} onClick={() => choose(choice.id)}><b>{choice.label}</b><small>{choice.severity} · {choice.score}/100</small></button>)}</div> : null}{message.evidence?.length ? <div className="assistant-evidence">{message.evidence.map(ref => <button key={`${ref.kind}-${ref.id}`} onClick={() => void onAction({ type: "show_evidence", wallet_id: ref.wallet_id || (ref.kind === "wallet" || ref.kind === "account" ? ref.id : context.wallet_id) })}>{ref.kind}: {ref.label}</button>)}</div> : null}</article>) : <div className="assistant-empty"><Mic/><b>Investigate by voice or text</b><p>Try “Show high-risk wallets,” “Why was this wallet flagged?” or “Summarize this investigation.”</p></div>}</div>
      {error && <div className="assistant-error"><AlertTriangle/>{error}</div>}
      <label className="assistant-transcript"><span>Editable transcript / command</span><textarea value={input} onChange={e => setInput(e.target.value)} placeholder="Type a command or press the microphone…" onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void submit(); } }}/></label>
      <footer><button className={`mic-button ${state === "listening" ? "recording" : ""}`} disabled={state === "transcribing" || state === "processing"} onClick={() => state === "listening" ? recorder.current?.stop() : void startRecording()} aria-label={state === "listening" ? "Stop recording" : "Start push-to-talk recording"}>{state === "listening" ? <Square/> : speechStatus?.speech_available ? <Mic/> : <MicOff/>}</button><button className="assistant-send" disabled={!input.trim() || state === "processing"} onClick={() => void submit()}><Send/>Submit</button><button onClick={cancel} disabled={state === "idle" || state === "error"}>Stop</button><button onClick={() => setMessages([])} aria-label="Clear conversation"><Trash2/></button></footer>
    </section>}
  </div>;
}

function DecisionConfirmation({ wallet, status, onCancel, onConfirm }: { wallet: string; status: string; onCancel: () => void; onConfirm: (note: string) => Promise<void> }) {
  const [note, setNote] = React.useState(""), [busy, setBusy] = React.useState(false), [error, setError] = React.useState("");
  return <div className="decision-modal" role="dialog" aria-modal="true" aria-labelledby="decision-title"><form onSubmit={async e => { e.preventDefault(); if (note.trim().length < 10) return; setBusy(true); setError(""); try { await onConfirm(note.trim()); } catch (err) { setError((err as Error).message); setBusy(false); } }}><span className="eyebrow">REQUIRES ON-SCREEN CONFIRMATION</span><h2 id="decision-title">{status.replaceAll("_", " ")}</h2><p>Wallet/account: <b>{wallet}</b></p><label>Required analyst rationale<textarea autoFocus minLength={10} required value={note} onChange={e => setNote(e.target.value)} placeholder="Document the evidence and rationale (minimum 10 characters)…"/></label>{error && <div className="error">{error}</div>}<div><button type="button" onClick={onCancel}>Cancel</button><button className="primary" disabled={busy || note.trim().length < 10}>{busy ? "Saving…" : "Confirm decision"}</button></div><small>A spoken “yes” cannot submit this decision. Saving uses the authorized endpoint and audit trail.</small></form></div>;
}

function Console({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [view, setView] = React.useState("dashboard"),
    [datasets, setDatasets] = React.useState<Dataset[]>([]),
    [blockchainDatasets, setBlockchainDatasets] = React.useState<any[]>([]),
    [datasetId, setDatasetId] = React.useState<number | undefined>(undefined),
    [runId, setRunId] = React.useState<number | undefined>(undefined),
    [summary, setSummary] = React.useState<any>(undefined),
    [notice, setNotice] = React.useState("");
  const load = React.useCallback(async () => {
    const [bank,blockchain]=await Promise.allSettled([api("/api/datasets"),api("/api/blockchain-datasets")]);
    if(bank.status==="fulfilled"){
      const ds=bank.value.filter((dataset: Dataset) => !dataset.name.toLowerCase().includes("synthetic"));
      setDatasets(ds); if(!datasetId&&ds[0])setDatasetId(ds[0].id);
    }
    if(blockchain.status==="fulfilled")setBlockchainDatasets(blockchain.value);
  }, [datasetId]);
  React.useEffect(() => { load(); }, [load]);
  React.useEffect(() => {
    if (datasetId) api(`/api/datasets/${datasetId}/summary`).then((s: any) => {
      setSummary(s);
      if (s.run_id) setRunId(s.run_id);
    }).catch(() => {});
  }, [datasetId, notice]);
  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    onLogout();
  }
  const nav = [
    ["dashboard", Grid2X2, "Overview"],
    ["elliptic", Network, "Elliptic++ Bitcoin"],
    ["network", Network, "Network explorer"],
    ["accounts", Search, "Investigations"],
    ["upload", Database, "Data & uploads"],
    ["honeypot", FlaskConical, "Honeypot lab"],
    ["audit", Clock3, "Reports"],
    ...(user.role === "supervisor" ? [["settings", Settings, "Settings"]] : []),
  ] as any[];
  const currentLabel = nav.find(([id]) => id === view)?.[2] || (view === "transactions" ? "Imported transactions" : "Overview");
  const initials = user.name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div className="shell">
      <aside>
        <div className="logo">
          <b className="mads-wordmark">MADs</b>
          <span>Mule Account<br />Detection System</span>
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav aria-label="Primary navigation">
          {nav.map(([id, Icon, label]) => (
            <button key={id} className={view === id ? "active" : ""} onClick={() => setView(id)} aria-label={label} aria-current={view === id ? "page" : undefined}>
              <Icon /><span>{label}</span>
              {id === "accounts" && summary?.awaiting_review ? <i className="nav-count">{summary.awaiting_review}</i> : null}
            </button>
          ))}
        </nav>
        <div className="evidence-note"><ShieldCheck /><b>Stay evidence-led</b><p>Risk scores support analyst review; they are not proof of fraud.</p></div>
        <div className="side-foot">
          <span className="user-avatar">{initials}</span>
          <p><b>{user.name}</b><small>{user.role}</small></p>
          <button onClick={logout} aria-label="Sign out"><LogOut /></button>
        </div>
      </aside>
      <div className="workspace">
        <header>
          <div className="breadcrumbs"><span>Workspace</span><i>/</i><b>{currentLabel}</b></div>
          <div className="top-actions">
            {view === "elliptic" ? (
              <span className="environment-pill"><i /> Historical Bitcoin subset</span>
            ) : (
              <>
                <select aria-label="Active dataset" value={datasetId || ""} onChange={(e) => { const next=Number(e.target.value)||undefined;setSummary(undefined);setDatasetId(next);setRunId(undefined); }}>
                  <option value="">No dataset selected</option>
                  {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
                <span className="environment-pill"><i /> {runId ? `Analysis #${runId}` : "Demo environment"}</span>
              </>
            )}
            <button className="icon-btn" aria-label="Search accounts" onClick={() => setView("accounts")}><Search /></button>
            <button className="user-avatar top-user" onClick={logout} aria-label="Sign out">{initials}</button>
          </div>
        </header>
        <main className="content">
          {notice && <div className="toast" onClick={() => setNotice("")}>{notice}<X /></div>}
          <AnimatePresence mode="wait">
            <motion.div key={view} className="view-stage" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.18 }}>
              {view === "dashboard" && <Dashboard summary={summary} datasetId={datasetId} runId={runId} setRunId={setRunId} setView={setView} flash={setNotice} blockchainDataset={blockchainDatasets[0]} />}
              {view === "upload" && <UploadView onDone={async (id, automaticRunId) => { setSummary(undefined);setDatasetId(id);if(automaticRunId)setRunId(automaticRunId);await load();const uploadedSummary=await api(`/api/datasets/${id}/summary`);setSummary(uploadedSummary);if(uploadedSummary.run_id)setRunId(uploadedSummary.run_id);setView("dashboard");setNotice(`CSV imported: ${uploadedSummary.dataset.transaction_count.toLocaleString()} rows analyzed and all overview graphs refreshed.`); }} onBlockchainDone={() => { setView("elliptic"); setNotice("Official Elliptic++ subset imported successfully."); }} />}
              {view === "elliptic" && <EllipticView />}
              {view === "accounts" && <Accounts runId={runId} onInspect={() => setView("network")} />}
              {view === "transactions" && <TransactionsView datasetId={datasetId} runId={runId} onBack={() => setView("dashboard")} />}
              {view === "network" && <NetworkView datasetId={datasetId} runId={runId} />}
              {view === "honeypot" && <HoneypotView summary={summary} runId={runId} onInspect={() => setView("network")} />}
              {view === "audit" && <Audit />}
              {view === "settings" && <SettingsView />}
            </motion.div>
          </AnimatePresence>
        </main>
        <div style={{ display: view === "dashboard" ? "contents" : "none" }}>
          <VoiceAssistant
            context={{ domain: "bank", dataset_id: datasetId, run_id: runId }}
            resetKey={`welcome-${user.id}`}
            autoSpeak
            welcomeText={`Hi ${user.name}. Welcome to MADs. I’m your investigation copilot. I can find high-risk accounts, explain why they were flagged, trace transaction networks, and summarize the evidence. Elliptic++ is historical Bitcoin data, while Network Explorer follows directed money flows. Remember, a risk score guides review; it is not proof of fraud. When you’re ready, select a dataset and ask me what you want to investigate.`}
            onAction={(action) => { if (action.type === "filter_high_risk") setView("accounts"); else if (["select_wallet", "show_evidence", "expand_network"].includes(action.type)) setView("network"); }}
          />
        </div>
      </div>
    </div>
  );
}

function Dashboard({
  summary,
  datasetId,
  runId,
  setRunId,
  setView,
  flash,
  blockchainDataset,
}: any) {
  const [busy, setBusy] = React.useState(false),
    [job, setJob] = React.useState<any>();
  async function analyze() {
    if (!datasetId) return;
    setBusy(true);
    try {
      const j = await api(`/api/datasets/${datasetId}/analyses`, { method: "POST" });
      setRunId(j.job_id); setJob(j);
      const timer = window.setInterval(async () => {
        try {
          const s = await api(`/api/analyses/${j.job_id}`); setJob(s);
          if (["completed", "failed"].includes(s.status)) {
            window.clearInterval(timer); setBusy(false);
            flash(s.status === "completed" ? "Analysis complete — findings are ready." : `Analysis failed: ${s.error || "Unknown error"}`);
          }
        } catch (error) {
          window.clearInterval(timer); setBusy(false); flash(`Could not refresh analysis: ${(error as Error).message}`);
        }
      }, 700);
    } catch (error) {
      setBusy(false); flash(`Could not start analysis: ${(error as Error).message}`);
    }
  }
  const cards = [
    ["Transactions analyzed", summary?.dataset.transaction_count || 0, Database, "Imported records in the active CSV", "transactions"],
    ["Flagged accounts", summary?.flagged_accounts || 0, AlertTriangle, "Click to inspect every explanation", "flagged"],
    ["High-risk accounts", summary?.high_risk || 0, ShieldCheck, "Strict threshold matches requiring priority review", "high"],
    ["Open investigations", summary?.awaiting_review || 0, FileSearch, "Accounts awaiting a final analyst decision", "open"],
  ] as any[];
  function openMetric(target:string) {
    if (target === "transactions") { setView("transactions"); return; }
    sessionStorage.setItem("severityFilter", target === "high" ? "High" : "");
    setView("accounts");
  }
  const riskData = [
    { name: "High risk", value: summary?.high_risk || 0, color: "#f45f72" },
    {
      name: "Review queue",
      value: Math.max(
        (summary?.flagged_accounts || 0) - (summary?.high_risk || 0),
        0,
      ),
      color: "#b06ff1",
    },
    {
      name: "Unflagged",
      value: Math.max(
        (summary?.dataset?.account_count || 0) -
          (summary?.flagged_accounts || 0),
        0,
      ),
      color: "#a6df49",
    },
  ].filter((item) => item.value > 0);
  const riskTotal = riskData.reduce((sum, item) => sum + item.value, 0);
  const highDegrees = riskTotal ? ((summary?.high_risk || 0) / riskTotal) * 360 : 0;
  const reviewDegrees = riskTotal ? (((summary?.flagged_accounts || 0) - (summary?.high_risk || 0)) / riskTotal) * 360 + highDegrees : 0;
  const riskGradient = `conic-gradient(#f45f72 0deg ${highDegrees}deg, #a86ceb ${highDegrees}deg ${reviewDegrees}deg, #9edc43 ${reviewDegrees}deg 360deg)`;
  return (
    <>
      <section className="command-hero">
        <div className="page-title">
          <div>
            <span className="eyebrow teal">MADs / FINANCIAL INTELLIGENCE</span>
            <h1>Overview</h1>
            <p>Your fraud intelligence at a glance.</p>
          </div>
          <div className="actions">
            {!datasetId && <button className="secondary" onClick={() => setView("upload")}><Upload /> Import CSV dataset</button>}
            <button
              className="primary"
              onClick={analyze}
              disabled={!datasetId || busy}
            >
              <Play />
              {busy ? "Analysis running…" : "Run new analysis"}
            </button>
          </div>
        </div>
      </section>
      {blockchainDataset&&<button className="dashboard-blockchain" onClick={()=>setView("elliptic")}><span><Network/><i/></span><div><small>HISTORICAL BITCOIN DATA — ELLIPTIC++</small><b>{blockchainDataset.name}</b><p>{blockchainDataset.transaction_node_count.toLocaleString()} transaction nodes · {blockchainDataset.wallet_count.toLocaleString()} wallet addresses · bounded real-data subset</p></div><ChevronRight/></button>}
      <section className="monitoring-banner">
        <Activity />
        <div><b>{summary?.dataset?.name ? `${summary.dataset.name} is active` : datasetId ? "Loading imported dataset…" : "Connect a transaction dataset"}</b><span>{summary?.dataset ? `${summary.dataset.transaction_count.toLocaleString()} accepted rows from ${summary.dataset.filename} · every metric, graph, and finding below is derived from this imported CSV.` : "Upload a validated CSV to calculate overview metrics and graphs."}</span></div>
        <button onClick={() => setView("upload")}>Upload dataset</button>
      </section>
      {job && job.status !== "completed" && (
        <div className="progress">
          <span style={{ width: `${job.progress || 5}%` }} />
          <p>
            {job.status === "failed"
              ? job.error
              : `Running deterministic detectors… ${job.progress || 0}%`}
          </p>
        </div>
      )}
      <section className="metrics">
        {cards.map(([label, value, Icon, description, target], index) => (
          <button type="button" key={label} className="tilt-card metric-action" onClick={()=>openMetric(target)} style={{"--delay": `${index * -0.45}s`} as React.CSSProperties}>
            <div className="metric-icon">
              <span className="icon-depth"><Icon /></span>
            </div>
            <span>{label}</span>
            <strong>{value.toLocaleString()}</strong>
            <small>{description}</small>
            <em>Open details <ChevronRight/></em>
          </button>
        ))}
      </section>
      <section className="chart-grid grid gap-4 xl:grid-cols-2">
        <article className="panel depth-panel chart-panel">
          <div className="panel-head">
            <div>
              <h2>Risk activity</h2>
              <p>Imported transactions across the current dataset</p>
            </div>
            <BarChart3 />
          </div>
          {summary?.activity?.length ? (
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={summary.activity} margin={{ left: 0, right: 12, top: 16, bottom: 0 }}>
                  <defs><linearGradient id="riskActivityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#9bd33f" stopOpacity={0.34}/><stop offset="100%" stopColor="#9bd33f" stopOpacity={0.02}/></linearGradient></defs>
                  <CartesianGrid stroke="#e4e1d9" vertical={false} strokeDasharray="4 6" />
                  <XAxis dataKey="date" tick={{ fill: "#8e8b99", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#8e8b99", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "#fffefa", border: "1px solid #e4e1d8", borderRadius: 10, color: "#11162d" }} />
                  <Area type="monotone" dataKey="count" name="Transactions" stroke="#8fc93a" strokeWidth={3} fill="url(#riskActivityFill)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <Empty text="Import transactions to view activity." />
          )}
        </article>
        <article className="panel depth-panel chart-panel">
          <div className="panel-head">
            <div>
              <h2>Risk distribution</h2>
              <p>Accounts in the active investigation scope</p>
            </div>
            <Activity />
          </div>
          {riskData.length ? (
            <div className="chart-wrap risk-chart-wrap">
              <div className="risk-donut" role="img" aria-label={`Risk distribution: ${riskData.map(item=>`${item.name} ${item.value}`).join(", ")}`} style={{background:riskGradient}}>
                <div className="donut-total"><b>{summary?.flagged_accounts || 0}</b><span>flagged</span></div>
              </div>
              <div className="chart-legend">{riskData.map((item) => <span key={item.name}><i style={{ background: item.color }} />{item.name} <b>{item.value}</b></span>)}</div>
            </div>
          ) : (
            <Empty text="Run an analysis to chart account risk." />
          )}
        </article>
        <article className="panel depth-panel chart-panel">
          <div className="panel-head">
            <div><h2>Detected pattern distribution</h2><p>Explainable findings produced from the imported CSV</p></div>
            <Network />
          </div>
          {summary?.patterns?.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={summary.patterns} margin={{left:0,right:12,top:16,bottom:18}}><CartesianGrid stroke="#e4e1d9" vertical={false} strokeDasharray="4 6"/><XAxis dataKey="name" tick={{fill:"#8e8b99",fontSize:10}} axisLine={false} tickLine={false}/><YAxis tick={{fill:"#8e8b99",fontSize:11}} axisLine={false} tickLine={false} allowDecimals={false}/><Tooltip contentStyle={{background:"#fffefa",border:"1px solid #e4e1d8",borderRadius:10,color:"#11162d"}}/><Bar dataKey="value" name="Findings" fill="#a86ceb" radius={[8,8,0,0]}/></BarChart></ResponsiveContainer></div>:<Empty text="No detector pattern crossed the configured threshold."/>}
        </article>
      </section>
      <section className="split">
        <article className="panel depth-panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">VALUE BY CURRENCY</span>
              <h2>Imported transaction value</h2>
            </div>
            <CircleDollarSign />
          </div>
          {summary?.totals?.length ? (
            summary.totals.map((x: any) => (
              <div className="currency" key={x.currency}>
                <b>{x.currency}</b>
                <strong>{money(x.amount)}</strong>
                <span
                  style={{
                    width: `${Math.min(100, 20 + Math.log10(x.amount || 1) * 12)}%`,
                  }}
                />
              </div>
            ))
          ) : (
            <Empty text="Import a dataset to see transaction totals." />
          )}
        </article>
        <article className="panel accent-panel depth-panel">
          <div className="holo-rings" aria-hidden="true"><i/><i/><i/></div>
          <span className="eyebrow">NEXT BEST ACTION</span>
          <h2>
            {runId
              ? "Review the highest-risk network"
              : "Establish an evidence baseline"}
          </h2>
          <p>
            {runId
              ? "Open the flagged queue, inspect why an account scored highly, then trace each supporting transfer in context."
              : "Run the explainable detectors. Currency boundaries, time windows, and fund reuse controls are enforced."}
          </p>
          <button
            className="secondary"
            onClick={() => setView(runId ? "accounts" : "upload")}
          >
            {runId ? "Open flagged queue" : "Import transactions"}
            <ChevronRight />
          </button>
        </article>
      </section>
      <p className="score-note">
        <ShieldCheck /> Risk scores prioritize investigation; they are not
        calibrated probabilities of fraud.
      </p>
    </>
  );
}

function UploadView({ onDone, onBlockchainDone }: { onDone: (id: number, runId?: number) => void; onBlockchainDone: () => void }) {
  const [mode,setMode]=React.useState<"bank"|"elliptic">("bank");
  return <>
    <div className="import-mode" role="tablist" aria-label="Dataset import type">
      <button className={mode==="bank"?"active":""} onClick={()=>setMode("bank")}>Bank transaction CSV</button>
      <button className={mode==="elliptic"?"active":""} onClick={()=>setMode("elliptic")}>Elliptic++ Blockchain Dataset</button>
    </div>
    {mode==="bank"?<BankUploadView onDone={onDone}/>:<EllipticUpload onDone={onBlockchainDone}/>} 
  </>;
}

function BankUploadView({ onDone }: { onDone: (id: number, runId?: number) => void }) {
  const [name, setName] = React.useState(""),
    [tx, setTx] = React.useState<File>(),
    [acct, setAcct] = React.useState<File>(),
    [preview, setPreview] = React.useState<any>(),
    [validating, setValidating] = React.useState(false),
    [busy, setBusy] = React.useState(false),
    [error, setError] = React.useState("");
  async function check(f: File) {
    setTx(f);
    setPreview(undefined);
    setValidating(true);
    setError("");
    const form = new FormData();
    form.append("file", f);
    try {
      setPreview(
        await api("/api/uploads/preview", { method: "POST", body: form }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setValidating(false);
    }
  }
  async function submit() {
    if (!tx) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("name", name || tx.name.replace(".csv", ""));
    form.append("transactions", tx);
    if (acct) form.append("accounts", acct);
    try {
      const d = await api("/api/datasets", { method: "POST", body: form });
      if (d.run_id) {
        let state:any={status:"queued"};
        for (let attempt=0;attempt<300&&!['completed','failed'].includes(state.status);attempt++) {
          if (attempt) await new Promise(resolve=>window.setTimeout(resolve,500));
          state=await api(`/api/analyses/${d.run_id}`);
        }
        if (state.status!=="completed") throw new Error(state.error||"Automatic analysis did not complete in time");
      }
      onDone(d.id,d.run_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow teal">MADs / FINANCIAL INTELLIGENCE</span>
          <h1>Data &amp; uploads</h1>
          <p>Import a transaction file to begin analysis.</p>
        </div>
        <div className="sample-links">
          <a href="/datasets/ibm-aml-transactions.csv" download>
            <Download /> IBM AML dataset
          </a>
          <a href={`${API}/api/samples/transactions`}>
            <Download /> Schema sample
          </a>
          <a href={`${API}/api/samples/accounts`}>
            <Download /> Account sample
          </a>
        </div>
      </div>
      <div className="upload-intro"><Database /><div><h2>Bring your transaction data into focus.</h2><p>Upload a transaction CSV to validate its structure and preview the analysis workflow.</p></div></div>
      <section className="upload-grid">
        <article className="panel upload-panel">
          <label>
            Dataset name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="January monitoring batch"
            />
          </label>
          <label className="drop">
            <Upload />
            <b>Upload transaction CSV</b>
            <span>Drag and drop your file here, or browse from your device</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => e.target.files?.[0] && check(e.target.files[0])}
            />
            {tx && <em>{tx.name}</em>}
          </label>
          <label className="drop compact">
            <Database />
            <b>Account metadata CSV</b>
            <span>Optional · enables shared-attribute analysis</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setAcct(e.target.files?.[0])}
            />
            {acct && <em>{acct.name}</em>}
          </label>
          {error && (
            <div className="error">
              <AlertTriangle />
              {error}
            </div>
          )}
          <button
            className="primary wide"
            disabled={!preview?.valid || busy || validating}
            onClick={submit}
          >
            {validating ? "Validating selected CSV…" : busy ? "Importing and analyzing every row…" : "Import and analyze validated CSV"}
          </button>
        </article>
        <aside className="panel safety-checklist">
          <h2><ShieldCheck /> Data safety checklist</h2>
          <p>✓ Use synthetic or anonymized data for demos</p>
          <p>✓ Do not upload passwords, PINs or card details</p>
          <p>✓ Validate file columns before processing</p>
          <p>✓ Restrict access to uploaded files</p>
        </aside>
        <article className="panel preview">
          <div className="panel-head">
            <div>
              <span className="eyebrow">VALIDATION PREVIEW</span>
              <h2>
                {preview
                  ? `${preview.row_count} valid rows`
                  : "Select a transaction file"}
              </h2>
            </div>
            {preview && (
              <span className={preview.valid ? "valid" : "invalid"}>
                {preview.valid ? "Ready" : "Needs attention"}
              </span>
            )}
          </div>
          {preview?.errors?.map((e: any) => (
            <div className="row-error" key={e.row}>
              Row {e.row}: {e.message}
            </div>
          ))}
          {preview?.preview?.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Sender</th>
                    <th>Receiver</th>
                    <th>Amount</th>
                    <th>Currency</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.preview.map((r: any) => (
                    <tr key={r.transaction_id}>
                      <td>{r.transaction_id}</td>
                      <td>{r.sender_account}</td>
                      <td>{r.receiver_account}</td>
                      <td>{r.amount}</td>
                      <td>{r.currency}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty text="A row-level preview and validation errors will appear here." />
          )}
        </article>
      </section>
    </>
  );
}

const ellipticFileNames=["wallets_features.csv","wallets_classes.csv","AddrAddr_edgelist.csv","AddrTx_edgelist.csv","TxAddr_edgelist.csv","txs_features.csv","txs_classes.csv","txs_edgelist.csv"];
function EllipticUpload({onDone}:{onDone:()=>void}){
  const [files,setFiles]=React.useState<Record<string,File>>({}),[name,setName]=React.useState("Elliptic++ laptop demo"),[limit,setLimit]=React.useState(500),[busy,setBusy]=React.useState(false),[error,setError]=React.useState("");
  async function submit(){
    if(ellipticFileNames.some(f=>!files[f]))return;
    setBusy(true);setError("");const form=new FormData();form.append("name",name);form.append("max_transactions",String(limit));
    ellipticFileNames.forEach(filename=>form.append(filename.replace(".csv",""),files[filename]));
    try{await api("/api/blockchain-datasets/import",{method:"POST",body:form});onDone();}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  return <>
    <div className="page-title"><div><span className="eyebrow teal">OFFICIAL RESEARCH DATASET / BITCOIN</span><h1>Elliptic++ Blockchain Dataset</h1><p>Import the official files as typed wallets, transactions, and directed relationships.</p></div><a className="secondary" href="https://github.com/git-disl/EllipticPlusPlus" target="_blank" rel="noreferrer">Official source ↗</a></div>
    <div className="dataset-warning"><ShieldCheck/><div><b>Historical Bitcoin data — Elliptic++</b><p>Real research records only. Time steps remain ordinal; labels remain separate; missing capabilities stay disabled.</p></div></div>
    <section className="elliptic-upload-layout">
      <article className="panel elliptic-upload">
        <div className="field-row"><label>Import name<input value={name} onChange={e=>setName(e.target.value)}/></label><label>Transaction-node limit<input type="number" min="1" max="25000" value={limit} onChange={e=>setLimit(Number(e.target.value))}/></label></div>
        <div className="file-matrix">{ellipticFileNames.map(filename=><label key={filename} className={files[filename]?"file-ready":""}><Database/><span><b>{filename}</b><small>{files[filename]?`${(files[filename].size/1048576).toFixed(1)} MB selected`:"Required official CSV"}</small></span><input type="file" accept=".csv,text/csv" onChange={e=>e.target.files?.[0]&&setFiles(old=>({...old,[filename]:e.target.files![0]}))}/></label>)}</div>
        {error&&<div className="error"><AlertTriangle/>{error}</div>}
        <button className="primary wide" disabled={busy||ellipticFileNames.some(f=>!files[f])} onClick={submit}>{busy?"Validating, hashing, and importing…":"Import verified Elliptic++ subset"}</button>
      </article>
      <aside className="panel capability-note"><h2>Integrity rules</h2><p>✓ Chunked file handling and SHA-256 checksums</p><p>✓ Idempotent repeated imports</p><p>✓ Complete input/output structure for selected transactions</p><p>✓ No invented transfers, amounts, timestamps, or identities</p><p>✓ Reference labels excluded from detector inputs</p></aside>
    </section>
  </>;
}

function EllipticView(){
  const [datasets,setDatasets]=React.useState<any[]>([]),[datasetId,setDatasetId]=React.useState<number>(),[summary,setSummary]=React.useState<any>(),[wallets,setWallets]=React.useState<any[]>([]),[wallet,setWallet]=React.useState(""),[query,setQuery]=React.useState(""),[detail,setDetail]=React.useState<any>(),[evaluation,setEvaluation]=React.useState<any>(),[hops,setHops]=React.useState(1),[nodes,setNodes]=React.useState<Node[]>([]),[edges,setEdges]=React.useState<Edge[]>([]),[graphTruncated,setGraphTruncated]=React.useState(false),[error,setError]=React.useState(""),[decisionDraft,setDecisionDraft]=React.useState<{status:string}|null>(null);
  React.useEffect(()=>{api("/api/blockchain-datasets").then((d:any[])=>{setDatasets(d);if(d[0])setDatasetId(d[0].id)}).catch(e=>setError(e.message));},[]);
  React.useEffect(()=>{if(!datasetId)return;Promise.all([api(`/api/blockchain-datasets/${datasetId}/summary`),api(`/api/blockchain-datasets/${datasetId}/wallets?page_size=30`),api(`/api/blockchain-datasets/${datasetId}/evaluation`)]).then(([s,w,e])=>{setSummary(s);setWallets(w.items);setEvaluation(e);if(w.items[0])setWallet(w.items[0].address)}).catch(e=>setError(e.message));},[datasetId]);
  const loadWallet=React.useCallback(async(address=wallet)=>{if(!datasetId||!address)return;try{const [d,n]=await Promise.all([api(`/api/blockchain-datasets/${datasetId}/wallets/${encodeURIComponent(address)}`),api(`/api/blockchain-datasets/${datasetId}/network?wallet=${encodeURIComponent(address)}&hops=${hops}&node_limit=45&edge_limit=90`)]);setDetail(d);setGraphTruncated(Boolean(n.truncated));const center={x:360,y:230};const others=n.nodes.filter((x:any)=>!(x.node_type==="wallet"&&x.id===address));setNodes(n.nodes.map((x:any)=>{const key=`${x.node_type}:${x.id}`,i=others.indexOf(x),angle=i/Math.max(others.length,1)*Math.PI*2-Math.PI/2,r=x.node_type==="transaction"?150:235;return{id:key,position:x.node_type==="wallet"&&x.id===address?center:{x:center.x+Math.cos(angle)*r,y:center.y+Math.sin(angle)*r},data:{label:""},ariaLabel:x.node_type==="transaction"?"Bitcoin transaction node":"Wallet node",className:`elliptic-node ${x.node_type} ${x.severity?.toLowerCase()||""} ${x.id===address?"selected":""}`}}));setEdges(n.edges.map((e:any)=>({id:String(e.id),source:`${e.source_type}:${e.source}`,target:`${e.target_type}:${e.target}`,animated:e.relationship_type!=="ADDR_ADDR",markerEnd:{type:MarkerType.ArrowClosed,color:"#8574a8"},style:{stroke:e.relationship_type==="ADDR_ADDR"?"#a8a2b4":"#8574a8",strokeWidth:1.8}})));}catch(e){setError((e as Error).message)}},[datasetId,wallet,hops]);
  React.useEffect(()=>{loadWallet()},[loadWallet]);
  async function search(){if(!datasetId)return;const w=await api(`/api/blockchain-datasets/${datasetId}/wallets?q=${encodeURIComponent(query)}&page_size=30`);setWallets(w.items);if(w.items[0])setWallet(w.items[0].address)}
  async function decide(status:string){if(!datasetId||!wallet)return;const note=(status==="confirmed_suspicious"||status==="cleared")?(prompt("Required analyst note:")||""):"";if((status==="confirmed_suspicious"||status==="cleared")&&!note)return;await api(`/api/blockchain-datasets/${datasetId}/wallets/${encodeURIComponent(wallet)}/decision`,{method:"POST",body:JSON.stringify({status,note})});loadWallet()}
  async function assistantAction(action:AssistantAction){
    if(!datasetId)return;
    if(action.type==="filter_high_risk"){const result=await api(`/api/blockchain-datasets/${datasetId}/wallets?severity=High&page_size=100`);setWallets(result.items);setQuery("");return;}
    if((action.type==="select_wallet"||action.type==="show_evidence")&&action.wallet_id){setWallet(action.wallet_id);if(action.type==="show_evidence")window.setTimeout(()=>document.getElementById("elliptic-evidence")?.scrollIntoView({behavior:"smooth",block:"center"}),80);return;}
    if(action.type==="expand_network"){setHops(value=>Math.min(3,value+1));return;}
    if(action.type==="open_decision_form"&&action.wallet_id&&action.status){setWallet(action.wallet_id);setDecisionDraft({status:action.status});}
  }
  if(!datasets.length)return <><div className="page-title"><div><span className="eyebrow teal">BLOCKCHAIN INTELLIGENCE</span><h1>Historical Bitcoin data — Elliptic++</h1><p>No official Elliptic++ dataset has been imported into this workspace.</p></div></div>{error&&<div className="error"><AlertTriangle/>{error}</div>}<div className="panel empty-blockchain"><Network/><h2>Import the eight official CSV files</h2><p>Use Data &amp; uploads → Elliptic++ Blockchain Dataset. MADs will never substitute demo records.</p></div></>;
  return <>
    <div className="page-title"><div><span className="eyebrow teal">HISTORICAL BITCOIN DATA / REAL BOUNDED SUBSET</span><h1>Elliptic++ Blockchain Dataset</h1><p>Wallet addresses and transaction nodes are preserved as different entities.</p></div><div className="blockchain-actions"><select value={datasetId} onChange={e=>setDatasetId(Number(e.target.value))}>{datasets.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select>{datasetId&&<a className="secondary" href={`${API}/api/blockchain-datasets/${datasetId}/export`}><Download/>Export</a>}</div></div>
    <div className="dataset-warning"><Activity/><div><b>Historical Bitcoin data — Elliptic++</b><p>{summary?.notice}</p></div></div>
    <section className="blockchain-stats"><article><Database/><span>Transaction nodes</span><b>{summary?.dataset.transaction_node_count?.toLocaleString()}</b></article><article><Users/><span>Wallet addresses</span><b>{summary?.dataset.wallet_count?.toLocaleString()}</b></article><article><Network/><span>Official relationships</span><b>{summary?.dataset.relationship_count?.toLocaleString()}</b></article><article><AlertTriangle/><span>Structurally flagged</span><b>{summary?.scores.flagged?.toLocaleString()}</b></article></section>
    <section className="capability-panel panel"><div className="panel-head"><div><span className="eyebrow">DETECTOR CAPABILITY GATING</span><h2>What this dataset can support</h2></div><span className="subset-pill">Subset · not full corpus</span></div><div className="capability-grid">{Object.entries(summary?.capabilities||{}).map(([key,value]:any)=><div key={key} className={value.available?"available":"unavailable"}><i>{value.available?"✓":"—"}</i><span><b>{key.replaceAll("_"," ")}</b><small>{value.reason}</small></span></div>)}</div><p className="subset-method">Selection: {summary?.dataset.subset_method}</p></section>
    <section className="elliptic-workbench">
      <aside className="panel wallet-list"><div className="wallet-search"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search wallet address" onKeyDown={e=>e.key==="Enter"&&search()}/><button onClick={search}><Search/></button></div>{wallets.map(item=><button key={item.address} className={wallet===item.address?"active":""} onClick={()=>setWallet(item.address)}><span className={`risk-dot ${item.severity.toLowerCase()}`}/><p><b>{item.address}</b><small>Wallet · {statusLabel(item.review_status)}</small></p><strong>{item.score}</strong></button>)}</aside>
      <article className="graph-panel elliptic-graph"><div className="graph-title"><div><h2>Wallet ↔ transaction network</h2><p>Circles are wallets; diamonds are Bitcoin transactions</p></div><select value={hops} onChange={e=>setHops(Number(e.target.value))}><option value="1">1-hop</option><option value="2">2-hop</option><option value="3">3-hop</option></select></div><div className="legend"><span><i className="wallet-key"/>Wallet address</span><span><i className="tx-key"/>Transaction node</span><span>Arrows preserve official direction</span>{graphTruncated&&<span className="graph-limit">Showing a focused 45-node neighborhood</span>}</div><div className="graph"><ReactFlow nodes={nodes} edges={edges} fitView onNodeClick={(_,node)=>{if(node.id.startsWith("wallet:"))setWallet(node.id.slice(7))}}><Background color="#d8d5ce" gap={24} size={1}/><Controls showInteractive={false}/></ReactFlow></div></article>
      <aside id="elliptic-evidence" className="evidence blockchain-evidence">{detail?<><span className="eyebrow">SELECTED WALLET ADDRESS</span><h2>{wallet}</h2><div className="risk-score"><strong>{detail.score.score}</strong><span>/100<br/>structural score</span></div><div className="score-bar"><i style={{width:`${detail.score.score}%`}}/></div><dl><div><dt>Severity</dt><dd>{detail.score.severity}</dd></div><div><dt>Analyst judgment</dt><dd>{statusLabel(detail.score.review_status)}</dd></div><div><dt>First ordinal step</dt><dd>{detail.wallet.first_time_step??"—"}</dd></div></dl><div className="reason-box"><b>Structural evidence</b>{detail.score.reasons.length?detail.score.reasons.map((r:string)=><p key={r}>{r}</p>):<p>No structural threshold crossed.</p>}</div><div className="reference-label"><span>DATASET REFERENCE LABEL</span><b>{detail.reference_label?.name||"Unavailable"}</b><p>Not a MADs prediction. Never used as detector input.</p></div><div className="decision-row"><button onClick={()=>decide("confirmed_suspicious")}>Confirm</button><button onClick={()=>decide("cleared")}>Clear</button></div><a className="primary report-link" href={`${API}/api/blockchain-datasets/${datasetId}/report/${encodeURIComponent(wallet)}`} target="_blank" rel="noreferrer">Open evidence report ↗</a></>:<Empty text="Select a wallet to inspect evidence."/>}</aside>
    </section>
    <section className="panel evaluation-card"><div><span className="eyebrow">REFERENCE-LABEL EVALUATION</span><h2>Graph-only detector evaluation</h2><p>{evaluation?.scope}</p><small>{evaluation?.methodology}</small></div><div className="metric"><span>Precision</span><b>{evaluation?.precision==null?"N/A":`${(evaluation.precision*100).toFixed(1)}%`}</b></div><div className="metric"><span>Recall</span><b>{evaluation?.recall==null?"N/A":`${(evaluation.recall*100).toFixed(1)}%`}</b></div><div className="metric"><span>Known-label sample</span><b>{evaluation?.known_label_sample_count??0}</b><small>{evaluation?.unknown_labels_excluded??0} unknown excluded</small></div></section>
    {datasetId&&<VoiceAssistant context={{domain:"elliptic",dataset_id:datasetId,wallet_id:wallet}} resetKey={`elliptic-${datasetId}`} onAction={assistantAction}/>}
    {decisionDraft&&<DecisionConfirmation wallet={wallet} status={decisionDraft.status} onCancel={()=>setDecisionDraft(null)} onConfirm={async note=>{await api(`/api/blockchain-datasets/${datasetId}/wallets/${encodeURIComponent(wallet)}/decision`,{method:"POST",body:JSON.stringify({status:decisionDraft.status,note})});setDecisionDraft(null);await loadWallet();}}/>}
  </>;
}

function TransactionsView({ datasetId, runId, onBack }: { datasetId?: number; runId?: number; onBack: () => void }) {
  const [data,setData]=React.useState<any>({items:[],total:0,page:1,page_size:50}),[q,setQ]=React.useState(""),[page,setPage]=React.useState(1),[error,setError]=React.useState("");
  React.useEffect(()=>{if(!datasetId)return;api(`/api/datasets/${datasetId}/transactions?page=${page}&page_size=50&q=${encodeURIComponent(q)}`).then(setData).catch(e=>setError(e.message));},[datasetId,page,q]);
  return <>
    <div className="page-title"><div><span className="eyebrow teal">VERIFIED CSV RECORDS</span><h1>Imported transactions</h1><p>{data.total.toLocaleString()} accepted records from {data.source_filename||"the active CSV"}. No generated transactions are shown.</p></div><div className="actions"><button className="secondary" onClick={onBack}>Back to overview</button>{runId&&<><a className="secondary" href={`${API}/api/analyses/${runId}/report`} target="_blank" rel="noreferrer"><FileSearch/>Full analysis report</a><a className="secondary" href={`${API}/api/analyses/${runId}/export?format=csv`}><Download/>Export findings CSV</a></>}</div></div>
    <div className="toolbar"><label><Search/><input value={q} onChange={e=>{setQ(e.target.value);setPage(1)}} placeholder="Search transaction or account ID"/></label></div>
    {error&&<div className="error"><AlertTriangle/>{error}</div>}
    <section className="panel table-panel"><div className="table-wrap"><table><thead><tr><th>Transaction ID</th><th>Timestamp</th><th>Sender</th><th>Receiver</th><th>Documented amount</th></tr></thead><tbody>{data.items.map((row:any)=><tr key={row.transaction_id}><td><b>{row.transaction_id}</b></td><td>{new Date(row.timestamp).toLocaleString()}</td><td>{row.sender_account}</td><td>{row.receiver_account}</td><td>{row.currency} {row.amount.toLocaleString(undefined,{maximumFractionDigits:2})}</td></tr>)}</tbody></table></div>{!data.items.length&&<Empty text="No imported transactions match this search."/>}</section>
    <div className="pagination"><button disabled={page<=1} onClick={()=>setPage(x=>x-1)}>Previous</button><span>Page {page} of {Math.max(1,Math.ceil(data.total/50))}</span><button disabled={page*50>=data.total} onClick={()=>setPage(x=>x+1)}>Next</button></div>
  </>;
}

function Accounts({
  runId,
  onInspect,
}: {
  runId?: number;
  onInspect: () => void;
}) {
  const [data, setData] = React.useState<Score[]>([]),
    [q, setQ] = React.useState(""),
    [severity, setSeverity] = React.useState(sessionStorage.getItem("severityFilter")||""),
    [page,setPage]=React.useState(1),[total,setTotal]=React.useState(0),[detail,setDetail]=React.useState<any>(),[detailLoading,setDetailLoading]=React.useState(false),[decisionDraft,setDecisionDraft]=React.useState<{status:string}|null>(null),[error,setError]=React.useState("");
  const load=React.useCallback(async()=>{if(!runId)return;try{const x=await api(`/api/analyses/${runId}/scores?q=${encodeURIComponent(q)}&severity=${severity}&page=${page}&page_size=50`);setData(x.items);setTotal(x.total)}catch(e){setError((e as Error).message)}},[runId,q,severity,page]);
  React.useEffect(() => { void load(); }, [load]);
  async function explain(account:string){if(!runId)return;setError("");setDetail(undefined);setDetailLoading(true);try{setDetail(await api(`/api/analyses/${runId}/accounts/${encodeURIComponent(account)}`));}catch(e){setError((e as Error).message)}finally{setDetailLoading(false)}}
  async function startReview(account:string){if(!runId)return;await api(`/api/analyses/${runId}/accounts/${encodeURIComponent(account)}/decision`,{method:"POST",body:JSON.stringify({status:"under_review",note:"Review opened from prioritized queue"})});await load();if(detail?.score.account_id===account)await explain(account)}
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow teal">PRIORITIZED REVIEW QUEUE</span>
          <h1>Flagged accounts</h1>
          <p>
            Detector contributions are capped and overlapping patterns are
            deduplicated.
          </p>
        </div>
        {runId && (
          <div className="actions">
            <a className="secondary" href={`${API}/api/analyses/${runId}/report`} target="_blank" rel="noreferrer"><FileSearch /> Complete report</a>
            <a
              className="secondary"
              href={`${API}/api/analyses/${runId}/export?format=csv`}
            >
              <Download /> Export CSV
            </a>
            <a
              className="secondary"
              href={`${API}/api/analyses/${runId}/export?format=json`}
            >
              <Download /> JSON
            </a>
          </div>
        )}
      </div>
      <div className="toolbar">
        <label>
          <Search />
          <input
            placeholder="Search account ID"
            value={q}
            onChange={(e) => {setQ(e.target.value);setPage(1)}}
          />
        </label>
        <label>
          <Filter />
          <select
            value={severity}
            onChange={(e) => {setSeverity(e.target.value);setPage(1);sessionStorage.setItem("severityFilter",e.target.value)}}
          >
            <option value="">All severities</option>
            <option>High</option>
            <option>Medium</option>
            <option>Low</option>
          </select>
        </label>
      </div>
      <section className="panel table-panel">
        {data.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Risk</th>
                  <th>Severity</th>
                  <th>Leading reasons</th>
                  <th>Review status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <b>{s.account_id}</b>
                    </td>
                    <td>
                      <div className="risk-cell">
                        <strong>{s.score}</strong>
                        <span>
                          <i style={{ width: `${s.score}%` }} />
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className={`severity ${s.severity.toLowerCase()}`}>
                        {s.severity}
                      </span>
                    </td>
                    <td>
                      {Object.entries(s.breakdown).map(([k, v]) => (
                        <span className="reason-tag" key={k}>
                          {k.replace("_", " ")} +{v}
                        </span>
                      ))}
                    </td>
                    <td>{statusLabel(s.review_status)}</td>
                    <td>
                      <div className="row-actions"><button className="secondary compact-action" onClick={()=>void explain(s.account_id)}><Eye/>Why flagged?</button><button className="icon-btn" aria-label={`Open network for ${s.account_id}`} onClick={() => {sessionStorage.setItem("account", s.account_id);onInspect();}}><Network /></button></div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            text={
              runId
                ? "No accounts match the current filters."
                : "Run an analysis to populate the review queue."
            }
          />
        )}
      </section>
      <div className="pagination"><button disabled={page<=1} onClick={()=>setPage(x=>x-1)}>Previous</button><span>{total.toLocaleString()} flagged accounts · Page {page} of {Math.max(1,Math.ceil(total/50))}</span><button disabled={page*50>=total} onClick={()=>setPage(x=>x+1)}>Next</button></div>
      {error&&<div className="error"><AlertTriangle/>{error}</div>}
      {(detailLoading||detail)&&<div className="evidence-overlay" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!detailLoading)setDetail(undefined)}}><section className="panel flag-explanation" role="dialog" aria-modal="true" aria-label="Why this account was flagged">{detailLoading?<div className="evidence-loading"><Activity/><b>Loading verified evidence…</b><span>Reading detector findings and supporting CSV transactions.</span></div>:detail&&<><div className="panel-head"><div><span className="eyebrow">WHY THIS ACCOUNT WAS FLAGGED</span><h2>{detail.score.account_id}</h2><p>Automated score {detail.score.score}/100 ({detail.score.severity}) · Analyst status: {statusLabel(detail.score.review_status)}</p></div><button className="icon-btn" onClick={()=>setDetail(undefined)} aria-label="Close explanation"><X/></button></div><div className="explanation-grid"><div><h3>Explainable signals</h3>{detail.findings.map((finding:any)=><article className="reason-box" key={finding.id}><b>{finding.detector.replaceAll("_"," ")} · v{finding.detector_version}</b><p>{finding.reason}</p><small>{finding.limitations.join(" ")}</small><div>{finding.transaction_ids.map((id:string)=><code key={id}>{id}</code>)}</div></article>)}</div><aside><h3>Change analyst status</h3><p>Automated evidence remains unchanged; your judgment and note are stored separately in the audit trail.</p><button onClick={()=>void startReview(detail.score.account_id)}>Start review</button><button onClick={()=>setDecisionDraft({status:"confirmed_suspicious"})}>Confirm suspicious</button><button onClick={()=>setDecisionDraft({status:"cleared"})}>Clear account</button><a className="primary report-link" href={`${API}/api/analyses/${runId}/report/${encodeURIComponent(detail.score.account_id)}`} target="_blank" rel="noreferrer"><Download/>Account evidence report</a></aside></div></>}</section></div>}
      {decisionDraft&&detail&&<DecisionConfirmation wallet={detail.score.account_id} status={decisionDraft.status} onCancel={()=>setDecisionDraft(null)} onConfirm={async note=>{await api(`/api/analyses/${runId}/accounts/${encodeURIComponent(detail.score.account_id)}/decision`,{method:"POST",body:JSON.stringify({status:decisionDraft.status,note})});setDecisionDraft(null);await load();await explain(detail.score.account_id)}}/>}
    </>
  );
}

function NetworkView({
  datasetId,
  runId,
}: {
  datasetId?: number;
  runId?: number;
}) {
  const [account, setAccount] = React.useState(
      sessionStorage.getItem("account") || "00100",
    ),
    [detail, setDetail] = React.useState<any>(),
    [hops, setHops] = React.useState(1),
    [truncated, setTruncated] = React.useState(false),
    [graphSource, setGraphSource] = React.useState(""),
    [queue, setQueue] = React.useState<Score[]>([]),
    [nodes, setNodes] = React.useState<Node[]>([]),
    [edges, setEdges] = React.useState<Edge[]>([]),
    [error, setError] = React.useState(""),
    [decisionDraft, setDecisionDraft] = React.useState<{ status: string } | null>(null);
  const loadVersion = React.useRef(0);
  React.useEffect(() => {
    if (runId) api(`/api/analyses/${runId}/scores?page_size=12`).then((result: any) => {
      const items = result.items || [];
      setQueue(items);
      if (items[0]) {
        setAccount(items[0].account_id);
        sessionStorage.setItem("account", items[0].account_id);
      }
    }).catch(() => setQueue([]));
  }, [runId]);
  const load = React.useCallback(
    async (id = account) => {
      if (!datasetId) return;
      const version = ++loadVersion.current;
      setError("");
      try {
        const [net, det] = await Promise.all([
          api(`/api/datasets/${datasetId}/network?account_id=${encodeURIComponent(id)}&hops=${hops}${runId ? `&run_id=${runId}` : ""}`),
          runId
            ? api(
                `/api/analyses/${runId}/accounts/${encodeURIComponent(id)}`,
              ).catch(() => null)
            : null,
        ]);
        if (version !== loadVersion.current) return;
        setDetail(det);
        setTruncated(net.truncated);
        setGraphSource(net.source || "relational");
        const center = { x: 310, y: 230 };
        const neighbors = net.nodes.filter((n: any) => n.id !== id);
        setNodes(
          net.nodes.map((n: any) => {
            const neighborIndex = neighbors.findIndex((x: any) => x.id === n.id);
            const angle = (neighborIndex / Math.max(neighbors.length, 1)) * Math.PI * 2 - Math.PI / 2;
            const radius = hops === 2 ? 215 : 185;
            return {
              id: n.id,
              position:
                n.id === id
                  ? center
                  : {
                      x: center.x + Math.cos(angle) * radius,
                      y: center.y + Math.sin(angle) * radius,
                    },
              data: { label: "", score: n.score, severity: n.severity },
              ariaLabel: n.id === id ? "Selected account node" : "Connected account node",
              className: `flow-node ${String(n.severity || "unflagged").toLowerCase()} ${n.id === id ? "selected" : ""}`,
            };
          }),
        );
        setEdges(
          net.edges.map((e: any, i: number) => {
            const supporting = e.source === id || e.target === id;
            return {
              id: `e${i}-${e.source}-${e.target}`,
              source: e.source,
              target: e.target,
              label: `${e.currency} ${e.total.toLocaleString()} · ${e.count}×`,
              data: { transactions: e.transactions },
              className: supporting ? "supporting-edge" : "",
              animated: e.count > 1,
              markerEnd: { type: MarkerType.ArrowClosed, color: supporting ? "#f45f72" : "#a8acb8" },
              style: { stroke: supporting ? "#f45f72" : "#a8acb8", strokeWidth: supporting ? 3 : 1.7 },
              labelStyle: { fill: "#777381", fontSize: 10 },
              labelBgStyle: { fill: "#fffefa", fillOpacity: 0.94 },
            };
          }),
        );
      } catch (e) {
        if (version === loadVersion.current) setError((e as Error).message);
      }
    },
    [datasetId, runId, account, hops],
  );
  React.useEffect(() => {
    load();
  }, [load]);
  async function decide(status: string) {
    if (!runId) return;
    const note =
      status === "confirmed_suspicious" || status === "cleared"
        ? prompt("Required decision note:") || ""
        : "";
    if ((status === "confirmed_suspicious" || status === "cleared") && !note)
      return;
    await api(`/api/analyses/${runId}/accounts/${account}/decision`, {
      method: "POST",
      body: JSON.stringify({ status, note }),
    });
    load();
  }
  async function assistantAction(action: AssistantAction) {
    if (!runId) return;
    if (action.type === "filter_high_risk") {
      const result = await api(`/api/analyses/${runId}/scores?severity=High&page_size=100`);
      setQueue(result.items || []);
      return;
    }
    if ((action.type === "select_wallet" || action.type === "show_evidence") && action.wallet_id) {
      setAccount(action.wallet_id); sessionStorage.setItem("account", action.wallet_id);
      if (action.type === "show_evidence") {
        const wanted = new Set(action.transaction_ids || []);
        if (wanted.size) setEdges(current => current.map(edge => {
          const transactions = (edge.data?.transactions as { id: string }[] | undefined) || [];
          const highlighted = transactions.some(tx => wanted.has(tx.id));
          return highlighted ? { ...edge, animated: true, className: "assistant-highlighted-edge", style: { ...edge.style, stroke: "#8e54ca", strokeWidth: 4 } } : edge;
        }));
        window.setTimeout(() => document.getElementById("bank-evidence")?.scrollIntoView({ behavior: "smooth", block: "center" }), 80);
      }
      return;
    }
    if (action.type === "expand_network") { setHops(value => Math.min(2, value + 1)); return; }
    if (action.type === "open_decision_form" && action.wallet_id && action.status) {
      setAccount(action.wallet_id); sessionStorage.setItem("account", action.wallet_id); setDecisionDraft({ status: action.status });
    }
  }
  return (
    <>
      <div className="page-title compact-title">
        <div>
          <span className="eyebrow teal">MADs / FINANCIAL INTELLIGENCE</span>
          <h1>Network explorer</h1>
          <p>Follow the transaction trail and inspect explainable evidence.</p>
        </div>
        <div className="network-controls">
          <input
            value={account}
            onChange={(e) => setAccount(e.target.value)}
            aria-label="Account ID"
          />
          <button className="secondary" onClick={() => load()}>
            Trace
          </button>
          <select
            value={hops}
            onChange={(e) => setHops(Number(e.target.value))}
          >
            <option value={1}>1-hop</option>
            <option value={2}>2-hop</option>
          </select>
        </div>
      </div>
      {error && (
        <div className="error">
          <AlertTriangle />
          {error}
        </div>
      )}
      <section className="network-layout">
        <aside className="network-queue">
          <div className="queue-head"><span className="eyebrow">INVESTIGATIONS</span><b>{queue.length} priority accounts</b></div>
          {queue.map((item) => (
            <button key={item.account_id} className={item.account_id === account ? "active" : ""} onClick={() => { setAccount(item.account_id); sessionStorage.setItem("account", item.account_id); }}>
              <span className={`risk-dot ${item.severity.toLowerCase()}`} />
              <p><b>{item.account_id}</b><small>{statusLabel(item.review_status)}</small></p>
              <strong>{item.score}</strong>
            </button>
          ))}
        </aside>
        <article className="graph-panel">
          <div className="graph-title"><div><h2>Transaction network</h2><p>Select a node to inspect an account</p></div><span><i /> {nodes.length} nodes</span></div>
          <div className="legend">
            <span>
              <i className="high" />
              High risk
            </span>
            <span>
              <i className="medium" />
              Medium risk
            </span>
            <span>
              <i />
              Unflagged
            </span>
            <span>Arrows show direction</span>
            <span className="graph-source">
              {graphSource === "neo4j" ? "Neo4j graph" : "Relational fallback"}
            </span>
          </div>
          <div className="graph">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              minZoom={0.35}
              maxZoom={1.8}
              onNodeClick={(_, node) => {
                setAccount(node.id);
                sessionStorage.setItem("account", node.id);
              }}
            >
              <Background color="#d8d5ce" gap={24} size={1} />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
          {truncated && (
            <div className="truncated">
              Network limits reached. Results were truncated.
            </div>
          )}
        </article>
        <aside id="bank-evidence" className="evidence">
          {detail ? (
            <>
              <div className="account-head">
                <div>
                  <span className="eyebrow">SELECTED ACCOUNT</span>
                  <h2>{account}</h2>
                </div>
                <div
                  className={`score-orb ${detail.score.severity.toLowerCase()}`}
                >
                  {detail.score.score}
                  <small>/100</small>
                </div>
              </div>
              <p className="notice">{detail.notice}</p>
              <div className="decision-row">
                <button onClick={() => decide("under_review")}>
                  Start review
                </button>
                <button onClick={() => decide("confirmed_suspicious")}>
                  Confirm
                </button>
                <button onClick={() => decide("cleared")}>Clear</button>
              </div>
              {detail.findings.map((f: any) => (
                <div className="finding" key={f.id}>
                  <span>
                    {f.detector.replaceAll("_", " ")} · v{f.detector_version}
                  </span>
                  <p>{f.reason}</p>
                  <details>
                    <summary>
                      {f.transaction_ids.length} supporting transactions
                    </summary>
                    {detail.transactions
                      .filter((t: any) =>
                        f.transaction_ids.includes(t.transaction_id),
                      )
                      .map((t: any) => (
                        <div className="tx" key={t.transaction_id}>
                          <b>{t.transaction_id}</b>
                          <span>
                            {t.sender_account} → {t.receiver_account}
                          </span>
                          <strong>{money(t.amount, t.currency)}</strong>
                        </div>
                      ))}
                    <small>{f.limitations.join(" ")}</small>
                  </details>
                </div>
              ))}
              <a
                className="report"
                href={`${API}/api/analyses/${runId}/report/${account}`}
                target="_blank"
              >
                <Download /> Printable investigation report
              </a>
            </>
          ) : (
            <Empty text="Select a flagged account to review reasons and supporting transactions." />
          )}
        </aside>
      </section>
      {detail?.transactions?.length ? (
        <section className="timeline-strip">
          <div><span className="eyebrow">IMPORTED DATA REPLAY</span><h2>Chronological transaction timeline</h2></div>
          <div className="timeline-track">{detail.transactions.slice(0, 8).map((tx: any, index: number) => <div key={tx.transaction_id} style={{ "--step": index } as React.CSSProperties}><i /><b>{tx.transaction_id}</b><span>{tx.sender_account} → {tx.receiver_account}</span><strong>{money(tx.amount, tx.currency)}</strong></div>)}</div>
        </section>
      ) : null}
      {datasetId && runId && <VoiceAssistant context={{ domain: "bank", dataset_id: datasetId, run_id: runId, wallet_id: account }} resetKey={`bank-${datasetId}-${runId}`} onAction={assistantAction} />}
      {decisionDraft && <DecisionConfirmation wallet={account} status={decisionDraft.status} onCancel={() => setDecisionDraft(null)} onConfirm={async note => { await api(`/api/analyses/${runId}/accounts/${encodeURIComponent(account)}/decision`, { method: "POST", body: JSON.stringify({ status: decisionDraft.status, note }) }); setDecisionDraft(null); await load(); }} />}
    </>
  );
}

function HoneypotView({ summary, runId, onInspect }: { summary: any; runId?: number; onInspect: () => void }) {
  const [sessions,setSessions]=React.useState<any[]>([]),[selected,setSelected]=React.useState<number>(),[detail,setDetail]=React.useState<any>(),[name,setName]=React.useState("Payment portal decoy"),[profile,setProfile]=React.useState("payment_portal"),[eventType,setEventType]=React.useState("login_failure"),[source,setSource]=React.useState("test-client-01"),[target,setTarget]=React.useState("decoy-account"),[amount,setAmount]=React.useState(""),[note,setNote]=React.useState("Reviewed in the isolated honeypot laboratory"),[busy,setBusy]=React.useState(false),[error,setError]=React.useState("");
  const refresh=React.useCallback(async(id?:number)=>{const rows=await api("/api/honeypot/sessions");setSessions(rows);const wanted=id||selected||rows[0]?.id;if(wanted){setSelected(wanted);setDetail(await api(`/api/honeypot/sessions/${wanted}`))}else setDetail(undefined)},[selected]);
  React.useEffect(()=>{void refresh().catch(e=>setError(e.message))},[]);
  async function createSession(){setBusy(true);setError("");try{const x=await api("/api/honeypot/sessions",{method:"POST",body:JSON.stringify({name,decoy_profile:profile})});await refresh(x.session.id)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  async function addEvent(){if(!selected)return;setBusy(true);setError("");try{const x=await api(`/api/honeypot/sessions/${selected}/events`,{method:"POST",body:JSON.stringify({event_type:eventType,source_alias:source,target_alias:target,amount:amount?Number(amount):null,currency:amount?"USD":null})});setDetail(x);await refresh(selected)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  async function changeStatus(status:string){if(!selected)return;setBusy(true);setError("");try{const x=await api(`/api/honeypot/sessions/${selected}/status`,{method:"POST",body:JSON.stringify({status,note})});setDetail(x);await refresh(selected)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  return (
    <>
      <div className="page-title">
        <div><span className="eyebrow teal">MADs / DEFENSIVE DECEPTION</span><h1>Honeypot lab</h1><p>Persistent decoy sessions with live event scoring, evidence capture, and reporting.</p></div>
        <div className="actions"><button className="secondary" onClick={onInspect}>Open network explorer</button>{selected&&<a className="primary report-link" href={`${API}/api/honeypot/sessions/${selected}/report`} target="_blank" rel="noreferrer"><Download/>Evidence report</a>}</div>
      </div>
      <section className="simulation-banner"><ShieldCheck /><div><b>Working isolated honeypot · Safe defensive sandbox</b><span>Events are persisted, scored, audited, and reportable. The decoy never settles money or contacts an external account.</span></div><strong>ISOLATED</strong></section>
      {error&&<div className="error"><AlertTriangle/>{error}</div>}
      <section className="metrics honeypot-metrics">
        {[
          ["Decoy sessions", sessions.length, Activity],
          ["Captured events", detail?.session.event_count || 0, Database],
          ["Session risk", detail?`${detail.session.risk_score}/100`:"—", AlertTriangle],
          ["Live integrations", 0, ShieldCheck],
        ].map(([label, value, Icon]: any) => <article className="tilt-card" key={label}><div className="metric-icon"><Icon /></div><span>{label}</span><strong>{value}</strong><small>{label === "Live integrations" ? "No external systems" : "Persisted in this workspace"}</small></article>)}
      </section>
      <section className="honeypot-grid">
        <article className="panel session-list"><div className="panel-head"><div><h2>Monitoring sessions</h2><p>Create and select isolated decoys</p></div></div><div className="honeypot-create"><input value={name} onChange={e=>setName(e.target.value)} aria-label="Session name"/><select value={profile} onChange={e=>setProfile(e.target.value)} aria-label="Decoy profile"><option value="payment_portal">Payment portal</option><option value="wallet_console">Wallet console</option><option value="kyc_portal">KYC portal</option></select><button className="primary" disabled={busy||name.trim().length<3} onClick={()=>void createSession()}><Plus/>Create session</button></div>{sessions.map(s=><button key={s.id} className={`session-card ${selected===s.id?"active":""}`} onClick={()=>void refresh(s.id)}><ShieldCheck/><p><b>HP-{String(s.id).padStart(3,"0")}</b><span>{s.name}</span><small>{s.event_count} events · {s.status}</small></p><strong>{s.risk_score}</strong></button>)}{!sessions.length&&<Empty text="Create the first isolated monitoring session."/>}</article>
        <article className="panel honeypot-console"><div className="panel-head"><div><span className="eyebrow">{detail?`SESSION / HP-${String(detail.session.id).padStart(3,"0")}`:"NO SESSION SELECTED"}</span><h2>{detail?.session.name||"Create a decoy session"}</h2></div>{detail&&<span className={`status-pill ${detail.session.status}`}>{detail.session.status}</span>}</div>{detail?<><div className="event-composer"><h3>Inject a safe test event</h3><p>Use aliases only. This exercises the real capture, scoring, audit, and report pipeline.</p><select value={eventType} onChange={e=>setEventType(e.target.value)}><option value="login_failure">Login failure (+8)</option><option value="account_enumeration">Account enumeration (+18)</option><option value="transfer_attempt">Transfer attempt (+28)</option><option value="automation_signal">Automation signal (+22)</option><option value="privileged_action">Privileged action (+38)</option></select><input value={source} onChange={e=>setSource(e.target.value)} placeholder="Source alias"/><input value={target} onChange={e=>setTarget(e.target.value)} placeholder="Target decoy alias"/><input value={amount} onChange={e=>setAmount(e.target.value)} type="number" min="0" placeholder="Optional test amount (USD)"/><button className="primary" disabled={busy||detail.session.status==="closed"||!source.trim()} onClick={()=>void addEvent()}><Activity/>Capture event</button></div><div className="honeypot-status"><input value={note} onChange={e=>setNote(e.target.value)} aria-label="Status rationale"/><button disabled={busy||note.trim().length<10} onClick={()=>void changeStatus("monitoring")}>Monitor</button><button disabled={busy||note.trim().length<10} onClick={()=>void changeStatus("escalated")}>Escalate</button><button disabled={busy||note.trim().length<10} onClick={()=>void changeStatus("closed")}>Close</button></div><div className="event-stream"><h3>Captured evidence</h3>{detail.events.map((e:any)=><article key={e.id}><i className={e.severity.toLowerCase()}/><div><b>{e.event_type.replaceAll("_"," ")}</b><span>{e.source_alias} → {e.target_alias}</span><p>{e.reason}</p><small>{new Date(e.created_at).toLocaleString()}</small></div><strong>+{e.contribution}</strong></article>)}{!detail.events.length&&<Empty text="No events captured. Inject a safe test event above."/>}</div></>:<Empty text="Create or select a session to begin monitoring."/>}</article>
      </section>
    </>
  );
}

function SettingsView() {
  const [value, setValue] = React.useState<any>(),
    [saved, setSaved] = React.useState(""),[error,setError]=React.useState("");
  React.useEffect(() => {
    api("/api/settings").then(setValue);
  }, []);
  if (!value) return <Empty text="Loading detection settings…" />;
  async function save() {
    setError("");setSaved("");
    try{const r = await api("/api/settings", {method: "POST",body: JSON.stringify({ config: value.config })});setValue(r);setSaved(`Version ${r.version} saved. New analyses will use it.`);}catch(e){setError((e as Error).message)}
  }
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow teal">SUPERVISOR CONTROL</span>
          <h1>
            Detection settings <span className="version">v{value.version}</span>
          </h1>
          <p>Historical runs retain their original version.</p>
        </div>
        <button className="primary" onClick={save}>
          <ShieldCheck /> Save new version
        </button>
      </div>
      {saved && <div className="success">{saved}</div>}
      {error && <div className="error"><AlertTriangle/>{error}</div>}
      <div className="simulation-banner"><ShieldCheck/><div><b>Strict, versioned detector parameters</b><span>Invalid ranges are rejected by the API. Medium risk must remain below high risk. Historical reports retain the exact settings version used.</span></div></div>
      <section className="settings-grid">
        {Object.entries(value.config).map(([k, v]) => {
          const limits:any={fan_window_minutes:[1,1440],fan_min_senders:[2,100],fan_min_receivers:[1,100],fan_share:[0.1,1],cycle_window_hours:[1,720],cycle_max_length:[3,8],chain_window_minutes:[1,1440],chain_min_share:[0.1,1],new_account_days:[1,3650],shared_min_accounts:[2,100],medium_risk_score:[1,99],high_risk_score:[2,100]};
          return (
          <label className="setting" key={k}>
            <span>{k.replaceAll("_", " ")}</span>
            <small>Allowed: {limits[k]?.[0]}–{limits[k]?.[1]}</small>
            <input
              type="number"
              step={String(v).includes(".") ? "0.05" : "1"}
              min={limits[k]?.[0]} max={limits[k]?.[1]}
              value={v as any}
              onChange={(e) =>
                setValue({
                  ...value,
                  config: { ...value.config, [k]: Number(e.target.value) },
                })
              }
            />
          </label>
        )})}
      </section>
    </>
  );
}
function Audit() {
  const [rows, setRows] = React.useState<any[]>([]);
  React.useEffect(() => {
    api("/api/audit").then(setRows);
  }, []);
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow teal">IMMUTABLE ACTIVITY TRAIL</span>
          <h1>Audit history</h1>
          <p>
            Authentication, imports, analyses, settings, and review decisions.
          </p>
        </div>
      </div>
      <section className="panel audit-list">
        {rows.length ? (
          rows.map((x) => (
            <div key={x.id}>
              <i />
              <span>{new Date(x.created_at).toLocaleString()}</span>
              <b>{x.action}</b>
              <code>
                {x.target_type} #{x.target_id}
              </code>
              <small>User {x.user_id || "system"}</small>
            </div>
          ))
        ) : (
          <Empty text="No audit events yet." />
        )}
      </section>
    </>
  );
}
function Empty({ text }: { text: string }) {
  return (
    <div className="empty">
      <Network />
      <p>{text}</p>
    </div>
  );
}
const appWindow = window as typeof window & { __muleTraceRoot?: ReturnType<typeof createRoot> };
const appRoot =
  appWindow.__muleTraceRoot ||
  (appWindow.__muleTraceRoot = createRoot(document.getElementById("root")!));
appRoot.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
