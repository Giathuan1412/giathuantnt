"""Đổi 1 bit trong tập tin để mô phỏng việc dữ liệu bị thay đổi (hiệu ứng thác đổ)."""
import os
import random
import shutil

BAK = ".bak"


def flip_bit(path, byte_index=None, bit_index=None):
    """Đổi 1 bit của tập tin. Bỏ trống vị trí thì chọn ngẫu nhiên.
    Tự sao lưu bản gốc sang <path>.bak (chỉ lần đầu, để khôi phục được).
    Trả về (byte_index, bit_index, byte_cu, byte_moi, loi)."""
    if not os.path.isfile(path):
        return None, None, None, None, "Không tìm thấy tập tin."
    size = os.path.getsize(path)
    if size == 0:
        return None, None, None, None, "Tập tin rỗng, không có bit nào để đổi."
    if byte_index is None:
        byte_index = random.randrange(size)
    if bit_index is None:
        bit_index = random.randrange(8)
    if not 0 <= byte_index < size:
        return None, None, None, None, "Byte phải từ 0 đến %d." % (size - 1)
    if not 0 <= bit_index <= 7:
        return None, None, None, None, "Bit phải từ 0 đến 7."
    try:
        if not os.path.exists(path + BAK):
            shutil.copy2(path, path + BAK)
        with open(path, "r+b") as f:
            f.seek(byte_index)
            old = f.read(1)[0]
            new = old ^ (1 << bit_index)
            f.seek(byte_index)
            f.write(bytes([new]))
    except OSError as e:
        return None, None, None, None, "Không ghi được tập tin (%s)." % e.strerror
    return byte_index, bit_index, old, new, None


def has_backup(path):
    return os.path.isfile(path + BAK)


def restore(path):
    """Khôi phục tập tin từ bản sao lưu. Trả về None nếu ổn, hoặc thông báo lỗi."""
    if not has_backup(path):
        return "Không có bản sao lưu để khôi phục."
    try:
        shutil.copy2(path + BAK, path)
        os.remove(path + BAK)
    except OSError as e:
        return "Không khôi phục được (%s)." % e.strerror
    return None
