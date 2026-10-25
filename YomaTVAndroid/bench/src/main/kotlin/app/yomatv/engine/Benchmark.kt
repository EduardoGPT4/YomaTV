package app.yomatv.engine

import com.sun.net.httpserver.HttpServer
import java.io.File
import java.net.InetSocketAddress

fun main(args: Array<String>) {
    val root=File(System.getProperty("user.dir")); val report=File(root,"verification").apply{mkdirs()}
    val live=args.contains("--live") || args.contains("--prepare-resume");val file=File(report,"private/${if(live)"provider" else "loopback"}.mp4.part").apply{parentFile.mkdirs()}
    var server:HttpServer?=null
    val started=System.nanoTime(); var resolve=0.0
    val allowed:(String)->Boolean;val video:String;val referer:String
    if(live){
        val page="https://animeav1.com/media/dark-summoner-to-dekiteiru/1"
        referer=Provider.embed(Network.html(page,"page","https://animeav1.com/"),"SUB")
        video=Provider.video(Network.html(referer,"embed",page));allowed={Provider.allowed(it,"video")}
        resolve=(System.nanoTime()-started)/1e9
        if(args.contains("--prepare-resume")){
            val connection=Network.open(video,mapOf("Referer" to referer,"Range" to "bytes=0-0")){Provider.allowed(it,"video")}
            try{
                check(connection.responseCode==206)
                val total=connection.getHeaderField("Content-Range").substringAfter('/').toLong();check(total==file.length())
                fun escape(s:String)=s.replace("\\","\\\\").replace("\"","\\\"")
                val etag=escape(connection.getHeaderField("ETag").orEmpty());val modified=escape(connection.getHeaderField("Last-Modified").orEmpty())
                File(report,"private/android-resume.json").writeText("""{"total":$total,"etag":"$etag","modified":"$modified"}""")
                var remaining=total-8*1024*1024
                file.inputStream().use{input->File(report,"private/android-provider.part").outputStream().use{output->val buffer=ByteArray(1024*1024);while(remaining>0){val n=input.read(buffer,0,minOf(buffer.size.toLong(),remaining).toInt());check(n>0);output.write(buffer,0,n);remaining-=n}}}
                println("""{"ok":true,"prepared_partial_bytes":${total-8*1024*1024},"remaining_bytes":8388608}""")
            }finally{connection.disconnect()}
            return
        }
    }else{
        server=HttpServer.create(InetSocketAddress("127.0.0.1",0),0)
        val total=64*1024*1024
        server.createContext("/video.mp4"){exchange->
            val offset=exchange.requestHeaders.getFirst("Range")?.substringAfter("bytes=")?.substringBefore('-')?.toIntOrNull()?:0
            exchange.responseHeaders.set("ETag","\"bench-v1\"");exchange.responseHeaders.set("Content-Type","video/mp4")
            if(offset>0)exchange.responseHeaders.set("Content-Range","bytes $offset-${total-1}/$total")
            exchange.sendResponseHeaders(if(offset>0)206 else 200,(total-offset).toLong())
            runCatching{exchange.responseBody.use{out->val buffer=ByteArray(256*1024){42};var remaining=total-offset;while(remaining>0){val count=minOf(buffer.size,remaining);out.write(buffer,0,count);remaining-=count}}};exchange.close()
        }
        server.start();video="http://127.0.0.1:${server.address.port}/video.mp4";referer=video;allowed={it==video}
    }
    try{
        if(file.exists())file.delete()
        var saved=Resume();val first=System.nanoTime()
        try{Transfer(allowed).download(video,referer,file,cancelled={file.length()>=16L*1024*1024},checkpoint={saved=it.resume})}catch(_:TransferStopped){}
        val firstSeconds=(System.nanoTime()-first)/1e9;val partial=file.length()
        val resumeAt=System.nanoTime()
        val result=Transfer(allowed).download(video,referer,file,saved)
        val resumeSeconds=(System.nanoTime()-resumeAt)/1e9
        val hashAt=System.nanoTime();val sha=Integrity.sha256(file);val hashSeconds=(System.nanoTime()-hashAt)/1e9
        val mp4=if(live)Integrity.mp4(file)else true
        check(mp4);check(result.bytes==file.length())
        val runtime=Runtime.getRuntime();val heap=(runtime.totalMemory()-runtime.freeMemory())/1048576.0
        val json="""{"ok":true,"kind":"${if(live)"public_mp4upload" else "local_loopback"}","runtime":"JVM on Windows; Android request profile","physical_android_tested":false,"resolve_seconds":$resolve,"first_segment_bytes":$partial,"first_segment_seconds":$firstSeconds,"resume_bytes":${result.bytes-partial},"resume_seconds":$resumeSeconds,"resumed_without_restarting":${partial>0&&saved.etag.isNotBlank()},"total_bytes":${result.bytes},"average_mib_per_second":${result.bytes/1048576.0/(firstSeconds+resumeSeconds)},"average_mbps":${result.bytes*8.0/1_000_000/(firstSeconds+resumeSeconds)},"sha256_seconds":$hashSeconds,"heap_used_mib":$heap,"mp4_structure_valid":$mp4,"sha256":"$sha"}"""
        File(report,if(live)"provider-speed.json"else"loopback-speed.json").writeText(json);println(json)
    }finally{server?.stop(0)}
}
