// import { useState, useEffect, useRef, useCallback } from "react";

// // ─── Font ─────────────────────────────────────────────────────────────────────
// const _fl = document.createElement("link");
// _fl.rel = "stylesheet";
// _fl.href = "https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@300;400;500;600&display=swap";
// document.head.appendChild(_fl);

// // ─── API Layer ────────────────────────────────────────────────────────────────
// const BASE = "http://localhost:8000/api";

// const apiFetch = async (path, opts) => {
//   const res = await fetch(`${BASE}${path}`, opts);
//   if (!res.ok) {
//     const text = await res.text().catch(() => res.statusText);
//     throw new Error(`${res.status}: ${text}`);
//   }
//   return res.json();
// };

// const API = {
//   dashboard:   (grade)  => apiFetch(`/dashboard${grade ? `?grade=${grade}` : ""}`),
//   call:        (id)     => apiFetch(`/call/${id}`),
//   upload:      (files)  => { const fd = new FormData(); files.forEach(f => fd.append("files", f)); return apiFetch("/upload", { method: "POST", body: fd }); },
//   jobStatus:   (id)     => apiFetch(`/jobs/${id}`),
//   leaderboard: ()       => apiFetch("/leaderboard"),
//   seed:        ()       => apiFetch("/seed", { method: "POST" }),
//   reset:       ()       => apiFetch("/debug/reset", { method: "DELETE" }),
//   debugStore:  ()       => apiFetch("/debug/store"),
//   debugEnv:    ()       => apiFetch("/debug/env"),
//   audioUrl:    (id)     => `${BASE}/audio/${id}`,
// };

// // Log backend mode to browser console on load
// fetch(`${BASE}/debug/env`)
//   .then(r => r.json())
//   .then(env => {
//     console.log("%c[CallIQ Backend Mode]", "color:#6366f1;font-weight:bold;font-size:14px");
//     console.log("USE_MOCK:", env.USE_MOCK);
//     console.log("Mode:", env.mode);
//     console.log("Sarvam Key Set:", env.sarvam_key_set);
//     console.log("Uploaded files:", env.uploaded_files);
//     if (env.mode && env.mode.includes("MOCK")) {
//       console.warn("%c⚠️  MOCK MODE ACTIVE — Your uploaded audio will NOT be transcribed!", "color:orange;font-size:13px");
//       console.warn("To use real Sarvam AI: set USE_MOCK=false and sarvam_api_key in backend/.env");
//     }
//   })
//   .catch(() => console.error("[CallIQ] Backend not reachable at", BASE));

// // ─── Grade config ─────────────────────────────────────────────────────────────
// const GRADE_CONFIG = {
//   excellent: { color: "#22c55e", bg: "rgba(34,197,94,0.10)",  border: "rgba(34,197,94,0.30)",  label: "Excellent", letter: "A" },
//   good:      { color: "#38bdf8", bg: "rgba(56,189,248,0.10)", border: "rgba(56,189,248,0.30)", label: "Good",      letter: "B" },
//   average:   { color: "#f59e0b", bg: "rgba(245,158,11,0.10)", border: "rgba(245,158,11,0.30)", label: "Average",   letter: "C" },
//   poor:      { color: "#f43f5e", bg: "rgba(244,63,94,0.10)",  border: "rgba(244,63,94,0.30)",  label: "Poor",      letter: "D" },
// };
// const gc = (g) => GRADE_CONFIG[g] || { color: "#94a3b8", bg: "rgba(148,163,184,0.06)", border: "#1e293b", label: g || "—", letter: "—" };

// // ─── Helpers ──────────────────────────────────────────────────────────────────
// const fmtDate = (iso) => iso ? iso.slice(0, 16).replace("T", " ") : "—";

// // ─── Score Ring ───────────────────────────────────────────────────────────────
// function ScoreRing({ score, size = 72 }) {
//   if (score == null) return (
//     <div style={{ width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 11 }}>—</div>
//   );
//   const g = score >= 90 ? "excellent" : score >= 75 ? "good" : score >= 60 ? "average" : "poor";
//   const color = gc(g).color;
//   const r = size / 2 - 6;
//   const circ = 2 * Math.PI * r;
//   const dash = (score / 100) * circ;
//   return (
//     <svg width={size} height={size} style={{ transform: "rotate(-90deg)", flexShrink: 0 }}>
//       <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1e293b" strokeWidth={5} />
//       <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={5}
//         strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
//         style={{ transition: "stroke-dasharray 0.8s ease" }} />
//       <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
//         fill={color} fontSize={size * 0.22} fontFamily="IBM Plex Mono" fontWeight="600"
//         style={{ transform: "rotate(90deg)", transformOrigin: "center" }}>{score}</text>
//     </svg>
//   );
// }

// // ─── Stat Card ────────────────────────────────────────────────────────────────
// function StatCard({ label, count, active, colorKey, onClick }) {
//   const cfg = GRADE_CONFIG[colorKey] || { color: "#94a3b8", bg: "rgba(148,163,184,0.06)", border: "#1e293b" };
//   return (
//     <button onClick={onClick} style={{
//       flex: 1, minWidth: 0, display: "flex", flexDirection: "column", alignItems: "center",
//       gap: 4, padding: "14px 8px", borderRadius: 12, cursor: "pointer",
//       background: active ? cfg.bg : "rgba(15,23,42,0.5)",
//       border: `1px solid ${active ? cfg.border : "#0f172a"}`,
//       transition: "all 0.18s",
//       boxShadow: active ? `0 0 20px ${cfg.color}22` : "none",
//     }}>
//       <span style={{ fontSize: 26, fontFamily: "Syne", fontWeight: 800, color: active ? cfg.color : "#e2e8f0" }}>
//         {count ?? 0}
//       </span>
//       <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", color: active ? cfg.color : "#334155" }}>
//         {label}
//       </span>
//     </button>
//   );
// }

// // ─── Status Badge ─────────────────────────────────────────────────────────────
// function StatusBadge({ status }) {
//   const map = {
//     completed:  { color: "#22c55e", label: "Done" },
//     processing: { color: "#f59e0b", label: "Processing…" },
//     pending:    { color: "#6366f1", label: "Pending" },
//     failed:     { color: "#f43f5e", label: "Failed" },
//   };
//   const s = map[status] || { color: "#94a3b8", label: status };
//   return (
//     <span style={{
//       fontSize: 9, fontFamily: "IBM Plex Mono", padding: "2px 7px", borderRadius: 5,
//       color: s.color, background: `${s.color}18`, border: `1px solid ${s.color}44`,
//       letterSpacing: 0.5,
//     }}>{s.label}</span>
//   );
// }

// // ─── Call List Item ───────────────────────────────────────────────────────────
// function CallItem({ call, active, onClick }) {
//   const cfg = gc(call.grade);
//   const isProcessing = call.status === "processing" || call.status === "pending";
//   return (
//     <button onClick={onClick} style={{
//       width: "100%", textAlign: "left", padding: "12px 14px", borderRadius: 10,
//       background: active ? cfg.bg : "rgba(15,23,42,0.4)",
//       border: `1px solid ${active ? cfg.border : "#0f172a"}`,
//       cursor: "pointer", transition: "all 0.15s", marginBottom: 4,
//     }}>
//       <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
//         <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 600, color: active ? "#e2e8f0" : "#94a3b8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>
//           {call.phone_number || call.call_id}
//         </span>
//         {call.total_score != null
//           ? <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 700, color: cfg.color, flexShrink: 0 }}>{call.total_score}%</span>
//           : <StatusBadge status={call.status} />}
//       </div>
//       <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
//         <span style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "60%" }}>
//           {call.agent_id === "UNKNOWN" ? "—" : call.agent_id}
//         </span>
//         <div style={{ display: "flex", gap: 5, alignItems: "center", flexShrink: 0 }}>
//           {call.has_fatal && <span style={{ fontSize: 8, color: "#f43f5e", fontFamily: "IBM Plex Mono", letterSpacing: 0.5 }}>⚠ FATAL</span>}
//           {call.grade && (
//             <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", padding: "1px 6px", borderRadius: 4, background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}>
//               {cfg.label}
//             </span>
//           )}
//         </div>
//       </div>
//       <div style={{ fontSize: 9, color: "#1e3a5f", fontFamily: "IBM Plex Mono", marginTop: 3 }}>
//         {call.duration_formatted !== "—" ? `${call.duration_formatted} · ` : ""}{call.created_at?.slice(0, 10)}
//       </div>
//       {/* Processing progress bar */}
//       {isProcessing && (
//         <div style={{ marginTop: 6, height: 2, background: "#0f172a", borderRadius: 1, overflow: "hidden" }}>
//           <div style={{ height: "100%", background: "#6366f1", borderRadius: 1, animation: "slide 1.5s infinite" }} />
//         </div>
//       )}
//     </button>
//   );
// }

// // ─── Transcript Panel ─────────────────────────────────────────────────────────
// function TranscriptPanel({ transcript }) {
//   if (!transcript?.length) return (
//     <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 48 }}>
//       Transcript not available
//     </div>
//   );

//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
//       {transcript.map((entry, i) => {
//         const isAgent = entry.speaker_label === "Agent";
//         const flagged = entry.is_flagged;
//         return (
//           <div key={i} style={{ display: "flex", gap: 10, flexDirection: isAgent ? "row" : "row-reverse" }}>
//             {/* Avatar */}
//             <div style={{
//               width: 28, height: 28, borderRadius: "50%", flexShrink: 0, marginTop: 2,
//               background: isAgent ? (flagged ? "rgba(244,63,94,0.15)" : "rgba(99,102,241,0.15)") : "rgba(30,41,59,0.8)",
//               border: `2px solid ${isAgent ? (flagged ? "#f43f5e" : "#6366f1") : "#334155"}`,
//               display: "flex", alignItems: "center", justifyContent: "center",
//               fontSize: 9, fontFamily: "IBM Plex Mono", fontWeight: 600,
//               color: isAgent ? (flagged ? "#f43f5e" : "#a5b4fc") : "#94a3b8",
//             }}>{isAgent ? "AG" : "CX"}</div>

//             <div style={{ maxWidth: "76%", display: "flex", flexDirection: "column", gap: 3, alignItems: isAgent ? "flex-start" : "flex-end" }}>
//               <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
//                 <span style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>
//                   {entry.start_time?.toFixed(1)}s
//                 </span>
//                 <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: isAgent ? "#6366f1" : "#475569" }}>
//                   {entry.speaker_label}
//                 </span>
//                 {flagged && (
//                   <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: "#f43f5e", padding: "0 5px", borderRadius: 3, background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.25)" }}>
//                     ⚠ Review
//                   </span>
//                 )}
//               </div>
//               {/* Message bubble — red bordered if flagged */}
//               <div style={{
//                 padding: "10px 14px", borderRadius: 12, fontSize: 12, lineHeight: 1.65,
//                 fontFamily: "IBM Plex Mono", color: flagged ? "#fca5a5" : "#cbd5e1",
//                 background: flagged
//                   ? "rgba(244,63,94,0.08)"
//                   : isAgent ? "rgba(99,102,241,0.09)" : "rgba(30,41,59,0.7)",
//                 border: `1px solid ${flagged ? "rgba(244,63,94,0.3)" : isAgent ? "rgba(99,102,241,0.2)" : "#0f172a"}`,
//                 borderLeft: flagged ? "3px solid #f43f5e" : undefined,
//               }}>
//                 {entry.text}
//               </div>
//               {flagged && entry.flag_reason && (
//                 <span style={{ fontSize: 10, color: "#f43f5e88", fontFamily: "IBM Plex Mono", marginLeft: 4 }}>
//                   ↳ {entry.flag_reason}
//                 </span>
//               )}
//             </div>
//           </div>
//         );
//       })}
//     </div>
//   );
// }

// // ─── Analysis Panel ───────────────────────────────────────────────────────────
// function AnalysisPanel({ scorecard }) {
//   const [openSection, setOpenSection] = useState("OPENING");

//   if (!scorecard) return (
//     <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 48 }}>
//       Analysis not available — call may still be processing.
//     </div>
//   );

//   const sectionColors = { OPENING: "#818cf8", SALES: "#38bdf8", SOFT_SKILLS: "#a78bfa", CLOSING: "#34d399" };

//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
//       {/* Improvement areas */}
//       {scorecard.improvement_areas?.length > 0 && (
//         <div style={{ padding: 14, borderRadius: 12, background: "rgba(244,63,94,0.06)", border: "1px solid rgba(244,63,94,0.18)" }}>
//           <div style={{ fontSize: 9, color: "#f43f5e", fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>⚠ Areas to Improve</div>
//           {scorecard.improvement_areas.map((a, i) => (
//             <div key={i} style={{ fontSize: 11, color: "#fca5a5", fontFamily: "IBM Plex Mono", marginBottom: 5, lineHeight: 1.5 }}>• {a}</div>
//           ))}
//         </div>
//       )}

//       {/* Strengths */}
//       {scorecard.strengths?.length > 0 && (
//         <div style={{ padding: 14, borderRadius: 12, background: "rgba(34,197,94,0.05)", border: "1px solid rgba(34,197,94,0.18)" }}>
//           <div style={{ fontSize: 9, color: "#22c55e", fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>✓ Strengths</div>
//           {scorecard.strengths.map((s, i) => (
//             <div key={i} style={{ fontSize: 11, color: "#86efac", fontFamily: "IBM Plex Mono", marginBottom: 5 }}>✓ {s}</div>
//           ))}
//         </div>
//       )}

//       {/* Section accordions */}
//       {scorecard.sections?.map(sec => {
//         const isOpen = openSection === sec.section_name;
//         const color = sectionColors[sec.section_name] || "#94a3b8";
//         return (
//           <div key={sec.section_name} style={{ borderRadius: 12, border: `1px solid ${isOpen ? color + "44" : "#0f172a"}`, overflow: "hidden" }}>
//             <button onClick={() => setOpenSection(isOpen ? null : sec.section_name)} style={{
//               width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
//               padding: "12px 16px", background: isOpen ? `${color}10` : "rgba(15,23,42,0.5)",
//               border: "none", cursor: "pointer",
//             }}>
//               <span style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 13, color: isOpen ? color : "#94a3b8" }}>
//                 {sec.section_name.replace("_", " ")}
//               </span>
//               <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
//                 <div style={{ width: 56, height: 3, background: "#1e293b", borderRadius: 2, overflow: "hidden" }}>
//                   <div style={{ height: "100%", width: `${sec.section_percentage}%`, background: color }} />
//                 </div>
//                 <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", color, fontWeight: 600 }}>
//                   {sec.section_score}/{sec.section_max}
//                 </span>
//                 <span style={{ color: "#475569", fontSize: 10 }}>{isOpen ? "▲" : "▼"}</span>
//               </div>
//             </button>

//             {isOpen && (
//               <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
//                 {sec.parameters?.map((p, i) => {
//                   const pct = p.percentage ?? 0;
//                   const pColor = pct >= 90 ? "#22c55e" : pct >= 70 ? "#38bdf8" : pct >= 50 ? "#f59e0b" : "#f43f5e";
//                   return (
//                     <div key={i}>
//                       <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
//                         <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
//                           <span style={{ fontSize: 11, color: "#cbd5e1", fontFamily: "IBM Plex Mono" }}>{p.parameter}</span>
//                           {p.is_critical_miss && (
//                             <span style={{ fontSize: 8, color: "#f43f5e", padding: "0 4px", borderRadius: 3, background: "rgba(244,63,94,0.12)", border: "1px solid rgba(244,63,94,0.3)", letterSpacing: 0.5 }}>MISSED</span>
//                           )}
//                         </div>
//                         <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 600, color: pColor, flexShrink: 0 }}>
//                           {p.score}/{p.max_score}
//                         </span>
//                       </div>
//                       <div style={{ height: 3, background: "#1e293b", borderRadius: 2, marginBottom: 4, overflow: "hidden" }}>
//                         <div style={{ height: "100%", width: `${pct}%`, background: pColor, borderRadius: 2, boxShadow: `0 0 6px ${pColor}66`, transition: "width 0.6s ease" }} />
//                       </div>
//                       <p style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", margin: 0, lineHeight: 1.5 }}>{p.reason}</p>
//                     </div>
//                   );
//                 })}
//               </div>
//             )}
//           </div>
//         );
//       })}
//     </div>
//   );
// }

// // ─── Fatal Flags ──────────────────────────────────────────────────────────────
// function FatalFlagsPanel({ fatalFlags }) {
//   if (!fatalFlags) return null;
//   const entries = [
//     ["Right Party Confirmation", fatalFlags.right_party_confirmation],
//     ["Rude Behaviour",           fatalFlags.rude_behaviour],
//     ["Miss Sell",                fatalFlags.miss_sell],
//     ["Disposition",              fatalFlags.disposition],
//   ];
//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
//       {entries.map(([label, val]) => {
//         const fatal = val === "F";
//         return (
//           <div key={label} style={{
//             display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8,
//             background: fatal ? "rgba(244,63,94,0.09)" : "rgba(34,197,94,0.05)",
//             border: `1px solid ${fatal ? "rgba(244,63,94,0.28)" : "rgba(34,197,94,0.18)"}`,
//           }}>
//             <span style={{ width: 6, height: 6, borderRadius: "50%", flexShrink: 0, background: fatal ? "#f43f5e" : "#22c55e", boxShadow: `0 0 8px ${fatal ? "#f43f5e" : "#22c55e"}99` }} />
//             <span style={{ flex: 1, fontSize: 10, fontFamily: "IBM Plex Mono", color: "#94a3b8" }}>{label}</span>
//             <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono", fontWeight: 700, color: fatal ? "#f43f5e" : "#22c55e", letterSpacing: 1 }}>{val || "NF"}</span>
//           </div>
//         );
//       })}
//     </div>
//   );
// }

// // ─── Audio Player — FIX 1 applied ────────────────────────────────────────────
// // OLD BUG: isMock = audioUrl.includes("localhost") → always true → audio never played
// // FIX: isMock only if audioUrl is null/empty. Backend URL with localhost is still real.
// function AudioPlayer({ audioUrl, callId }) {
//   const audioRef = useRef(null);
//   const [playing, setPlaying] = useState(false);
//   const [progress, setProgress] = useState(0);
//   const [duration, setDuration] = useState(0);
//   const [volume, setVolume] = useState(0.8);
//   const [loadError, setLoadError] = useState(false);

//   // FIX: only treat as mock/unavailable if there's no URL at all
//   const hasAudio = !!audioUrl;

//   const fmtT = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

//   // Reset on call change
//   useEffect(() => {
//     setPlaying(false); setProgress(0); setDuration(0); setLoadError(false);
//   }, [callId]);

//   useEffect(() => {
//     if (audioRef.current) audioRef.current.volume = volume;
//   }, [volume]);

//   const togglePlay = () => {
//     if (!audioRef.current || !hasAudio || loadError) return;
//     if (playing) {
//       audioRef.current.pause();
//     } else {
//       audioRef.current.play().catch(() => setLoadError(true));
//     }
//     setPlaying(p => !p);
//   };

//   const seek = (e) => {
//     if (!audioRef.current || !hasAudio || !duration) return;
//     const rect = e.currentTarget.getBoundingClientRect();
//     audioRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * duration;
//   };

//   return (
//     <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "0 8px", height: "100%" }}>
//       <audio
//         ref={audioRef}
//         src={hasAudio ? audioUrl : undefined}
//         onTimeUpdate={() => audioRef.current && setProgress(audioRef.current.currentTime)}
//         onLoadedMetadata={() => audioRef.current && setDuration(audioRef.current.duration)}
//         onEnded={() => setPlaying(false)}
//         onError={() => setLoadError(true)}
//       />

//       {/* Play/Pause button */}
//       <button onClick={togglePlay} style={{
//         width: 38, height: 38, borderRadius: "50%",
//         background: hasAudio && !loadError ? "#6366f1" : "#1e293b",
//         border: `1px solid ${hasAudio && !loadError ? "#6366f1" : "#334155"}`,
//         cursor: hasAudio && !loadError ? "pointer" : "default",
//         display: "flex", alignItems: "center", justifyContent: "center",
//         boxShadow: hasAudio && !loadError ? "0 0 20px #6366f144" : "none", flexShrink: 0,
//       }}>
//         {playing
//           ? <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
//           : <svg width="14" height="14" viewBox="0 0 24 24" fill={hasAudio && !loadError ? "white" : "#334155"}><path d="M8 5v14l11-7z"/></svg>
//         }
//       </button>

//       {/* Time + Seek bar */}
//       <span style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", width: 34, flexShrink: 0 }}>
//         {fmtT(progress)}
//       </span>
//       <div
//         onClick={seek}
//         style={{ flex: 1, height: 4, background: "#1e293b", borderRadius: 4, position: "relative", cursor: hasAudio ? "pointer" : "default" }}
//       >
//         <div style={{
//           position: "absolute", left: 0, top: 0, height: "100%",
//           background: "#6366f1", borderRadius: 4,
//           width: duration ? `${(progress / duration) * 100}%` : "0%",
//           transition: "width 0.25s linear",
//         }} />
//       </div>
//       <span style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono", width: 34, flexShrink: 0 }}>
//         {fmtT(duration)}
//       </span>

//       {/* Volume */}
//       <svg width="14" height="14" viewBox="0 0 24 24" fill="#475569" style={{ flexShrink: 0 }}>
//         <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
//       </svg>
//       <input type="range" min={0} max={1} step={0.05} value={volume}
//         onChange={e => setVolume(Number(e.target.value))}
//         style={{ width: 64, accentColor: "#6366f1", cursor: "pointer" }} />

//       {/* Status label */}
//       {loadError && (
//         <span style={{ fontSize: 9, color: "#f43f5e", fontFamily: "IBM Plex Mono", maxWidth: 180 }}>
//           No audio — demo call has no real audio file. Upload your own WAV.
//         </span>
//       )}
//       {!hasAudio && !loadError && <span style={{ fontSize: 9, color: "#1e3a5f", fontFamily: "IBM Plex Mono" }}>Select call</span>}
//     </div>
//   );
// }

// // ─── Right Score Panel ────────────────────────────────────────────────────────
// function RightPanel({ callDetail }) {
//   if (!callDetail) return (
//     <div style={{ padding: 16, color: "#1e3a5f", fontFamily: "IBM Plex Mono", fontSize: 11, textAlign: "center" }}>
//       Select a call
//     </div>
//   );

//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
//       {/* Score card */}
//       {callDetail.scorecard && (
//         <div style={{ padding: 16, borderRadius: 12, background: "rgba(15,23,42,0.6)", border: "1px solid #0f172a", textAlign: "center" }}>
//           <ScoreRing score={callDetail.scorecard.total_score} size={80} />
//           <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 20, color: gc(callDetail.scorecard.grade).color, marginTop: 8 }}>
//             Grade {callDetail.scorecard.letter_grade}
//           </div>
//           <div style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", marginTop: 6, lineHeight: 1.5 }}>
//             {callDetail.scorecard.summary_note}
//           </div>
//         </div>
//       )}

//       {/* Speaker stats */}
//       {callDetail.speaker_stats?.length > 0 && (
//         <div>
//           <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8, fontFamily: "IBM Plex Mono" }}>
//             Speaker Stats
//           </div>
//           {callDetail.speaker_stats.map(s => (
//             <div key={s.speaker_id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #0f172a" }}>
//               <div>
//                 <div style={{ fontSize: 10, fontFamily: "IBM Plex Mono", color: s.label === "Agent" ? "#a5b4fc" : "#94a3b8" }}>{s.label}</div>
//                 <div style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>{s.speaker_id}</div>
//               </div>
//               <div style={{ textAlign: "right" }}>
//                 <div style={{ fontSize: 10, fontFamily: "IBM Plex Mono", color: "#cbd5e1" }}>{s.talk_time_formatted}</div>
//                 <div style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>{s.word_count} words</div>
//               </div>
//             </div>
//           ))}
//         </div>
//       )}

//       {/* Fatal flags */}
//       {callDetail.scorecard?.fatal_flags && (
//         <div>
//           <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8, fontFamily: "IBM Plex Mono" }}>
//             Fatal Flags
//           </div>
//           <FatalFlagsPanel fatalFlags={callDetail.scorecard.fatal_flags} />
//         </div>
//       )}

//       {/* Section scores mini */}
//       {callDetail.scorecard?.sections && (
//         <div>
//           <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8, fontFamily: "IBM Plex Mono" }}>
//             Section Scores
//           </div>
//           {callDetail.scorecard.sections.map(s => {
//             const pct = s.section_percentage ?? 0;
//             const color = pct >= 80 ? "#22c55e" : pct >= 60 ? "#f59e0b" : "#f43f5e";
//             return (
//               <div key={s.section_name} style={{ marginBottom: 9 }}>
//                 <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
//                   <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: "#475569" }}>
//                     {s.section_name.replace("_", " ")}
//                   </span>
//                   <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color }}>{s.section_score}/{s.section_max}</span>
//                 </div>
//                 <div style={{ height: 3, background: "#0f172a", borderRadius: 2, overflow: "hidden" }}>
//                   <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 2, transition: "width 0.6s ease" }} />
//                 </div>
//               </div>
//             );
//           })}
//         </div>
//       )}
//     </div>
//   );
// }

// // ─── Main App ─────────────────────────────────────────────────────────────────
// export default function App() {
//   const [metrics, setMetrics]           = useState(null);
//   const [callList, setCallList]         = useState([]);
//   const [activeGrade, setActiveGrade]   = useState(null);
//   const [selectedCall, setSelectedCall] = useState(null);
//   const [callDetail, setCallDetail]     = useState(null);
//   const [activeTab, setActiveTab]       = useState("transcript");
//   const [uploading, setUploading]       = useState(false);
//   const [loading, setLoading]           = useState(true);
//   const [backendError, setBackendError] = useState(null);
//   const [backendMode, setBackendMode]   = useState(null); // "MOCK" | "LIVE" | null

//   // pollingRef: call_id → intervalId
//   // FIX 3: use a ref so intervals don't create stale closures over callList
//   const pollingRef    = useRef({});
//   const selectedIdRef = useRef(null);   // tracks selected call_id for auto-refresh
//   const fileInputRef  = useRef();

//   // ── Load dashboard ──────────────────────────────────────────────────────────
//   const loadDashboard = useCallback(async (grade) => {
//     try {
//       const data = await API.dashboard(grade);
//       setMetrics(data.metrics);
//       setCallList(data.calls);
//       setBackendError(null);
//     } catch (e) {
//       setBackendError(e.message);
//     } finally {
//       setLoading(false);
//     }
//   }, []);

//   useEffect(() => { loadDashboard(activeGrade); }, [activeGrade, loadDashboard]);

//   // Fetch backend env on mount so mode banner shows immediately
//   useEffect(() => {
//     API.debugEnv().then(env => {
//       setBackendMode(env.mode && env.mode.includes("MOCK") ? "MOCK" : "LIVE");
//     }).catch(() => {});
//   }, []);

//   // ── Polling for processing calls ────────────────────────────────────────────
//   // FIX 2 + 3: When a call completes, reload dashboard AND auto-update callDetail
//   // if the completed call is the one currently selected.
//   const startPolling = useCallback((callId) => {
//     if (pollingRef.current[callId]) return; // already polling

//     pollingRef.current[callId] = setInterval(async () => {
//       try {
//         const updated = await API.call(callId);

//         if (updated.status === "completed" || updated.status === "failed") {
//           clearInterval(pollingRef.current[callId]);
//           delete pollingRef.current[callId];

//           // Refresh the sidebar list
//           setCallList(prev => prev.map(c =>
//             c.call_id === callId
//               ? { ...c, status: updated.status, total_score: updated.total_score, grade: updated.grade, has_fatal: false }
//               : c
//           ));

//           // FIX 2: If this call is currently selected, auto-load its detail
//           if (selectedIdRef.current === callId) {
//             setCallDetail(updated);
//             setSelectedCall(prev => prev ? { ...prev, status: updated.status, total_score: updated.total_score, grade: updated.grade } : prev);
//           }

//           // Full dashboard refresh for accurate metrics counts
//           setActiveGrade(g => { loadDashboard(g); return g; });
//         }
//       } catch (_) {}
//     }, 3000);
//   }, [loadDashboard]);

//   // Start polling for any pending/processing calls in the list
//   useEffect(() => {
//     callList.forEach(c => {
//       if (c.status === "processing" || c.status === "pending") {
//         startPolling(c.call_id);
//       }
//     });
//   }, [callList, startPolling]);

//   // Cleanup all intervals on unmount
//   useEffect(() => {
//     return () => Object.values(pollingRef.current).forEach(clearInterval);
//   }, []);

//   // ── Select a call ───────────────────────────────────────────────────────────
//   const selectCall = useCallback(async (callItem) => {
//     setSelectedCall(callItem);
//     setCallDetail(null);
//     selectedIdRef.current = callItem.call_id;

//     try {
//       const detail = await API.call(callItem.call_id);
//       setCallDetail(detail);
//       // If it's processing, make sure polling is active
//       if (detail.status === "processing" || detail.status === "pending") {
//         startPolling(callItem.call_id);
//       }
//     } catch (e) {
//       console.error("Could not load call detail:", e);
//     }
//   }, [startPolling]);

//   // ── Upload ──────────────────────────────────────────────────────────────────
//   const handleUpload = async (files) => {
//     setUploading(true);
//     try {
//       const result = await API.upload(files);
//       await loadDashboard(activeGrade);
//       // Auto-select the first uploaded call after dashboard refreshes
//     } catch (e) {
//       alert(`Upload failed: ${e.message}\n\nIs the backend running? uvicorn main:app --reload`);
//     } finally {
//       setUploading(false);
//     }
//   };

//   // ── Seed demo data ──────────────────────────────────────────────────────────
//   const seedData = async () => {
//     try {
//       await API.seed();
//       await loadDashboard(null);
//       setActiveGrade(null);
//     } catch (e) {
//       alert(`Seed failed: ${e.message}`);
//     }
//   };

//   // ── Reset store ─────────────────────────────────────────────────────────────
//   const resetStore = async () => {
//     if (!confirm("Clear all records from the store?")) return;
//     try {
//       await API.reset();
//       setCallList([]); setMetrics(null); setSelectedCall(null); setCallDetail(null);
//       await loadDashboard(null);
//     } catch (e) {
//       alert(`Reset failed: ${e.message}`);
//     }
//   };

//   // ─────────────────────────────────────────────────────────────────────────────
//   return (
//     <div style={{ display: "flex", height: "100vh", width: "100vw", background: "#020817", color: "#e2e8f0", fontFamily: "IBM Plex Mono, monospace", overflow: "hidden" }}>

//       {/* BG */}
//       <div style={{ position: "fixed", inset: 0, pointerEvents: "none", backgroundImage: "radial-gradient(ellipse 80% 50% at 15% 5%, rgba(99,102,241,0.05) 0%, transparent 60%), radial-gradient(ellipse 60% 40% at 85% 85%, rgba(56,189,248,0.03) 0%, transparent 60%)" }} />

//       {/* ── SIDEBAR ──────────────────────────────────────────────────────────── */}
//       <aside style={{ width: 256, flexShrink: 0, display: "flex", flexDirection: "column", borderRight: "1px solid #0f172a", background: "rgba(2,8,23,0.97)", zIndex: 10, overflow: "hidden" }}>

//         {/* Logo */}
//         <div style={{ padding: "18px 16px 12px", borderBottom: "1px solid #0f172a" }}>
//           <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
//             <span style={{ fontSize: 18, color: "#6366f1" }}>◈</span>
//             <span style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 18, color: "#e2e8f0", letterSpacing: -0.5 }}>CallIQ</span>
//           </div>
//           <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, fontFamily: "IBM Plex Mono" }}>SARVAM AI · QA PLATFORM</div>
//         </div>

//         {/* Upload + seed + reset */}
//         <div style={{ padding: "10px 12px 6px", borderBottom: "1px solid #0f172a", display: "flex", flexDirection: "column", gap: 5 }}>
//           <input ref={fileInputRef} type="file" multiple accept=".wav,.mp3,.m4a,.ogg" style={{ display: "none" }}
//             onChange={e => e.target.files.length && handleUpload(Array.from(e.target.files))} />
//           <button onClick={() => fileInputRef.current.click()} style={{
//             padding: "9px", borderRadius: 9, border: "1px dashed #1e3a5f",
//             background: uploading ? "rgba(99,102,241,0.12)" : "rgba(15,23,42,0.5)",
//             cursor: "pointer", fontSize: 11, fontFamily: "IBM Plex Mono",
//             color: uploading ? "#a5b4fc" : "#475569",
//           }}>
//             {uploading ? "⟳ Processing…" : "↑ Upload Audio Files"}
//           </button>
//           <div style={{ display: "flex", gap: 4 }}>
//             <button onClick={seedData} style={{ flex: 1, padding: "5px", borderRadius: 7, border: "1px solid #0f172a", background: "transparent", cursor: "pointer", fontSize: 9, fontFamily: "IBM Plex Mono", color: "#334155", letterSpacing: 1 }}>
//               LOAD DEMO DATA
//             </button>
//             <button onClick={resetStore} title="Clear store" style={{ padding: "5px 8px", borderRadius: 7, border: "1px solid #0f172a", background: "transparent", cursor: "pointer", fontSize: 9, fontFamily: "IBM Plex Mono", color: "#1e3a5f" }}>
//               ✕
//             </button>
//           </div>
//         </div>

//         {/* Call count */}
//         <div style={{ padding: "8px 14px 4px", fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", fontFamily: "IBM Plex Mono" }}>
//           {callList.length} {activeGrade ? activeGrade.toUpperCase() : "TOTAL"} CALLS
//         </div>

//         {/* Call list */}
//         <div style={{ flex: 1, overflowY: "auto", padding: "4px 12px 12px" }}>
//           {loading && (
//             <div style={{ color: "#334155", fontSize: 11, textAlign: "center", padding: 24, fontFamily: "IBM Plex Mono" }}>Loading…</div>
//           )}
//           {!loading && callList.length === 0 && (
//             <div style={{ color: "#334155", fontSize: 11, textAlign: "center", padding: 24, fontFamily: "IBM Plex Mono", lineHeight: 1.6 }}>
//               {activeGrade ? `No ${activeGrade} calls.` : "No calls yet.\nUpload audio or click\nLOAD DEMO DATA."}
//             </div>
//           )}
//           {callList.map(call => (
//             <CallItem
//               key={call.call_id}
//               call={call}
//               active={selectedCall?.call_id === call.call_id}
//               onClick={() => selectCall(call)}
//             />
//           ))}
//         </div>
//       </aside>

//       {/* ── MAIN COLUMN ──────────────────────────────────────────────────────── */}
//       <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

//         {/* ── STAT TABS ──────────────────────────────────────────────────────── */}
//         <div style={{ display: "flex", gap: 8, padding: "12px 16px", borderBottom: "1px solid #0f172a", flexShrink: 0, background: "rgba(2,8,23,0.9)" }}>
//           <StatCard label="Total Calls"  count={metrics?.total_calls}     active={activeGrade === null}        colorKey={null}        onClick={() => setActiveGrade(null)} />
//           <StatCard label="Attended"     count={metrics?.attended_calls}   active={false}                       colorKey={null}        onClick={() => setActiveGrade(null)} />
//           <StatCard label="Not Attended" count={metrics?.not_attended}     active={false}                       colorKey={null}        onClick={() => setActiveGrade(null)} />
//           <StatCard label="Excellent"    count={metrics?.excellent}        active={activeGrade === "excellent"} colorKey="excellent"   onClick={() => setActiveGrade(g => g === "excellent" ? null : "excellent")} />
//           <StatCard label="Good"         count={metrics?.good}             active={activeGrade === "good"}      colorKey="good"        onClick={() => setActiveGrade(g => g === "good" ? null : "good")} />
//           <StatCard label="Average"      count={metrics?.average}          active={activeGrade === "average"}   colorKey="average"     onClick={() => setActiveGrade(g => g === "average" ? null : "average")} />
//           <StatCard label="Poor"         count={metrics?.poor}             active={activeGrade === "poor"}      colorKey="poor"        onClick={() => setActiveGrade(g => g === "poor" ? null : "poor")} />
//         </div>

//         {/* Mode banner — always visible so user knows MOCK vs LIVE */}
//         {backendMode === "MOCK" && (
//           <div style={{ margin: "8px 16px 0", padding: "10px 16px", borderRadius: 8,
//             background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)",
//             display: "flex", alignItems: "center", gap: 10 }}>
//             <span style={{ fontSize: 16 }}>⚠️</span>
//             <div>
//               <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", color: "#f59e0b", fontWeight: 600 }}>
//               </span>
//               <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono", color: "#78350f", marginLeft: 12 }}>
//                 Set <code style={{color:"#fbbf24"}}>USE_MOCK=false</code> and <code style={{color:"#fbbf24"}}>sarvam_api_key=YOUR_KEY</code> in backend/.env to use real AI
//               </span>
//             </div>
//           </div>
//         )}
//         {backendMode === "LIVE" && (
//           <div style={{ margin: "8px 16px 0", padding: "6px 16px", borderRadius: 8,
//             background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.2)",
//             display: "flex", alignItems: "center", gap: 8 }}>
//             <span style={{ fontSize: 14 }}>✅</span>
//             <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono", color: "#22c55e" }}>
//              real audio
//             </span>
//           </div>
//         )}

//         {/* Backend error banner */}
//         {backendError && (
//           <div style={{ margin: "12px 16px 0", padding: "12px 16px", borderRadius: 10, background: "rgba(244,63,94,0.07)", border: "1px solid rgba(244,63,94,0.2)", fontSize: 11, fontFamily: "IBM Plex Mono", color: "#fca5a5", lineHeight: 1.6 }}>
//             ⚠ Backend not reachable: {backendError}
//             <br />
//             <span style={{ color: "#475569" }}>Run: <code style={{ color: "#a5b4fc" }}>cd backend && uvicorn main:app --reload --port 8000</code></span>
//           </div>
//         )}

//         {/* ── EMPTY STATE ────────────────────────────────────────────────────── */}
//         {!selectedCall ? (
//           <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "#1e3a5f" }}>
//             <span style={{ fontSize: 36 }}>◈</span>
//             <span style={{ fontSize: 12, fontFamily: "IBM Plex Mono" }}>
//               {activeGrade ? `Showing ${activeGrade} calls — select one to inspect` : "Select a call from the sidebar"}
//             </span>
//           </div>
//         ) : (
//           <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

//             {/* Call header */}
//             <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px 0", flexShrink: 0 }}>
//               <div>
//                 <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3, flexWrap: "wrap" }}>
//                   <span style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 16, color: "#e2e8f0" }}>
//                     {selectedCall.phone_number || selectedCall.call_id}
//                   </span>
//                   <StatusBadge status={selectedCall.status} />
//                   {selectedCall.grade && (
//                     <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono", padding: "2px 8px", borderRadius: 6, background: gc(selectedCall.grade).bg, color: gc(selectedCall.grade).color, border: `1px solid ${gc(selectedCall.grade).border}` }}>
//                       {gc(selectedCall.grade).label}
//                     </span>
//                   )}
//                   {selectedCall.has_fatal && (
//                     <span style={{ fontSize: 10, color: "#f43f5e", fontFamily: "IBM Plex Mono", padding: "2px 8px", borderRadius: 6, background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.25)" }}>
//                       ⚠ FATAL FLAG
//                     </span>
//                   )}
//                 </div>
//                 <div style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono" }}>
//                   {selectedCall.agent_id !== "UNKNOWN" ? `${selectedCall.agent_id} · ` : ""}
//                   {selectedCall.duration_formatted !== "—" ? `${selectedCall.duration_formatted} · ` : ""}
//                   {fmtDate(selectedCall.created_at)}
//                 </div>
//               </div>
//               {selectedCall.total_score != null && <ScoreRing score={selectedCall.total_score} size={58} />}
//             </div>

//             {/* Tabs */}
//             <div style={{ display: "flex", padding: "10px 20px 0", borderBottom: "1px solid #0f172a", flexShrink: 0 }}>
//               {[["transcript", "⌨ Transcript"], ["analysis", "◈ QA Analysis"]].map(([t, label]) => (
//                 <button key={t} onClick={() => setActiveTab(t)} style={{
//                   padding: "8px 20px", fontFamily: "IBM Plex Mono", fontSize: 11, letterSpacing: 1,
//                   background: "none", border: "none", cursor: "pointer",
//                   color: activeTab === t ? "#a5b4fc" : "#334155",
//                   borderBottom: `2px solid ${activeTab === t ? "#6366f1" : "transparent"}`,
//                   transition: "all 0.15s",
//                 }}>{label}</button>
//               ))}
//             </div>

//             {/* Panels */}
//             <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
//               {/* Main panel */}
//               <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
//                 {!callDetail ? (
//                   <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 48 }}>
//                     {selectedCall.status === "processing" || selectedCall.status === "pending"
//                       ? "⟳ Processing call — transcript will appear automatically when ready…"
//                       : "Loading…"}
//                   </div>
//                 ) : activeTab === "transcript"
//                   ? <TranscriptPanel transcript={callDetail.transcript} />
//                   : <AnalysisPanel scorecard={callDetail.scorecard} />
//                 }
//               </div>

//               {/* Right panel */}
//               <div style={{ width: 258, flexShrink: 0, borderLeft: "1px solid #0f172a", overflowY: "auto", padding: 16 }}>
//                 <RightPanel callDetail={callDetail} />
//               </div>
//             </div>
//           </div>
//         )}

//         {/* ── AUDIO PLAYER ─────────────────────────────────────────────────── */}
//         <div style={{ height: 56, flexShrink: 0, borderTop: "1px solid #0f172a", background: "rgba(2,8,23,0.97)" }}>
//           <AudioPlayer
//             audioUrl={selectedCall ? API.audioUrl(selectedCall.call_id) : null}
//             callId={selectedCall?.call_id}
//           />
//         </div>
//       </div>

//       <style>{`
//         * { box-sizing: border-box; margin: 0; padding: 0; }
//         ::-webkit-scrollbar { width: 3px; }
//         ::-webkit-scrollbar-track { background: transparent; }
//         ::-webkit-scrollbar-thumb { background: #0f172a; border-radius: 2px; }
//         button { outline: none; }
//         @keyframes slide {
//           0%   { transform: translateX(-100%); width: 60%; }
//           100% { transform: translateX(200%); width: 60%; }
//         }
//       `}</style>
//     </div>
//   );
// }





// ***********************************************************************************
// import { useState, useEffect, useRef, useCallback } from "react";

// // ─── Font ─────────────────────────────────────────────────────────────────────
// const _fl = document.createElement("link");
// _fl.rel = "stylesheet";
// _fl.href = "https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@300;400;500;600&display=swap";
// document.head.appendChild(_fl);

// // ─── API Layer ────────────────────────────────────────────────────────────────
// const BASE = "http://localhost:8000/api";

// const apiFetch = async (path, opts) => {
//   const res = await fetch(`${BASE}${path}`, opts);
//   if (!res.ok) {
//     const text = await res.text().catch(() => res.statusText);
//     throw new Error(`${res.status}: ${text}`);
//   }
//   return res.json();
// };

// const API = {
//   dashboard:   (grade)  => apiFetch(`/dashboard${grade ? `?grade=${grade}` : ""}`),
//   call:        (id)     => apiFetch(`/call/${id}`),
//   upload:      (files)  => { const fd = new FormData(); files.forEach(f => fd.append("files", f)); return apiFetch("/upload", { method: "POST", body: fd }); },
//   jobStatus:   (id)     => apiFetch(`/jobs/${id}`),
//   leaderboard: ()       => apiFetch("/leaderboard"),
//   seed:        ()       => apiFetch("/seed", { method: "POST" }),
//   reset:       ()       => apiFetch("/debug/reset", { method: "DELETE" }),
//   debugStore:  ()       => apiFetch("/debug/store"),
//   // FIX 1: audioUrl must NOT include "localhost" check — that breaks the player.
//   // Just return the full URL. The audio element handles it natively.
//   audioUrl:    (id)     => `${BASE}/audio/${id}`,
// };

// // ─── Grade config ─────────────────────────────────────────────────────────────
// const GRADE_CONFIG = {
//   excellent: { color: "#22c55e", bg: "rgba(34,197,94,0.10)",  border: "rgba(34,197,94,0.30)",  label: "Excellent", letter: "A" },
//   good:      { color: "#38bdf8", bg: "rgba(56,189,248,0.10)", border: "rgba(56,189,248,0.30)", label: "Good",      letter: "B" },
//   average:   { color: "#f59e0b", bg: "rgba(245,158,11,0.10)", border: "rgba(245,158,11,0.30)", label: "Average",   letter: "C" },
//   poor:      { color: "#f43f5e", bg: "rgba(244,63,94,0.10)",  border: "rgba(244,63,94,0.30)",  label: "Poor",      letter: "D" },
// };
// const gc = (g) => GRADE_CONFIG[g] || { color: "#94a3b8", bg: "rgba(148,163,184,0.06)", border: "#1e293b", label: g || "—", letter: "—" };

// // ─── Helpers ──────────────────────────────────────────────────────────────────
// const fmtDate = (iso) => iso ? iso.slice(0, 16).replace("T", " ") : "—";

// // ─── Score Ring ───────────────────────────────────────────────────────────────
// function ScoreRing({ score, size = 72 }) {
//   if (score == null) return (
//     <div style={{ width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 11 }}>—</div>
//   );
//   const g = score >= 90 ? "excellent" : score >= 75 ? "good" : score >= 60 ? "average" : "poor";
//   const color = gc(g).color;
//   const r = size / 2 - 6;
//   const circ = 2 * Math.PI * r;
//   const dash = (score / 100) * circ;
//   return (
//     <svg width={size} height={size} style={{ transform: "rotate(-90deg)", flexShrink: 0 }}>
//       <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1e293b" strokeWidth={5} />
//       <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={5}
//         strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
//         style={{ transition: "stroke-dasharray 0.8s ease" }} />
//       <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
//         fill={color} fontSize={size * 0.22} fontFamily="IBM Plex Mono" fontWeight="600"
//         style={{ transform: "rotate(90deg)", transformOrigin: "center" }}>{score}</text>
//     </svg>
//   );
// }

// // ─── Stat Card ────────────────────────────────────────────────────────────────
// function StatCard({ label, count, active, colorKey, onClick }) {
//   const cfg = GRADE_CONFIG[colorKey] || { color: "#94a3b8", bg: "rgba(148,163,184,0.06)", border: "#1e293b" };
//   return (
//     <button onClick={onClick} style={{
//       flex: 1, minWidth: 0, display: "flex", flexDirection: "column", alignItems: "center",
//       gap: 4, padding: "14px 8px", borderRadius: 12, cursor: "pointer",
//       background: active ? cfg.bg : "rgba(15,23,42,0.5)",
//       border: `1px solid ${active ? cfg.border : "#0f172a"}`,
//       transition: "all 0.18s",
//       boxShadow: active ? `0 0 20px ${cfg.color}22` : "none",
//     }}>
//       <span style={{ fontSize: 26, fontFamily: "Syne", fontWeight: 800, color: active ? cfg.color : "#e2e8f0" }}>
//         {count ?? 0}
//       </span>
//       <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", color: active ? cfg.color : "#334155" }}>
//         {label}
//       </span>
//     </button>
//   );
// }

// // ─── Status Badge ─────────────────────────────────────────────────────────────
// function StatusBadge({ status }) {
//   const map = {
//     completed:  { color: "#22c55e", label: "Done" },
//     processing: { color: "#f59e0b", label: "Processing…" },
//     pending:    { color: "#6366f1", label: "Pending" },
//     failed:     { color: "#f43f5e", label: "Failed" },
//   };
//   const s = map[status] || { color: "#94a3b8", label: status };
//   return (
//     <span style={{
//       fontSize: 9, fontFamily: "IBM Plex Mono", padding: "2px 7px", borderRadius: 5,
//       color: s.color, background: `${s.color}18`, border: `1px solid ${s.color}44`,
//       letterSpacing: 0.5,
//     }}>{s.label}</span>
//   );
// }

// // ─── Call List Item ───────────────────────────────────────────────────────────
// function CallItem({ call, active, onClick }) {
//   const cfg = gc(call.grade);
//   const isProcessing = call.status === "processing" || call.status === "pending";
//   return (
//     <button onClick={onClick} style={{
//       width: "100%", textAlign: "left", padding: "12px 14px", borderRadius: 10,
//       background: active ? cfg.bg : "rgba(15,23,42,0.4)",
//       border: `1px solid ${active ? cfg.border : "#0f172a"}`,
//       cursor: "pointer", transition: "all 0.15s", marginBottom: 4,
//     }}>
//       <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
//         <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 600, color: active ? "#e2e8f0" : "#94a3b8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>
//           {call.phone_number || call.call_id}
//         </span>
//         {call.total_score != null
//           ? <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 700, color: cfg.color, flexShrink: 0 }}>{call.total_score}%</span>
//           : <StatusBadge status={call.status} />}
//       </div>
//       <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
//         <span style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "60%" }}>
//           {call.agent_id === "UNKNOWN" ? "—" : call.agent_id}
//         </span>
//         <div style={{ display: "flex", gap: 5, alignItems: "center", flexShrink: 0 }}>
//           {call.has_fatal && <span style={{ fontSize: 8, color: "#f43f5e", fontFamily: "IBM Plex Mono", letterSpacing: 0.5 }}>⚠ FATAL</span>}
//           {call.grade && (
//             <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", padding: "1px 6px", borderRadius: 4, background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}>
//               {cfg.label}
//             </span>
//           )}
//         </div>
//       </div>
//       <div style={{ fontSize: 9, color: "#1e3a5f", fontFamily: "IBM Plex Mono", marginTop: 3 }}>
//         {call.duration_formatted !== "—" ? `${call.duration_formatted} · ` : ""}{call.created_at?.slice(0, 10)}
//       </div>
//       {/* Processing progress bar */}
//       {isProcessing && (
//         <div style={{ marginTop: 6, height: 2, background: "#0f172a", borderRadius: 1, overflow: "hidden" }}>
//           <div style={{ height: "100%", background: "#6366f1", borderRadius: 1, animation: "slide 1.5s infinite" }} />
//         </div>
//       )}
//     </button>
//   );
// }

// // ─── Transcript Panel ─────────────────────────────────────────────────────────
// function TranscriptPanel({ transcript }) {
//   if (!transcript?.length) return (
//     <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 48 }}>
//       Transcript not available
//     </div>
//   );

//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
//       {transcript.map((entry, i) => {
//         const isAgent = entry.speaker_label === "Agent";
//         const flagged = entry.is_flagged;
//         return (
//           <div key={i} style={{ display: "flex", gap: 10, flexDirection: isAgent ? "row" : "row-reverse" }}>
//             {/* Avatar */}
//             <div style={{
//               width: 28, height: 28, borderRadius: "50%", flexShrink: 0, marginTop: 2,
//               background: isAgent ? (flagged ? "rgba(244,63,94,0.15)" : "rgba(99,102,241,0.15)") : "rgba(30,41,59,0.8)",
//               border: `2px solid ${isAgent ? (flagged ? "#f43f5e" : "#6366f1") : "#334155"}`,
//               display: "flex", alignItems: "center", justifyContent: "center",
//               fontSize: 9, fontFamily: "IBM Plex Mono", fontWeight: 600,
//               color: isAgent ? (flagged ? "#f43f5e" : "#a5b4fc") : "#94a3b8",
//             }}>{isAgent ? "AG" : "CX"}</div>

//             <div style={{ maxWidth: "76%", display: "flex", flexDirection: "column", gap: 3, alignItems: isAgent ? "flex-start" : "flex-end" }}>
//               <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
//                 <span style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>
//                   {entry.start_time?.toFixed(1)}s
//                 </span>
//                 <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: isAgent ? "#6366f1" : "#475569" }}>
//                   {entry.speaker_label}
//                 </span>
//                 {flagged && (
//                   <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: "#f43f5e", padding: "0 5px", borderRadius: 3, background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.25)" }}>
//                     ⚠ Review
//                   </span>
//                 )}
//               </div>
//               {/* Message bubble — red bordered if flagged */}
//               <div style={{
//                 padding: "10px 14px", borderRadius: 12, fontSize: 12, lineHeight: 1.65,
//                 fontFamily: "IBM Plex Mono", color: flagged ? "#fca5a5" : "#cbd5e1",
//                 background: flagged
//                   ? "rgba(244,63,94,0.08)"
//                   : isAgent ? "rgba(99,102,241,0.09)" : "rgba(30,41,59,0.7)",
//                 border: `1px solid ${flagged ? "rgba(244,63,94,0.3)" : isAgent ? "rgba(99,102,241,0.2)" : "#0f172a"}`,
//                 borderLeft: flagged ? "3px solid #f43f5e" : undefined,
//               }}>
//                 {entry.text}
//               </div>
//               {flagged && entry.flag_reason && (
//                 <span style={{ fontSize: 10, color: "#f43f5e88", fontFamily: "IBM Plex Mono", marginLeft: 4 }}>
//                   ↳ {entry.flag_reason}
//                 </span>
//               )}
//             </div>
//           </div>
//         );
//       })}
//     </div>
//   );
// }

// // ─── Analysis Panel ───────────────────────────────────────────────────────────
// function AnalysisPanel({ scorecard }) {
//   const [openSection, setOpenSection] = useState("OPENING");

//   if (!scorecard) return (
//     <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 48 }}>
//       Analysis not available — call may still be processing.
//     </div>
//   );

//   const sectionColors = { OPENING: "#818cf8", SALES: "#38bdf8", SOFT_SKILLS: "#a78bfa", CLOSING: "#34d399" };

//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
//       {/* Improvement areas */}
//       {scorecard.improvement_areas?.length > 0 && (
//         <div style={{ padding: 14, borderRadius: 12, background: "rgba(244,63,94,0.06)", border: "1px solid rgba(244,63,94,0.18)" }}>
//           <div style={{ fontSize: 9, color: "#f43f5e", fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>⚠ Areas to Improve</div>
//           {scorecard.improvement_areas.map((a, i) => (
//             <div key={i} style={{ fontSize: 11, color: "#fca5a5", fontFamily: "IBM Plex Mono", marginBottom: 5, lineHeight: 1.5 }}>• {a}</div>
//           ))}
//         </div>
//       )}

//       {/* Strengths */}
//       {scorecard.strengths?.length > 0 && (
//         <div style={{ padding: 14, borderRadius: 12, background: "rgba(34,197,94,0.05)", border: "1px solid rgba(34,197,94,0.18)" }}>
//           <div style={{ fontSize: 9, color: "#22c55e", fontFamily: "IBM Plex Mono", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>✓ Strengths</div>
//           {scorecard.strengths.map((s, i) => (
//             <div key={i} style={{ fontSize: 11, color: "#86efac", fontFamily: "IBM Plex Mono", marginBottom: 5 }}>✓ {s}</div>
//           ))}
//         </div>
//       )}

//       {/* Section accordions */}
//       {scorecard.sections?.map(sec => {
//         const isOpen = openSection === sec.section_name;
//         const color = sectionColors[sec.section_name] || "#94a3b8";
//         return (
//           <div key={sec.section_name} style={{ borderRadius: 12, border: `1px solid ${isOpen ? color + "44" : "#0f172a"}`, overflow: "hidden" }}>
//             <button onClick={() => setOpenSection(isOpen ? null : sec.section_name)} style={{
//               width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
//               padding: "12px 16px", background: isOpen ? `${color}10` : "rgba(15,23,42,0.5)",
//               border: "none", cursor: "pointer",
//             }}>
//               <span style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 13, color: isOpen ? color : "#94a3b8" }}>
//                 {sec.section_name.replace("_", " ")}
//               </span>
//               <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
//                 <div style={{ width: 56, height: 3, background: "#1e293b", borderRadius: 2, overflow: "hidden" }}>
//                   <div style={{ height: "100%", width: `${sec.section_percentage}%`, background: color }} />
//                 </div>
//                 <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", color, fontWeight: 600 }}>
//                   {sec.section_score}/{sec.section_max}
//                 </span>
//                 <span style={{ color: "#475569", fontSize: 10 }}>{isOpen ? "▲" : "▼"}</span>
//               </div>
//             </button>

//             {isOpen && (
//               <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
//                 {sec.parameters?.map((p, i) => {
//                   const pct = p.percentage ?? 0;
//                   const pColor = pct >= 90 ? "#22c55e" : pct >= 70 ? "#38bdf8" : pct >= 50 ? "#f59e0b" : "#f43f5e";
//                   return (
//                     <div key={i}>
//                       <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
//                         <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
//                           <span style={{ fontSize: 11, color: "#cbd5e1", fontFamily: "IBM Plex Mono" }}>{p.parameter}</span>
//                           {p.is_critical_miss && (
//                             <span style={{ fontSize: 8, color: "#f43f5e", padding: "0 4px", borderRadius: 3, background: "rgba(244,63,94,0.12)", border: "1px solid rgba(244,63,94,0.3)", letterSpacing: 0.5 }}>MISSED</span>
//                           )}
//                         </div>
//                         <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono", fontWeight: 600, color: pColor, flexShrink: 0 }}>
//                           {p.score}/{p.max_score}
//                         </span>
//                       </div>
//                       <div style={{ height: 3, background: "#1e293b", borderRadius: 2, marginBottom: 4, overflow: "hidden" }}>
//                         <div style={{ height: "100%", width: `${pct}%`, background: pColor, borderRadius: 2, boxShadow: `0 0 6px ${pColor}66`, transition: "width 0.6s ease" }} />
//                       </div>
//                       <p style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", margin: 0, lineHeight: 1.5 }}>{p.reason}</p>
//                     </div>
//                   );
//                 })}
//               </div>
//             )}
//           </div>
//         );
//       })}
//     </div>
//   );
// }

// // ─── Fatal Flags ──────────────────────────────────────────────────────────────
// function FatalFlagsPanel({ fatalFlags }) {
//   if (!fatalFlags) return null;
//   const entries = [
//     ["Right Party Confirmation", fatalFlags.right_party_confirmation],
//     ["Rude Behaviour",           fatalFlags.rude_behaviour],
//     ["Miss Sell",                fatalFlags.miss_sell],
//     ["Disposition",              fatalFlags.disposition],
//   ];
//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
//       {entries.map(([label, val]) => {
//         const fatal = val === "F";
//         return (
//           <div key={label} style={{
//             display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8,
//             background: fatal ? "rgba(244,63,94,0.09)" : "rgba(34,197,94,0.05)",
//             border: `1px solid ${fatal ? "rgba(244,63,94,0.28)" : "rgba(34,197,94,0.18)"}`,
//           }}>
//             <span style={{ width: 6, height: 6, borderRadius: "50%", flexShrink: 0, background: fatal ? "#f43f5e" : "#22c55e", boxShadow: `0 0 8px ${fatal ? "#f43f5e" : "#22c55e"}99` }} />
//             <span style={{ flex: 1, fontSize: 10, fontFamily: "IBM Plex Mono", color: "#94a3b8" }}>{label}</span>
//             <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono", fontWeight: 700, color: fatal ? "#f43f5e" : "#22c55e", letterSpacing: 1 }}>{val || "NF"}</span>
//           </div>
//         );
//       })}
//     </div>
//   );
// }

// // ─── Audio Player — FIX 1 applied ────────────────────────────────────────────
// // OLD BUG: isMock = audioUrl.includes("localhost") → always true → audio never played
// // FIX: isMock only if audioUrl is null/empty. Backend URL with localhost is still real.
// function AudioPlayer({ audioUrl, callId }) {
//   const audioRef = useRef(null);
//   const [playing, setPlaying] = useState(false);
//   const [progress, setProgress] = useState(0);
//   const [duration, setDuration] = useState(0);
//   const [volume, setVolume] = useState(0.8);
//   const [loadError, setLoadError] = useState(false);

//   // FIX: only treat as mock/unavailable if there's no URL at all
//   const hasAudio = !!audioUrl;

//   const fmtT = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

//   // Reset on call change
//   useEffect(() => {
//     setPlaying(false); setProgress(0); setDuration(0); setLoadError(false);
//   }, [callId]);

//   useEffect(() => {
//     if (audioRef.current) audioRef.current.volume = volume;
//   }, [volume]);

//   const togglePlay = () => {
//     if (!audioRef.current || !hasAudio || loadError) return;
//     if (playing) {
//       audioRef.current.pause();
//     } else {
//       audioRef.current.play().catch(() => setLoadError(true));
//     }
//     setPlaying(p => !p);
//   };

//   const seek = (e) => {
//     if (!audioRef.current || !hasAudio || !duration) return;
//     const rect = e.currentTarget.getBoundingClientRect();
//     audioRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * duration;
//   };

//   return (
//     <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "0 8px", height: "100%" }}>
//       <audio
//         ref={audioRef}
//         src={hasAudio ? audioUrl : undefined}
//         onTimeUpdate={() => audioRef.current && setProgress(audioRef.current.currentTime)}
//         onLoadedMetadata={() => audioRef.current && setDuration(audioRef.current.duration)}
//         onEnded={() => setPlaying(false)}
//         onError={() => setLoadError(true)}
//       />

//       {/* Play/Pause button */}
//       <button onClick={togglePlay} style={{
//         width: 38, height: 38, borderRadius: "50%",
//         background: hasAudio && !loadError ? "#6366f1" : "#1e293b",
//         border: `1px solid ${hasAudio && !loadError ? "#6366f1" : "#334155"}`,
//         cursor: hasAudio && !loadError ? "pointer" : "default",
//         display: "flex", alignItems: "center", justifyContent: "center",
//         boxShadow: hasAudio && !loadError ? "0 0 20px #6366f144" : "none", flexShrink: 0,
//       }}>
//         {playing
//           ? <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
//           : <svg width="14" height="14" viewBox="0 0 24 24" fill={hasAudio && !loadError ? "white" : "#334155"}><path d="M8 5v14l11-7z"/></svg>
//         }
//       </button>

//       {/* Time + Seek bar */}
//       <span style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", width: 34, flexShrink: 0 }}>
//         {fmtT(progress)}
//       </span>
//       <div
//         onClick={seek}
//         style={{ flex: 1, height: 4, background: "#1e293b", borderRadius: 4, position: "relative", cursor: hasAudio ? "pointer" : "default" }}
//       >
//         <div style={{
//           position: "absolute", left: 0, top: 0, height: "100%",
//           background: "#6366f1", borderRadius: 4,
//           width: duration ? `${(progress / duration) * 100}%` : "0%",
//           transition: "width 0.25s linear",
//         }} />
//       </div>
//       <span style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono", width: 34, flexShrink: 0 }}>
//         {fmtT(duration)}
//       </span>

//       {/* Volume */}
//       <svg width="14" height="14" viewBox="0 0 24 24" fill="#475569" style={{ flexShrink: 0 }}>
//         <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
//       </svg>
//       <input type="range" min={0} max={1} step={0.05} value={volume}
//         onChange={e => setVolume(Number(e.target.value))}
//         style={{ width: 64, accentColor: "#6366f1", cursor: "pointer" }} />

//       {/* Status label */}
//       {loadError && <span style={{ fontSize: 9, color: "#f43f5e", fontFamily: "IBM Plex Mono" }}>No audio</span>}
//       {!hasAudio && !loadError && <span style={{ fontSize: 9, color: "#1e3a5f", fontFamily: "IBM Plex Mono" }}>Select call</span>}
//     </div>
//   );
// }

// // ─── Right Score Panel ────────────────────────────────────────────────────────
// function RightPanel({ callDetail }) {
//   if (!callDetail) return (
//     <div style={{ padding: 16, color: "#1e3a5f", fontFamily: "IBM Plex Mono", fontSize: 11, textAlign: "center" }}>
//       Select a call
//     </div>
//   );

//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
//       {/* Score card */}
//       {callDetail.scorecard && (
//         <div style={{ padding: 16, borderRadius: 12, background: "rgba(15,23,42,0.6)", border: "1px solid #0f172a", textAlign: "center" }}>
//           <ScoreRing score={callDetail.scorecard.total_score} size={80} />
//           <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 20, color: gc(callDetail.scorecard.grade).color, marginTop: 8 }}>
//             Grade {callDetail.scorecard.letter_grade}
//           </div>
//           <div style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", marginTop: 6, lineHeight: 1.5 }}>
//             {callDetail.scorecard.summary_note}
//           </div>
//         </div>
//       )}

//       {/* Speaker stats */}
//       {callDetail.speaker_stats?.length > 0 && (
//         <div>
//           <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8, fontFamily: "IBM Plex Mono" }}>
//             Speaker Stats
//           </div>
//           {callDetail.speaker_stats.map(s => (
//             <div key={s.speaker_id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #0f172a" }}>
//               <div>
//                 <div style={{ fontSize: 10, fontFamily: "IBM Plex Mono", color: s.label === "Agent" ? "#a5b4fc" : "#94a3b8" }}>{s.label}</div>
//                 <div style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>{s.speaker_id}</div>
//               </div>
//               <div style={{ textAlign: "right" }}>
//                 <div style={{ fontSize: 10, fontFamily: "IBM Plex Mono", color: "#cbd5e1" }}>{s.talk_time_formatted}</div>
//                 <div style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>{s.word_count} words</div>
//               </div>
//             </div>
//           ))}
//         </div>
//       )}

//       {/* Fatal flags */}
//       {callDetail.scorecard?.fatal_flags && (
//         <div>
//           <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8, fontFamily: "IBM Plex Mono" }}>
//             Fatal Flags
//           </div>
//           <FatalFlagsPanel fatalFlags={callDetail.scorecard.fatal_flags} />
//         </div>
//       )}

//       {/* Section scores mini */}
//       {callDetail.scorecard?.sections && (
//         <div>
//           <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8, fontFamily: "IBM Plex Mono" }}>
//             Section Scores
//           </div>
//           {callDetail.scorecard.sections.map(s => {
//             const pct = s.section_percentage ?? 0;
//             const color = pct >= 80 ? "#22c55e" : pct >= 60 ? "#f59e0b" : "#f43f5e";
//             return (
//               <div key={s.section_name} style={{ marginBottom: 9 }}>
//                 <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
//                   <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color: "#475569" }}>
//                     {s.section_name.replace("_", " ")}
//                   </span>
//                   <span style={{ fontSize: 9, fontFamily: "IBM Plex Mono", color }}>{s.section_score}/{s.section_max}</span>
//                 </div>
//                 <div style={{ height: 3, background: "#0f172a", borderRadius: 2, overflow: "hidden" }}>
//                   <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 2, transition: "width 0.6s ease" }} />
//                 </div>
//               </div>
//             );
//           })}
//         </div>
//       )}
//     </div>
//   );
// }

// // ─── Main App ─────────────────────────────────────────────────────────────────
// export default function App() {
//   const [metrics, setMetrics]           = useState(null);
//   const [callList, setCallList]         = useState([]);
//   const [activeGrade, setActiveGrade]   = useState(null);
//   const [selectedCall, setSelectedCall] = useState(null);
//   const [callDetail, setCallDetail]     = useState(null);
//   const [activeTab, setActiveTab]       = useState("transcript");
//   const [uploading, setUploading]       = useState(false);
//   const [loading, setLoading]           = useState(true);
//   const [backendError, setBackendError] = useState(null);

//   // pollingRef: call_id → intervalId
//   // FIX 3: use a ref so intervals don't create stale closures over callList
//   const pollingRef    = useRef({});
//   const selectedIdRef = useRef(null);   // tracks selected call_id for auto-refresh
//   const fileInputRef  = useRef();

//   // ── Load dashboard ──────────────────────────────────────────────────────────
//   const loadDashboard = useCallback(async (grade) => {
//     try {
//       const data = await API.dashboard(grade);
//       setMetrics(data.metrics);
//       setCallList(data.calls);
//       setBackendError(null);
//     } catch (e) {
//       setBackendError(e.message);
//     } finally {
//       setLoading(false);
//     }
//   }, []);

//   useEffect(() => { loadDashboard(activeGrade); }, [activeGrade, loadDashboard]);

//   // ── Polling for processing calls ────────────────────────────────────────────
//   // FIX 2 + 3: When a call completes, reload dashboard AND auto-update callDetail
//   // if the completed call is the one currently selected.
//   const startPolling = useCallback((callId) => {
//     if (pollingRef.current[callId]) return; // already polling

//     pollingRef.current[callId] = setInterval(async () => {
//       try {
//         const updated = await API.call(callId);

//         if (updated.status === "completed" || updated.status === "failed") {
//           clearInterval(pollingRef.current[callId]);
//           delete pollingRef.current[callId];

//           // Refresh the sidebar list
//           setCallList(prev => prev.map(c =>
//             c.call_id === callId
//               ? { ...c, status: updated.status, total_score: updated.total_score, grade: updated.grade, has_fatal: false }
//               : c
//           ));

//           // FIX 2: If this call is currently selected, auto-load its detail
//           if (selectedIdRef.current === callId) {
//             setCallDetail(updated);
//             setSelectedCall(prev => prev ? { ...prev, status: updated.status, total_score: updated.total_score, grade: updated.grade } : prev);
//           }

//           // Full dashboard refresh for accurate metrics counts
//           setActiveGrade(g => { loadDashboard(g); return g; });
//         }
//       } catch (_) {}
//     }, 3000);
//   }, [loadDashboard]);

//   // Start polling for any pending/processing calls in the list
//   useEffect(() => {
//     callList.forEach(c => {
//       if (c.status === "processing" || c.status === "pending") {
//         startPolling(c.call_id);
//       }
//     });
//   }, [callList, startPolling]);

//   // Cleanup all intervals on unmount
//   useEffect(() => {
//     return () => Object.values(pollingRef.current).forEach(clearInterval);
//   }, []);

//   // ── Select a call ───────────────────────────────────────────────────────────
//   const selectCall = useCallback(async (callItem) => {
//     setSelectedCall(callItem);
//     setCallDetail(null);
//     selectedIdRef.current = callItem.call_id;

//     try {
//       const detail = await API.call(callItem.call_id);
//       setCallDetail(detail);
//       // If it's processing, make sure polling is active
//       if (detail.status === "processing" || detail.status === "pending") {
//         startPolling(callItem.call_id);
//       }
//     } catch (e) {
//       console.error("Could not load call detail:", e);
//     }
//   }, [startPolling]);

//   // ── Upload ──────────────────────────────────────────────────────────────────
//   const handleUpload = async (files) => {
//     setUploading(true);
//     try {
//       const result = await API.upload(files);
//       await loadDashboard(activeGrade);
//       // Auto-select the first uploaded call after dashboard refreshes
//     } catch (e) {
//       alert(`Upload failed: ${e.message}\n\nIs the backend running? uvicorn main:app --reload`);
//     } finally {
//       setUploading(false);
//     }
//   };

//   // ── Seed demo data ──────────────────────────────────────────────────────────
//   const seedData = async () => {
//     try {
//       await API.seed();
//       await loadDashboard(null);
//       setActiveGrade(null);
//     } catch (e) {
//       alert(`Seed failed: ${e.message}`);
//     }
//   };

//   // ── Reset store ─────────────────────────────────────────────────────────────
//   const resetStore = async () => {
//     if (!confirm("Clear all records from the store?")) return;
//     try {
//       await API.reset();
//       setCallList([]); setMetrics(null); setSelectedCall(null); setCallDetail(null);
//       await loadDashboard(null);
//     } catch (e) {
//       alert(`Reset failed: ${e.message}`);
//     }
//   };

//   // ─────────────────────────────────────────────────────────────────────────────
//   return (
//     <div style={{ display: "flex", height: "100vh", width: "100vw", background: "#020817", color: "#e2e8f0", fontFamily: "IBM Plex Mono, monospace", overflow: "hidden" }}>

//       {/* BG */}
//       <div style={{ position: "fixed", inset: 0, pointerEvents: "none", backgroundImage: "radial-gradient(ellipse 80% 50% at 15% 5%, rgba(99,102,241,0.05) 0%, transparent 60%), radial-gradient(ellipse 60% 40% at 85% 85%, rgba(56,189,248,0.03) 0%, transparent 60%)" }} />

//       {/* ── SIDEBAR ──────────────────────────────────────────────────────────── */}
//       <aside style={{ width: 256, flexShrink: 0, display: "flex", flexDirection: "column", borderRight: "1px solid #0f172a", background: "rgba(2,8,23,0.97)", zIndex: 10, overflow: "hidden" }}>

//         {/* Logo */}
//         <div style={{ padding: "18px 16px 12px", borderBottom: "1px solid #0f172a" }}>
//           <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
//             <span style={{ fontSize: 18, color: "#6366f1" }}>◈</span>
//             <span style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 18, color: "#e2e8f0", letterSpacing: -0.5 }}>Athena</span>
//           </div>
//           <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2, fontFamily: "IBM Plex Mono" }}>call Analysis</div>
//         </div>

//         {/* Upload + seed + reset */}
//         <div style={{ padding: "10px 12px 6px", borderBottom: "1px solid #0f172a", display: "flex", flexDirection: "column", gap: 5 }}>
//           <input ref={fileInputRef} type="file" multiple accept=".wav,.mp3,.m4a,.ogg" style={{ display: "none" }}
//             onChange={e => e.target.files.length && handleUpload(Array.from(e.target.files))} />
//           <button onClick={() => fileInputRef.current.click()} style={{
//             padding: "9px", borderRadius: 9, border: "1px dashed #1e3a5f",
//             background: uploading ? "rgba(99,102,241,0.12)" : "rgba(15,23,42,0.5)",
//             cursor: "pointer", fontSize: 11, fontFamily: "IBM Plex Mono",
//             color: uploading ? "#a5b4fc" : "#475569",
//           }}>
//             {uploading ? "⟳ Processing…" : "↑ Upload Audio Files"}
//           </button>
//           <div style={{ display: "flex", gap: 4 }}>
//             <button onClick={seedData} style={{ flex: 1, padding: "5px", borderRadius: 7, border: "1px solid #0f172a", background: "transparent", cursor: "pointer", fontSize: 9, fontFamily: "IBM Plex Mono", color: "#334155", letterSpacing: 1 }}>
//               LOAD DEMO DATA
//             </button>
//             <button onClick={resetStore} title="Clear store" style={{ padding: "5px 8px", borderRadius: 7, border: "1px solid #0f172a", background: "transparent", cursor: "pointer", fontSize: 9, fontFamily: "IBM Plex Mono", color: "#1e3a5f" }}>
//               ✕
//             </button>
//           </div>
//         </div>

//         {/* Call count */}
//         <div style={{ padding: "8px 14px 4px", fontSize: 9, color: "#1e3a5f", letterSpacing: 2, textTransform: "uppercase", fontFamily: "IBM Plex Mono" }}>
//           {callList.length} {activeGrade ? activeGrade.toUpperCase() : "TOTAL"} CALLS
//         </div>

//         {/* Call list */}
//         <div style={{ flex: 1, overflowY: "auto", padding: "4px 12px 12px" }}>
//           {loading && (
//             <div style={{ color: "#334155", fontSize: 11, textAlign: "center", padding: 24, fontFamily: "IBM Plex Mono" }}>Loading…</div>
//           )}
//           {!loading && callList.length === 0 && (
//             <div style={{ color: "#334155", fontSize: 11, textAlign: "center", padding: 24, fontFamily: "IBM Plex Mono", lineHeight: 1.6 }}>
//               {activeGrade ? `No ${activeGrade} calls.` : "No calls yet.\nUpload audio or click\nLOAD DEMO DATA."}
//             </div>
//           )}
//           {callList.map(call => (
//             <CallItem
//               key={call.call_id}
//               call={call}
//               active={selectedCall?.call_id === call.call_id}
//               onClick={() => selectCall(call)}
//             />
//           ))}
//         </div>
//       </aside>

//       {/* ── MAIN COLUMN ──────────────────────────────────────────────────────── */}
//       <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

//         {/* ── STAT TABS ──────────────────────────────────────────────────────── */}
//         <div style={{ display: "flex", gap: 8, padding: "12px 16px", borderBottom: "1px solid #0f172a", flexShrink: 0, background: "rgba(2,8,23,0.9)" }}>
//           <StatCard label="Total Calls"  count={metrics?.total_calls}     active={activeGrade === null}        colorKey={null}        onClick={() => setActiveGrade(null)} />
//           <StatCard label="Attended"     count={metrics?.attended_calls}   active={false}                       colorKey={null}        onClick={() => setActiveGrade(null)} />
//           <StatCard label="Not Attended" count={metrics?.not_attended}     active={false}                       colorKey={null}        onClick={() => setActiveGrade(null)} />
//           <StatCard label="Excellent"    count={metrics?.excellent}        active={activeGrade === "excellent"} colorKey="excellent"   onClick={() => setActiveGrade(g => g === "excellent" ? null : "excellent")} />
//           <StatCard label="Good"         count={metrics?.good}             active={activeGrade === "good"}      colorKey="good"        onClick={() => setActiveGrade(g => g === "good" ? null : "good")} />
//           <StatCard label="Average"      count={metrics?.average}          active={activeGrade === "average"}   colorKey="average"     onClick={() => setActiveGrade(g => g === "average" ? null : "average")} />
//           <StatCard label="Poor"         count={metrics?.poor}             active={activeGrade === "poor"}      colorKey="poor"        onClick={() => setActiveGrade(g => g === "poor" ? null : "poor")} />
//         </div>

//         {/* Backend error banner */}
//         {backendError && (
//           <div style={{ margin: "12px 16px 0", padding: "12px 16px", borderRadius: 10, background: "rgba(244,63,94,0.07)", border: "1px solid rgba(244,63,94,0.2)", fontSize: 11, fontFamily: "IBM Plex Mono", color: "#fca5a5", lineHeight: 1.6 }}>
//             ⚠ Backend not reachable: {backendError}
//             <br />
//             <span style={{ color: "#475569" }}>Run: <code style={{ color: "#a5b4fc" }}>cd backend && uvicorn main:app --reload --port 8000</code></span>
//           </div>
//         )}

//         {/* ── EMPTY STATE ────────────────────────────────────────────────────── */}
//         {!selectedCall ? (
//           <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "#1e3a5f" }}>
//             <span style={{ fontSize: 36 }}>◈</span>
//             <span style={{ fontSize: 12, fontFamily: "IBM Plex Mono" }}>
//               {activeGrade ? `Showing ${activeGrade} calls — select one to inspect` : "Select a call from the sidebar"}
//             </span>
//           </div>
//         ) : (
//           <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

//             {/* Call header */}
//             <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px 0", flexShrink: 0 }}>
//               <div>
//                 <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3, flexWrap: "wrap" }}>
//                   <span style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 16, color: "#e2e8f0" }}>
//                     {selectedCall.phone_number || selectedCall.call_id}
//                   </span>
//                   <StatusBadge status={selectedCall.status} />
//                   {selectedCall.grade && (
//                     <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono", padding: "2px 8px", borderRadius: 6, background: gc(selectedCall.grade).bg, color: gc(selectedCall.grade).color, border: `1px solid ${gc(selectedCall.grade).border}` }}>
//                       {gc(selectedCall.grade).label}
//                     </span>
//                   )}
//                   {selectedCall.has_fatal && (
//                     <span style={{ fontSize: 10, color: "#f43f5e", fontFamily: "IBM Plex Mono", padding: "2px 8px", borderRadius: 6, background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.25)" }}>
//                       ⚠ FATAL FLAG
//                     </span>
//                   )}
//                 </div>
//                 <div style={{ fontSize: 10, color: "#334155", fontFamily: "IBM Plex Mono" }}>
//                   {selectedCall.agent_id !== "UNKNOWN" ? `${selectedCall.agent_id} · ` : ""}
//                   {selectedCall.duration_formatted !== "—" ? `${selectedCall.duration_formatted} · ` : ""}
//                   {fmtDate(selectedCall.created_at)}
//                 </div>
//               </div>
//               {selectedCall.total_score != null && <ScoreRing score={selectedCall.total_score} size={58} />}
//             </div>

//             {/* Tabs */}
//             <div style={{ display: "flex", padding: "10px 20px 0", borderBottom: "1px solid #0f172a", flexShrink: 0 }}>
//               {[["transcript", "⌨ Transcript"], ["analysis", "◈ QA Analysis"]].map(([t, label]) => (
//                 <button key={t} onClick={() => setActiveTab(t)} style={{
//                   padding: "8px 20px", fontFamily: "IBM Plex Mono", fontSize: 11, letterSpacing: 1,
//                   background: "none", border: "none", cursor: "pointer",
//                   color: activeTab === t ? "#a5b4fc" : "#334155",
//                   borderBottom: `2px solid ${activeTab === t ? "#6366f1" : "transparent"}`,
//                   transition: "all 0.15s",
//                 }}>{label}</button>
//               ))}
//             </div>

//             {/* Panels */}
//             <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
//               {/* Main panel */}
//               <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
//                 {!callDetail ? (
//                   <div style={{ color: "#334155", fontFamily: "IBM Plex Mono", fontSize: 12, textAlign: "center", padding: 48 }}>
//                     {selectedCall.status === "processing" || selectedCall.status === "pending"
//                       ? "⟳ Processing call — transcript will appear automatically when ready…"
//                       : "Loading…"}
//                   </div>
//                 ) : activeTab === "transcript"
//                   ? <TranscriptPanel transcript={callDetail.transcript} />
//                   : <AnalysisPanel scorecard={callDetail.scorecard} />
//                 }
//               </div>

//               {/* Right panel */}
//               <div style={{ width: 258, flexShrink: 0, borderLeft: "1px solid #0f172a", overflowY: "auto", padding: 16 }}>
//                 <RightPanel callDetail={callDetail} />
//               </div>
//             </div>
//           </div>
//         )}

//         {/* ── AUDIO PLAYER ─────────────────────────────────────────────────── */}
//         <div style={{ height: 56, flexShrink: 0, borderTop: "1px solid #0f172a", background: "rgba(2,8,23,0.97)" }}>
//           <AudioPlayer
//             audioUrl={selectedCall ? API.audioUrl(selectedCall.call_id) : null}
//             callId={selectedCall?.call_id}
//           />
//         </div>
//       </div>

//       <style>{`
//         * { box-sizing: border-box; margin: 0; padding: 0; }
//         ::-webkit-scrollbar { width: 3px; }
//         ::-webkit-scrollbar-track { background: transparent; }
//         ::-webkit-scrollbar-thumb { background: #0f172a; border-radius: 2px; }
//         button { outline: none; }
//         @keyframes slide {
//           0%   { transform: translateX(-100%); width: 60%; }
//           100% { transform: translateX(200%); width: 60%; }
//         }
//       `}</style>
//     </div>
//   );
// }


// **********************************************************************************
import { useState, useEffect, useRef, useCallback } from "react";

// ─── Font ──────────────────────────────────────────────────────────────────
const _fl = document.createElement("link");
_fl.rel = "stylesheet";
_fl.href = "https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@300;400;500;600&display=swap";
document.head.appendChild(_fl);

// ─── API Layer (matches your FastAPI routes exactly) ──────────────────────
const API_HOST = window.location.hostname === "localhost"
  ? "127.0.0.1"
  : (window.location.hostname || "127.0.0.1");
const BASE = `http://${API_HOST}:8000/api`;

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
function TranscriptView({ transcript }) {
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
  const [loadError, setLoadError] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const hasAudio = Boolean(audioUrl);
  const audioSrc = hasAudio ? `${audioUrl}${audioUrl.includes("?") ? "&" : "?"}reload=${reloadToken}` : undefined;
  const fmtT = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  console.log("audio player hit")
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  useEffect(() => {
    if (audioRef.current && hasAudio) {
      setLoadError(false);
      audioRef.current.load();
    }
  }, [audioSrc, hasAudio]);

  const togglePlay = async () => {
    if (!audioRef.current || !hasAudio) {
      return;
    }

    if (loadError) {
      setLoadError(false);
      setPlaying(false);
      setProgress(0);
      setDuration(0);
      setReloadToken((value) => value + 1);
      return;
    }

    if (audioRef.current.paused) {
      try {
        await audioRef.current.play();
      } catch (error) {
        console.error("Audio playback failed:", error);
        setLoadError(true);
      }
      return;
    }

    audioRef.current.pause();
  };



  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "0 8px", height: "100%" }}>
      <audio
        key={`${callId}-${reloadToken}`}
        ref={audioRef}
        src={audioSrc}
        preload="metadata"
        crossOrigin="anonymous"
        onTimeUpdate={() => {
          if (audioRef.current) {
            setProgress(audioRef.current.currentTime);
          }
        }}
        onLoadedMetadata={() => {
          if (audioRef.current) {
            setDuration(audioRef.current.duration || 0);
          }
          setLoadError(false);
        }}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => {
          setPlaying(false);
          setProgress(0);
        }}
        onError={(event) => {
          console.error("Audio failed to load:", audioUrl, event);
          setLoadError(true);
          setPlaying(false);
        }}
      />


      {/* Play/Pause */}
      <button onClick={togglePlay} style={{
        width: 38, height: 38, borderRadius: "50%",
        background: hasAudio && !loadError ? "#6366f1" : "#1e293b",
        border: "none", cursor: hasAudio && !loadError ? "pointer" : "default",
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: hasAudio && !loadError ? "0 0 20px #6366f155" : "none", flexShrink: 0,
      }}>
        {playing
          ? <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
          : loadError
            ? <svg width="14" height="14" viewBox="0 0 24 24" fill="#fca5a5"><path d="M12 5v14m-7-7h14"/></svg>
            : <svg width="14" height="14" viewBox="0 0 24 24" fill={hasAudio ? "white" : "#334155"}><path d="M8 5v14l11-7z"/></svg>}
      </button>


      {/* Seek */}
      <span style={{ fontSize: 10, color: "#475569", fontFamily: "IBM Plex Mono", width: 32, flexShrink: 0 }}>{fmtT(progress)}</span>
      <div style={{ flex: 1, height: 4, background: "#1e293b", borderRadius: 4, position: "relative", cursor: "pointer" }}
        onClick={e => {
          if (!audioRef.current || !hasAudio || loadError || !duration) return;
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

      {!hasAudio && <span style={{ fontSize: 9, color: "#334155", fontFamily: "IBM Plex Mono" }}>No audio</span>}
      {hasAudio && (
      
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {loadError && <span style={{ fontSize: 9, color: "#f43f5e", fontFamily: "IBM Plex Mono" }}>Audio failed</span>}
      
          <button
            onClick={() => setReloadToken((v) => v + 1)}
            style={{ fontSize: 9, color: "#a5b4fc", fontFamily: "IBM Plex Mono", background: "transparent", border: "1px solid #475569", borderRadius: 4, padding: "2px 6px", cursor: "pointer" }}
          >
            Retry
          </button>
      
          <a
            href={audioUrl}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 9, color: "#a5b4fc", fontFamily: "IBM Plex Mono", textDecoration: "none" }}
          >
            Open audio
          </a>
          <a
            href={audioUrl}
            download
            style={{ fontSize: 9, color: "#a5b4fc", fontFamily: "IBM Plex Mono", textDecoration: "none" }}
          >
            Download
          </a>
        </div>
      )}
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
    } catch {
      setError("Backend not connected. Run: uvicorn main:app --reload");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(activeGrade); }, [activeGrade, loadDashboard]);

  // ── Auto-refresh processing calls ────────────────────────────────────────
  useEffect(() => {
    const activePollers = pollingRef.current;
    const processing = callList.filter(c => c.status === "processing" || c.status === "pending");
    processing.forEach(c => {
      if (activePollers[c.call_id]) return;
      activePollers[c.call_id] = setInterval(async () => {
        try {
          const updated = await API.call(c.call_id);
          if (updated.status === "completed" || updated.status === "failed") {
            clearInterval(activePollers[c.call_id]);
            delete activePollers[c.call_id];
            if (selectedCall?.call_id === c.call_id) {
              setCallDetail(updated);
              setSelectedCall((current) => (current?.call_id === updated.call_id ? {
                ...current,
                status: updated.status,
                total_score: updated.total_score,
                grade: updated.grade,
                has_fatal: Boolean(updated.scorecard && Object.values(updated.scorecard.fatal_flags || {}).includes("F")),
                agent_id: updated.agent_id,
                duration_formatted: updated.duration_formatted,
              } : current));
            }
            loadDashboard(activeGrade);
          }
        } catch (pollError) {
          console.error("Polling failed for call", c.call_id, pollError);
        }
      }, 4000);
    });
    return () => Object.values(activePollers).forEach(clearInterval);
  }, [callList, activeGrade, loadDashboard, selectedCall?.call_id]);

  // ── Select call and load detail ────────────────────────────────────────────
  const selectCall = useCallback(async (callItem) => {
    setSelectedCall(callItem);
    setCallDetail(null);
    setActiveTab("transcript");
    setError(null);

    try {
      const detail = await API.call(callItem.call_id);
      setSelectedCall((current) => (current?.call_id === callItem.call_id ? {
        ...callItem,
        status: detail.status,
        total_score: detail.total_score,
        grade: detail.grade,
        has_fatal: Boolean(detail.scorecard && Object.values(detail.scorecard.fatal_flags || {}).includes("F")),
        agent_id: detail.agent_id,
        duration_formatted: detail.duration_formatted,
      } : current));
      setCallDetail(detail);
    } catch (loadError) {
      console.error("Could not load call detail:", loadError);
      setCallDetail({
        transcript: [],
        speaker_stats: [],
        scorecard: null,
      });
      setError(`Could not load call ${callItem.call_id}.`);
    }
  }, []);

  // ── Upload ────────────────────────────────────────────────────────────────
  const handleUpload = async (files) => {
    setUploading(true);
    try {
      await API.upload(files);
      await loadDashboard(activeGrade);
    } catch {
      alert("Upload failed. backend nahi chal rha?");
    } finally {
      setUploading(false);
    }
  };

  // ── Seed mock data ────────────────────────────────────────────────────────
  const seedData = async () => {
    try {
      await API.seed();
      await loadDashboard(null);
    } catch {
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
            <span style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 18, color: "#e2e8f0" }}>Athena</span>
          </div>
          <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: 2 }}>Call Analytics Platform</div>
        </div>

        {/* Upload zone */}
        <div style={{ padding: "12px 12px 8px" }}>
          <input ref={fileInputRef} type="file" multiple accept=".wav,.mp3,.m4a" style={{ display: "none" }} onChange={(event) => handleUpload(Array.from(event.target.files || []))} />
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
          }}>LOAD DATA</button>
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
                    ? <TranscriptView transcript={callDetail.transcript} />
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
            ? <AudioPlayer key={selectedCall.call_id} audioUrl={API.audioUrl(selectedCall.call_id)} callId={selectedCall.call_id} />
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
