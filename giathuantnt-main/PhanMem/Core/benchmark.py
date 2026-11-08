"""Đo thời gian chạy SHA-1 và SHA-512."""
import os
import time
import database
from Util.file_reader import hash_file


def run_benchmark(paths, runs=3, progress=None):
    """Trả về {(tên file, thuật toán): [ms, ...]}."""
    out = {}
    total = len(paths) * 2 * runs
    done = 0
    for p in paths:
        size = os.path.getsize(p)
        for algo in ("SHA-1", "SHA-512"):
            times = []
            for n in range(1, runs + 1):
                t0 = time.perf_counter()
                hash_file(p, algo)
                ms = (time.perf_counter() - t0) * 1000
                times.append(ms)
                database.add_benchmark(os.path.basename(p), size, algo, n, ms)
                done += 1
                if progress:
                    progress(done, total)
            out[(os.path.basename(p), algo)] = times
    return out
