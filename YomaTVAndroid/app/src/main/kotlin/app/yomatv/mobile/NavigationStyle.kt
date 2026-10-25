package app.yomatv.mobile

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.drawable.GradientDrawable
import android.view.View

fun outlined(color: Int, radius: Float) = GradientDrawable().apply {
    setColor(color); cornerRadius=radius; setStroke(1,0xff393449.toInt())
}

/** Small vector icons keep the bottom navigation sharp at every display density. */
class NavGlyph(context: Context, private val kind: String): View(context) {
    var tint: Int = PAPER
        set(value){field=value;invalidate()}
    private val pen=Paint(Paint.ANTI_ALIAS_FLAG).apply {style=Paint.Style.STROKE;strokeWidth=1.6f;strokeCap=Paint.Cap.ROUND;strokeJoin=Paint.Join.ROUND}
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas);canvas.save();canvas.scale(width/24f,height/24f);pen.color=tint
        val path=Path()
        when(kind){
            "notifications"->{path.moveTo(5f,17f);path.lineTo(7f,14f);path.lineTo(7f,9f);path.cubicTo(7f,2f,17f,2f,17f,9f);path.lineTo(17f,14f);path.lineTo(19f,17f);path.close();canvas.drawPath(path,pen);canvas.drawLine(10f,21f,14f,21f,pen)}
            "account"->{canvas.drawCircle(12f,8f,3f,pen);path.moveTo(5f,21f);path.cubicTo(5f,12f,19f,12f,19f,21f);canvas.drawPath(path,pen)}
            "catalog"->{path.moveTo(3f,10f);path.lineTo(12f,3f);path.lineTo(21f,10f);path.lineTo(21f,21f);path.lineTo(15f,21f);path.lineTo(15f,14f);path.lineTo(9f,14f);path.lineTo(9f,21f);path.lineTo(3f,21f);path.close();canvas.drawPath(path,pen)}
            "schedule"->{canvas.drawRoundRect(3f,5f,21f,21f,2f,2f,pen);canvas.drawLine(3f,10f,21f,10f,pen);canvas.drawLine(8f,3f,8f,7f,pen);canvas.drawLine(16f,3f,16f,7f,pen)}
            "downloads"->{path.moveTo(12f,3f);path.lineTo(12f,16f);path.moveTo(7f,11f);path.lineTo(12f,16f);path.lineTo(17f,11f);path.moveTo(3f,16f);path.lineTo(3f,21f);path.lineTo(21f,21f);path.lineTo(21f,16f);canvas.drawPath(path,pen)}
            else->{pen.style=Paint.Style.FILL;for(x in listOf(5f,12f,19f))canvas.drawCircle(x,12f,1.6f,pen);pen.style=Paint.Style.STROKE}
        }
        canvas.restore()
    }
}
