import hashlib, os, tempfile, random
from sha1_impl import SHA1
from sha512_impl import SHA512
import database, monitor, benchmark
from file_reader import hash_file

random.seed(1)
for n in [0,1,3,55,56,63,64,65,111,112,119,127,128,129,200,1000,70000]:
    data = bytes(random.getrandbits(8) for _ in range(n))
    a = SHA1(); a.update(data[:n//2]); a.update(data[n//2:])
    b = SHA512(); b.update(data[:n//3]); b.update(data[n//3:])
    assert a.hexdigest()==hashlib.sha1(data).hexdigest(), ("sha1",n)
    assert b.hexdigest()==hashlib.sha512(data).hexdigest(), ("sha512",n)
print("SHA OK")
d=tempfile.mkdtemp(); database.DB_PATH=os.path.join(d,"t.db"); database.init_db()
p=os.path.join(d,"a.txt"); open(p,"wb").write(b"hello"*50000)
for algo in ("SHA-1","SHA-512"):
    h,_=hash_file(p,algo); assert h==getattr(hashlib,algo.replace("-","").lower())(open(p,"rb").read()).hexdigest()
    assert database.add_file(p,algo,h,os.path.getsize(p)); assert not database.add_file(p,algo,h,1)
r=database.get_all_files(); print([s for _,s,_ in monitor.check_all(r)])
open(p,"ab").write(b"x"); print([s for _,s,_ in monitor.check_all(database.get_all_files())])
os.remove(p); print([s for _,s,_ in monitor.check_all(database.get_all_files())])
print(len(database.get_history()), len(database.get_history("MISSING")))
q=os.path.join(d,"b.bin"); open(q,"wb").write(os.urandom(300000))
res=benchmark.run_benchmark([q],3); print({k:[round(x,1) for x in v] for k,v in res.items()})
