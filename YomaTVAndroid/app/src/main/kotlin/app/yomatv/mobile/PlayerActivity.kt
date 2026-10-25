package app.yomatv.mobile

import android.app.AlertDialog
import android.app.PictureInPictureParams
import android.content.pm.ActivityInfo
import android.content.res.Configuration
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Rational
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView

@androidx.annotation.OptIn(markerClass = [UnstableApi::class])
class PlayerActivity : ComponentActivity() {
    private lateinit var store: Store
    private lateinit var episode: Episode
    private lateinit var root: FrameLayout
    private lateinit var view: PlayerView
    private lateinit var toast: TextView
    private lateinit var actions: LinearLayout
    private lateinit var caption: TextView
    private var player: ExoPlayer? = null
    private var alreadyWatched = false
    private var notifiedSync = false
    private var lastSave = 0L
    private var nextTask: Runnable? = null
    private var nextTicks = 8
    private val handler = Handler(Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            save(false)
            val current = store.get(episode.key, episode.owner)
            if (current?.sync == "Actualizado en MyAnimeList" && !notifiedSync) {
                notifiedSync = true; slide("Capítulo ${episode.number} actualizado en MyAnimeList")
            }
            handler.postDelayed(this, 1000)
        }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = Store(this)
        val owner = intent.getLongExtra("owner", 0)
        val found = store.get(intent.getStringExtra("key").orEmpty(), owner)
        if (owner != Prefs(this).owner || found == null || found.state != "done" || !store.video(found).exists() || store.video(found).length() != found.total) {
            Toast.makeText(this, "El capítulo no está disponible para esta cuenta.", Toast.LENGTH_LONG).show(); finish(); return
        }
        episode = found; alreadyWatched = found.watched; notifiedSync = found.sync == "Actualizado en MyAnimeList"
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        root = FrameLayout(this).apply { setBackgroundColor(INK) }
        view = PlayerView(this).apply { useController = true; controllerShowTimeoutMs = 2500; setShowNextButton(false); setShowPreviousButton(false) }
        root.addView(view, FrameLayout.LayoutParams(-1, -1))
        actions = LinearLayout(this).apply { setPadding(dp(10), dp(4), dp(10), dp(4)); gravity = Gravity.CENTER_VERTICAL; background = background(0xdc0e0d14.toInt(), dp(16).toFloat()) }
        actions.addView(control("‹", "Cerrar reproductor") { finish() })
        caption = TextView(this).apply { text = "${episode.title} · ${episode.number}"; textSize = 16f; setTextColor(PAPER); includeFontPadding=false;gravity=Gravity.CENTER_VERTICAL;maxLines = 1; ellipsize = android.text.TextUtils.TruncateAt.END }
        actions.addView(caption, LinearLayout.LayoutParams(0,-2,1f))
        actions.addView(control("+85 s", "Saltar intro 85 segundos") { player?.let { it.seekTo((it.currentPosition + 85_000).coerceAtMost(it.duration.coerceAtLeast(0))); save(true) } })
        actions.addView(control("1×", "Velocidad de reproducción") { speed() })
        actions.addView(control("▣", "Picture in picture") {
            runCatching { enterPictureInPictureMode(PictureInPictureParams.Builder().setAspectRatio(Rational(16,9)).build()) }
                .onFailure { slide("Este dispositivo no permite picture-in-picture.") }
        })
        actions.minimumHeight=dp(56)
        root.addView(actions, FrameLayout.LayoutParams(-1, -2, Gravity.TOP).apply { setMargins(dp(8),dp(8),dp(8),0) })
        toast = TextView(this).apply {
            textSize = 15f; setTextColor(PAPER); includeFontPadding=false;gravity=Gravity.CENTER;setLineSpacing(0f,1.15f);setPadding(dp(18), dp(12), dp(18), dp(12)); background = background(SURFACE, dp(24).toFloat()); visibility = View.GONE
        }
        root.addView(toast, FrameLayout.LayoutParams(-2, -2, Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply { bottomMargin = dp(92); leftMargin = dp(18); rightMargin = dp(18) })
        view.setControllerVisibilityListener(PlayerView.ControllerVisibilityListener { visibility -> if (!isInPictureInPictureMode) actions.visibility = visibility })
        root.setOnApplyWindowInsetsListener { _, insets ->
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                val cutout = insets.getInsets(android.view.WindowInsets.Type.displayCutout())
                root.setPadding(cutout.left, cutout.top, cutout.right, cutout.bottom)
                window.insetsController?.hide(android.view.WindowInsets.Type.systemBars())
                window.insetsController?.systemBarsBehavior = android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
            insets
        }
        setContentView(root)
    }
    private fun control(text: String, description: String, action: () -> Unit) = Button(this).apply {
        this.text = text; contentDescription = description; isAllCaps = false; textSize = 14f; setTextColor(PAPER)
        includeFontPadding=false;gravity=Gravity.CENTER;setPadding(dp(10),dp(6),dp(10),dp(6))
        background = background(SURFACE, dp(12).toFloat()); minWidth = dp(48); minimumWidth = dp(48); minHeight = dp(48); minimumHeight = dp(48)
        setOnClickListener { action() }
    }
    private fun createPlayer() {
        if (!::episode.isInitialized || player != null) return
        if (Prefs(this).owner != episode.owner) { finish(); return }
        val current = store.get(episode.key, episode.owner) ?: return
        val file = store.video(current)
        val exo = ExoPlayer.Builder(this).setSeekBackIncrementMs(10_000).setSeekForwardIncrementMs(10_000).build()
        player = exo; view.player = exo
        exo.addListener(object : Player.Listener {
            override fun onPositionDiscontinuity(oldPosition: Player.PositionInfo, newPosition: Player.PositionInfo, reason: Int) { save(true) }
            override fun onIsPlayingChanged(isPlaying: Boolean) { if (!isPlaying) save(true) }
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) { save(true); scheduleNext() }
            }
            override fun onPlayerError(error: androidx.media3.common.PlaybackException) { slide("No se pudo reproducir el archivo. Usa «Verificar archivo» en Descargas.") }
        })
        exo.setMediaItem(MediaItem.fromUri(android.net.Uri.fromFile(file)))
        exo.seekTo(current.position.coerceAtLeast(0)); exo.prepare(); exo.playWhenReady = true
    }
    private fun save(force: Boolean) {
        val p = player ?: return
        if (Prefs(this).owner != episode.owner) { p.pause(); finish(); return }
        val duration = p.duration
        if (duration == C.TIME_UNSET || duration <= 0) return
        val position = p.currentPosition.coerceIn(0,duration)
        val threshold = !alreadyWatched && position.toDouble() / duration >= .8
        if (force || threshold || System.currentTimeMillis() - lastSave >= 10_000) {
            store.update(episode.key, episode.owner, "position" to position, "duration" to duration)
            lastSave = System.currentTimeMillis()
        }
        if (threshold) {
            alreadyWatched = true
            store.update(episode.key, episode.owner, "watched" to true, "pending" to true, "sync" to "Pendiente de MyAnimeList")
            Queue.sync(this); slide("Capítulo ${episode.number} visto · sincronizando con MAL")
        }
    }
    private fun speed() {
        val values = floatArrayOf(.5f,.75f,1f,1.25f,1.5f,1.75f,2f)
        AlertDialog.Builder(this).setTitle("Velocidad").setItems(values.map { "$it×" }.toTypedArray()) { _, which -> player?.setPlaybackSpeed(values[which]) }.show()
    }
    private fun slide(message: String) {
        toast.animate().cancel(); toast.text = message; toast.visibility = View.VISIBLE; toast.alpha = 0f; toast.translationY = dp(18).toFloat()
        toast.animate().translationY(0f).alpha(1f).setDuration(220).withEndAction {
            toast.postDelayed({ toast.animate().alpha(0f).translationY(dp(12).toFloat()).setDuration(180).withEndAction { toast.visibility = View.GONE }.start() }, 4500)
        }.start()
    }
    private fun scheduleNext() {
        if (nextTask != null) return
        val nextId = episode.payload.optLong("next_episode_id")
        val next = store.list(episode.owner).firstOrNull { it.episodeId == nextId && it.language == episode.language && it.state == "done" && store.video(it).exists() }
        if (next == null) { slide("Terminaste. El siguiente capítulo todavía no está guardado."); return }
        nextTicks = 8
        toast.setOnClickListener { nextTask?.let { handler.removeCallbacks(it) }; nextTask = null; toast.setOnClickListener(null); slide("Siguiente automático cancelado") }
        val task = object : Runnable {
            override fun run() {
                if (isFinishing || Prefs(this@PlayerActivity).owner != episode.owner) return
                if (nextTicks <= 0) {
                    nextTask = null; releasePlayer(); cleanupWatched(); episode = next; alreadyWatched = next.watched; notifiedSync = next.sync == "Actualizado en MyAnimeList"
                    caption.text = "${episode.title} · ${episode.number}"; toast.setOnClickListener(null); createPlayer(); slide("Capítulo ${next.number}"); return
                }
                toast.text = "Capítulo ${next.number} en ${nextTicks--} s · toca para cancelar"; toast.visibility = View.VISIBLE; toast.alpha = 1f; toast.translationY = 0f
                handler.postDelayed(this, 1000)
            }
        }
        nextTask = task; handler.post(task)
    }
    private fun releasePlayer() { save(true); view.player = null; player?.release(); player = null }
    private fun cleanupWatched() {
        if (Prefs(this).cleanWatched && alreadyWatched) runCatching { store.get(episode.key, episode.owner)?.let { store.removeVideo(it) } }
    }
    override fun onStart() { super.onStart(); if (::episode.isInitialized) { createPlayer(); handler.post(tick) } }
    override fun onPictureInPictureModeChanged(inPictureInPictureMode: Boolean, newConfig: Configuration) {
        super.onPictureInPictureModeChanged(inPictureInPictureMode,newConfig)
        actions.visibility = if (inPictureInPictureMode) View.GONE else View.VISIBLE; view.useController = !inPictureInPictureMode
    }
    override fun onStop() {
        if (::episode.isInitialized && !isInPictureInPictureMode) { nextTask?.let { handler.removeCallbacks(it) }; nextTask = null; handler.removeCallbacks(tick); releasePlayer() }
        super.onStop()
    }
    override fun onDestroy() {
        if (::episode.isInitialized) { releasePlayer(); cleanupWatched() }
        handler.removeCallbacksAndMessages(null); store.close(); super.onDestroy()
    }
}
