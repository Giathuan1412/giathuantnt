"""So sánh hash và xác định trạng thái: OK, MODIFIED, MISSING, ERROR."""
import os
import Core.database
from Util.file_reader import hash_file


def check_one(rec):
    """rec = (id, path, algo, hash_cu, size, ngay). Trả về (status, hash_moi)."""
    file_id, path, algo, old_hash = rec[0], rec[1], rec[2], rec[3]
    if not os.path.exists(path):
        status, new = "MISSING", ""
    else:
        new, err = hash_file(path, algo)
        if err:
            status, new = "ERROR", ""
        else:
            status = "OK" if new == old_hash else "MODIFIED"
    Core.database.add_scan(file_id, new, status)
    return status, new


def check_all(records, progress=None):
    results = []
    for i, rec in enumerate(records, 1):
        status, new = check_one(rec)
        results.append((rec, status, new))
        if progress:
            progress(i, len(records))
    return results
