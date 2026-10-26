package app.yomatv.mobile

import android.content.Intent
import android.webkit.WebView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class NavigationTest {
    private val instrumentation get()=InstrumentationRegistry.getInstrumentation()
    private fun select(activity:MainActivity,key:String){MainActivity::class.java.getDeclaredMethod("selectTab",String::class.java).apply{isAccessible=true}.invoke(activity,key)}
    private fun browser(activity:MainActivity):WebView=MainActivity::class.java.getDeclaredField("web").apply{isAccessible=true}.get(activity) as WebView
    private fun value(scenario:ActivityScenario<MainActivity>,script:String):String{
        val latch=CountDownLatch(1);var result=""
        scenario.onActivity{browser(it).evaluateJavascript(script){s->result=s;latch.countDown()}}
        assertTrue(latch.await(10,TimeUnit.SECONDS));return result
    }
    @Test fun tabsPreserveChapterDomFiltersHistoryAndScroll(){
        val intent=Intent(instrumentation.targetContext,MainActivity::class.java).putExtra("qa_offline",true)
        ActivityScenario.launch<MainActivity>(intent).use { scenario->
            lateinit var home:WebView;lateinit var season:WebView
            scenario.onActivity{a->home=browser(a);home.loadDataWithBaseURL(SITE,"<html><body style='height:6000px'><input id='search' value='capítulo abierto'><div id='chapter'>Capítulo 9</div></body></html>","text/html","UTF-8",SITE)}
            Thread.sleep(1000)
            value(scenario,"location.hash='watch/99';window.testToken='chapter9';document.querySelector('#search').value='mi búsqueda';window.scrollTo(0,450);true")
            Thread.sleep(250)
            scenario.onActivity{a->select(a,"schedule");season=browser(a);assertNotSame(home,season);season.loadDataWithBaseURL(SITE,"<html><body style='height:6000px'><input id='day' value='miércoles'></body></html>","text/html","UTF-8",SITE)}
            Thread.sleep(800)
            value(scenario,"location.hash='schedule';window.testToken='schedule-filter';window.scrollTo(0,300);true")
            scenario.onActivity{a->select(a,"downloads");select(a,"more");select(a,"catalog");assertSame(home,browser(a))}
            assertEquals("\"chapter9\"",value(scenario,"window.testToken"));assertEquals("\"#watch/99\"",value(scenario,"location.hash"));assertEquals("\"mi búsqueda\"",value(scenario,"document.querySelector('#search').value"))
            assertTrue(value(scenario,"window.scrollY").toDouble()>300)
            scenario.onActivity{a->select(a,"schedule");assertSame(season,browser(a))}
            assertEquals("\"schedule-filter\"",value(scenario,"window.testToken"));assertEquals("\"miércoles\"",value(scenario,"document.querySelector('#day').value"));assertTrue(value(scenario,"window.scrollY").toDouble()>200)
        }
    }
    @Test fun oldQueuedWorkerClassesStillResolve(){
        assertTrue(androidx.work.Worker::class.java.isAssignableFrom(Class.forName("app.seasonav1.mobile.DownloadWorker")))
        assertTrue(androidx.work.Worker::class.java.isAssignableFrom(Class.forName("app.seasonav1.mobile.SyncWorker")))
    }
    @Test fun accountNeverReplacesTheMoreMenuOrTheOpenChapter(){
        ActivityScenario.launch<MainActivity>(Intent(instrumentation.targetContext,MainActivity::class.java).putExtra("qa_offline",true)).use{scenario->
            lateinit var home:WebView
            scenario.onActivity{a->home=browser(a);home.loadDataWithBaseURL(SITE,"<html><body style='height:5000px'><p>Capítulo abierto</p></body></html>","text/html","UTF-8",SITE)}
            Thread.sleep(700);value(scenario,"location.hash='watch/99';window.keptChapter='original';window.scrollTo(0,400);true")
            scenario.onActivity{a->MainActivity::class.java.getDeclaredMethod("openWebAccount").apply{isAccessible=true}.invoke(a);assertNotSame(home,browser(a))}
            scenario.onActivity{a->
                select(a,"more")
                assertEquals("more",MainActivity::class.java.getDeclaredField("page").apply{isAccessible=true}.get(a))
                val content=MainActivity::class.java.getDeclaredField("content").apply{isAccessible=true}.get(a)as android.view.ViewGroup
                assertNotNull(content.findViewWithTag<android.view.View>("more-entry-library"))
                select(a,"catalog");assertSame(home,browser(a))
            }
            assertEquals("\"original\"",value(scenario,"window.keptChapter"));assertEquals("\"#watch/99\"",value(scenario,"location.hash"))
            scenario.onActivity{a->
                MainActivity::class.java.getDeclaredMethod("openWebAccount").apply{isAccessible=true}.invoke(a)
                MainActivity::class.java.getDeclaredMethod("closeWebAccount").apply{isAccessible=true}.invoke(a)
                assertSame(home,browser(a))
            }
            assertTrue(value(scenario,"window.scrollY").toDouble()>200)
        }
    }
}
