package app.yomatv.mobile

import android.content.Intent
import android.content.res.Configuration
import android.view.ContextThemeWrapper
import android.view.Gravity
import android.view.View
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class LabelLayoutTest {
    private val instrumentation get()=InstrumentationRegistry.getInstrumentation()

    @Test fun navigationCaptionsAreCenteredAndFitNarrowScreensWithLargeText(){
        instrumentation.runOnMainSync {
            val base=instrumentation.targetContext
            for(width in listOf(320,360,412,480))for(scale in listOf(.9f,1f,1.3f,2f)){
                val configuration=Configuration(base.resources.configuration).apply{fontScale=scale}
                val context=ContextThemeWrapper(base.createConfigurationContext(configuration),R.style.Theme_Yoma)
                val bar=LinearLayout(context).apply{isBaselineAligned=false}
                listOf("catalog" to "Inicio","schedule" to "Temporada","downloads" to "Descargas","more" to "Más").forEach{(key,name)->
                    bar.addView(NavigationTab(context,key,name),LinearLayout.LayoutParams(0,-1,1f))
                }
                bar.measure(View.MeasureSpec.makeMeasureSpec(context.dp(width),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(context.dp(200),View.MeasureSpec.AT_MOST))
                bar.layout(0,0,bar.measuredWidth,bar.measuredHeight)
                for(i in 0 until bar.childCount){
                    val tab=bar.getChildAt(i)as LinearLayout;val icon=tab.getChildAt(0);val text=tab.getChildAt(1)as TextView
                    val message="${text.text}, width=$width, font=$scale"
                    assertEquals(message,Gravity.CENTER,text.gravity)
                    assertEquals(message,(icon.left+icon.right)/2f,(text.left+text.right)/2f,1f)
                    assertTrue(message,text.layout.height<=text.height-text.compoundPaddingTop-text.compoundPaddingBottom)
                    assertTrue(message,text.bottom<=tab.height-tab.paddingBottom)
                    for(line in 0 until text.lineCount)assertEquals(message,0,text.layout.getEllipsisCount(line))
                }
            }
        }
    }

    @Test fun malActionsSearchAndFormLabelsStayInsideTheirOwnBoxes(){
        val testAssets=instrumentation.context.assets
        val context=instrumentation.targetContext
        Prefs(context).apply{owner=0;paused=true}
        val theme=listOf("app.css","features.css","medianoche.css","mobile-app.css").joinToString("\n"){testAssets.open("web-layout/$it").bufferedReader().use{r->r.readText()}}
        val features=testAssets.open("web-layout/feature-ui.js").bufferedReader().use{it.readText()}
        val tile=features.substringAfter("function malTile(").substringBefore("function detailDownloadCounts")
        val app=testAssets.open("web-layout/app.js").bufferedReader().use{it.readText()}
        val search=app.substringAfter("function searchBox()").substringBefore("function dateText")
        val layout=context.assets.open("native-layout.css").bufferedReader().use{it.readText()}
        val html="""<!doctype html><html class="yoma-native" data-density="normal"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>$theme
        $layout</style></head><body><main id="main"><div id="search-fixture"></div><section class="personal-section"><div class="card-grid personal-cards" id="mal-fixture"></div></section><div class="field-pair"><div class="field"><label for="quality">Calidad y servidor preferidos</label><select class="select-input" id="quality"><option>Mejor calidad disponible</option></select></div><div class="field"><label for="notes">Una etiqueta larga de varias líneas</label><input class="form-input" id="notes" value="Texto de prueba"></div></div></main><script>
        const MAL_STATUSES={watching:'Viendo',plan_to_watch:'Por ver'};const search='';
        function e(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
        function icon(){return '<svg viewBox="0 0 24 24"><circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/></svg>';}
        function malTile($tile
        function searchBox()$search
        const image='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="140"><rect width="100" height="140" fill="#332b43"/></svg>');
        document.querySelector('#search-fixture').innerHTML=searchBox();
        document.querySelector('#mal-fixture').innerHTML=Array.from({length:8},(_,i)=>malTile({mal_id:i+1,slug:i%2?'':'synthetic',title:'Una historia con un título largo para comprobar su distribución '+i,cover:image,watched:i,num_episodes:25,score:i%2?0:8,status:i%2?'plan_to_watch':'watching'})).join('');
        window.layoutReady=true;
        </script></body></html>""".trimIndent()
        ActivityScenario.launch<MainActivity>(Intent(context,MainActivity::class.java).putExtra("qa_offline",true)).use{scenario->
            lateinit var web:WebView
            scenario.onActivity{a->web=WebView(a).apply{settings.javaScriptEnabled=true;settings.useWideViewPort=true};a.setContentView(web)}
            for(width in listOf(320,360,412,480))for(zoom in listOf(90,100,130,160)){
                val loaded=CountDownLatch(1)
                scenario.onActivity{a->
                    web.layoutParams=android.widget.FrameLayout.LayoutParams(a.dp(width),-1)
                    web.settings.textZoom=zoom
                    web.webViewClient=object:WebViewClient(){override fun onPageFinished(view:WebView,url:String){loaded.countDown()}}
                    web.loadDataWithBaseURL("https://layout.example.test/",html,"text/html","UTF-8",null)
                }
                assertTrue("Fixture did not load",loaded.await(15,TimeUnit.SECONDS));Thread.sleep(100)
                val done=CountDownLatch(1);var result=""
                scenario.onActivity{web.evaluateJavascript(CHECK_LAYOUT){value->result=value;done.countDown()}}
                assertTrue(done.await(10,TimeUnit.SECONDS))
                val checked=JSONObject(result)
                assertTrue("width=$width zoom=$zoom: $checked",checked.getJSONArray("errors").length()==0)
                assertEquals(8,checked.getInt("cards"))
            }
            scenario.onActivity{web.destroy()}
        }
    }

    companion object {
        private val CHECK_LAYOUT="""(()=>{
          const errors=[],cards=[...document.querySelectorAll('.mal-card')],box=el=>el.getBoundingClientRect();
          if(!window.layoutReady||cards.length!==8)errors.push('Fixture not ready');
          if(document.documentElement.scrollWidth>document.documentElement.clientWidth+1)errors.push('Page horizontal overflow');
          for(const [i,card]of cards.entries()){
            const r=box(card),title=card.querySelector('.mal-title'),meta=card.querySelector('.card-meta'),actions=card.querySelector('.mal-card-actions');
            for(const el of[title,meta,actions,...actions.children]){const q=box(el);if(q.left<r.left-1||q.right>r.right+1)errors.push('Card '+i+' text outside card');}
            if(box(meta).top<box(title).bottom-1||box(actions).top<box(meta).bottom-1)errors.push('Card '+i+' overlapping rows');
            let bottom=0;for(const button of actions.children){const q=box(button);if(q.top<bottom-1)errors.push('Card '+i+' overlapping actions');bottom=q.bottom;const range=document.createRange();range.selectNodeContents(button);for(const text of range.getClientRects())if(text.left<q.left-1||text.right>q.right+1||text.bottom>q.bottom+1)errors.push('Card '+i+' clipped action text');}
          }
          const search=document.querySelector('.search-box'),input=search.querySelector('input'),icon=search.querySelector('svg'),a=box(input),b=box(icon);
          if(Math.abs((a.top+a.bottom-b.top-b.bottom)/2)>1)errors.push('Search icon is not vertically centered');
          if(a.left+parseFloat(getComputedStyle(input).paddingLeft)<b.right+5)errors.push('Search text overlaps icon');
          for(const field of document.querySelectorAll('.field')){const label=field.querySelector('label'),control=field.querySelector('input,select');if(box(label).bottom>box(control).top-4)errors.push('Field label overlaps control');if(box(control).right>box(field).right+1)errors.push('Field control outside column');}
          return{errors,cards:cards.length,viewport:document.documentElement.clientWidth};
        })()""".trimIndent()
    }
}
