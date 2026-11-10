// Records the mic and returns a 16 kHz mono 16-bit WAV Blob (no ffmpeg needed on the server).
// Uses ScriptProcessorNode: deprecated but works in all current browsers and keeps this file simple.
export class Recorder {
  constructor() { this.active = false; }

  async start(onLevel, onSilence) {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
    });
    const AC = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AC();
    this.src = this.ctx.createMediaStreamSource(this.stream);
    this.proc = this.ctx.createScriptProcessor(4096, 1, 1);
    this.chunks = [];
    this.heardSpeech = false;
    this.startedAt = this.lastVoice = performance.now();
    this.fired = false;
    this.active = true;
    this.proc.onaudioprocess = (e) => {
      if (!this.active) return;
      const d = e.inputBuffer.getChannelData(0);
      this.chunks.push(new Float32Array(d));
      let sum = 0;
      for (let i = 0; i < d.length; i++) sum += d[i] * d[i];
      const rms = Math.sqrt(sum / d.length);
      const now = performance.now();
      if (onLevel) onLevel(rms);
      if (rms > 0.02) { this.heardSpeech = true; this.lastVoice = now; }
      const silentTooLong = this.heardSpeech && now - this.lastVoice > 1500;
      const tooLong = now - this.startedAt > 12000;
      if ((silentTooLong || tooLong) && !this.fired) { this.fired = true; if (onSilence) onSilence(); }
    };
    this.src.connect(this.proc);
    this.proc.connect(this.ctx.destination);
  }

  async stop() {
    this.active = false;
    const inRate = this.ctx.sampleRate;
    try { this.proc.disconnect(); this.src.disconnect(); } catch (_) {}
    this.stream.getTracks().forEach((t) => t.stop());
    await this.ctx.close();
    let total = 0;
    for (const c of this.chunks) total += c.length;
    const all = new Float32Array(total);
    let off = 0;
    for (const c of this.chunks) { all.set(c, off); off += c.length; }
    return encodeWav(downsample(all, inRate, 16000), 16000);
  }

  cancel() { if (this.active) this.stop().catch(() => {}); }
}

function downsample(x, inRate, outRate) {
  if (inRate === outRate) return x;
  const ratio = inRate / outRate;
  const n = Math.floor(x.length / ratio);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {                     // box filter: average the samples in each window
    const a = Math.floor(i * ratio), b = Math.min(x.length, Math.floor((i + 1) * ratio));
    let s = 0;
    for (let j = a; j < b; j++) s += x[j];
    out[i] = s / Math.max(1, b - a);
  }
  return out;
}

function encodeWav(samples, rate) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
  v.setUint16(34, 16, true); w(36, "data"); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}
