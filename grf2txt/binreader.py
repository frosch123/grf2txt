from typing import BinaryIO, Optional, Any
import struct


class BinaryReader:
    """
    Read binary data.
    """

    file: BinaryIO
    hash: Optional[Any]

    def __init__(self, file: BinaryIO, hash: Optional[Any] = None):
        self.file = file
        self.hash = hash

    def attach_hash(self, hash: Optional[Any]) -> None:
        self.hash = hash

    def detach_hash(self) -> None:
        self.hash = None

    def read(self, amount: int) -> bytes:
        b = self.file.read(amount)
        if self.hash:
            self.hash.update(b)
        return b

    def str(self) -> bytes:
        """
        Read zero-terminated string.
        """
        result = bytearray()
        while True:
            b = self.read(1)
            if b == b"\0" or b == b"" or b is None:
                break
            else:
                result.extend(b)
        return result

    def skip(self, amount: int) -> None:
        self.read(amount)

    def uint_ext(self) -> int:
        """
        Read NewGRF-style extended byte.
        """
        b = self.uint8()
        if b == 0xFF:
            b = self.uint16()
        return b

    def gamma(self) -> tuple[int, int]:
        """
        Read OTTD-savegame-style gamma value.
        """
        b = self.uint8()
        if (b & 0x80) == 0:
            return (b & 0x7F, 1)
        elif (b & 0xC0) == 0x80:
            return ((b & 0x3F) << 8 | self.uint8(), 2)
        elif (b & 0xE0) == 0xC0:
            return ((b & 0x1F) << 16 | self.uint16(be=True), 3)
        elif (b & 0xF0) == 0xE0:
            return ((b & 0x0F) << 24 | self.uint24(be=True), 4)
        elif (b & 0xF8) == 0xF0:
            return ((b & 0x07) << 32 | self.uint32(be=True), 5)
        else:
            raise RuntimeError("Invalid gamma encoding.")

    def gamma_str(self) -> bytes:
        """
        Read OTTD-savegame-style gamma string (SLE_STR).
        """
        size = self.gamma()[0]
        return self.read(size)

    def int8(self) -> int:
        b = self.read(1)
        if len(b) != 1:
            raise RuntimeError("Unexpected end-of-file.")
        return struct.unpack("<b", b)[0]

    def uint8(self) -> int:
        b = self.read(1)
        if len(b) != 1:
            raise RuntimeError("Unexpected end-of-file.")
        return struct.unpack("<B", b)[0]

    def int16(self, be: bool = False) -> int:
        b = self.read(2)
        if len(b) != 2:
            raise RuntimeError("Unexpected end-of-file.")
        return struct.unpack(">h" if be else "<h", b)[0]

    def uint16(self, be: bool = False) -> int:
        b = self.read(2)
        if len(b) != 2:
            raise RuntimeError("Unexpected end-of-file.")
        return struct.unpack(">H" if be else "<H", b)[0]

    def uint24(self, be: bool = False) -> int:
        b = self.read(3)
        if len(b) != 3:
            raise RuntimeError("Unexpected end-of-file.")
        if be:
            return b[0] << 16 | b[1] << 8 | b[2]
        else:
            return b[2] << 16 | b[1] << 8 | b[0]

    def int32(self, be: bool = False) -> int:
        b = self.read(4)
        if len(b) != 4:
            raise RuntimeError("Unexpected end-of-file.")
        return struct.unpack(">l" if be else "<l", b)[0]

    def uint32(self, be: bool = False) -> int:
        b = self.read(4)
        if len(b) != 4:
            raise RuntimeError("Unexpected end-of-file.")
        return struct.unpack(">L" if be else "<L", b)[0]

    def int64(self, be: bool = False) -> int:
        b = self.read(8)
        if len(b) != 8:
            raise RuntimeError("Unexpected end-of-file.")
        return struct.unpack(">q" if be else "<q", b)[0]

    def uint64(self, be: bool = False) -> int:
        b = self.read(8)
        if len(b) != 8:
            raise RuntimeError("Unexpected end-of-file.")
        return struct.unpack(">Q" if be else "<Q", b)[0]
