import json

from seasonav1.schedule import SCHEDULE_URL


def schedule_page(animes):
    media=[{"slug":slug,"title":slug.title(),"startDate":"2026-10-01",
            "latestEpisode":{"number":number,"createdAt":published}} for slug,number,published in animes]
    return '<script>kit.start(app,element,{data:[{data:{media:'+json.dumps(media)+'}}]});</script>'


def catalog_page(slug,numbers=(1,2),mirror="https://www.mp4upload.com/embed-test.html",server="MP4Upload",language="SUB"):
    return '<script>kit.start(app,element,{data:[{data:'+json.dumps({"media":{"title":slug.title()},"episodes":[{"number":n} for n in numbers],
              "embeds":{language:[{"server":server,"url":mirror}]}})+'}]});</script>'


class FixtureClient:
    pages={SCHEDULE_URL:schedule_page([("lunes",2,"2026-10-05T14:00:00Z"),("domingo",2,"2026-10-11T14:00:00Z")]),
           "https://animeav1.com/media/lunes":catalog_page("lunes"),"https://animeav1.com/media/domingo":catalog_page("domingo")}

    def __init__(self,*args):self.requests=0;self.urls=[]
    def fetch(self,url):
        self.requests+=1;self.urls.append(url)
        return self.pages[url]
