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
        lateinit var screen:android.view.View
        fun capture(name:String){
            instrumentation.waitForIdleSync()
            val file=File(context.getExternalFilesDir(null),"verification/yoma-$name.png");file.parentFile!!.mkdirs()
            // Render the actual app view; emulator System UI overlays are unrelated to this layout.
            instrumentation.runOnMainSync {
                val bitmap=Bitmap.createBitmap(screen.width,screen.height,Bitmap.Config.ARGB_8888)
                screen.draw(android.graphics.Canvas(bitmap))
                file.outputStream().use{out->assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG,100,out))}
                bitmap.recycle()
            }
        }
        fun readable(view:android.view.View){
            if(view is android.widget.TextView&&view.layout!=null&&view.height>0){
                assertTrue("Clipped label: ${view.text}",view.layout.height<=view.height-view.compoundPaddingTop-view.compoundPaddingBottom+1)
            }
            if(view is android.view.ViewGroup)for(i in 0 until view.childCount)readable(view.getChildAt(i))
        }
        ActivityScenario.launch<MainActivity>(Intent(context,MainActivity::class.java).putExtra("qa_offline",true).putExtra("downloads",true)).use{scenario->
            Thread.sleep(800)
            scenario.onActivity { activity->
                screen=MainActivity::class.java.getDeclaredField("root").apply{isAccessible=true}.get(activity)as android.view.View
                val field=MainActivity::class.java.getDeclaredField("nav").apply{isAccessible=true}
                val nav=field.get(activity)as android.view.ViewGroup
                assertEquals(4,nav.childCount)
                assertEquals(listOf("Inicio","Temporada","Descargas","Más"),(0 until nav.childCount).map{nav.getChildAt(it).contentDescription.toString()})
                for(i in 0 until nav.childCount)assertTrue(nav.getChildAt(i).height>=activity.dp(44))
                readable(nav)
            }
            capture("downloads")
            scenario.onActivity { activity->MainActivity::class.java.getDeclaredMethod("selectTab",String::class.java).apply{isAccessible=true}.invoke(activity,"more") }
            scenario.onActivity { activity->
                val page=MainActivity::class.java.getDeclaredField("page").apply{isAccessible=true}.get(activity)
                assertEquals("more",page)
                val nav=MainActivity::class.java.getDeclaredField("nav").apply{isAccessible=true}.get(activity)as android.view.ViewGroup
                assertTrue(nav.getChildAt(3).isSelected)
                val content=MainActivity::class.java.getDeclaredField("content").apply{isAccessible=true}.get(activity)as android.view.ViewGroup
                for(key in listOf("library","settings","radio")){
                    val section=content.findViewWithTag<android.widget.LinearLayout>("more-section-$key")
                    val heading=section.findViewWithTag<android.widget.TextView>("more-section-heading-$key")
                    val card=section.findViewWithTag<android.view.ViewGroup>("more-section-card-$key")
                    val parent=section.parent as android.view.ViewGroup
                    val previous=parent.getChildAt(parent.indexOfChild(section)-1)
                    val above=section.top+heading.top-previous.bottom
                    val below=card.top-heading.bottom
                    assertTrue("Heading must belong to its following card: $key",above>below)
                    assertTrue("Heading needs separation from the previous card: $key",above>=activity.dp(24))
                    assertTrue("Heading must stay close to its own card: $key",below in activity.dp(6)..activity.dp(10))
                    assertEquals("Card and heading share their section",section,card.parent)
                }
                for(route in listOf("library","history","mal","favorites","collections","settings","notifications","native","radio","stats","queue","sync")){
                    val row=content.findViewWithTag<android.view.ViewGroup>("more-entry-$route")
                    assertNotNull("Missing menu action: $route",row)
                    assertTrue(row.getChildAt(0)is NavGlyph)
                    assertTrue(row.getChildAt(2)is NavGlyph)
                    assertTrue(row.height>=activity.dp(44))
                    assertEquals(row.contentDescription.toString(),(row.getChildAt(1)as android.widget.TextView).text.toString())
                }
                readable(content)
            }
            capture("more")
            scenario.onActivity{activity->
                val content=MainActivity::class.java.getDeclaredField("content").apply{isAccessible=true}.get(activity)as android.view.ViewGroup
                val scroll=content.getChildAt(0)as android.widget.ScrollView
                scroll.scrollTo(0,scroll.getChildAt(0).height)
            }
            capture("more-bottom")
            scenario.onActivity{activity->MainActivity::class.java.getDeclaredMethod("show",String::class.java).apply{isAccessible=true}.invoke(activity,"settings")}
            scenario.onActivity{activity->readable(MainActivity::class.java.getDeclaredField("content").apply{isAccessible=true}.get(activity)as android.view.View)}
            capture("settings")
        }
    }
}
