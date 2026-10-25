'use strict';
(() => {
  class YomaTVVideoBridge {
    constructor({ send, sourceAllowed }) {
      this.send = send;
      this.sourceAllowed = sourceAllowed;
      this.nonce = null;
      this.video = null;
      this.active = false;
      this.cleanups = [];
      this.lastState = 0;
      this.lastPointer = 0;
      this.observer = new MutationObserver(() => this.attach());
      this.observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
      });
      this.pointer = () => {
        this.revealPip();
        if (this.nonce && Date.now() - this.lastPointer > 200) {
          this.lastPointer = Date.now();
          this.emit('pointer', {});
        }
      };
      document.addEventListener('pointermove', this.pointer, { passive: true });
      document.addEventListener('pointerdown', this.pointer, { passive: true });
      this.key = (event) => this.keyboard(event);
      window.addEventListener('keydown', this.key, true);
      this.attach();
    }
    emit(type, payload) {
      if (this.nonce) this.send({ type, nonce: this.nonce, payload });
    }
    attach() {
      const video = document.querySelector(
        'video#player,video#player_html5_api,#player video.vjs-tech'
      );
      if (video === this.video) return;
      this.cleanups.forEach((fn) => fn());
      this.cleanups = [];
      this.video = video;
      if (!video) return;
      for (const type of [
        'timeupdate',
        'seeked',
        'durationchange',
        'loadedmetadata',
        'play',
        'pause',
        'ended',
        'volumechange',
        'error',
        'emptied',
        'progress',
        'ratechange',
        'enterpictureinpicture',
        'leavepictureinpicture',
      ]) {
        const fn = () => this.state(type !== 'timeupdate');
        video.addEventListener(type, fn);
        this.cleanups.push(() => video.removeEventListener(type, fn));
      }
      if (this.active) this.activate();
      this.state(true);
    }
    state(force = false) {
      if (!this.nonce) return;
      if (!force && Date.now() - this.lastState < 500) return;
      this.lastState = Date.now();
      const v = this.video;
      const ad =
        !!document.querySelector(
          '#player.vjs-ad-playing,#player.vjs-ad-loading,#player.vjs-ad-waiting,.vast-ad-active'
        ) ||
        (!!v?.currentSrc && !this.sourceAllowed(v.currentSrc));
      const valid =
        !!v &&
        !ad &&
        Number.isFinite(v.duration) &&
        v.duration > 0 &&
        v.duration <= 43200;
      this.validMedia = valid;
      if (this.pip) {
        this.pip.hidden = !valid || !this.active || !this.pipSupported();
        const floating = document.pictureInPictureElement === v;
        this.pip.setAttribute('aria-pressed', String(floating));
        this.pip.title = floating ? 'Cerrar ventana flotante' : 'Picture-in-picture · Ventana flotante';
      }
      if (valid && (v.paused || this.wasPaused)) this.revealPip();
      this.wasPaused = !v || v.paused;
      const buffered = [];
      if (valid) for (let i = 0; i < Math.min(v.buffered.length, 32); i++)
        buffered.push([v.buffered.start(i), v.buffered.end(i)]);
      this.emit('state', {
        position: valid ? v.currentTime : 0,
        duration: valid ? v.duration : 0,
        paused: !v || v.paused,
        ended: !!v?.ended,
        volume: v?.volume ?? 1,
        muted: !!v?.muted,
        videoReady: valid,
        ad,
        error: !!v?.error,
        buffered,
        playbackRate: v?.playbackRate ?? 1,
      });
    }
    activate() {
      if (!this.video) return;
      this.active = true;
      this.originalControls ??= this.video.controls;
      this.originalTabIndex ??= { value: this.video.getAttribute('tabindex') };
      this.video.setAttribute('tabindex', '0');
      this.video.controls = false;
      if (!this.style) {
        this.style = document.createElement('style');
        this.style.textContent =
          'html.seasonav1-controlled #player .vjs-control-bar{display:none!important}' +
          '.seasonav1-pip{position:fixed!important;z-index:2147483647!important;top:12px!important;right:12px!important;width:38px!important;height:34px!important;display:grid!important;place-items:center!important;background:#080d14dd!important;border:1px solid #ffffff50!important;border-radius:7px!important;color:#fff!important;cursor:pointer!important;opacity:1;transition:opacity .2s!important;padding:7px!important}' +
          '.seasonav1-pip svg{width:22px;height:18px;fill:none;stroke:currentColor;stroke-width:1.7}' +
          '.seasonav1-pip:hover,.seasonav1-pip:focus-visible{color:#b1efd9!important;outline:2px solid #b1efd9!important;outline-offset:2px!important}' +
          '.seasonav1-pip[hidden]{display:none!important}.seasonav1-pip.asleep:not(:focus-visible){opacity:0!important;pointer-events:none!important}';
        document.head.append(this.style);
      }
      document.documentElement.classList.add('seasonav1-controlled');
      if (!this.pip) {
        // Keep this button in the video's document: PiP requires a direct user gesture.
        this.pip = document.createElement('button');
        this.pip.type = 'button';
        this.pip.className = 'seasonav1-pip';
        this.pip.title = 'Picture-in-picture · Ventana flotante';
        this.pip.setAttribute('aria-label', 'Picture-in-picture, ventana flotante');
        this.pip.innerHTML = '<svg viewBox="0 0 24 20" aria-hidden="true"><rect x="1" y="1" width="22" height="18" rx="2"/><rect x="11" y="9" width="9" height="7" rx="1"/></svg>';
        this.pip.addEventListener('click', (e) => {
          e.preventDefault(); e.stopImmediatePropagation();
          this.togglePip();
        });
        this.pip.addEventListener('focus', () => this.revealPip());
        document.body.append(this.pip);
      }
      this.revealPip();
    }
    pipSupported() {
      return document.pictureInPictureEnabled === true && !!this.video && !this.video.disablePictureInPicture && typeof this.video.requestPictureInPicture === 'function';
    }
    revealPip() {
      if (!this.pip) return;
      clearTimeout(this.pipTimer);
      this.pip.classList.remove('asleep');
      if (!this.video?.paused) this.pipTimer = setTimeout(() => this.pip?.classList.add('asleep'), 2800);
    }
    async togglePip() {
      if (!this.active || !this.validMedia || !this.pipSupported()) return;
      try {
        if (document.pictureInPictureElement === this.video) await document.exitPictureInPicture();
        else await this.video.requestPictureInPicture();
        this.state(true);
      } catch {
        this.emit('error', { message: 'El navegador no permitió la ventana flotante. Inicia el video y vuelve a pulsar el icono de su esquina superior derecha.' });
      }
    }
    keyboard(event) {
      this.pointer();
      if (!this.active || !this.validMedia || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.target?.closest('input,select,textarea,button,a,[contenteditable="true"]')) return;
      const key = event.key.toLowerCase(), v = this.video;
      if (![' ','k','arrowleft','arrowright','f','m'].includes(key)) return;
      event.preventDefault(); event.stopImmediatePropagation();
      if (event.repeat && !key.startsWith('arrow')) return;
      if (key === 'f') { this.emit('key', { key: 'f' }); return; }
      const m = { nonce: this.nonce };
      if (key === ' ' || key === 'k') m.type = v.paused ? 'play' : 'pause';
      if (key === 'm') m.type = 'mute';
      if (key.startsWith('arrow')) { m.type = 'seek'; m.value = v.currentTime + (key === 'arrowleft' ? -10 : 10); }
      this.command(m);
    }
    restore() {
      document.documentElement.classList.remove('seasonav1-controlled');
      this.style?.remove();
      this.style = null;
      this.pip?.remove();
      this.pip = null;
      clearTimeout(this.pipTimer);
      if (this.video && this.originalControls !== undefined)
        this.video.controls = this.originalControls;
      this.originalControls = undefined;
      if (this.video && this.originalTabIndex) {
        if (this.originalTabIndex.value === null) this.video.removeAttribute('tabindex');
        else this.video.setAttribute('tabindex', this.originalTabIndex.value);
      }
      this.originalTabIndex = null;
      this.active = false;
    }
    async command(m) {
      if (m.type === 'connect') {
        this.restore();
        this.nonce = m.nonce;
        this.attach();
        this.emit('ready', { videoFound: !!this.video, controlsVersion: 2 });
        this.state(true);
        return;
      }
      if (m.nonce !== this.nonce) return;
      if (m.type === 'disconnect') {
        this.restore();
        this.nonce = null;
        return;
      }
      const v = this.video;
      if (!v) return;
      try {
        if (m.type === 'activate') this.activate();
        if (m.type === 'release') this.restore();
        if (m.type === 'play') await v.play();
        if (m.type === 'pause') v.pause();
        if (
          m.type === 'seek' &&
          Number.isFinite(m.value) &&
          Number.isFinite(v.duration)
        )
          v.currentTime = Math.max(0, Math.min(v.duration, m.value));
        if (m.type === 'volume' && Number.isFinite(m.value)) {
          v.volume = Math.max(0, Math.min(1, m.value));
          if (v.volume > 0) v.muted = false;
        }
        if (m.type === 'mute') v.muted = !v.muted;
        if (m.type === 'rate' && Number.isFinite(m.value) && m.value >= 0.5 && m.value <= 2) v.playbackRate = m.value;
        this.state(true);
      } catch {
        this.emit('error', {
          message:
            'Pulsa también el botón de reproducción del video si el navegador bloquea el inicio.',
        });
      }
    }
    destroy() {
      this.restore();
      this.observer.disconnect();
      this.cleanups.forEach((fn) => fn());
      for (const event of ['pointermove', 'pointerdown'])
        document.removeEventListener(event, this.pointer);
      window.removeEventListener('keydown', this.key, true);
      this.nonce = null;
    }
  }
  globalThis.YomaTVVideoBridge = YomaTVVideoBridge;
})();
