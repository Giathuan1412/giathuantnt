"""SHA-1 tự cài đặt theo FIPS 180-4 (khối 512 bit, mã băm 160 bit)."""

MASK = 0xFFFFFFFF


def _rotl(x, n):
    return ((x << n) | (x >> (32 - n))) & MASK


class SHA1:
    block_size = 64

    def __init__(self):
        self._h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
        self._buf = b""
        self._length = 0  # tổng số byte đã nhận

    def update(self, data: bytes):
        self._length += len(data)
        self._buf += data
        while len(self._buf) >= 64:
            self._compress(self._buf[:64])
            self._buf = self._buf[64:]

    def _pad(self):
        l_bits = self._length * 8
        pad = b"\x80" + b"\x00" * ((55 - self._length) % 64)
        return pad + l_bits.to_bytes(8, "big")

    def _expand(self, block):
        w = [int.from_bytes(block[i:i + 4], "big") for i in range(0, 64, 4)]
        for t in range(16, 80):
            w.append(_rotl(w[t - 3] ^ w[t - 8] ^ w[t - 14] ^ w[t - 16], 1))
        return w

    def _compress(self, block):
        w = self._expand(block)
        a, b, c, d, e = self._h
        for t in range(80):
            if t < 20:
                f, k = (b & c) | (~b & d), 0x5A827999
            elif t < 40:
                f, k = b ^ c ^ d, 0x6ED9EBA1
            elif t < 60:
                f, k = (b & c) | (b & d) | (c & d), 0x8F1BBCDC
            else:
                f, k = b ^ c ^ d, 0xCA62C1D6
            temp = (_rotl(a, 5) + (f & MASK) + e + k + w[t]) & MASK
            e, d, c, b, a = d, c, _rotl(b, 30), a, temp
        self._h = [(x + y) & MASK for x, y in zip(self._h, (a, b, c, d, e))]

    def hexdigest(self) -> str:
        # làm việc trên bản sao để có thể gọi hexdigest() nhiều lần
        tmp = SHA1()
        tmp._h, tmp._buf, tmp._length = list(self._h), self._buf, self._length
        tail = tmp._pad()
        tmp._buf += tail
        while len(tmp._buf) >= 64:
            tmp._compress(tmp._buf[:64])
            tmp._buf = tmp._buf[64:]
        return "".join("%08x" % x for x in tmp._h)
