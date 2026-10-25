'use strict';
// Only isolated content scripts can use this relay; no externally_connectable access.
const NS = 'seasonav1.player/v1';
let routes = {},
  frames = {};
const loaded = chrome.storage.session.get(['routes', 'frames']).then((data) => {
  routes = data.routes || {};
  frames = data.frames || {};
});
function webURL(raw) {
  try {
    const u = new URL(raw);
    return (
      u.origin === 'https://hk-br035.gt.tc' &&
      u.pathname.startsWith('/seasonav1/')
    );
  } catch {
    return false;
  }
}
function embedURL(raw) {
  try {
    const u = new URL(raw);
    return (
      u.protocol === 'https:' &&
      !u.port &&
      !u.username &&
      ['www.mp4upload.com', 'mp4upload.com'].includes(u.hostname) &&
      /^\/embed-[a-z0-9]{5,40}\.html$/i.test(u.pathname)
    );
  } catch {
    return false;
  }
}
function validNonce(n) {
  return typeof n === 'string' && /^[a-f0-9]{32}$/.test(n);
}
async function persist() {
  await chrome.storage.session.set({ routes, frames });
}
async function toParent(tabId, data) {
  try {
    await chrome.tabs.sendMessage(
      tabId,
      { namespace: NS, ...data },
      { frameId: 0 }
    );
  } catch {}
}
async function bind(tabId, route, frame) {
  route.frameId = frame.frameId;
  route.documentId = frame.documentId;
  await persist();
  try {
    await chrome.tabs.sendMessage(
      tabId,
      { namespace: NS, type: 'connect', nonce: route.nonce },
      { frameId: frame.frameId }
    );
  } catch {
    route.frameId = null;
    await persist();
  }
}
async function relay(message, sender) {
  await loaded;
  if (
    sender.id !== chrome.runtime.id ||
    message?.namespace !== NS ||
    !Number.isInteger(sender.tab?.id)
  )
    return { ok: false };
  const tabId = sender.tab.id,
    key = String(tabId);
  if (sender.frameId === 0 && webURL(sender.url)) {
    if (!validNonce(message.nonce)) return { ok: false };
    if (message.type === 'connect') {
      if (!embedURL(message.frame_url)) return { ok: false };
      const old = routes[key];
      if (old && old.nonce !== message.nonce && old.frameId !== null) {
        try {
          await chrome.tabs.sendMessage(
            tabId,
            { namespace: NS, type: 'disconnect', nonce: old.nonce },
            { frameId: old.frameId }
          );
        } catch {}
      }
      const route = (routes[key] = {
        nonce: message.nonce,
        url: message.frame_url,
        frameId: null,
        documentId: null,
      });
      const frame = Object.values(frames[key] || {})
        .filter((f) => f.url === route.url)
        .sort((a, b) => b.created - a.created)[0];
      if (frame) await bind(tabId, route, frame);
      else await persist();
      return { ok: true, installed: true };
    }
    const route = routes[key];
    if (!route || route.nonce !== message.nonce) return { ok: false };
    if (message.type === 'disconnect') {
      if (route.frameId !== null) {
        try {
          await chrome.tabs.sendMessage(
            tabId,
            { namespace: NS, type: 'disconnect', nonce: route.nonce },
            { frameId: route.frameId }
          );
        } catch {}
      }
      delete routes[key];
      await persist();
      return { ok: true };
    }
    if (
      ![
        'activate',
        'release',
        'play',
        'pause',
        'seek',
        'volume',
        'mute',
        'rate',
      ].includes(message.type) ||
      route.frameId === null
    )
      return { ok: false };
    const value = message.value;
    if (
      ['seek', 'volume', 'rate'].includes(message.type) &&
      (typeof value !== 'number' ||
        !Number.isFinite(value) ||
        value < 0 ||
        (message.type === 'volume' && value > 1) ||
        (message.type === 'rate' && (value < 0.5 || value > 2)) ||
        value > 43200)
    )
      return { ok: false };
    try {
      await chrome.tabs.sendMessage(
        tabId,
        { namespace: NS, type: message.type, nonce: message.nonce, value },
        { frameId: route.frameId }
      );
    } catch {
      return { ok: false };
    }
    return { ok: true };
  }
  if (sender.frameId > 0 && embedURL(sender.url)) {
    if (message.type === 'hello') {
      (frames[key] ||= {})[String(sender.frameId)] = {
        frameId: sender.frameId,
        documentId: sender.documentId,
        url: sender.url,
        created: Date.now(),
      };
      const route = routes[key];
      if (route && route.url === sender.url)
        await bind(tabId, route, frames[key][String(sender.frameId)]);
      else await persist();
      return { ok: true };
    }
    const route = routes[key];
    if (
      !route ||
      route.nonce !== message.nonce ||
      route.frameId !== sender.frameId ||
      route.url !== sender.url ||
      (route.documentId && route.documentId !== sender.documentId)
    )
      return { ok: false };
    if (!['ready', 'state', 'pointer', 'error', 'key'].includes(message.type))
      return { ok: false };
    if (message.type === 'key' && message.payload?.key !== 'f') return { ok: false };
    await toParent(tabId, {
      type: message.type,
      nonce: route.nonce,
      payload: message.payload,
    });
    return { ok: true };
  }
  return { ok: false };
}
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  relay(message, sender)
    .then(reply)
    .catch(() => reply({ ok: false }));
  return true;
});
chrome.tabs.onRemoved.addListener(async (tabId) => {
  await loaded;
  delete routes[String(tabId)];
  delete frames[String(tabId)];
  await persist();
});
