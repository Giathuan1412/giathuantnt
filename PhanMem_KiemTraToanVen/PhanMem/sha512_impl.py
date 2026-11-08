"""SHA-512 tự cài đặt theo FIPS 180-4 (khối 1024 bit, mã băm 512 bit)."""
from math import isqrt

MASK = 0xFFFFFFFFFFFFFFFF


def _primes(n):
    ps, x = [], 2
    while len(ps) < n:
        if all(x % p for p in ps):
            ps.append(x)
        x += 1
    return ps


def _icbrt(n):
    lo, hi = 0, 1 << ((n.bit_length() // 3) + 2)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if mid ** 3 <= n:
            lo = mid
        else:
            hi = mid - 1
    return lo


# Hằng số: 64 bit đầu phần thập phân của căn bậc hai (H0..H7) và căn bậc ba (K0..K79)
# của các số nguyên tố đầu tiên, đúng như mô tả trong FIPS 180-4.
_P = _primes(80)
H_INIT = [isqrt(p << 128) & MASK for p in _P[:8]]
K = [_icbrt(p << 192) & MASK for p in _P]


def _rotr(x, n):
    return ((x >> n) | (x << (64 - n))) & MASK


class SHA512:
    block_size = 128

    def __init__(self):
        self._h = list(H_INIT)
        self._buf = b""
        self._length = 0

    def update(self, data: bytes):
        self._length += len(data)
        self._buf += data
        while len(self._buf) >= 128:
            self._compress(self._buf[:128])
            self._buf = self._buf[128:]

    def _pad(self):
        l_bits = self._length * 8
        pad = b"\x80" + b"\x00" * ((111 - self._length) % 128)
        return pad + l_bits.to_bytes(16, "big")

    def _expand(self, block):
        w = [int.from_bytes(block[i:i + 8], "big") for i in range(0, 128, 8)]
        for t in range(16, 80):
            s0 = _rotr(w[t - 15], 1) ^ _rotr(w[t - 15], 8) ^ (w[t - 15] >> 7)
            s1 = _rotr(w[t - 2], 19) ^ _rotr(w[t - 2], 61) ^ (w[t - 2] >> 6)
            w.append((w[t - 16] + s0 + w[t - 7] + s1) & MASK)
        return w

    def _compress(self, block):
        w = self._expand(block)
        a, b, c, d, e, f, g, h = self._h
        for t in range(80):
            S1 = _rotr(e, 14) ^ _rotr(e, 18) ^ _rotr(e, 41)
            ch = (e & f) ^ (~e & MASK & g)
            t1 = (h + S1 + ch + K[t] + w[t]) & MASK
            S0 = _rotr(a, 28) ^ _rotr(a, 34) ^ _rotr(a, 39)
            maj = (a & b) ^ (a & c) ^ (b & c)
            t2 = (S0 + maj) & MASK
            h, g, f, e, d, c, b, a = g, f, e, (d + t1) & MASK, c, b, a, (t1 + t2) & MASK
        self._h = [(x + y) & MASK for x, y in zip(self._h, (a, b, c, d, e, f, g, h))]

    def hexdigest(self) -> str:
        tmp = SHA512()
        tmp._h, tmp._buf, tmp._length = list(self._h), self._buf, self._length
        tmp._buf += tmp._pad()
        while len(tmp._buf) >= 128:
            tmp._compress(tmp._buf[:128])
            tmp._buf = tmp._buf[128:]
        return "".join("%016x" % x for x in tmp._h)
