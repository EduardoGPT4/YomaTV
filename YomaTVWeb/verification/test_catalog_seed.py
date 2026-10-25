"""Pure source-partition tests; no HTTP, no official API, no server credentials."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('facets_seed',ROOT/'catalog_facets_seed.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
calls=[]

def fake_page(params):
    calls.append(params)
    if params['minYear']!=params['maxYear']:
        return {'pagination':{'totalRecords':1000,'totalPages':50},'items':[]}
    all_rows=[{'slug':f"year-{params['minYear']}-anime-{n}"} for n in range(3)]
    page=params['page']
    return {'pagination':{'totalRecords':3,'totalPages':2},'items':all_rows[:2] if page==1 else all_rows[2:]}

module.page=fake_page
result=module.members({'genre':'accion'},2000,2001)
assert len(result)==6
assert all(call['genre']=='accion' for call in calls)
assert {call['page'] for call in calls}=={1,2}
checks=['source_1000_cap_is_partitioned_instead_of_truncated','all_pages_in_every_year_partition_are_merged','filter_parameters_are_preserved_across_partitions']

def incomplete(params):
    return {'pagination':{'totalRecords':3,'totalPages':1},'items':[{'slug':'one'}]}
module.page=incomplete
try:
    module.members({'genre':'accion'},2000,2000)
except RuntimeError as error:
    assert 'Incomplete' in str(error)
else:
    raise AssertionError('An incomplete source partition was accepted.')
checks.append('incomplete_source_partition_is_rejected')

def changing(params):
    return {'pagination':{'totalRecords':3 if params['page']==1 else 4,'totalPages':2},'items':[{'slug':str(params['page'])}]}
module.page=changing
try:
    module.members({},2000,2000)
except RuntimeError as error:
    assert 'changed' in str(error)
else:
    raise AssertionError('A changed source count was accepted.')
checks.append('changed_source_pagination_is_rejected')
output={'ok':True,'count':len(checks),'checks':checks,'network_requests':0}
(ROOT/'verification/catalog-seed-check.json').write_text(json.dumps(output,indent=2),encoding='utf8')
print(json.dumps(output,indent=2))
