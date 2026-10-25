"""No HTTP: versions include textual directory edits as well as filter facets."""
import copy,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import catalog_facets_seed as builder
data=json.loads(gzip.decompress((ROOT/'htdocs/data/catalog-facets.json.gz').read_bytes()))
version=builder.snapshot_version(data)
assert version==data['version']
checks=[]
for field in ['title','synopsis']:
 changed=copy.deepcopy(data);changed['directory'][0][field]+=' changed'
 assert builder.snapshot_version(changed)!=version
 checks.append(field+'_edit_changes_snapshot_version')
assert builder.snapshot_version({**data,'directory':list(reversed(data['directory']))})==version
checks.append('reordered_equivalent_directory_keeps_same_version')
offline=json.loads((ROOT/'htdocs/data/offline-catalog.json').read_text(encoding='utf8'))
assert offline['version']==version and {a['slug'] for a in offline['items']}=={a['slug'] for a in data['directory']}
checks.append('offline_projection_matches_current_directory_and_version')
result={'ok':True,'count':len(checks),'checks':checks,'network_requests':0}
(ROOT/'verification/catalog-version-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
