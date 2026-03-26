import { useState, useEffect, useRef, useCallback } from "react";

// ─── Font ──────────────────────────────────────────────────────────────────
const _fl = document.createElement("link");
_fl.rel = "stylesheet";
_fl.href = "https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@300;400;500;600&display=swap";
document.head.appendChild(_fl);

// ─── API Layer (matches your FastAPI routes exactly) ──────────────────────
const BASE = "http://localhost:8000/api";
const apiFetch = (path, opts) =>
  fetch(`${BASE}${path}`, opts).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); });

const API = {
  dashboard:   (grade) => apiFetch(`/dashboard${grade ? `?grade=${grade}` : ""}`),
  call:        (id)    => apiFetch(`/call/${id}`),
  upload:      (files) => { const fd = new FormData(); files.forEach(f => fd.append("files", f)); return apiFetch("/upload", { method: "POST", body: fd }); },
  jobStatus:   (id)    => apiFetch(`/jobs/${id}`),
  leaderboard: ()      => apiFetch("/leaderboard"),
  seed:        ()      => apiFetch("/seed", { method: "POST" }),
  audioUrl:    (id)    => `${BASE}/audio/${id}`,
};

// ─── Helpers ────────────────────────────────────────────────────────────────
const GRADE_CONFIG = {
  excellent: { color: "#22c55e", bg: "rgba(34,197,94,0.10)",  border: "rgba(34,197,94,0.30)",  label: "Excellent", letter: "A" },
  good:      { color: "#38bdf8", bg: "rgba(56,189,248,0.10)", border: "rgba(56,189,248,0.30)", label: "Good",      letter: "B" },
  average:   { color: "#f59e0b", bg: "rgba(245,158,11,0.10)", border: "rgba(245,158,11,0.30)", label: "Average",   letter: "C" },
  poor:      { color: "#f43f5e", bg: "rgba(244,63,94,0.10)",  border: "rgba(244,63,94,0.30)",  label: "Poor",      letter: "D" },
};
const gc = (g) => GRADE_CONFIG[g] || { color: "#94a3b8", bg: "transparent", border: "#334155", label: g || "—", letter: "—" };

const fmtScore = (s) => s != null ? `${s}` : "—";
const fmtPct   = (p) => p != null ? `${p}%` : "—";

// ─── Score Ring ──────────────────────────────────────────────────────────────
function ScoreRing({ score, size = 72 }) {
  if (score == null) return <div style={{ width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12 }}>—</div>;
  const g = score >= 90 ? "excellent" : score >= 75 ? "good" : score >= 60 ? "average" : "poor";
  const color = gc(g).color;
  const r = size / 2 - 6;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)", flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1e293b" strokeWidth={5} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={5}
        strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
        style={{ transition: "stroke-dasharray 0.8s ease" }} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        fill={color} fontSize={size * 0.22} fontFamily="IBM Plex Mono" fontWeight="600"
        style={{ transform: "rotate(90deg)", transformOrigin: "center" }}>{score}</text>
    </svg>
  );
}

// ─── Stat Card ───────────────────────────────────────────────────────────────
function StatCard({ label, count, active, color, onClick }) {
  const cfg = GRADE_CONFIG[color] || { color: "#94a3b8", bg: "rgba(148,163,184,0.06)", border: "#1e293b" };
  return (
    <button onClick={onClick} style={{
      flex: 1, minWidth: 0, display: "flex", flexDirection: "column", alignItems: "center",
      gap: 4, padding: "14px 8px", borderRadius: 12, cursor: "pointer",
      background: active ? cfg.bg : "rgba(15,23,42,0.5)",
      border: `1px solid ${active ? cfg.border : "#0f172a"}`,
      transition: "all 0.18s",
      boxShadow: active ? `0 0 20px ${cfg.color}22` : "none",
    }}>
      <span style={{ fontSize: 26, fontFamily: "Syne", fontWeight: 800, color: active ? cfg.color : "#e2e8f0" }}>{count ?? 0}</span>
      <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", color: active ? cfg.color : "#334155" }}>{label}</span>
    </button>
  );
}

// ─── Call List Item ───────────────────────────────────────────────────────────
function CallListItem({ call, active, onClick }) {
  const cfg = gc(call.grade);
  return (
    <button onClick={onClick} style={{
      width: "100%", textAlign: "left", padding: "12px 14px", borderRadius: 10,
      background: active ? cfg.bg : "rgba(15,23,42,0.4)",
      border: `1px solid ${active ? cfg.border : "#0f172a"}`,
      cursor: "pointer", transition: "all 0.15s", marginBottom: 4,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 600, color: active ? "#e2e8f0" : "#94a3b8" }}>
          {call.phone_number || call.call_id}
        </span>
        {call.total_score != null
          ? <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 700, color: cfg.color }}>{call.total_score}%</span>
          : <span style={{ fontSize: 9, color: "#1e3a5f", fontFamily: "IBM Plex Mono" }}>{call.status}</span>}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "65%" }}>
          {call.agent_id}
        </span>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {call.has_fatal && <span style={{ fontSize: 9, color: "#f43f5e", fontFamily: "IBM Plex Mono" }}>FATAL</span>}
          {call.grade && <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", padding: "1px 6px", borderRadius: 4, background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}>{cfg.label}</span>}
        </div>
      </div>
      <div style={{ fontSize: 9, color: "#1e3a5f", fontFamily: "IBM Plex Mono", marginTop: 3 }}>{call.duration_formatted} · {call.created_at?.slice(0,10)}</div>
    </button>
  );
}

// ─── Transcript View (with red flagging) ─────────────────────────────────────
function TranscriptView({ transcript, speakerStats }) {
  if (!transcript?.length) return (
    <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 40 }}>
      Transcript not available
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {transcript.map((entry, i) => {
        const isAgent = entry.speaker_label === "Agent";
        const isFlagged = entry.is_flagged;
        return (
          <div key={i} style={{ display: "flex", gap: 10, flexDirection: isAgent ? "row" : "row-reverse" }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%", flexShrink: 0, marginTop: 2,
              background: isAgent ? (isFlagged ? "rgba(244,63,94,0.15)" : "rgba(99,102,241,0.15)") : "rgba(30,41,59,0.8)",
              border: `2px solid ${isAgent ? (isFlagged ? "#f43f5e" : "#6366f1") : "#334155"}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 9, fontFamily: "IBM Plex Mono", color: isAgent ? (isFlagged ? "#f43f5e" : "#a5b4fc") : "#94a3b8",
              fontWeight: 600,
            }}>{isAgent ? "AG" : "CX"}</div>

            <div style={{ maxWidth: "76%", display: "flex", flexDirection: "column", gap: 3, alignItems: isAgent ? "flex-start" : "flex-end" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>
                  {entry.start_time?.toFixed(1)}s – {entry.end_time?.toFixed(1)}s
                </span>
                <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: isAgent ? "#6366f1" : "#475569" }}>
                  {entry.speaker_label}
                </span>
                {isFlagged && (
                  <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: "#f43f5e", padding: "0 4px", borderRadius: 3, background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.25)" }}>
                    ⚠ Review
                  </span>
                )}
              </div>
              <div style={{
                padding: "10px 14px", borderRadius: 12, fontSize: 12, lineHeight: 1.65,
                fontFamily: "IBM Plex Mono", color: isFlagged ? "#fca5a5" : "#cbd5e1",
                background: isFlagged
                  ? "rgba(244,63,94,0.08)"
                  : isAgent ? "rgba(99,102,241,0.09)" : "rgba(30,41,59,0.7)",
                border: `1px solid ${isFlagged ? "rgba(244,63,94,0.3)" : isAgent ? "rgba(99,102,241,0.2)" : "#0f172a"}`,
                borderLeft: isFlagged ? "3px solid #f43f5e" : undefined,
              }}>
                {entry.text}
              </div>
              {isFlagged && entry.flag_reason && (
                <span style={{ fontSize: 10, color: "#f43f5e", fontFamily: "IBM Plex Mono", marginLeft: 4 }}>
                  ↳ {entry.flag_reason}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Analysis Panel ───────────────────────────────────────────────────────────
function AnalysisPanel({ scorecard }) {
  const [openSection, setOpenSection] = useState("OPENING");
  if (!scorecard) return (
    <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 40 }}>
      Analysis not available — call may still be processing.
    </div>
  );

  const sectionColors = { OPENING: "#818cf8", SALES: "#38bdf8", SOFT_SKILLS: "#a78bfa", CLOSING: "#34d399" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Improvement areas */}
      {scorecard.improvement_areas?.length > 0 && (
        <div style={{ padding: 14, borderRadius: 12, background: "rgba(244,63,94,0.06)", border: "1px solid rgba(244,63,94,0.2)" }}>
          <div style={{ fontSize: 9, color: "#f43f5e", fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>
            Areas to Improve
          </div>
          {scorecard.improvement_areas.map((a, i) => (
            <div key={i} style={{ fontSize: 11, color: "#fca5a5", fontFamily: "IBM Plex Mono", marginBottom: 4 }}>
              • {a}
            </div>
          ))}
        </div>
      )}

      {/* Strengths */}
      {scorecard.strengths?.length > 0 && (
        <div style={{ padding: 14, borderRadius: 12, background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.2)" }}>
          <div style={{ fontSize: 9, color: "#22c55e", fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>
            Strengths
          </div>
          {scorecard.strengths.map((s, i) => (
            <div key={i} style={{ fontSize: 11, color: "#86efac", fontFamily: "IBM Plex Mono", marginBottom: 4 }}>
              ✓ {s}
            </div>
          ))}
        </div>
      )}

      {/* Sections */}
      {scorecard.sections?.map(sec => {
        const isOpen = openSection === sec.section_name;
        const color = sectionColors[sec.section_name] || "#94a3b8";
        return (
          <div key={sec.section_name} style={{ borderRadius: 12, border: `1px solid ${isOpen ? color + "44" : "#0f172a"}`, overflow: "hidden" }}>
            <button onClick={() => setOpenSection(isOpen ? null : sec.section_name)} style={{
              width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "12px 16px", background: isOpen ? `${color}10` : "rgba(15,23,42,0.5)",
              border: "none", cursor: "pointer",
            }}>
              <span style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 13, color: isOpen ? color : "#94a3b8" }}>
                {sec.section_name.replace("_", " ")}
              </span>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <div style={{ width: 60, height: 3, background: "#1e293b", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${sec.section_percentage}%`, background: color, borderRadius: 2 }} />
                </div>
                <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", color, fontWeight: 600 }}>
                  {sec.section_score}/{sec.section_max}
                </span>
              </div>
            </button>
            {isOpen && (
              <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
                {sec.parameters?.map((p, i) => {
                  const pColor = p.percentage >= 90 ? "#22c55e" : p.percentage >= 70 ? "#38bdf8" : p.percentage >= 50 ? "#f59e0b" : "#f43f5e";
                  return (
                    <div key={i}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ fontSize: 11, color: "#cbd5e1", fontFamily: "IBM Plex Mono" }}>{p.parameter}</span>
                          {p.is_critical_miss && <span style={{ fontSize: 9, color: "#f43f5e", fontFamily: "IBM Plex Mono", padding: "0 4px", borderRadius: 3, background: "rgba(244,63,94,0.1)" }}>MISSED</span>}
                        </div>
                        <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 600, color: pColor }}>
                          {p.score}/{p.max_score}
                        </span>
                      </div>
                      <div style={{ height: 3, background: "#1e293b", borderRadius: 2, marginBottom: 4, overflow: "hidden" }}>
                        <div style={{ height: "100%", width: `${p.percentage}%`, background: pColor, borderRadius: 2, boxShadow: `0 0 6px ${pColor}66`, transition: "width 0.6s ease" }} />
                      </div>
                      <p style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", margin: 0 }}>{p.reason}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Fatal Flags Panel ───────────────────────────────────────────────────────
function FatalFlagsPanel({ fatalFlags }) {
  if (!fatalFlags) return null;
  const entries = [
    ["Right Party Confirmation", fatalFlags.right_party_confirmation],
    ["Rude Behaviour",           fatalFlags.rude_behaviour],
    ["Miss Sell",                fatalFlags.miss_sell],
    ["Disposition",              fatalFlags.disposition],
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {entries.map(([label, val]) => {
        const isFatal = val === "F";
        return (
          <div key={label} style={{
            display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8,
            background: isFatal ? "rgba(244,63,94,0.1)" : "rgba(34,197,94,0.06)",
            border: `1px solid ${isFatal ? "rgba(244,63,94,0.3)" : "rgba(34,197,94,0.2)"}`,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: isFatal ? "#f43f5e" : "#22c55e", flexShrink: 0, boxShadow: `0 0 8px ${isFatal ? "#f43f5e" : "#22c55e"}99` }} />
            <span style={{ flex: 1, fontSize: 11, fontFamily: "IBM Plex Mono", color: "#94a3b8" }}>{label}</span>
            <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono", fontWeight: 700, color: isFatal ? "#f43f5e" : "#22c55e", letterSpacing: 1 }}>{val || "NF"}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Audio Player ─────────────────────────────────────────────────────────────
function AudioPlayer({ audioUrl, callId }) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const isMock = !audioUrl || audioUrl.includes("localhost");

  const fmtT = (s) => `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,"0")}`;

  useEffect(() => {
    setPlaying(false); setProgress(0); setDuration(0);
  }, [callId]);

  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = volume;
  }, [volume]);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "0 8px", height: "100%" }}>
      <audio ref={audioRef} src={isMock ? undefined : audioUrl}
        onTimeUpdate={() => { if (audioRef.current) setProgress(audioRef.current.currentTime); }}
        onLoadedMetadata={() => { if (audioRef.current) setDuration(audioRef.current.duration); }}
        onEnded={() => setPlaying(false)} />

      {/* Play/Pause */}
      <button onClick={() => {
        if (!audioRef.current || isMock) return;
        playing ? audioRef.current.pause() : audioRef.current.play();
        setPlaying(p => !p);
      }} style={{
        width: 38, height: 38, borderRadius: "50%",
        background: "#6366f1", border: "none", cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: "0 0 20px #6366f155", flexShrink: 0,
      }}>
        {playing
          ? <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
          : <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>}
      </button>

      {/* Seek */}
      <span style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", width: 32, flexShrink: 0 }}>{fmtT(progress)}</span>
      <div style={{ flex: 1, height: 4, background: "#1e293b", borderRadius: 4, position: "relative", cursor: "pointer" }}
        onClick={e => {
          if (!audioRef.current || isMock) return;
          const rect = e.currentTarget.getBoundingClientRect();
          const pct = (e.clientX - rect.left) / rect.width;
          audioRef.current.currentTime = pct * duration;
        }}>
        <div style={{ position: "absolute", left: 0, top: 0, height: "100%", background: "#6366f1", borderRadius: 4, width: duration ? `${(progress/duration)*100}%` : "0%", transition: "width 0.3s" }} />
      </div>
      <span style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono", width: 32, flexShrink: 0 }}>{fmtT(duration)}</span>

      {/* Volume */}
      <svg width="14" height="14" viewBox="0 0 24 24" fill="#475569" style={{ flexShrink: 0 }}>
        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
      </svg>
      <input type="range" min={0} max={1} step={0.05} value={volume}
        onChange={e => setVolume(Number(e.target.value))}
        style={{ width: 64, accentColor: "#6366f1", cursor: "pointer" }} />

      {isMock && <span style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>MOCK MODE</span>}
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [metrics, setMetrics] = useState(null);
  const [callList, setCallList] = useState([]);
  const [activeGrade, setActiveGrade] = useState(null);  // null = "all"
  const [selectedCall, setSelectedCall] = useState(null);
  const [callDetail, setCallDetail] = useState(null);
  const [activeTab, setActiveTab] = useState("transcript");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const pollingRef = useRef({});

  // ── Load dashboard ──────────────────────────────────────────────────────────
  const loadDashboard = useCallback(async (grade) => {
    try {
      const data = await API.dashboard(grade);
      setMetrics(data.metrics);
      setCallList(data.calls);
      setError(null);
    } catch (e) {
      setError("Backend not connected. Run: uvicorn main:app --reload");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(activeGrade); }, [activeGrade, loadDashboard]);

  // ── Auto-refresh processing calls ────────────────────────────────────────
  useEffect(() => {
    const processing = callList.filter(c => c.status === "processing" || c.status === "pending");
    processing.forEach(c => {
      if (pollingRef.current[c.call_id]) return;
      pollingRef.current[c.call_id] = setInterval(async () => {
        try {
          const updated = await API.call(c.call_id);
          if (updated.status === "completed" || updated.status === "failed") {
            clearInterval(pollingRef.current[c.call_id]);
            delete pollingRef.current[c.call_id];
            loadDashboard(activeGrade);
          }
        } catch (_) {}
      }, 4000);
    });
    return () => Object.values(pollingRef.current).forEach(clearInterval);
  }, [callList]);

  // ── Load call detail ──────────────────────────────────────────────────────
  const selectCall = async (callItem) => {
    setSelectedCall(callItem);
    setCallDetail(null);
    try {
      const detail = await API.call(callItem.call_id);
      setCallDetail(detail);
    } catch (e) {
      console.error("Could not load call detail:", e);
    }
  };

  // ── Upload ────────────────────────────────────────────────────────────────
  const handleUpload = async (files) => {
    setUploading(true);
    try {
      await API.upload(files);
      await loadDashboard(activeGrade);
    } catch (e) {
      alert("Upload failed. Is the backend running?");
    } finally {
      setUploading(false);
    }
  };

  // ── Seed mock data ────────────────────────────────────────────────────────
  const seedData = async () => {
    try {
      await API.seed();
      await loadDashboard(null);
    } catch (e) {
      alert("Seed failed. Is USE_MOCK=true set in backend?");
    }
  };

  const fileInputRef = useRef();

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", background: "#020817", color: "#e2e8f0", fontFamily: "IBM Plex Mono, monospace", overflow: "hidden", position: "relative" }}>

      {/* BG gradient */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", backgroundImage: "radial-gradient(ellipse 80% 50% at 15% 5%, rgba(99,102,241,0.05) 0%, transparent 60%), radial-gradient(ellipse 60% 40% at 85% 85%, rgba(56,189,248,0.03) 0%, transparent 60%)" }} />

      {/* ── SIDEBAR ────────────────────────────────────────────────────────── */}
      <aside style={{ width: 260, flexShrink: 0, display: "flex", flexDirection: "column", borderRight: "1px solid #0f172a", background: "rgba(2,8,23,0.95)", zIndex: 10, overflow: "hidden" }}>
        {/* Logo */}
        <div style={{ padding: "18px 16px 12px", borderBottom: "1px solid #0f172a" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
            <span style={{ fontSize: 18, color: "#6366f1" }}>◈</span>
            <span style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 18, color: "#e2e8f0" }}>CallIQ</span>
          </div>
          <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2 }}>SARVAM AI · QA PLATFORM</div>
        </div>

        {/* Upload zone */}
        <div style={{ padding: "12px 12px 8px" }}>
          <input ref={fileInputRef} type="file" multiple accept=".wav,.mp3,.m4a" style={{ display: "none" }} onChange={e => handleUpload(Array.from(e.target.files))} />
          <button onClick={() => fileInputRef.current.click()} style={{
            width: "100%", padding: "10px", borderRadius: 10,
            background: uploading ? "rgba(99,102,241,0.15)" : "rgba(15,23,42,0.6)",
            border: "1px dashed #1e3a5f", cursor: "pointer", fontSize: 11,
            fontFamily: "IBM Plex Mono", color: uploading ? "#a5b4fc" : "#334155",
            transition: "all 0.2s",
          }}>
            {uploading ? "⟳ Processing…" : "↑ Upload Audio Files"}
          </button>
          <button onClick={seedData} style={{
            width: "100%", marginTop: 4, padding: "6px", borderRadius: 8,
            background: "transparent", border: "1px solid #0f172a", cursor: "pointer",
            fontSize: 9, fontFamily: "IBM Plex Mono", color: "#1e3a5f",
            letterSpacing: 1,
          }}>LOAD DEMO DATA</button>
        </div>

        {/* Call list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "4px 12px 12px" }}>
          <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8, paddingLeft: 2 }}>
            {callList.length} CALLS
          </div>
          {loading && <div style={{ color: "#334155", fontSize: 11, textAlign: "center", padding: 20 }}>Loading…</div>}
          {!loading && callList.length === 0 && (
            <div style={{ color: "#334155", fontSize: 11, textAlign: "center", padding: 20 }}>
              {activeGrade ? `No ${activeGrade} calls found.` : "No calls yet. Upload audio or load demo data."}
            </div>
          )}
          {callList.map(call => (
            <CallListItem key={call.call_id} call={call} active={selectedCall?.call_id === call.call_id} onClick={() => selectCall(call)} />
          ))}
        </div>
      </aside>

      {/* ── MAIN COLUMN ──────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* ── STAT TABS ──────────────────────────────────────────────────────── */}
        <div style={{ display: "flex", gap: 8, padding: "14px 20px", borderBottom: "1px solid #0f172a", flexShrink: 0, background: "rgba(2,8,23,0.8)" }}>
          <StatCard label="Total Calls" count={metrics?.total_calls} active={activeGrade === null} color={null} onClick={() => setActiveGrade(null)} />
          <StatCard label="Attended"    count={metrics?.attended_calls} active={false} color={null} onClick={() => setActiveGrade(null)} />
          <StatCard label="Not Attended" count={metrics?.not_attended} active={false} color={null} onClick={() => setActiveGrade(null)} />
          <StatCard label="Excellent" count={metrics?.excellent} active={activeGrade === "excellent"} color="excellent" onClick={() => setActiveGrade(activeGrade === "excellent" ? null : "excellent")} />
          <StatCard label="Good"      count={metrics?.good}      active={activeGrade === "good"}      color="good"      onClick={() => setActiveGrade(activeGrade === "good" ? null : "good")} />
          <StatCard label="Average"   count={metrics?.average}   active={activeGrade === "average"}   color="average"   onClick={() => setActiveGrade(activeGrade === "average" ? null : "average")} />
          <StatCard label="Poor"      count={metrics?.poor}      active={activeGrade === "poor"}      color="poor"      onClick={() => setActiveGrade(activeGrade === "poor" ? null : "poor")} />
        </div>

        {/* ── CONTENT AREA ─────────────────────────────────────────────────── */}
        {error && (
          <div style={{ margin: 20, padding: 16, borderRadius: 12, background: "rgba(244,63,94,0.08)", border: "1px solid rgba(244,63,94,0.25)", fontSize: 12, fontFamily: "IBM Plex Mono", color: "#fca5a5" }}>
            ⚠ {error}
          </div>
        )}

        {!selectedCall ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 12 }}>
            <span style={{ fontSize: 32 }}>◈</span>
            <span style={{ fontSize: 13, color: "#334155", fontFamily: "IBM Plex Mono" }}>
              {activeGrade ? `Showing ${activeGrade} calls — select one to inspect` : "Select a call from the sidebar"}
            </span>
          </div>
        ) : (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

            {/* Call header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px 0", flexShrink: 0 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 3 }}>
                  <span style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 16, color: "#e2e8f0" }}>
                    {selectedCall.phone_number || selectedCall.call_id}
                  </span>
                  {selectedCall.grade && (
                    <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono", padding: "2px 8px", borderRadius: 6, background: gc(selectedCall.grade).bg, color: gc(selectedCall.grade).color, border: `1px solid ${gc(selectedCall.grade).border}` }}>
                      {gc(selectedCall.grade).label}
                    </span>
                  )}
                  {selectedCall.has_fatal && <span style={{ fontSize: 10, color: "#f43f5e", fontFamily: "IBM Plex Mono", padding: "2px 8px", borderRadius: 6, background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.3)" }}>FATAL FLAG</span>}
                </div>
                <div style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono" }}>
                  {selectedCall.agent_id} · {selectedCall.duration_formatted} · {selectedCall.created_at?.slice(0, 16).replace("T", " ")}
                </div>
              </div>
              {selectedCall.total_score != null && <ScoreRing score={selectedCall.total_score} size={60} />}
            </div>

            {/* Tabs */}
            <div style={{ display: "flex", padding: "10px 20px 0", borderBottom: "1px solid #0f172a", flexShrink: 0 }}>
              {[["transcript","Transcript"], ["analysis","QA Analysis"]].map(([t, label]) => (
                <button key={t} onClick={() => setActiveTab(t)} style={{
                  padding: "8px 20px", fontFamily: "IBM Plex Mono", fontSize: 11, letterSpacing: 1,
                  background: "none", border: "none", cursor: "pointer",
                  color: activeTab === t ? "#a5b4fc" : "#334155",
                  borderBottom: `2px solid ${activeTab === t ? "#6366f1" : "transparent"}`,
                  transition: "all 0.15s",
                }}>{label}</button>
              ))}
            </div>

            {/* Main panels */}
            <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
              {/* Left: transcript or analysis */}
              <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
                {!callDetail
                  ? <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 40 }}>Loading…</div>
                  : activeTab === "transcript"
                    ? <TranscriptView transcript={callDetail.transcript} speakerStats={callDetail.speaker_stats} />
                    : <AnalysisPanel scorecard={callDetail.scorecard} />
                }
              </div>

              {/* Right: score + fatal flags panel */}
              <div style={{ width: 260, flexShrink: 0, borderLeft: "1px solid #0f172a", overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>

                {/* Score summary */}
                {callDetail?.scorecard && (
                  <div style={{ padding: 16, borderRadius: 12, background: "rgba(15,23,42,0.6)", border: "1px solid #0f172a", textAlign: "center" }}>
                    <ScoreRing score={callDetail.scorecard.total_score} size={80} />
                    <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 20, color: gc(callDetail.scorecard.grade).color, marginTop: 8 }}>
                      Grade {callDetail.scorecard.letter_grade}
                    </div>
                    <div style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", marginTop: 4 }}>
                      {callDetail.scorecard.summary_note}
                    </div>
                  </div>
                )}

                {/* Speaker stats */}
                {callDetail?.speaker_stats?.length > 0 && (
                  <div>
                    <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>Speaker Stats</div>
                    {callDetail.speaker_stats.map(s => (
                      <div key={s.speaker_id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #0f172a" }}>
                        <div>
                          <div style={{ fontSize: 10, fontFamily: "IBM Plex Mono", color: s.label === "Agent" ? "#a5b4fc" : "#94a3b8" }}>{s.label}</div>
                          <div style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>{s.speaker_id}</div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: 10, fontFamily: "IBM Plex Mono", color: "#cbd5e1" }}>{s.talk_time_formatted}</div>
                          <div style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>{s.word_count} words</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Fatal flags */}
                {callDetail?.scorecard?.fatal_flags && (
                  <div>
                    <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>Fatal Flags</div>
                    <FatalFlagsPanel fatalFlags={callDetail.scorecard.fatal_flags} />
                  </div>
                )}

                {/* Section breakdown mini */}
                {callDetail?.scorecard?.sections && (
                  <div>
                    <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>Section Scores</div>
                    {callDetail.scorecard.sections.map(s => {
                      const color = s.section_percentage >= 80 ? "#22c55e" : s.section_percentage >= 60 ? "#f59e0b" : "#f43f5e";
                      return (
                        <div key={s.section_name} style={{ marginBottom: 8 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                            <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: "#475569" }}>{s.section_name.replace("_"," ")}</span>
                            <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color }}>{s.section_score}/{s.section_max}</span>
                          </div>
                          <div style={{ height: 3, background: "#0f172a", borderRadius: 2, overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${s.section_percentage}%`, background: color, borderRadius: 2 }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── AUDIO PLAYER (bottom fixed) ──────────────────────────────────── */}
        <div style={{ height: 56, flexShrink: 0, borderTop: "1px solid #0f172a", background: "rgba(2,8,23,0.95)", backdropFilter: "blur(8px)" }}>
          {selectedCall
            ? <AudioPlayer audioUrl={API.audioUrl(selectedCall.call_id)} callId={selectedCall.call_id} />
            : <div style={{ height: "100%", display: "flex", alignItems: "center", paddingLeft: 20, fontSize: 10, color: "#1e3a5f", fontFamily: "IBM Plex Mono" }}>Select a call to play audio</div>}
        </div>
      </div>

      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #0f172a; border-radius: 2px; }
        button { outline: none; }
      `}</style>
    </div>
  );
}
