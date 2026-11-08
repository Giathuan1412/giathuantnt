"""Đọc tập tin theo từng khối và đưa cho bộ băm."""
import os
from src.sha1_impl import SHA1
from src.sha512_impl import SHA512

CHUNK = 64 * 1024  # 64 KB, là bội số của 64 và 128 byte
ALGOS = {"SHA-1": SHA1, "SHA-512": SHA512}


def hash_file(path, algo):
    """Trả về (hash, None) hoặc (None, thông báo lỗi)."""
    if not os.path.isfile(path):
        return None, "Không tìm thấy tập tin."
    hasher = ALGOS[algo]()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                hasher.update(chunk)
    except PermissionError:
        return None, "Không có quyền đọc tập tin."
    except OSError as e:
        return None, "Không đọc được tập tin (%s)." % e.strerror
    return hasher.hexdigest(), None
