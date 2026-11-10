// Bolo Form Widget Logic — embed iframe
import { Recorder } from "/recorder.js";

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(window.location.search);
const publicKey = params.get("key") || "";
const formId = params.get("form") || "farmer_scheme";
const parentOrigin = params.get("origin") || "*";

const state = {
  sid: null,
  rec: new Recorder(),
  recording: false,
  busy: false,
  provider: "mock",
  audio: null,
  lastAudioSrc: null,
  current: null,
  committedKeys: new Set(),
};

const MIC = {
  idle: ["నొక్కి చెప్పండి", "Tap to speak"],
  listening: ["వింటున్నాను…", "Listening"],
  processing: ["ఆలోచిస్తున్నాను…", "Thinking"],
  speaking: ["చెబుతున్నాను…", "Speaking"],
  error: ["మళ్ళీ ప్రయత్నించండి", "Try again"],
};

function show(id) {
  for (const s of document.querySelectorAll(".screen")) s.hidden = s.id !== id;
  window.scrollTo({ top: 0 });
}
function setText(id, t) { $(id).textContent = t == null ? "" : String(t); }

function setMic(name) {
  const m = $("mic");
  m.dataset.state = name;
  m.setAttribute("aria-pressed", String(name === "listening"));
  m.disabled = name === "processing";
  const [te, en] = MIC[name] || MIC.idle;
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
  a.play().catch(done);
}

function fillList(ul, items) {
  ul.replaceChildren();
  for (const f of items) {
    const li = document.createElement("li");
    const l = document.createElement("span"); l.className = "lbl te"; l.textContent = f.label_te;
    const v = document.createElement("span"); v.className = "val te"; v.textContent = f.value || "—";
    li.append(l, v);
    ul.append(li);
  }
}

async function api(path, opts = {}) {
  let res;
  try { res = await fetch(path, opts); }
  catch (_) { throw new Error("Server connection error"); }
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
  return data;
}

// Send field update to host parent page via postMessage
function notifyHostField(field) {
  if (!field || !field.key || field.status === "empty") return;
  const target = parentOrigin || "*";
  window.parent.postMessage({
    type: "bolo:field",
    key: field.key,
    value: field.value,
    display_company_lang: field.value_en || field.value,
    status: field.status,
  }, target);
}

function notifyHostComplete(submissionId) {
  const target = parentOrigin || "*";
  window.parent.postMessage({
    type: "bolo:complete",
    submission_id: submissionId,
  }, target);
}

function render(turn) {
  state.current = turn;
  state.sid = turn.session_id || state.sid;

  // Sync any newly committed fields to parent form
  if (turn.form) {
    for (const f of turn.form) {
      if (f.status !== "empty" && !state.committedKeys.has(f.key + ":" + f.value)) {
        state.committedKeys.add(f.key + ":" + f.value);
        notifyHostField(f);
      }
    }
  }

  if (turn.action === "review") return renderReview(turn);
  if (turn.action === "done") return renderDone(turn);

  show("s-question");
  const total = turn.progress.total, idx = Math.min(turn.progress.index + 1, total);
  setText("progress-text", `${idx} / ${total}`);
  $("progress-fill").style.width = `${(turn.progress.index / total) * 100}%`;
  if (turn.field) { setText("q-te", turn.field.prompt_te); setText("q-en", turn.field.prompt_en); }

  const plain = turn.field && turn.say_te === turn.field.prompt_te;
  const showMsg = !(plain || turn.action === "confirm");
  $("message").hidden = !showMsg;
  if (showMsg) {
    setText("msg-te", turn.say_te);
    setText("msg-en", turn.say_en);
  }

  const c = $("confirm-card");
  c.hidden = turn.action !== "confirm" || !turn.confirm;
  if (!c.hidden) {
    setText("confirm-value", turn.confirm.display);
    setText("confirm-en", turn.confirm.display_en && turn.confirm.display_en !== turn.confirm.display
      ? turn.confirm.display_en : "");
  }

  if (turn.action === "fallback") { $("typed").hidden = false; $("typed-input").focus(); }
  setText("heard", turn.heard !== undefined ? turn.heard : "");
  $("mockbox").hidden = state.provider !== "mock";
  fillList($("sofar"), turn.form.filter((f) => f.status !== "empty"));
  playPrompt(turn.prompt);
}

function renderReview(turn) {
  show("s-review");
  stopAudio();
  setMic("idle");
  const ul = $("review-list");
  ul.replaceChildren();
  for (const f of turn.form) {
    const li = document.createElement("li");
    const l = document.createElement("span"); l.className = "lbl te"; l.textContent = f.label_te;
    const v = document.createElement("span"); v.className = "val te"; v.textContent = f.value || "—";
    li.append(l, v);
    ul.append(li);
  }
  playPrompt(turn.prompt);
}

function renderDone(turn) {
  show("s-done");
  stopAudio();
  setMic("idle");
  setText("done-sub-id", turn.submission_id || state.sid);
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
    setText("msg-te", e.message);
    $("message").hidden = false;
    $("typed").hidden = false;
  }
}

async function startSession() {
  $("welcome-error").hidden = true;
  try {
    const turn = await api("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ form_id: formId, public_key: publicKey }),
    });
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
      setText("msg-te", "మైక్ అనుమతి లేదు. టైప్ చేయండి.");
      setText("msg-en", "Mic permission denied. Please type.");
      $("message").hidden = false;
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

// Wiring
$("start").addEventListener("click", startSession);
$("mic").addEventListener("click", toggleMic);
$("replay").addEventListener("click", () => {
  if (state.lastAudioSrc) playPrompt({ audio_b64: state.lastAudioSrc.split(",")[1], mime: "audio/wav" });
});
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
  try {
    const subRes = await api(`/api/sessions/${state.sid}/submit?key=${encodeURIComponent(publicKey)}`, {
      method: "POST",
    });
    notifyHostComplete(subRes.submission_id);
    render({ action: "done", submission_id: subRes.submission_id });
  } catch (e) {
    setText("review-error", e.message);
    $("review-error").hidden = false;
  }
});

// Announce ready to parent
window.parent.postMessage({ type: "bolo:ready" }, parentOrigin || "*");
