"""Real HTTP/SQLite checks: predicates precede pagination; personal data stays private."""
import json
import time
import test_web
test_web.BASE='http://127.0.0.1:8096/'
checks=[]
c=test_web.Client(); c.call('login',email='preview@example.test',password='Preview-Local-Test-8096')
anonymous=test_web.Client()
def find(client=c,**filters):
    return client.call('catalog',get=True,category='QA TV',**filters)['catalog']
def slugs(**filters): return {a['slug'] for a in find(**filters)['items']}
def check(ok,name):
    assert ok,name
    checks.append(name)

start=time.monotonic(); all_=find()
check(all_['total']==40 and len(all_['items'])==24 and all_['pages']==2,'bounded_results')
check(find(library='watching')['total']==32 and len(find(library='watching',page=2)['items'])==8,'personal_filters_before_pagination')
for status,n in [('planned',2),('completed',1),('paused',1),('dropped',1),('favorites',1),('none',3),('followed',37)]:
    check(find(library=status)['total']==n,'library_'+status)
check(slugs(download='downloaded')=={'qa-filter-00'},'only_own_confirmed_downloads')
check(slugs(download='queued')=={'qa-filter-01','qa-filter-02'},'pending_and_exported_queue')
check(find(download='unprepared')['total']==37,'cancelled_and_foreign_jobs_do_not_hide_unprepared')
check(find(library='planned',download='queued')['total']==1,'combined_personal_filters')
check(slugs(letter='A')=={'qa-filter-00'} and slugs(letter='#')=={'qa-filter-01'},'accent_initial_and_numeric_index')
check(find(search='ALGEBRA')['items'][0]['slug']=='qa-filter-00','accent_insensitive_search')
include=json.dumps(['Action','Comedy']);exclude=json.dumps(['Ecchi'])
check(slugs(include_genres=include,exclude_genres=exclude)=={'qa-filter-00','qa-filter-05'},'all_included_genres_and_any_excluded_genre')
check(find(include_genres=include)['total']==3,'genre_and_semantics')
check(find(include_genres=json.dumps(['Action']),exclude_genres=json.dumps(['Action']))['total']==0,'contradictory_genres_have_no_matches')
check(find(genre='Action')['total']==5,'legacy_single_genre_compatibility')
check('qa-filter-04' in slugs(year='2024',season='primavera2024',airing='finished_airing'),'mal_fills_missing_premiere_season_and_airing')
for lang,n in [('SUB',0),('LAT',1),('DUB',2)]: check(slugs(language=lang)=={f'qa-filter-{n:02}'},'verified_language_'+lang)
check(find(language='unknown')['total']==37,'unknown_language_never_inferred_from_queue')
check(find(order='score')['items'][0]['slug']=='qa-filter-00','sort_my_score')
check([a['slug'] for a in find(order='episodes')['items'][:2]]==['qa-filter-09','qa-filter-08'],'sort_actual_available_episodes')
check(find(order='updated')['items'][0]['slug']=='qa-filter-39','sort_last_update')
check(find(order='premiere')['items'][0]['slug']=='qa-filter-02','sort_premiere_with_known_dates_first')
a=find(order='title')['items'];z=find(order='title_desc')['items']
check(a[0]['slug']!=z[0]['slug'],'both_title_orders')
public=find(client=anonymous,include_genres=include,exclude_genres=exclude)
check(public['total']==2 and all(a['mal'] is None and a['status']=='none' and a['score']==0 and not a['notes'] for a in public['items']),'public_metadata_without_personal_lists')
check(public['items'][0]['mal_mean']==9.1 and public['items'][0]['studios']==['Estudio de prueba'],'public_api_mean_and_studio_metadata')
for f in [{'library':'none'},{'download':'downloaded'},{'order':'score'},{'unwatched':'1'}]: anonymous.call('catalog',get=True,expected=401,**f)
checks.append('personal_filters_require_session')
for f in [{'letter':'A% OR 1=1'},{'order':'title;DROP TABLE'},{'library':'unknown'},{'season':'verano99999'},{'language':'ES'},{'include_genres':'not-json'},{'exclude_genres':json.dumps(['x']*21)}]: c.call('catalog',get=True,expected=422,**f)
checks.append('invalid_filters_rejected')
def source(client=c,**filters): return client.call('catalog',get=True,category='QA Source',**filters)['catalog']
check(source()['total']==3 and source(client=anonymous)['total']==3,'source_catalog_includes_titles_outside_mal_and_library')
check(source(include_genres=json.dumps(['Acción']))['total']==2,'source_genres_include_anime_never_synchronized_from_mal')
check(source(include_genres=json.dumps(['Action']))['total']==2,'legacy_english_genre_links_map_to_animeav1_names')
check(source(include_genres=json.dumps(['accion']))['selected_genres']['include']==['Acción'],'source_url_genre_slug_is_accepted')
check(source(include_genres=json.dumps(['Acción','Comedia']))['total']==1,'source_genre_intersection')
check(source(exclude_genres=json.dumps(['Action']))['total']==1,'source_genre_exclusion_includes_known_untagged_title')
check(source(year='1998')['items'][0]['slug']=='qa-source-a' and source(year='2020')['total']==0,'personal_mal_year_cannot_override_source_year')
check(source(airing='finished_airing')['items'][0]['slug']=='qa-source-a','personal_mal_emission_cannot_override_source_emission')
check(source(library='watching')['total']==1 and source(library='none')['total']==2,'library_is_an_explicit_optional_restriction')
public=source(client=anonymous,include_genres=json.dumps(['Action']))
private=source(include_genres=json.dumps(['Action']))
check([a['slug'] for a in public['items']]==[a['slug'] for a in private['items']],'general_filters_are_identical_signed_in_and_anonymous')
check(all(a['mal'] is None for a in public['items']),'anonymous_source_results_never_expose_private_mal_links')
check(private['items'][0]['metadata_source']=='AnimeAV1' and 'Acción' in private['items'][0]['genres'],'source_metadata_is_displayed_with_spanish_genres')
result={'ok':True,'checks':checks,'count':len(checks),'seconds':round(time.monotonic()-start,2),'real_accounts_used':False}
(test_web.ROOT/'verification/catalog-filters-check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
