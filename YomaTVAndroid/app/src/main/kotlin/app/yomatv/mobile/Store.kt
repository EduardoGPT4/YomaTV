package app.yomatv.mobile

import android.app.Application
import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.os.Environment
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

class YomaApp : Application() {
    override fun onCreate() { super.onCreate(); Notices.channels(this) }
}

class Prefs(context: Context) {
    private val p = context.getSharedPreferences("season-private", Context.MODE_PRIVATE)
    var owner: Long get() = p.getLong("owner", 0); set(v) { p.edit().putLong("owner", v).apply() }
    var userAgent: String get() = p.getString("agent", "").orEmpty(); set(v) { p.edit().putString("agent", v).apply() }
    var wifiOnly: Boolean get() = p.getBoolean("wifi", true); set(v) { p.edit().putBoolean("wifi", v).apply() }
    var paused: Boolean get() = p.getBoolean("paused", false); set(v) { p.edit().putBoolean("paused", v).apply() }
    var cleanWatched: Boolean get() = p.getBoolean("clean", false); set(v) { p.edit().putBoolean("clean", v).apply() }
}

data class Episode(val payload: JSONObject, val state: String, val bytes: Long, val total: Long,
                   val etag: String, val modified: String, val position: Long, val duration: Long,
                   val watched: Boolean, val pending: Boolean, val sync: String, val error: String,
                   val attempts: Int, val speed: Double, val hash: String) {
    val owner get() = payload.getLong("owner")
    val episodeId get() = payload.getLong("episode_id")
    val slug get() = payload.getString("slug")
    val title get() = payload.getString("title")
    val number get() = payload.getString("number")
    val language get() = payload.optString("language", "SUB")
    val key get() = key(owner, slug, number, language)
    companion object {
        fun key(owner: Long, slug: String, number: String, language: String): String =
            MessageDigest.getInstance("SHA-256").digest("$owner:$slug:$number:$language".toByteArray()).joinToString("") { "%02x".format(it) }
    }
}

class Store(private val context: Context) : SQLiteOpenHelper(context, "season-downloads.db", null, 1) {
    override fun onConfigure(db: SQLiteDatabase) { db.enableWriteAheadLogging() }
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE downloads(id TEXT PRIMARY KEY,owner INTEGER NOT NULL,payload TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'queued',bytes INTEGER NOT NULL DEFAULT 0,total INTEGER NOT NULL DEFAULT 0,
            etag TEXT NOT NULL DEFAULT '',modified TEXT NOT NULL DEFAULT '',position INTEGER NOT NULL DEFAULT 0,
            duration INTEGER NOT NULL DEFAULT 0,watched INTEGER NOT NULL DEFAULT 0,pending INTEGER NOT NULL DEFAULT 0,
            sync TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '',attempts INTEGER NOT NULL DEFAULT 0,
            speed REAL NOT NULL DEFAULT 0,hash TEXT NOT NULL DEFAULT '',added INTEGER NOT NULL)""")
        db.execSQL("CREATE INDEX owner_state ON downloads(owner,state,added)")
    }
    override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) = Unit
    fun add(payload: JSONObject): Boolean {
        val owner = payload.getLong("owner"); val slug = payload.getString("slug")
        val number = payload.getString("number"); val language = payload.getString("language")
        require(owner > 0 && payload.getLong("episode_id") > 0)
        require(Regex("[A-Za-z0-9_-]{1,160}").matches(slug) && Regex("\\d{1,6}(?:\\.\\d{1,3})?").matches(number))
        require(language in setOf("SUB", "LAT", "DUB") && payload.getString("title").length in 1..500)
        require(payload.toString().length < 8192)
        val key = Episode.key(owner, slug, number, language)
        val values = ContentValues().apply {
            put("id", key); put("owner", owner); put("payload", payload.toString()); put("added", System.currentTimeMillis())
            put("watched", if (payload.optBoolean("watched")) 1 else 0)
        }
        if (writableDatabase.insertWithOnConflict("downloads", null, values, SQLiteDatabase.CONFLICT_IGNORE) != -1L) return true
        val reset = ContentValues().apply {
            put("payload", payload.toString()); put("state", "queued"); put("bytes", 0); put("total", 0)
            put("etag", ""); put("modified", ""); put("hash", ""); put("attempts", 0); put("error", ""); put("speed", 0)
        }
        return writableDatabase.update("downloads", reset, "id=? AND owner=? AND state='removed'", arrayOf(key, owner.toString())) == 1
    }
    fun list(owner: Long): List<Episode> = read("owner=?", arrayOf(owner.toString()))
    fun addBatch(payloads: List<JSONObject>): Int {
        var count = 0
        writableDatabase.beginTransaction()
        try {
            for (payload in payloads) if (add(payload)) count++
            writableDatabase.setTransactionSuccessful()
        } finally { writableDatabase.endTransaction() }
        return count
    }
    fun get(id: String, owner: Long): Episode? = read("id=? AND owner=?", arrayOf(id, owner.toString())).firstOrNull()
    private fun read(where: String, values: Array<String>): List<Episode> {
        val rows = mutableListOf<Episode>()
        readableDatabase.query("downloads", null, where, values, null, null, "added,rowid").use { cursor ->
            fun s(key: String) = cursor.getString(cursor.getColumnIndexOrThrow(key))
            fun l(key: String) = cursor.getLong(cursor.getColumnIndexOrThrow(key))
            while (cursor.moveToNext()) rows.add(Episode(JSONObject(s("payload")), s("state"), l("bytes"), l("total"), s("etag"), s("modified"), l("position"), l("duration"), l("watched") == 1L, l("pending") == 1L, s("sync"), s("error"), l("attempts").toInt(), cursor.getDouble(cursor.getColumnIndexOrThrow("speed")), s("hash")))
        }
        return rows
    }
    @Synchronized fun update(key: String, owner: Long, vararg fields: Pair<String, Any>) {
        val values = ContentValues()
        for ((name, value) in fields) {
            require(name in setOf("state","bytes","total","etag","modified","position","duration","watched","pending","sync","error","attempts","speed","hash"))
            when (value) {
                is String -> values.put(name, value); is Long -> values.put(name, value); is Int -> values.put(name, value)
                is Boolean -> values.put(name, if (value) 1 else 0); is Double -> values.put(name, value)
            }
        }
        writableDatabase.update("downloads", values, "id=? AND owner=?", arrayOf(key, owner.toString()))
    }
    fun recover(owner: Long) { writableDatabase.execSQL("UPDATE downloads SET state='queued',speed=0 WHERE owner=? AND state IN ('downloading','verifying')", arrayOf(owner)) }
    fun claim(ep: Episode): Boolean = writableDatabase.update("downloads", ContentValues().apply { put("state", "downloading"); put("error", ""); put("speed", 0) },
        "id=? AND owner=? AND state IN ('queued','retry')", arrayOf(ep.key, ep.owner.toString())) == 1
    fun video(ep: Episode, partial: Boolean = false): File {
        val root = context.getExternalFilesDir(Environment.DIRECTORY_MOVIES) ?: File(context.filesDir, "videos")
        val season = ep.payload.optString("season").takeIf { Regex("(?:invierno|primavera|verano|otoño)\\d{4}").matches(it) } ?: "biblioteca"
        val number = ep.number.substringBefore('.').padStart(4, '0') + ep.number.substringAfter('.', "").let { if (it.isEmpty()) "" else ".$it" }
        val title = ep.title.replace(Regex("[<>:\"/\\\\|?*\\p{Cntrl}]"), "_").trim(' ', '.').take(90).ifBlank { ep.slug }
        val file = File(root, "${ep.owner}/$season/${ep.slug}/capitulos/$title - $number [${ep.language}].mp4${if (partial) ".part" else ""}")
        require(file.canonicalPath.startsWith(root.canonicalPath + File.separator))
        return file
    }
    fun removeVideo(ep: Episode) {
        writableDatabase.beginTransaction()
        try {
            val current = get(ep.key, ep.owner) ?: return
            if (current.state in setOf("downloading", "verifying")) error("Pausa el capítulo antes de eliminarlo.")
            for (partial in listOf(false, true)) {
                val file = video(current, partial)
                if (file.exists() && !file.delete()) error("No se pudo eliminar el archivo.")
            }
            update(ep.key, ep.owner, "state" to "removed", "bytes" to 0L, "total" to 0L, "speed" to 0.0)
            writableDatabase.setTransactionSuccessful()
        } finally { writableDatabase.endTransaction() }
    }
}
