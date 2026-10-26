package app.yomatv.mobile

import android.widget.ImageView
import android.widget.TextView
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AccountAvatarTest {
    @Test fun profileImageIsRestrictedAndClearedWhenAccountChanges(){
        val photo="https://cdn.myanimelist.net/images/userimages/123.jpg?t=1"
        assertEquals(photo,AccountAvatar.picture(photo))
        for(url in listOf("http://cdn.myanimelist.net/x","https://cdn.myanimelist.net@evil.example/x","https://evil.example/x","https://cdn.myanimelist.net:8443/x","https://cdn.myanimelist.net/x#fragment","https://cdn.myanimelist.net/x\\evil"))assertEquals("",AccountAvatar.picture(url))
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        instrumentation.runOnMainSync {
            val avatar=AccountAvatar(instrumentation.targetContext){view,url->view.tag=url;view.setImageDrawable(android.graphics.drawable.ColorDrawable(0xffaabbcc.toInt()))}
            avatar.bind("Haru","");assertEquals("H",(avatar.getChildAt(0)as TextView).text.toString())
            val image=avatar.getChildAt(1)as ImageView
            image.setImageDrawable(android.graphics.drawable.ColorDrawable(0xffaabbcc.toInt()))
            image.tag="old-profile"
            // A changed/removed URL clears both the drawable and the pending image tag.
            avatar.bind("Nueva","https://cdn.myanimelist.net/images/userimages/new.jpg")
            avatar.bind("","");assertNull(image.drawable);assertNull(image.tag)
            assertEquals("S",(avatar.getChildAt(0)as TextView).text.toString())
            assertTrue(avatar.clipToOutline)
        }
    }
}
