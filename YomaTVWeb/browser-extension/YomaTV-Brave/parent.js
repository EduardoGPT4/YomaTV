'use strict';
(() => {
  if (
    window.top !== window ||
    location.origin !== 'https://hk-br035.gt.tc' ||
    !location.pathname.startsWith('/seasonav1/')
  )
    return;
  const NS = 'seasonav1.player/v1';
  let active = null;
  const reply = (type, nonce, payload) =>
    window.postMessage(
      { namespace: 'seasonav1.player.reply/v1', type, nonce, payload },
      location.origin
    );
  window.addEventListener('message', async (event) => {
    const m = event.data;
    if (
      event.source !== window ||
      event.origin !== location.origin ||
      m?.namespace !== 'seasonav1.player.command/v1' ||
      !/^[a-f0-9]{32}$/.test(m.nonce || '')
    )
      return;
    if (m.type === 'connect') {
      const frame = document.querySelector('iframe[data-season-player]');
      if (!frame || frame.src !== m.frame_url) return;
      active = m.nonce;
    } else if (m.nonce !== active) return;
    try {
      const r = await chrome.runtime.sendMessage({ ...m, namespace: NS });
      if (m.type === 'connect' && active === m.nonce && r?.installed)
        reply('installed', m.nonce, { installed: true, extensionVersion:chrome.runtime.getManifest().version });
    } catch {
      if (m.type === 'connect')
        reply('error', m.nonce, {
          message: 'Recarga la página después de instalar la extensión.',
        });
    }
    if (m.type === 'disconnect' && m.nonce === active) active = null;
  });
  chrome.runtime.onMessage.addListener((m, sender, respond) => {
    if (
      sender.id === chrome.runtime.id &&
      m?.namespace === NS &&
      m.nonce === active
    ) {
      reply(m.type, m.nonce, m.payload);
      respond({ ok: true });
    }
  });
})();
