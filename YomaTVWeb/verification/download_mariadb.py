"""Official, checksum-verified portable test runtime. Does not install a service."""
from pathlib import Path
import hashlib,urllib.request,zipfile
ROOT=Path(__file__).resolve().parent;base=ROOT/'tools';base.mkdir(exist_ok=True)
name='mariadb-11.4.13-winx64.zip'
checks=urllib.request.urlopen('https://dlm.mariadb.com/4801419/MariaDB/mariadb-11.4.13/winx64-packages/sha256sums.txt',timeout=60).read().decode()
expected=next(line.split()[0] for line in checks.splitlines() if name in line)
target=base/name
if not target.exists():
    with urllib.request.urlopen('https://dlm.mariadb.com/4801422/MariaDB/mariadb-11.4.13/winx64-packages/'+name,timeout=90) as response,target.open('xb') as out:
        while chunk:=response.read(1024*1024):out.write(chunk)
assert hashlib.file_digest(target.open('rb'),'sha256').hexdigest()==expected
with zipfile.ZipFile(target) as z:
    for entry in z.namelist():
        if not (base/entry).resolve().is_relative_to(base.resolve()):raise RuntimeError('Unsafe archive entry')
    z.extractall(base)
print('Official MariaDB archive SHA256 verified and extracted')
