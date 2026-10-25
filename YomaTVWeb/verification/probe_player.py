"""Inspect one public episode's compatible embeds through the local admin API."""
import json
import time
import test_web
test_web.BASE='http://127.0.0.1:8096/'
def main():
    c=test_web.Client();c.call('login',email='admin@example.test',password='Admin-Local-Test-8096')
    result=c.call('sync_anime',slug='dark-summoner-to-dekiteiru')
    episodes=result['detail']['episodes'];assert episodes
    time.sleep(2.2)
    player=c.call('player',episode_id=episodes[0]['id'])['player']
    result={'ok':bool(player['servers']),'slug':player['episode']['slug'],'episode':player['episode']['number'],
        'servers':player['servers'],'video_bytes_downloaded':0,'real_playback_verified':False}
    (test_web.ROOT/'verification/player-live-probe.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
