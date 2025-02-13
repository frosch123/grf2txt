from __future__ import annotations
from typing import Optional, Any, BinaryIO, MutableMapping
from dataclasses import dataclass, field
import hashlib
from io import BytesIO
from collections import defaultdict

from .binreader import BinaryReader


@dataclass
class GRFString:
    str_name: str = ""
    translations: dict[int, bytes] = field(default_factory=dict)

    def add_text(self, lang_id: int, text: bytes) -> None:
        if lang_id == 0x7E:
            self.str_name = text.decode("ascii")
        else:
            self.translations[lang_id] = text


class ParserState:
    action6_effect: bool = False
    actionb_string: Optional[GRFString] = None


class NewGRF:
    """
    NewGRF meta data.
    """

    md5sum: Optional[Any] = None
    unique_id: Optional[bytes] = None
    grf_version: Optional[int] = None  # NewGRF spec version
    version: Optional[int] = None  # Version of NewGRF
    min_compatible_version: Optional[int] = None
    container_version: Optional[int] = None

    plurals: MutableMapping[int, int]
    genders: MutableMapping[int, MutableMapping[int, list[str]]]
    cases: MutableMapping[int, MutableMapping[int, list[str]]]
    strings: MutableMapping[str, GRFString]

    STR_GRF_NAME = "STR_GRF_NAME"
    STR_GRF_DESCRIPTION = "STR_GRF_DESCRIPTION"
    STR_GRF_URL = "STR_GRF_URL"

    FEATURES = {
        0x00: "TRAIN",
        0x01: "ROAD_VEHICLE",
        0x02: "SHIP",
        0x03: "AIRCRAFT",
        0x04: "STATION",
        0x05: "CANAL",
        0x06: "BRIDGE",
        0x07: "HOUSE",
        0x08: "GLOBAL",
        0x09: "INDUSTRY_TILE",
        0x0A: "INDUSTRY",
        0x0B: "CARGO",
        0x0C: "SOUND_EFFECT",
        0x0D: "AIRPORT",
        0x0E: "SIGNAL",
        0x0F: "OBJECT",
        0x10: "RAILTYPE",
        0x11: "AIRPORT_TILE",
        0x12: "ROADTYPE",
        0x13: "TRAMTYPE",
        0x14: "ROAD_STOP",
    }

    @classmethod
    def str_feature(cls, feature: int, index: int) -> str:
        f = cls.FEATURES.get(feature, str(feature))
        return f"STR_{f}_{index}"

    @staticmethod
    def str_ext(index: int) -> str:
        if 0xC400 <= index < 0xC500:
            return f"STR_STATION_CLASS_{index - 0xC400}_NAME"
        elif 0xC500 <= index < 0xC600:
            return f"STR_STATION_{index - 0xC500}_NAME"
        elif 0xC900 <= index < 0xCA00:
            return f"STR_HOUSE_{index - 0xC900}_NAME"
        else:
            return f"STR_GENERIC_{index:04X}"

    @staticmethod
    def str_error(index: int) -> str:
        return f"STR_ERROR_{index}"

    @staticmethod
    def str_param_name(index: int) -> str:
        return f"STR_PARAM_{index}_NAME"

    @staticmethod
    def str_param_description(index: int) -> str:
        return f"STR_PARAM_{index}_DESCRIPTION"

    def __init__(self):
        self.plurals = dict()
        self.genders = defaultdict(lambda: defaultdict(list))
        self.cases = defaultdict(lambda: defaultdict(list))
        self.strings = defaultdict(GRFString)

        # Local variable to track mappings.
        self._feature_mapping = {}
        self._next_feature_map = None

    def read(self, fp: BinaryIO) -> None:
        """
        Read NewGRF meta data.
        """

        md5sum = hashlib.md5()
        reader = BinaryReader(fp, md5sum)

        size = reader.uint16()
        if size == 0:
            if reader.read(8) == b"GRF\x82\r\n\x1a\n":
                self.container_version = 2
                reader.uint32()
                if reader.uint8() != 0:
                    raise RuntimeError("Unknown container 2 compression.")
                size = reader.uint32()
            else:
                raise RuntimeError("Neither container 1 nor 2.")
        else:
            self.container_version = 1

        skip_sprites = 0
        sprite_index = 0
        state = ParserState()
        while size != 0:
            info = reader.uint8()
            if info == 0xFF:
                if skip_sprites > 0:
                    state.action6_effect = False
                    reader.skip(size)
                    skip_sprites -= 1
                else:
                    pseudo = reader.read(size)
                    if sprite_index != 0:
                        skip_sprites = self.read_pseudo(sprite_index, pseudo, state)
            else:
                state.action6_effect = False
                if skip_sprites > 0:
                    skip_sprites -= 1

                if self.container_version == 2 and info == 0xFD:
                    reader.skip(size)
                elif self.container_version == 1 and size >= 8:
                    reader.skip(7)
                    size -= 8
                    if (info & 0x02) != 0:
                        reader.skip(size)
                    else:
                        while size > 0:
                            i = reader.uint8()
                            if i < 0x80:
                                if i == 0:
                                    i = 0x80
                                reader.skip(i)
                            else:
                                i = 32 - (i >> 3)
                                reader.skip(1)
                            if i > size:
                                raise RuntimeError("Failed sprite decoding.")
                            size -= i
                else:
                    raise RuntimeError("Unknown info byte.")

            sprite_index += 1
            if self.container_version == 2:
                size = reader.uint32()
            else:
                size = reader.uint16()

        if self.container_version == 1:
            reader.uint16()
            try:
                reader.uint16()
            except Exception:
                # Some GRFs are encoded weirdly, and the checksum is only
                # 16-bits. This is against specs, but some already use this.
                # Given this is container v1, we allow this. OpenTTD client
                # doesn't even read these bytes, so it is fine.
                pass

        reader.detach_hash()

        if self.container_version == 2:
            id = reader.uint32()
            while id != 0:
                size = reader.uint32()
                reader.skip(size)
                id = reader.uint32()

        try:
            reader.uint8()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Junk at the end of file.")

        self.md5sum = md5sum.digest()

    def read_pseudo(self, sprite_index: int, pseudo: bytes, state: ParserState) -> int:
        """
        Read and parse pseudo sprite.

        @param sprite_index: Sprite number
        @param pseudo: Pseudo sprite
        @param state: Inter-sprite state
        @return: Number of sprites to skip
        """

        reader = BinaryReader(BytesIO(pseudo))

        action = reader.uint8()
        skip_sprites = 0
        if action == 0x00:
            feat = reader.uint8()
            feat = self._feature_mapping.get(feat, feat)

            num_props = reader.uint8()
            num_ids = reader.uint8()
            if num_ids:
                first_id = reader.uint_ext()
                if feat == 0x08:
                    for _ in range(num_props):
                        prop = reader.uint8()
                        if prop == 0x08:
                            reader.skip(num_ids)
                        elif prop == 0x10:
                            reader.skip(12 * 32 * num_ids)
                        elif prop in (0x0A, 0x0C, 0x0F):
                            reader.skip(2 * num_ids)
                        elif prop in (0x09, 0x0B, 0x0D, 0x0E, 0x12, 0x16, 0x17):
                            reader.skip(4 * num_ids)
                        elif prop in (0x11,):
                            reader.skip(8 * num_ids)
                        elif prop == 0x13:
                            for i in range(num_ids):
                                while True:
                                    gi = reader.uint8()
                                    if gi == 0:
                                        break
                                    self.genders[first_id + i][gi].append(reader.str().decode("utf-8"))
                        elif prop == 0x14:
                            for i in range(num_ids):
                                while True:
                                    gi = reader.uint8()
                                    if gi == 0:
                                        break
                                    self.cases[first_id + i][gi].append(reader.str().decode("utf-8"))
                        elif prop == 0x15:
                            for i in range(num_ids):
                                self.plurals[first_id + i] = reader.uint8()
                        else:
                            break
        elif action == 0x01:
            reader.uint8()
            num_sets = reader.uint8()
            # Some sets defines zero sprites, while they could as well not
            # have added this pseudo sprite. In these cases, there are less
            # than 3 bytes left in the buffer. We already read 3 bytes from
            # the buffer.
            if num_sets == 0 and len(pseudo) - 3 >= 3:
                reader.uint_ext()
                num_sets = reader.uint_ext()
            num_ent = reader.uint_ext()
            skip_sprites = num_sets * num_ent
        elif action == 0x04:
            feat = reader.uint8()
            feat = self._feature_mapping.get(feat, feat)

            lang_id = reader.uint8()
            num_ids = reader.uint8()
            if lang_id < 0x80:
                first_id = reader.uint_ext()  # assuming extended-byte for all features; technically false :)

                def str_id(index: int) -> str:
                    return self.str_feature(feat, index)

            else:
                first_id = reader.uint16()
                str_id = self.str_ext
                lang_id -= 0x80
            for i in range(num_ids):
                self.strings[str_id(first_id + i)].add_text(lang_id, reader.str())
        elif action == 0x05:
            reader.skip(1)
            skip_sprites = reader.uint_ext()
        elif action == 0x06:
            state.action6_effect = True
        elif action in (0x07, 0x09):
            state.actionb_string = None
        elif action == 0x08:
            self.grf_version = reader.uint8()
            self.unique_id = reader.uint32().to_bytes(4, "little")
            self.strings[self.STR_GRF_NAME].add_text(0x7F, reader.str())
            self.strings[self.STR_GRF_DESCRIPTION].add_text(0x7F, reader.str())
        elif action == 0x0A:
            num_sets = reader.uint8()
            for _ in range(num_sets):
                skip_sprites += reader.uint8()
                reader.skip(2)
        elif action == 0x0B:
            if state.actionb_string is None:
                state.actionb_string = self.strings[self.str_error(sprite_index)]
            reader.skip(1)
            lang_id = reader.uint8()
            reader.skip(1)
            text = reader.str()
            if text:
                state.actionb_string.add_text(lang_id, text)
            if lang_id == 0x7F:
                state.actionb_string = None
        elif action == 0x11:
            skip_sprites = reader.uint16()
        elif action == 0x12:
            num_defs = reader.uint8()
            for _ in range(num_defs):
                reader.skip(1)
                skip_sprites += reader.uint8()
                reader.skip(2)
        elif action == 0x14:
            self.read_a14(reader, bytearray())

        return skip_sprites

    def read_a14(self, reader: BinaryReader, path: bytes) -> bool:
        """
        Read Action 14.

        @param reader: Pseudo sprite reader
        @type reader: C{BinaryReader}

        @param path: Action 14 path
        @type path: C{list} of C{bytes}
        """

        while True:
            type_id = reader.uint8()
            if type_id == 0:
                return True

            subpath = path + reader.read(4)
            if type_id == ord("C"):
                if not self.read_a14(reader, subpath):
                    return False
            elif type_id == ord("B"):
                size = reader.uint16()
                bdata = BinaryReader(BytesIO(reader.read(size)))

                # JGRPP has a feature map, which uses the name of the feature
                # to assign an ID to it.
                if subpath == b"FIDMFTID" and self._next_feature_map:
                    self._feature_mapping[bdata.uint8()] = self._next_feature_map
                    self._next_feature_map = None

                if subpath == b"INFOVRSN" and size >= 4:
                    self.version = bdata.uint32()
                elif subpath == b"INFOMINV" and size >= 4:
                    self.min_compatible_version = bdata.uint32()
            elif type_id == ord("T"):
                grflangid = reader.uint8()
                sdata = reader.str()

                # JGRPP has a feature map, which uses the name of the feature
                # to assign an ID to it.
                if subpath == b"FIDMNAME":
                    if sdata == "road_stops":
                        self._next_feature_map = 0x14

                if subpath == b"INFONAME":
                    self.strings[self.STR_GRF_NAME].add_text(grflangid, sdata)
                elif subpath == b"INFODESC":
                    self.strings[self.STR_GRF_DESCRIPTION].add_text(grflangid, sdata)
                elif subpath == b"INFOURL_":
                    self.strings[self.STR_GRF_URL].add_text(grflangid, sdata)
                elif subpath[:8] == b"INFOPARA" and subpath[12:] == b"NAME":
                    param = int.from_bytes(subpath[8:12], byteorder="little", signed=False)
                    self.strings[self.str_param_name(param)].add_text(grflangid, sdata)
                elif subpath[:8] == b"INFOPARA" and subpath[12:] == b"DESC":
                    param = int.from_bytes(subpath[8:12], byteorder="little", signed=False)
                    self.strings[self.str_param_description(param)].add_text(grflangid, sdata)
            else:
                return False
