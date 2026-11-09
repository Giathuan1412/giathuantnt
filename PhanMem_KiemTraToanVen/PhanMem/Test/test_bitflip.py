"""Kiểm thử đổi bit: python test_bitflip.py"""
import os, tempfile
import Util.bitflip as bitflip, Data.database as database, Core.monitor as monitor
from Util.file_reader import hash_file

database.DB_PATH = os.path.join(tempfile.mkdtemp(), "t.db")
database.init_db()
p = os.path.join(tempfile.mkdtemp(), "a.txt")
open(p, "wb").write(b"hello integrity" * 100)
for algo in ("SHA-1", "SHA-512"):
    h, _ = hash_file(p, algo)
    database.add_file(p, algo, h, os.path.getsize(p))
recs = database.get_all_files()
assert all(monitor.check_one(r)[0] == "OK" for r in recs)
b, t, old, new, err = bitflip.flip_bit(p)
assert err is None and bin(old ^ new).count("1") == 1
assert all(monitor.check_one(r)[0] == "MODIFIED" for r in recs)
assert bitflip.restore(p) is None
assert all(monitor.check_one(r)[0] == "OK" for r in recs)
assert bitflip.flip_bit(p, 10**9, 0)[4] and bitflip.flip_bit(p, 0, 8)[4]
print("Tat ca kiem thu dat.")
