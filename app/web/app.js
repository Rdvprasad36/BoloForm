// Bolo Form frontend. Plain ES modules, no build step.
// Security rule: anything that came from the server or the user is inserted with textContent only.
import { Recorder } from "/recorder.js";

const $ = (id) => document.getElementById(id);
const state = { sid: null, rec: new Recorder(), recording: false, busy: false, provider: "mock",
                audio: null, lastAudioSrc: null, current: null };

const MIC = {
  idle: ["నొక్కి చెప్పండి", "Tap to speak"],
  listening: ["వింటున్నాను…", "Listening"],
  processing: ["ఆలోచిస్తున్నాను…", "Thinking"],
  speaking: ["చెబుతున్నాను…", "Speaking"],
  error: ["మళ్ళీ ప్రయత్నించండి", "Try again"],
};
const CHIP = { confirmed: "Confirmed", implicit: "Heard", typed: "Typed", needs_check: "Needs check",
               edited: "Edited", skipped: "Skipped", empty: "" };

// ------------------------------------------------------------------ helpers
function show(id) {
  for (const s of document.querySelectorAll(".screen")) s.hidden = s.id !== id;
  window.scrollTo({ top: 0 });
}
function setText(id, t) { $(id).textContent = t == null ? "" : String(t); }
function announce(t) { setText("live", t); }

function setMic(name) {
  const m = $("mic");
  m.dataset.state = name;
  m.setAttribute("aria-pressed", String(name === "listening"));
  m.disabled = name === "processing";
  const [te, en] = MIC[name];
  setText("mic-label", te);
  m.setAttribute("aria-label", en);
  state.busy = name === "processing";
  if (name !== "listening") $("meter-fill").style.width = "0";
}

function stopAudio() {
  if (state.audio) { state.audio.pause(); state.audio = null; }
}

function playPrompt(prompt) {
  stopAudio();
  if (!prompt || !prompt.audio_b64) { setMic("idle"); return; }
  const src = `data:${prompt.mime || "audio/wav"};base64,${prompt.audio_b64}`;
  state.lastAudioSrc = src;
  const a = new Audio(src);
  state.audio = a;
  setMic("speaking");
  const done = () => { if (state.audio === a) { state.audio = null; setMic("idle"); } };
  a.onended = done;
  a.onerror = done;
  a.play().catch(done);                      // autoplay blocked -> just go idle, user can tap Replay
}

function fillList(ul, items, withChip = true) {
  ul.replaceChildren();
  for (const f of items) {
    const li = document.createElement("li");
    const l = document.createElement("span"); l.className = "lbl te"; l.textContent = f.label_te;
    const v = document.createElement("span"); v.className = "val te"; v.textContent = f.value || "—";
    if (withChip && CHIP[f.status]) {
      const c = document.createElement("span");
      c.className = "chip" + (f.status === "needs_check" ? " check-me" : "");
      c.textContent = CHIP[f.status];
      v.append(c);
    }
    li.append(l, v);
    ul.append(li);
  }
}

// ------------------------------------------------------------------ network
async function api(path, opts = {}) {
  let res;
  try { res = await fetch(path, opts); }
  catch (_) { throw new Error("Cannot reach the server."); }
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
  return data;
}

async function postTurn({ audio, text, typed, hint, answer, command }) {
  setMic("processing");
  const fd = new FormData();
  if (audio) fd.append("audio", audio, "speech.wav");
  if (text != null) fd.append("text", text);
  if (typed) fd.append("typed", "1");
  if (hint) fd.append("hint", hint);
  if (answer) fd.append("answer", answer);
  if (command) fd.append("command", command);
  try {
    render(await api(`/api/sessions/${state.sid}/turn`, { method: "POST", body: fd }));
  } catch (e) {
    setMic("error");
    showMessage(e.message, "");
    $("typed").hidden = false;
  }
}

// ------------------------------------------------------------------ rendering
function showMessage(te, en) {
  const box = $("message");
  box.hidden = !(te || en);
  setText("msg-te", te);
  setText("msg-en", en);
}

function render(turn) {
  state.current = turn;
  state.sid = turn.session_id || state.sid;
  announce(turn.say_en);
  if (turn.action === "review") return renderReview(turn);
  if (turn.action === "done") return renderDone(turn);

  show("s-question");
  const total = turn.progress.total, idx = Math.min(turn.progress.index + 1, total);
  setText("progress-text", `${idx} / ${total}`);
  $("progress-fill").style.width = `${(turn.progress.index / total) * 100}%`;
  if (turn.field) { setText("q-te", turn.field.prompt_te); setText("q-en", turn.field.prompt_en); }

  // Show the spoken message when it is more than the plain question (greeting, errors, read-back)
  const plain = turn.field && turn.say_te === turn.field.prompt_te;
  showMessage(plain || turn.action === "confirm" ? "" : turn.say_te, plain || turn.action === "confirm" ? "" : turn.say_en);

  const c = $("confirm-card");
  c.hidden = turn.action !== "confirm" || !turn.confirm;
  if (!c.hidden) {
    setText("confirm-value", turn.confirm.display);
    setText("confirm-en", turn.confirm.display_en && turn.confirm.display_en !== turn.confirm.display
      ? turn.confirm.display_en : "");
  }
  if (turn.action === "fallback") { $("typed").hidden = false; $("typed-input").focus(); }
  if (turn.heard !== undefined) setText("heard", turn.heard);
  else setText("heard", "");
  $("mockbox").hidden = state.provider !== "mock";
  fillList($("sofar"), turn.form.filter((f) => f.status !== "empty"));
  playPrompt(turn.prompt);
}

function renderReview(turn) {
  show("s-review");
  stopAudio();
  setMic("idle");
  const order = { needs_check: 0, skipped: 1, empty: 1, implicit: 2, typed: 2, edited: 3, confirmed: 3 };
  const rows = [...turn.form].sort((a, b) => (order[a.status] ?? 2) - (order[b.status] ?? 2));
  const ul = $("review-list");
  ul.replaceChildren();
  for (const f of rows) {
    const li = document.createElement("li");
    const top = document.createElement("div"); top.className = "top-row";
    const l = document.createElement("span"); l.className = "lbl te"; l.textContent = f.label_te;
    const v = document.createElement("span"); v.className = "val te"; v.textContent = f.value || "—";
    if (CHIP[f.status]) {
      const chip = document.createElement("span");
      chip.className = "chip" + (f.status === "needs_check" ? " check-me" : "");
      chip.textContent = CHIP[f.status];
      v.append(chip);
    }
    top.append(l, v);
    const actions = document.createElement("div"); actions.className = "actions";
    const edit = document.createElement("button"); edit.className = "secondary"; edit.type = "button"; edit.textContent = "✎ Edit";
    const mic = document.createElement("button"); mic.className = "secondary"; mic.type = "button"; mic.textContent = "🎤 Say again";
    edit.addEventListener("click", () => openEditor(li, f));
    mic.addEventListener("click", async () => {
      try { render(await api(`/api/sessions/${state.sid}/rerecord/${encodeURIComponent(f.key)}`, { method: "POST" })); }
      catch (e) { setText("review-error", e.message); $("review-error").hidden = false; }
    });
    actions.append(edit, mic);
    li.append(top, actions);
    ul.append(li);
  }
  setText("review-error", "");
  $("review-error").hidden = true;
  playPrompt(turn.prompt);
}

function openEditor(li, f) {
  if (li.querySelector("input")) return;
  const input = document.createElement("input");
  input.type = "text"; input.value = f.value || ""; input.setAttribute("aria-label", `Edit ${f.label_en}`);
  const save = document.createElement("button"); save.className = "primary"; save.type = "button"; save.textContent = "Save";
  const run = async () => {
    try {
      const turn = await api(`/api/sessions/${state.sid}/fields/${encodeURIComponent(f.key)}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ value: input.value }) });
      if (turn.error) { setText("review-error", turn.say_en); $("review-error").hidden = false; }
      else renderReview(turn);
    } catch (e) { setText("review-error", e.message); $("review-error").hidden = false; }
  };
  save.addEventListener("click", run);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
  li.append(input, save);
  input.focus();
}

function renderDone(turn) {
  show("s-done");
  fillList($("done-list"), turn.form, false);
  playPrompt(turn.prompt);
}

// ------------------------------------------------------------------ actions
async function startSession() {
  $("welcome-error").hidden = true;
  try {
    const turn = await api("/api/sessions", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ form_id: $("form-select").value, telephony_sim: $("telephony").checked }) });
    state.provider = turn.provider;
    state.sid = turn.session_id;
    render(turn);
  } catch (e) {
    setText("welcome-error", e.message);
    $("welcome-error").hidden = false;
  }
}

async function toggleMic() {
  if (state.busy) return;
  stopAudio();
  if (!state.recording) {
    try {
      await state.rec.start((rms) => { $("meter-fill").style.width = `${Math.min(100, rms * 600)}%`; }, finishRecording);
      state.recording = true;
      setMic("listening");
    } catch (_) {
      setMic("error");
      showMessage("మైక్ అనుమతి లేదు. దయచేసి టైప్ చేయండి.", "Microphone permission denied. Please type instead.");
      $("typed").hidden = false;
    }
  } else {
    await finishRecording();
  }
}

async function finishRecording() {
  if (!state.recording) return;
  state.recording = false;
  setMic("processing");
  try {
    const blob = await state.rec.stop();
    await postTurn({ audio: blob });
  } catch (_) {
    setMic("error");
  }
}

// ------------------------------------------------------------------ wiring
$("start").addEventListener("click", startSession);
$("mic").addEventListener("click", toggleMic);
$("replay").addEventListener("click", () => { if (state.lastAudioSrc) playPrompt({ audio_b64: state.lastAudioSrc.split(",")[1], mime: state.lastAudioSrc.slice(5, state.lastAudioSrc.indexOf(";")) }); });
$("yes").addEventListener("click", () => postTurn({ answer: "yes" }));
$("no").addEventListener("click", () => postTurn({ answer: "no" }));
$("back").addEventListener("click", () => postTurn({ command: "back" }));
$("skip").addEventListener("click", () => postTurn({ command: "skip" }));
$("type-toggle").addEventListener("click", () => { $("typed").hidden = !$("typed").hidden; if (!$("typed").hidden) $("typed-input").focus(); });
$("typed-send").addEventListener("click", () => { const v = $("typed-input").value; $("typed-input").value = ""; postTurn({ text: v, typed: true }); });
$("typed-input").addEventListener("keydown", (e) => { if (e.key === "Enter") $("typed-send").click(); });
$("mock-send").addEventListener("click", () => { const v = $("mock-input").value; $("mock-input").value = ""; postTurn({ hint: v }); });
$("mock-input").addEventListener("keydown", (e) => { if (e.key === "Enter") $("mock-send").click(); });
$("finish").addEventListener("click", async () => {
  try { render(await api(`/api/sessions/${state.sid}/finish`, { method: "POST" })); }
  catch (e) { setText("review-error", e.message); $("review-error").hidden = false; }
});
$("read-all").addEventListener("click", async () => {
  try { playPrompt(await api(`/api/sessions/${state.sid}/summary_audio`, { method: "POST" })); }
  catch (e) { setText("review-error", e.message); $("review-error").hidden = false; }
});
$("delete").addEventListener("click", async () => {
  try { await api(`/api/sessions/${state.sid}`, { method: "DELETE" }); } catch (_) {}
  location.reload();
});
document.addEventListener("keydown", (e) => {
  const tag = (document.activeElement || {}).tagName;
  if (e.code === "Space" && !["INPUT", "TEXTAREA", "BUTTON", "SELECT"].includes(tag) && !$("s-question").hidden) {
    e.preventDefault(); toggleMic();
  }
  if (e.key === "Escape" && state.recording) { state.recording = false; state.rec.cancel(); setMic("idle"); }
});

(async function init() {
  try {
    const [forms, health] = await Promise.all([api("/api/forms"), api("/health")]);
    state.provider = health.provider;
    const sel = $("form-select");
    for (const f of forms) {
      const o = document.createElement("option");
      o.value = f.id; o.textContent = `${f.title_te} / ${f.title_en}`;
      sel.append(o);
    }
  } catch (e) {
    setText("welcome-error", e.message); $("welcome-error").hidden = false;
  }
})();
