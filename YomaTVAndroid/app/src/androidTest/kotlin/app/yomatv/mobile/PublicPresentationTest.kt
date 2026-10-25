package app.yomatv.mobile

import android.content.Intent
import android.graphics.Bitmap
import android.webkit.WebView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Anonymous catalog/weekly schedule only. Does not queue files or write MAL. */
@RunWith(AndroidJUnit4::class)
class PublicPresentationTest {
    @Test fun publishedMobileHomeAndScheduleHaveOneNavigation(){
        org.junit.Assume.assumeTrue("Opt-in public UI check",InstrumentationRegistry.getArguments().getString("public_ui")=="true")
        val instrumentation=InstrumentationRegistry.getInstrumentation();val context=instrumentation.targetContext
        Prefs(context).apply{owner=0;paused=true}
        fun browser(a:MainActivity)=MainActivity::class.java.getDeclaredField("web").apply{isAccessible=true}.get(a)as WebView
        fun ready(scenario:ActivityScenario<MainActivity>,selector:String){
            val deadline=System.currentTimeMillis()+120000;var okay=false
            while(System.currentTimeMillis()<deadline&&!okay){
                val latch=CountDownLatch(1)
                scenario.onActivity{a->browser(a).evaluateJavascript("Boolean(document.documentElement.classList.contains('yoma-native')&&document.querySelector('$selector')&&getComputedStyle(document.querySelector('.mobile-navigation')).display==='none'&&('$selector'!=='.yoma-featured'||document.querySelector('.yoma-featured>img')?.naturalWidth>0))"){value->okay=value=="true";latch.countDown()}}
                latch.await(3,TimeUnit.SECONDS);if(!okay)Thread.sleep(300)
            }
            assertTrue("Published mobile UI did not load: $selector",okay)
        }
        fun capture(name:String){
            instrumentation.waitForIdleSync();Thread.sleep(1500)
            val file=File(context.getExternalFilesDir(null),"verification/yoma-public-$name.png");file.parentFile!!.mkdirs()
            file.outputStream().use{instrumentation.uiAutomation.takeScreenshot().compress(Bitmap.CompressFormat.PNG,100,it)}
        }
        ActivityScenario.launch<MainActivity>(Intent(context,MainActivity::class.java)).use{scenario->
            ready(scenario,".yoma-featured");lateinit var home:WebView
            scenario.onActivity{a->home=browser(a);assertEquals(android.view.View.GONE,(MainActivity::class.java.getDeclaredField("header").apply{isAccessible=true}.get(a)as android.view.View).visibility)}
            capture("home")
            scenario.onActivity{a->MainActivity::class.java.getDeclaredMethod("selectTab",String::class.java).apply{isAccessible=true}.invoke(a,"schedule")}
            ready(scenario,".yoma-season");capture("schedule")
            scenario.onActivity{a->MainActivity::class.java.getDeclaredMethod("selectTab",String::class.java).apply{isAccessible=true}.invoke(a,"catalog");assertSame(home,browser(a))}
            ready(scenario,".yoma-featured")
        }
    }
}
