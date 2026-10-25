'use strict';
(() => {
  if (window.top === window) return;
  try {
    if (
      document.referrer &&
      new URL(document.referrer).origin !== 'https://hk-br035.gt.tc'
    )
      return;
  } catch {
    return;
  }
  const NS = 'seasonav1.player/v1';
  const bridge = new YomaTVVideoBridge({
    send: (message) =>
      chrome.runtime.sendMessage({ namespace: NS, ...message, ...(message.type==='ready'?{payload:{...message.payload,extensionVersion:chrome.runtime.getManifest().version}}:{}) }).catch(() => {}),
    sourceAllowed: (raw) => {
      try {
        const u = new URL(raw);
        return (
          u.protocol === 'https:' &&
          /^(?:[a-z0-9-]+\.)?mp4upload\.com$/i.test(u.hostname)
        );
      } catch {
        return false;
      }
    },
  });
  chrome.runtime.onMessage.addListener((m, sender, respond) => {
    if (
      sender.id !== chrome.runtime.id ||
      m?.namespace !== NS ||
      !/^[a-f0-9]{32}$/.test(m.nonce || '')
    )
      return;
    bridge
      .command(m)
      .then(() => respond({ ok: true }))
      .catch(() => respond({ ok: false }));
    return true;
  });
  chrome.runtime.sendMessage({ namespace: NS, type: 'hello' }).catch(() => {});
})();
