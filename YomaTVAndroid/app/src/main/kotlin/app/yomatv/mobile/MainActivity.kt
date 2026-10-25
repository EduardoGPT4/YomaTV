package app.yomatv.mobile

import android.Manifest
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ActivityInfo
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.ViewGroup
import android.webkit.*
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import androidx.work.WorkInfo
import androidx.work.WorkManager
import org.json.JSONObject

const val INK = 0xff0e0d14.toInt()
const val SURFACE = 0xff1b1925.toInt()
const val PAPER = 0xfff4eee5.toInt()
const val MUTED = 0xffb4adbf.toInt()
const val ACCENT = 0xffff6a55.toInt()
const val MINT = 0xffaee6c9.toInt()

fun android.content.Context.dp(value: Int) = (value * resources.displayMetrics.density).toInt()
fun background(color: Int, radius: Float = 18f) = GradientDrawable().apply { setColor(color); cornerRadius = radius }

class MainActivity : ComponentActivity() {
    private lateinit var web: WebView
    private lateinit var root: LinearLayout
    private lateinit var content: FrameLayout
    private lateinit var nav: LinearLayout
    private lateinit var title: TextView
    private lateinit var header: LinearLayout
    private lateinit var prefs: Prefs
    private var page = "web"
    private var activeTab = "catalog"
    private val webTabs = linkedMapOf<String, WebView>()
    private val readyTabs = mutableSetOf<String>()
    private val restoredTabs = mutableMapOf<String, Bundle>()
    private val nativeScroll = mutableMapOf<String, Int>()
    private var downloadFilter = "all"
    private var userName = ""
    private var malConnected = false
    private var group: String? = null
    private var signature = ""
    private var running = false
    private val queries = java.util.concurrent.Executors.newSingleThreadExecutor()
    private var reading = false
    private var queryStore: Store? = null
    private var pendingSync = false
    private var resumed = false
    private var webReady = false
    private var pendingAccount = false
    private val handler = Handler(Looper.getMainLooper())
    private var fullscreen: View? = null
    private var fullCallback: WebChromeClient.CustomViewCallback? = null
    private val tick = object : Runnable {
        override fun run() { if (resumed && page == "downloads") renderDownloads() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(INK) }
        root.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() or android.view.WindowInsets.Type.displayCutout())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            } else view.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, insets.systemWindowInsetBottom)
            insets
        }
        header = LinearLayout(this).apply { gravity = android.view.Gravity.CENTER_VERTICAL; setPadding(dp(18), dp(8), dp(12), dp(8)) }
        val logo = ImageView(this).apply { setImageResource(R.mipmap.ic_launcher); contentDescription = "YomaTV" }
        header.addView(logo, LinearLayout.LayoutParams(dp(38), dp(38)).apply { rightMargin = dp(12) })
        title = label("YomaTV", 24, PAPER, true)
        header.addView(title, LinearLayout.LayoutParams(0, dp(48), 1f))
        fun headerAction(kind:String,name:String,action:()->Unit){
            val item=FrameLayout(this).apply{background=outlined(SURFACE,dp(24).toFloat());contentDescription=name;isFocusable=true;isClickable=true;setOnClickListener{action()}}
            item.addView(NavGlyph(this,kind),FrameLayout.LayoutParams(dp(23),dp(23),android.view.Gravity.CENTER))
            header.addView(item,LinearLayout.LayoutParams(dp(44),dp(44)).apply{leftMargin=dp(9)})
        }
        headerAction("notifications","Notificaciones"){webRoute("notifications")}
        headerAction("account","Mi cuenta"){openWebAccount()}
        root.addView(header)
        content = FrameLayout(this)
        root.addView(content, LinearLayout.LayoutParams(-1, 0, 1f))
        nav = LinearLayout(this).apply {
            setPadding(dp(8), dp(8), dp(8), dp(8)); background = outlined(SURFACE, dp(26).toFloat())
            elevation = dp(6).toFloat()
        }
        listOf("catalog" to "Inicio", "schedule" to "Temporada", "downloads" to "Descargas", "more" to "Más").forEach { (key, name) ->
            val item=LinearLayout(this).apply {
                orientation=LinearLayout.VERTICAL;gravity=android.view.Gravity.CENTER
                contentDescription=name;isFocusable=true;isClickable=true;tag=key
                addView(NavGlyph(this@MainActivity,key),LinearLayout.LayoutParams(dp(27),dp(27)))
                addView(label(name,12).apply { setPadding(0,dp(5),0,0) })
                setOnClickListener { selectTab(key) }
            }
            nav.addView(item,LinearLayout.LayoutParams(0,dp(58),1f))
        }
        root.addView(nav,LinearLayout.LayoutParams(-1,-2).apply { setMargins(dp(10),0,dp(10),dp(4)) });setContentView(root)
        savedInstanceState?.let { saved ->
            activeTab=saved.getString("activeTab","catalog");group=saved.getString("downloadGroup")
            downloadFilter=saved.getString("downloadFilter","all")
            for(key in listOf("catalog","schedule","more"))saved.getBundle("web-$key")?.let{restoredTabs[key]=it}
            for(key in listOf("downloads","more","settings"))nativeScroll[key]=saved.getInt("scroll-$key",0)
        }
        web = webFor(if(activeTab in setOf("catalog","schedule","more"))activeTab else "catalog")
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                when { fullscreen != null -> exitFullscreen(); page == "downloads" && group != null -> { group = null; signature = ""; renderDownloads() }; page == "settings" -> show("more"); page == "more" -> selectTab("catalog"); page != "web" -> selectTab("catalog"); web.canGoBack() -> web.goBack(); else -> finish() }
            }
        })
        WorkManager.getInstance(this).getWorkInfosForUniqueWorkLiveData("downloads").observe(this) { infos ->
            running = infos.any { it.state == WorkInfo.State.RUNNING }; if (page == "downloads") { signature = ""; renderDownloads() }
        }
        selectTab(if (intent.getBooleanExtra("downloads", false)) "downloads" else activeTab)
        if (!(BuildConfig.DEBUG && intent.getBooleanExtra("qa_offline", false))) {
            Queue.start(this); Queue.sync(this)
        }
    }

    private fun webFor(key: String): WebView = webTabs.getOrPut(key) {
        val web = WebView(this)
        web.setBackgroundColor(INK)
        web.settings.apply {
            javaScriptEnabled = true; domStorageEnabled = true
            allowFileAccess = false; allowContentAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            mediaPlaybackRequiresUserGesture = true
            setSupportMultipleWindows(false)
        }
        prefs.userAgent = web.settings.userAgentString
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false)
        if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            WebViewCompat.addWebMessageListener(web, "YomaAndroid", setOf("https://hk-br035.gt.tc")) { view, message, origin, mainFrame, _ ->
                if (mainFrame && origin.scheme == "https" && origin.host == "hk-br035.gt.tc" && origin.port in setOf(-1,443) && trusted(view.url)) {
                    val data = message.data.orEmpty()
                    if (data.length <= 512 * 1024) runCatching { receive(JSONObject(data), view, key) }.onFailure { toast("No se pudo preparar la descarga. Abre de nuevo la ficha.") }
                }
            }
        } else toast("Actualiza Android System WebView para habilitar las descargas desde el catálogo.")
        web.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView, url: String, favicon: android.graphics.Bitmap?) { readyTabs.remove(key); if (isActiveBrowser(web)) webReady = false }
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (!request.isForMainFrame) return false
                val uri = request.url
                if (trusted(uri.toString()) || uri.scheme == "https" && uri.host in setOf("myanimelist.net", "www.myanimelist.net")) return false
                if (uri.scheme == "https") runCatching { startActivity(Intent(Intent.ACTION_VIEW, uri)) }
                return true
            }
            override fun onPageFinished(view: WebView, url: String) {
                if (trusted(url)) {
                    view.evaluateJavascript(assets.open("native-integration.js").bufferedReader().use { it.readText() }, null)
                    CookieManager.getInstance().flush()
                }
            }
            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                if (request.isForMainFrame) { readyTabs.remove(key); if(isActiveBrowser(web)) webReady=false; toast("Sin conexión. Tus capítulos guardados siguen disponibles."); if (prefs.owner > 0 && isActiveBrowser(web)) selectTab("downloads") }
            }
        }
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowCustomView(view: View, callback: CustomViewCallback) {
                if (fullscreen != null) { callback.onCustomViewHidden(); return }
                fullscreen = view; fullCallback = callback
                root.visibility = View.GONE
                addContentView(view, ViewGroup.LayoutParams(-1, -1))
                requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
                if (Build.VERSION.SDK_INT >= 30) window.insetsController?.hide(android.view.WindowInsets.Type.systemBars())
            }
            override fun onHideCustomView() { exitFullscreen() }
        }
        val restored=restoredTabs.remove(key)
        if(restored!=null)web.restoreState(restored)
        if(web.url==null && !(BuildConfig.DEBUG && intent.getBooleanExtra("qa_offline",false)))web.loadUrl(SITE+if(key=="schedule")"#schedule" else "#discover")
        web
    }
    private fun isActiveBrowser(candidate:WebView)=::web.isInitialized && candidate===web
    private fun rememberNativeScroll() {
        (content.getChildAt(0) as? ScrollView)?.let{nativeScroll[page]=it.scrollY}
    }
    private fun selectTab(key: String) {
        rememberNativeScroll()
        if(::web.isInitialized && page=="web")suspendWeb()
        activeTab=key
        when(key){
            "downloads"->show("downloads")
            "more"->{
                if(webTabs.containsKey("more")){web=webFor("more");webReady="more" in readyTabs;show("web")}
                else show("more")
            }
            else->{web=webFor(key);webReady=key in readyTabs;show("web")}
        }
    }
    override fun onSaveInstanceState(out: Bundle) {
        rememberNativeScroll();out.putString("activeTab",activeTab);out.putString("downloadGroup",group);out.putString("downloadFilter",downloadFilter)
        webTabs.forEach{(key,view)->out.putBundle("web-$key",Bundle().also{view.saveState(it)})}
        nativeScroll.forEach{(key,value)->out.putInt("scroll-$key",value)}
        super.onSaveInstanceState(out)
    }

    private fun trusted(url: String?): Boolean {
        val uri = runCatching { Uri.parse(url) }.getOrNull() ?: return false
        return uri.scheme == "https" && uri.host == "hk-br035.gt.tc" && uri.port == -1 && uri.userInfo == null && uri.path?.startsWith("/seasonav1/") == true
    }
    private fun exitFullscreen() {
        fullscreen?.let { (it.parent as? ViewGroup)?.removeView(it) }; fullscreen = null
        fullCallback?.onCustomViewHidden(); fullCallback = null; root.visibility = View.VISIBLE
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        if (Build.VERSION.SDK_INT >= 30) window.insetsController?.show(android.view.WindowInsets.Type.systemBars())
    }
    private fun receive(message: JSONObject, source: WebView = web, key: String = activeTab) {
        if(source!==web && message.optString("type") in setOf("auth","plan"))return
        when (message.optString("type")) {
            "auth" -> {
                readyTabs.add(key); if(source === web)webReady = true
                userName=message.optString("name");malConnected=message.optBoolean("mal")
                val owner = message.optLong("owner").coerceAtLeast(0)
                if (owner != prefs.owner) {
                    WorkManager.getInstance(this).cancelUniqueWork("downloads"); prefs.owner = owner; group = null; signature = ""
                    // Hidden tabs must not restore another account's cached library.
                    webTabs.keys.filter{it!=key}.toList().forEach { other ->
                        webTabs.remove(other)?.let{old -> (old.parent as? ViewGroup)?.removeView(old);old.destroy()}
                        readyTabs.remove(other);restoredTabs.remove(other)
                    }
                    if (page == "downloads") content.removeAllViews()
                }
                if (owner > 0) { CookieManager.getInstance().flush(); Queue.start(this); Queue.sync(this) }
                if (page == "downloads") renderDownloads()
                if (pendingAccount) { pendingAccount=false; openWebAccount() }
            }
            "plan" -> choose(message)
            "navigation" -> if(source === web) updateNav(message.optString("route"))
            "more" -> { activeTab="more";show("more") }
            "notifications" -> web.evaluateJavascript("document.querySelector('#notifications-toggle')?.click()",null)
        }
    }
    private fun choose(plan: JSONObject) {
        val owner = plan.getLong("owner")
        if (owner <= 0 || owner != prefs.owner) { toast("La cuenta cambió. Abre de nuevo el anime."); return }
        val episodes = plan.getJSONArray("episodes"); require(episodes.length() in 1..10000)
        val slug = plan.getString("slug"); val language = plan.optString("language", "SUB")
        val existing = Store(this).use { store -> store.list(owner).filter { it.state != "removed" }.associateBy { it.key } }
        val entries = (0 until episodes.length()).map { episodes.getJSONObject(it) }
            .filter { Episode.key(owner, slug, it.getString("number"), language) !in existing }
            .sortedBy { it.getString("number").toDoubleOrNull() ?: Double.MAX_VALUE }
        if (entries.isEmpty()) { toast("Estos capítulos ya están descargados o en tu cola. Ábrelos en Descargas."); show("downloads"); return }
        val checked = BooleanArray(entries.size)
        entries.indices.filter { !entries[it].optBoolean("watched") }.take(3).forEach { checked[it] = true }
        if (entries.size == 1) checked[0] = true
        val labels = entries.map { "Capítulo ${it.getString("number")}${if (it.optBoolean("watched")) " · visto" else ""}" }.toTypedArray()
        val dialog = AlertDialog.Builder(this).setTitle("${plan.getString("title")} · $language")
            .setMultiChoiceItems(labels, checked) { _, which, value -> checked[which] = value }
            .setNeutralButton("Elegir todos", null)
            .setNegativeButton("Cancelar", null)
            .setPositiveButton("Guardar", null).create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener {
                val value = !checked.all { it }; checked.indices.forEach { checked[it] = value; dialog.listView.setItemChecked(it, value) }
            }
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                if (prefs.owner != owner) { dialog.dismiss(); toast("La cuenta cambió."); return@setOnClickListener }
                val selected = entries.filterIndexed { index, _ -> checked[index] }
                if (selected.isEmpty()) { toast("Elige al menos un capítulo."); return@setOnClickListener }
                if (selected.size > 500) { toast("Prepara como máximo 500 capítulos por lote."); return@setOnClickListener }
                var added = 0
                try {
                    Store(this).use { store ->
                        val payloads = selected.map { entry ->
                            JSONObject().put("owner", owner).put("episode_id", entry.getLong("episode_id"))
                                .put("slug", slug).put("title", plan.getString("title")).put("number", entry.getString("number"))
                                .put("language", language).put("season", plan.optString("season")).put("cover",plan.optString("cover"))
                                .put("mal_account_id", plan.optLong("mal_account_id")).put("progress_revision", plan.optString("progress_revision"))
                                .put("next_episode_id", entry.optLong("next_episode_id"))
                                .put("watched", entry.optBoolean("watched"))
                        }
                        added = store.addBatch(payloads)
                    }
                    if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
                    Queue.start(this); dialog.dismiss(); selectTab("downloads"); toast("$added capítulos añadidos${if (prefs.wifiOnly) " · solo Wi-Fi" else ""}.")
                } catch (_: Exception) { toast("No se pudo guardar el lote. Comprueba los datos del anime.") }
            }
        }
        dialog.show()
    }

    private fun show(target: String) {
        rememberNativeScroll(); page = target; signature = ""
        if(target=="downloads")activeTab="downloads"
        header.visibility = if (target == "web") View.GONE else View.VISIBLE
        (web.parent as? ViewGroup)?.removeView(web)
        content.removeAllViews()
        when (target) {
            "web" -> { title.text = "YomaTV"; content.addView(web, FrameLayout.LayoutParams(-1, -1)); resumeWeb() }
            "downloads" -> { title.text = "YomaTV"; suspendWeb(); renderDownloads() }
            "more" -> { title.text = "YomaTV"; suspendWeb(); renderMore() }
            else -> { title.text = "YomaTV"; suspendWeb(); renderSettings() }
        }
        updateNav(Uri.parse(web.url.orEmpty()).fragment.orEmpty())
    }
    private fun updateNav(route: String) {
        val index=listOf("catalog","schedule","downloads","more").indexOf(activeTab)
        for(i in 0 until nav.childCount){
            val item=nav.getChildAt(i) as LinearLayout;val color=if(i==index)ACCENT else PAPER
            (item.getChildAt(0) as NavGlyph).tint=color
            (item.getChildAt(1) as TextView).setTextColor(color)
            item.isSelected=i==index
        }
    }
    private fun webRoute(route: String) {
        if(page=="web")suspendWeb()
        activeTab="more";web=webFor("more");webReady="more" in readyTabs;show("web")
        if(trusted(web.url) && webReady) web.evaluateJavascript("location.hash="+JSONObject.quote("#$route"),null) else web.loadUrl(SITE+"#$route")
        updateNav(route)
    }
    private fun moreMenu() { activeTab="more";show("more") }
    private fun renderMore() {
        val layout=container()
        layout.addView(label("Más",36,PAPER,true));layout.addView(label("Tu espacio en YomaTV",16,MUTED))
        val profile=card(layout)
        profile.addView(label(if(prefs.owner>0)"Hola, ${userName.ifBlank { "de nuevo" }}" else "Tu próxima historia empieza aquí",22,PAPER,true))
        profile.addView(button(if(prefs.owner>0)"Ver mi cuenta  →" else "Iniciar sesión  →",false){openWebAccount()})
        fun section(title:String, entries:List<Triple<String,String,String>>) {
            layout.addView(label(title,13,MUTED));val box=card(layout)
            entries.forEach{(glyph,label,route)->box.addView(button("$glyph   $label   ›",false){
                when(route){"native"->show("settings");"more"->moreMenu();else->webRoute(route)}
            },LinearLayout.LayoutParams(-1,dp(54)))}
        }
        section("TU BIBLIOTECA",listOf(Triple("♡","Mi biblioteca","library"),Triple("◷","Historial","history"),Triple("MAL","MyAnimeList${if(malConnected)" · Conectado" else ""}","mal"),Triple("☆","Favoritos","favorites"),Triple("▤","Colecciones","collections")))
        section("PREFERENCIAS",listOf(Triple("◐","Apariencia y reproducción","settings"),Triple("♧","Notificaciones","notifications"),Triple("↓","Almacenamiento y descargas","native")))
        section("EXPLORA MÁS",listOf(Triple("♫","Radio anime","radio"),Triple("▥","Estadísticas","stats"),Triple("↔","Cola para la PC","queue"),Triple("✓","Sincronización MAL","sync")))
        layout.addView(label("YomaTV Android · ${BuildConfig.VERSION_NAME}",14,MUTED))
        restoreNativeScroll("more")
    }
    private fun restoreNativeScroll(key:String) {
        (content.getChildAt(0) as? ScrollView)?.let { scroll->scroll.post{scroll.scrollTo(0,nativeScroll[key]?:0)} }
    }
    private fun openWebAccount() {
        activeTab="more";web=webFor("more");webReady="more" in readyTabs;show("web")
        if(webReady)web.evaluateJavascript("document.querySelector('#account')?.click()",null) else { pendingAccount=true;web.loadUrl(SITE) }
    }
    private fun container(): LinearLayout {
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(18), dp(12), dp(18), dp(24)) }
        val scroll = ScrollView(this).apply { isFillViewport = true; addView(layout) }
        content.removeAllViews(); content.addView(scroll)
        return layout
    }
    private fun renderDownloads() {
        if (page != "downloads" || reading || isDestroyed) return
        reading = true
        val owner = prefs.owner
        queries.execute {
            val result = runCatching {
                val store = queryStore ?: Store(applicationContext).also { queryStore = it }
                store.list(owner).filter { it.state != "removed" }
            }
            runOnUiThread {
                reading = false
                if (!isDestroyed && page == "downloads") {
                    if (owner == prefs.owner) result.onSuccess { renderDownloadRows(it) } else renderDownloads()
                }
            }
        }
    }
    private fun renderDownloadRows(jobs: List<Episode>) {
        pendingSync = jobs.any { it.pending }
        handler.removeCallbacks(tick)
        if (resumed && page == "downloads" && (running || pendingSync)) handler.postDelayed(tick, if (running) 1000 else 5000)
        val stamp = downloadFilter + jobs.joinToString { "${it.key}:${it.state}:${it.bytes}:${it.position}:${it.sync}:${it.error}" } + group + running + prefs.paused
        if (stamp == signature) return
        signature = stamp
        val scroll = (content.getChildAt(0) as? ScrollView)?.scrollY ?: (nativeScroll["downloads"]?:0)
        val layout = container()
        val count = jobs.count { it.state == "done" }
        layout.addView(label("Descargas",36,PAPER,true))
        layout.addView(label("Tus episodios, donde quieras",16,MUTED))
        val used=jobs.filter{it.state=="done"}.sumOf{it.bytes}
        val free=runCatching{android.os.StatFs((getExternalFilesDir(null)?:filesDir).absolutePath).availableBytes}.getOrDefault(0L)
        val storage=card(layout)
        storage.addView(label("${formatBytes(used)} utilizados",20,PAPER,true))
        storage.addView(label("${formatBytes(free)} disponibles · $count capítulos",14,MUTED))
        storage.addView(ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal).apply{
            max=1000;progress=(1000.0*used/(used+free).coerceAtLeast(1)).toInt();progressTintList=android.content.res.ColorStateList.valueOf(ACCENT)
        })
        storage.addView(button("Administrar almacenamiento  →",false){show("settings")})
        val filters=LinearLayout(this).apply{setPadding(0,dp(16),0,dp(8))}
        listOf("all" to "Todas","active" to "En curso","done" to "Completadas").forEach{(key,name)->
            filters.addView(button(name,downloadFilter==key){downloadFilter=key;signature="";renderDownloads()},LinearLayout.LayoutParams(0,dp(46),1f).apply{rightMargin=dp(5)})
        }
        layout.addView(filters)
        layout.addView(button(if(prefs.paused)"Continuar descargas" else "Pausar descargas",false){
            if(prefs.paused){prefs.paused=false;Queue.start(this,true)}else Queue.pause(this)
            signature="";renderDownloads()
        })
        val visible=jobs.filter{downloadFilter=="all" || if(downloadFilter=="done")it.state=="done" else it.state!="done"}
        if (prefs.owner <= 0) layout.addView(label("Inicia sesión en el catálogo. Tus descargas se guardarán separadas por cuenta.", 16))
        else if (jobs.isEmpty()) layout.addView(label("Tu próxima historia puede viajar contigo. Abre un anime en Catálogo y pulsa «Capítulos para llevar».", 18))
        else if (group == null) {
            visible.groupBy { it.slug }.forEach { (slug, rows) ->
                val card = card(layout)
                val row=LinearLayout(this).apply{gravity=android.view.Gravity.CENTER_VERTICAL}
                val art=ImageView(this).apply{setImageResource(R.mipmap.ic_launcher);scaleType=ImageView.ScaleType.CENTER_CROP;clipToOutline=true;background=outlined(SURFACE,dp(12).toFloat());contentDescription=null}
                row.addView(art,LinearLayout.LayoutParams(dp(66),dp(80)).apply{rightMargin=dp(12)})
                CoverArt.show(art,rows.first().payload.optString("cover"))
                row.addView(label(rows.first().title,21,PAPER,true),LinearLayout.LayoutParams(0,-2,1f));card.addView(row)
                card.addView(label("${rows.count { it.state == "done" }} de ${rows.size} guardados · ${rows.count { it.watched }} vistos", 15, MUTED))
                val active = rows.firstOrNull { it.state in setOf("downloading", "retry", "failed") }
                if (active != null) {
                    card.addView(label("Cap. ${active.number} · ${status(active)}",14,if(active.state=="failed")ACCENT else MUTED))
                    if(active.total>0)card.addView(ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal).apply{max=1000;progress=(1000.0*active.bytes/active.total).toInt().coerceIn(0,1000);progressTintList=android.content.res.ColorStateList.valueOf(ACCENT)})
                }
                card.addView(button("Ver capítulos  →", false) { group = slug; signature = ""; renderDownloads() })
            }
        } else {
            layout.addView(button("‹ Todos los animes", false) { group = null; signature = ""; renderDownloads() })
            val selected = visible.filter { it.slug == group }.sortedBy { it.number.toDoubleOrNull() }
            layout.addView(label(selected.firstOrNull()?.title.orEmpty(), 25, PAPER, true))
            Store(this).use { store ->
                selected.forEach { ep ->
                    val card = card(layout)
                    card.addView(label("Capítulo ${ep.number} · ${ep.language}", 18, PAPER, true))
                    card.addView(label(status(ep), 14, if (ep.state == "done") MINT else MUTED))
                    if (ep.total > 0 && ep.state != "done") card.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply { max = 1000; progress = (1000.0 * ep.bytes / ep.total).toInt().coerceIn(0,1000); progressTintList = android.content.res.ColorStateList.valueOf(ACCENT) })
                    if (ep.error.isNotBlank()) card.addView(label(ep.error, 14, ACCENT))
                    if (ep.watched) card.addView(label("✓ Visto · ${ep.sync.ifBlank { if (ep.pending) "MAL pendiente" else "guardado en este dispositivo" }}", 14, MINT))
                    val actions = LinearLayout(this)
                    actions.addView(button(if (ep.state == "done") "▶ Ver" else if (ep.state == "paused") "Continuar" else if (ep.state == "failed") "Reintentar" else "Pausar", ep.state == "done") {
                        if (ep.state == "done") {
                            if (!store.video(ep).exists() || store.video(ep).length() != ep.total) { Store(this).use { it.update(ep.key, ep.owner, "state" to "failed", "error" to "El archivo ya no está en el dispositivo.") }; signature = ""; renderDownloads() }
                            else { web.onPause(); startActivity(Intent(this, PlayerActivity::class.java).putExtra("key", ep.key).putExtra("owner", ep.owner)) }
                        } else {
                            Store(this).use { it.update(ep.key, ep.owner, "state" to if (ep.state in setOf("paused", "failed")) "queued" else "paused", "attempts" to 0, "error" to "") }
                            Queue.start(this); signature = ""; renderDownloads()
                        }
                    }, LinearLayout.LayoutParams(0, dp(48), 1f))
                    actions.addView(button("•••", false) { episodeMenu(ep) }, LinearLayout.LayoutParams(dp(56), dp(48)))
                    card.addView(actions)
                }
            }
        }
        if(jobs.isNotEmpty()&&visible.isEmpty())layout.addView(label("No hay capítulos en este filtro.",16,MUTED))
        layout.addView(Switch(this).apply{text="Descargar solo con Wi-Fi";textSize=15f;setTextColor(PAPER);minHeight=dp(56);isChecked=prefs.wifiOnly;setOnCheckedChangeListener{_,checked->prefs.wifiOnly=checked;Queue.start(this@MainActivity,true)}})
        (content.getChildAt(0) as? ScrollView)?.post { (content.getChildAt(0) as? ScrollView)?.scrollTo(0, scroll) }
    }
    private fun status(ep: Episode): String = when (ep.state) {
        "done" -> "Guardado · ${formatBytes(ep.total)}${if (ep.duration > 0) " · ${ep.duration / 60000} min" else ""}"
        "downloading" -> if (running) "${formatBytes(ep.bytes)} / ${formatBytes(ep.total)} · ${formatBytes(ep.speed.toLong())}/s" else "Esperando reanudación"
        "verifying" -> "Comprobando video e integridad…"
        "paused" -> "En pausa · ${formatBytes(ep.bytes)} conservados"
        "retry" -> "Reintentará con espera progresiva · intento ${ep.attempts}/5"
        "failed" -> "No se completó"
        else -> if (prefs.paused) "En cola · pausa global" else if (prefs.wifiOnly && !running) "En cola · espera Wi-Fi o su turno" else "En cola"
    }
    private fun episodeMenu(ep: Episode) {
        AlertDialog.Builder(this).setTitle("Capítulo ${ep.number}")
            .setItems(arrayOf("Reintentar sincronización con MAL", "Verificar archivo", "Eliminar video")) { _, which ->
                when (which) {
                    0 -> { Store(this).use { it.update(ep.key, ep.owner, "pending" to ep.watched, "sync" to "Pendiente de sincronización") }; Queue.sync(this) }
                    1 -> Thread {
                        val result = Store(this).use { store -> val file = store.video(ep); file.exists() && file.length() == ep.total && app.yomatv.engine.Integrity.mp4(file) && app.yomatv.engine.Integrity.sha256(file) == ep.hash }
                        runOnUiThread { toast(if (result) "El archivo coincide con su SHA-256." else "El archivo está ausente o cambió.") }
                    }.start()
                    2 -> AlertDialog.Builder(this).setTitle("¿Eliminar este video?").setMessage("Se conserva el historial de visto y MAL. Pausa el capítulo primero si está descargando.")
                        .setNegativeButton("Conservar", null).setPositiveButton("Eliminar") { _, _ ->
                            runCatching { Store(this).use { it.removeVideo(ep) } }.onFailure { toast(it.message.orEmpty()) }; signature = ""; renderDownloads()
                        }.show()
                }
            }.show()
    }
    private fun renderSettings() {
        val layout = container()
        layout.addView(label("Tu biblioteca, contigo", 27, PAPER, true))
        layout.addView(label("Los videos se guardan en el almacenamiento privado de YomaTV. Al desinstalar la app, Android elimina esos archivos.", 16, MUTED))
        fun toggle(text: String, value: Boolean, change: (Boolean) -> Unit) {
            layout.addView(Switch(this).apply { this.text = text; textSize = 16f; setTextColor(PAPER); minHeight = dp(60); isChecked = value; setOnCheckedChangeListener { _, checked -> change(checked) } })
        }
        toggle("Descargar solo por Wi-Fi", prefs.wifiOnly) { prefs.wifiOnly = it; Queue.start(this, true) }
        toggle("Eliminar videos vistos al cerrar el reproductor", prefs.cleanWatched) { prefs.cleanWatched = it }
        layout.addView(label("Calidad original de MP4Upload. El idioma se toma de tu selección en el reproductor o las preferencias web; nunca se sustituye silenciosamente.", 14, MUTED))
        layout.addView(label("MyAnimeList", 22, PAPER, true))
        layout.addView(label("Al llegar al 80 % de la posición se guarda el visto, incluso al adelantar. Sin internet queda pendiente. Conecta y confirma el anime en MAL antes de descargar para autorizar la sincronización.", 16, MUTED))
        layout.addView(button("Reintentar pendientes", true) { Queue.sync(this); toast("Se revisarán los pendientes de esta cuenta.") })
        layout.addView(button("Cuenta y conexión MAL", false) { openWebAccount() })
        layout.addView(label("Las descargas usan una cola secuencial, cinco intentos con espera progresiva y comprobación MP4 + SHA-256. Android puede detener tareas prolongadas; el parcial se conserva para continuar.", 14, MUTED))
        layout.addView(label("YomaTV Android · ${BuildConfig.VERSION_NAME}", 14, MUTED));restoreNativeScroll("settings")
    }
    private fun label(text: String, size: Int, color: Int = PAPER, serif: Boolean = false) = TextView(this).apply {
        this.text = text; textSize = size.toFloat(); setTextColor(color); setPadding(0, dp(8), 0, dp(8)); if (serif) typeface = Typeface.create("serif", Typeface.NORMAL)
    }
    private fun button(text: String, primary: Boolean, action: () -> Unit) = Button(this).apply {
        this.text = text; isAllCaps = false; textSize = 14f; minHeight = dp(48); minimumHeight = dp(48)
        setTextColor(if (primary) INK else PAPER); background = outlined(if (primary) ACCENT else SURFACE, dp(26).toFloat())
        setPadding(dp(12), dp(4), dp(12), dp(4)); setOnClickListener { action() }
    }
    private fun card(parent: LinearLayout): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL; setPadding(dp(16), dp(12), dp(16), dp(12)); background = outlined(SURFACE, dp(20).toFloat())
        parent.addView(this, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(14) })
    }
    private fun toast(message: String) { Toast.makeText(this, message, Toast.LENGTH_LONG).show() }
    private fun suspendWeb() { web.evaluateJavascript("window.dispatchEvent(new Event('season-native-suspend'))",null); web.onPause() }
    private fun resumeWeb() { web.onResume(); web.evaluateJavascript("window.dispatchEvent(new Event('season-native-resume'))",null) }
    override fun onResume() { super.onResume(); resumed = true; if (::web.isInitialized && page == "web") resumeWeb(); signature = ""; if (page == "downloads") renderDownloads() }
    override fun onPause() { resumed = false; handler.removeCallbacks(tick); if (::web.isInitialized) suspendWeb(); super.onPause() }
    override fun onDestroy() { handler.removeCallbacksAndMessages(null); queries.execute { queryStore?.close() }; queries.shutdown(); webTabs.values.forEach{it.destroy()}; super.onDestroy() }
}
