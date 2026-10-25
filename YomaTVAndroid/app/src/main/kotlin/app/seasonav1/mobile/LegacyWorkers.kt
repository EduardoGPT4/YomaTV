package app.seasonav1.mobile

import android.content.Context
import androidx.work.WorkerParameters

/** Persisted WorkManager jobs from 1.0.x must still resolve after an APK update. */
class DownloadWorker(context:Context,params:WorkerParameters):app.yomatv.mobile.DownloadWorker(context,params)
class SyncWorker(context:Context,params:WorkerParameters):app.yomatv.mobile.SyncWorker(context,params)
