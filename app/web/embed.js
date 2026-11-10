// Bolo Form Embed Script — vanilla JS, no framework
// Usage: <script src="/embed.js" data-key="pk_demo_change_me" data-form="farmer_scheme" data-map='{"name":"[name=farmer_name]"}'>
(function () {
  const currentScript = document.currentScript || (function () {
    const scripts = document.getElementsByTagName("script");
    return scripts[scripts.length - 1];
  })();

  if (!currentScript) return;

  const publicKey = currentScript.getAttribute("data-key") || "";
  const formId = currentScript.getAttribute("data-form") || "farmer_scheme";
  let fieldMap = {};
  try {
    fieldMap = JSON.parse(currentScript.getAttribute("data-map") || "{}");
  } catch (_) {
    fieldMap = {};
  }

  // Inject host origin
  const scriptUrl = new URL(currentScript.src);
  const boloHost = scriptUrl.origin;

  // Insert button
  function initButton() {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "bolo-launch-btn";
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style="vertical-align:middle;margin-right:6px">
        <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V22h2v-3.08A7 7 0 0 0 19 12h-2Z"/>
      </svg>
      <span>Fill by voice / వాయిస్ ద్వారా నింపండి</span>
    `;

    // Inline button style
    btn.style.cssText = `
      display: inline-flex;
      align-items: center;
      background: #1e40af;
      color: #ffffff;
      font-family: system-ui, sans-serif;
      font-size: 15px;
      font-weight: 600;
      padding: 10px 18px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      margin: 12px 0;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      transition: background 0.15s ease;
    `;
    btn.onmouseover = () => (btn.style.background = "#1d4ed8");
    btn.onmouseout = () => (btn.style.background = "#1e40af");

    btn.addEventListener("click", openOverlay);

    // Insert before target form if found, or right after script
    const firstTarget = Object.values(fieldMap)[0];
    const targetEl = firstTarget ? document.querySelector(firstTarget) : null;
    const formEl = targetEl ? targetEl.closest("form") : null;
    if (formEl) {
      formEl.parentNode.insertBefore(btn, formEl);
    } else {
      currentScript.parentNode.insertBefore(btn, currentScript.nextSibling);
    }
  }

  // Overlay modal
  let overlay = null;
  function openOverlay() {
    if (overlay) {
      overlay.style.display = "flex";
      return;
    }

    overlay = document.createElement("div");
    overlay.className = "bolo-overlay";
    overlay.style.cssText = `
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.7);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      backdrop-filter: blur(2px);
    `;

    const container = document.createElement("div");
    container.style.cssText = `
      position: relative;
      width: 95%;
      max-width: 540px;
      height: 85vh;
      max-height: 720px;
      background: #ffffff;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
      display: flex;
      flex-direction: column;
    `;

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.innerHTML = "&times;";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.style.cssText = `
      position: absolute;
      top: 10px;
      right: 14px;
      background: transparent;
      border: none;
      font-size: 26px;
      font-weight: 400;
      color: #64748b;
      cursor: pointer;
      z-index: 10;
      line-height: 1;
    `;
    closeBtn.onclick = () => (overlay.style.display = "none");

    const iframe = document.createElement("iframe");
    iframe.src = `${boloHost}/widget?key=${encodeURIComponent(publicKey)}&form=${encodeURIComponent(formId)}&origin=${encodeURIComponent(window.location.origin)}`;
    iframe.allow = "microphone";
    iframe.style.cssText = `
      width: 100%;
      height: 100%;
      border: none;
    `;

    container.append(closeBtn, iframe);
    overlay.append(container);
    document.body.append(overlay);
  }

  // Set field value in host form
  function setFieldValue(key, val, displayCompany) {
    const sel = fieldMap[key];
    if (!sel) return;
    const el = document.querySelector(sel);
    if (!el) return;

    const valueToUse = displayCompany != null ? displayCompany : val;

    if (el.tagName === "SELECT") {
      let matched = false;
      const lower = String(val).toLowerCase().trim();
      const lowerDisplay = String(valueToUse).toLowerCase().trim();
      for (const opt of el.options) {
        const oVal = opt.value.toLowerCase().trim();
        const oText = opt.text.toLowerCase().trim();
        if (oVal === lower || oText === lower || oVal === lowerDisplay || oText === lowerDisplay) {
          el.value = opt.value;
          matched = true;
          break;
        }
      }
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } else if (el.type === "checkbox") {
      el.checked = Boolean(val === true || String(val).toLowerCase() === "true" || String(val) === "1" || String(val) === "yes" || String(val) === "అవును");
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } else if (el.type === "radio") {
      const radios = document.querySelectorAll(`[name="${el.name}"]`);
      for (const r of radios) {
        if (r.value.toLowerCase() === String(val).toLowerCase()) {
          r.checked = true;
          r.dispatchEvent(new Event("change", { bubbles: true }));
          break;
        }
      }
    } else {
      // Native input setter to trigger framework bindings (React, Vue, etc.)
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
      if (nativeSetter) {
        nativeSetter.call(el, valueToUse);
      } else {
        el.value = valueToUse;
      }
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }

    // Flash highlight
    el.style.transition = "background-color 0.4s ease";
    const oldBg = el.style.backgroundColor;
    el.style.backgroundColor = "#dcfce7"; // light green
    setTimeout(() => {
      el.style.backgroundColor = oldBg;
    }, 1500);
  }

  // Handle postMessage
  window.addEventListener("message", function (event) {
    if (event.origin !== boloHost) return;
    const data = event.data;
    if (!data || typeof data !== "object") return;

    if (data.type === "bolo:field") {
      setFieldValue(data.key, data.value, data.display_company_lang);
    } else if (data.type === "bolo:complete") {
      if (overlay) overlay.style.display = "none";
      showSuccessNotice("Form filled by Bolo Form! Please review and press Submit.");
    } else if (data.type === "bolo:cancel") {
      if (overlay) overlay.style.display = "none";
    }
  });

  function showSuccessNotice(msg) {
    const toast = document.createElement("div");
    toast.textContent = msg;
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #065f46;
      color: #ffffff;
      padding: 14px 22px;
      border-radius: 10px;
      font-family: system-ui, sans-serif;
      font-size: 15px;
      font-weight: 500;
      box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2);
      z-index: 1000000;
      transition: opacity 0.5s ease;
    `;
    document.body.append(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 500);
    }, 4500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initButton);
  } else {
    initButton();
  }
})();
