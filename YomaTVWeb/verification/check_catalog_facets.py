"""Validate the published filter snapshot against independently cached source pages."""
import gzip
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
data=json.loads(gzip.decompress((ROOT/'htdocs/data/catalog-facets.json.gz').read_bytes()))
meta=json.loads((ROOT/'htdocs/data/catalog-facets-meta.json').read_text(encoding='utf8'))
rows={row['slug']:row for row in data['anime']}
assert len(rows)==len(data['anime'])==meta['total']
assert meta['version']==data['version']
assert len(data['genres'])==46
assert all(set(row)=={'slug','genres','year','airing_status'} for row in rows.values())
assert all(row['year'] is None or 1900<=row['year']<=2100 for row in rows.values())
checks=['snapshot_version_count_and_unique_slugs','only_public_source_fields_in_snapshot','complete_source_taxonomy']

genre_sets=defaultdict(set)
year_sets=defaultdict(set)
status_sets=defaultdict(set)
for path in (ROOT/'verification/source-filter-cache').glob('*.json.gz'):
    page=json.loads(gzip.decompress(path.read_bytes()))
    filters=page['filters']
    slugs={row['slug'] for row in page['items']}
    for genre in filters['genres']:
        genre_sets[genre].update(slugs)
    if not filters['genres'] and filters['status'] is None and filters['years'][0]==filters['years'][1]:
        year_sets[filters['years'][0]].update(slugs)
    if not filters['genres'] and filters['status'] is not None:
        status_sets[filters['status']].update(slugs)

genre_counts={}
for genre in data['genres']:
    actual={slug for slug,row in rows.items() if genre['name'] in row['genres']}
    assert actual==genre_sets[genre['id']],genre['name']
    genre_counts[genre['name']]=len(actual)
checks.append('every_genre_matches_the_complete_public_html_membership')
for year,expected in year_sets.items():
    assert {slug for slug,row in rows.items() if row['year']==year}==expected,year
checks.append('every_premiere_year_matches_its_source_pages')
for code,name in [(1,'not_yet_aired'),(2,'currently_airing')]:
    assert {slug for slug,row in rows.items() if row['airing_status']==name}==status_sets[code]
checks.append('non_finished_emission_matches_the_complete_source_sets')
finished={slug for slug,row in rows.items() if row['airing_status']=='finished_airing'}
assert status_sets[0]<=finished
assert all(part['total']==len({slug for slug in finished if rows[slug]['year']==int(dict(pair.split('=') for pair in part['query'].split('&'))['minYear'])}) for part in data['partitions'] if part.get('method')=='validated_year_complement')
checks.append('finished_membership_matches_validated_source_year_counts')

base=json.loads(gzip.decompress((ROOT/'htdocs/data/catalog.json.gz').read_bytes()))
missing={row['slug'] for row in base['anime']}-rows.keys()
assert len(missing)<100,'Unexpected loss of catalog coverage.'
result={'ok':True,'count':len(checks),'checks':checks,'source_titles':len(rows),'genre_counts':genre_counts,
        'earliest_year':min(year_sets),'latest_year':max(year_sets),'old_titles_without_current_source_metadata':sorted(missing)}
(ROOT/'verification/catalog-facets-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({key:value for key,value in result.items() if key!='genre_counts'},ensure_ascii=False,indent=2))
