package app.yomatv.mobile

import android.content.Intent
import android.graphics.Bitmap
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class PresentationTest {
    @Test fun nativeScreensUseOneHeaderAndFourAccessibleTabs(){
        val instrumentation=InstrumentationRegistry.getInstrumentation();val context=instrumentation.targetContext
        Prefs(context).apply{owner=900_260_002;paused=true}
        fun capture(name:String){
            instrumentation.waitForIdleSync()
            // The render thread commits the new surface after the UI queue goes idle.
            Thread.sleep(300)
            val file=File(context.getExternalFilesDir(null),"verification/yoma-$name.png");file.parentFile!!.mkdirs()
            file.outputStream().use{out->assertTrue(instrumentation.uiAutomation.takeScreenshot().compress(Bitmap.CompressFormat.PNG,100,out))}
        }
        ActivityScenario.launch<MainActivity>(Intent(context,MainActivity::class.java).putExtra("qa_offline",true).putExtra("downloads",true)).use{scenario->
            Thread.sleep(800)
            scenario.onActivity { activity->
                val field=MainActivity::class.java.getDeclaredField("nav").apply{isAccessible=true}
                val nav=field.get(activity)as android.view.ViewGroup
                assertEquals(4,nav.childCount)
                assertEquals(listOf("Inicio","Temporada","Descargas","Más"),(0 until nav.childCount).map{nav.getChildAt(it).contentDescription.toString()})
                for(i in 0 until nav.childCount)assertTrue(nav.getChildAt(i).height>=activity.dp(44))
            }
            capture("downloads")
            scenario.onActivity { activity->MainActivity::class.java.getDeclaredMethod("selectTab",String::class.java).apply{isAccessible=true}.invoke(activity,"more") }
            scenario.onActivity { activity->
                val page=MainActivity::class.java.getDeclaredField("page").apply{isAccessible=true}.get(activity)
                assertEquals("more",page)
                val nav=MainActivity::class.java.getDeclaredField("nav").apply{isAccessible=true}.get(activity)as android.view.ViewGroup
                assertTrue(nav.getChildAt(3).isSelected)
            }
            capture("more")
        }
    }
}
