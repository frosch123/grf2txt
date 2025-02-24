from __future__ import annotations
from typing import Optional, Callable
from dataclasses import dataclass, field


@dataclass
class CommandName:
    base_name: str = ""
    translation_name: str = ""

    def __post_init__(self):
        if not self.translation_name:
            self.translation_name = self.base_name


@dataclass
class StackParam:
    offset: int = 0
    size: int = 0


@dataclass
class TextCommand(CommandName):
    inline_param_size: int = 0
    stack_param: list[StackParam] = field(default_factory=list)


class TextRefStack:
    stack_index: list[int]
    commands: list[TextCommand]

    def __init__(self):
        self.stack_index = list(range(64))
        self.commands = []

    def standard_command(self, cc: ControlCode) -> None:
        if cc.inline_param_size or cc.stack_param_size:
            tc = TextCommand(cc.base_name, cc.translation_name, cc.inline_param_size)
            for size in cc.stack_param_size:
                assert len(self.stack_index) >= size
                sp = StackParam(self.stack_index[0], size)
                del self.stack_index[0:size]
                tc.stack_param.append(sp)
            if tc.base_name:
                self.commands.append(tc)

    def push_word(self, cc: ControlCode) -> None:
        self.stack_index[:0] = [-1, -1]

    def rotate_words(self, cc: ControlCode) -> None:
        assert len(self.stack_index) >= 8
        self.stack_index[0:8] = self.stack_index[6:8] + self.stack_index[0:6]

    def get_stack_types(self) -> dict[int, tuple[CommandName, int]]:
        result = dict()
        for tc in self.commands:
            for sp in tc.stack_param:
                for i in range(sp.size):
                    result[sp.offset + i] = (CommandName(tc.base_name, tc.translation_name), i)
        return result


@dataclass
class ControlCode(CommandName):
    inline_param_size: int = 0
    stack_param_size: list[int] = field(default_factory=list)
    command_handler: Callable[[TextRefStack, ControlCode], None] = TextRefStack.standard_command


# Mapping for NewGRF text codes into UTF-8 characters if possible.
CTRL_CODES = {
    0x01: ControlCode(inline_param_size=1),  # SETX
    0x0E: ControlCode(base_name="{TINY_FONT}"),  # OTTD and NML differ in spelling
    0x0F: ControlCode(base_name="{BIG_FONT}"),  # OTTD and NML differ in spelling
    0x1F: ControlCode(inline_param_size=2),  # SETXY
    0x7B: ControlCode(base_name="{COMMA}", stack_param_size=[4]),
    0x7C: ControlCode(base_name="{COMMA}", stack_param_size=[2]),
    0x7D: ControlCode(base_name="{COMMA}", stack_param_size=[1]),
    0x7E: ControlCode(base_name="{COMMA}", stack_param_size=[2]),
    0x7F: ControlCode(base_name="{CURRENCY_LONG}", stack_param_size=[4]),
    0x80: ControlCode(base_name="{STRING}", stack_param_size=[2]),
    0x81: ControlCode(base_name="{STRING}", inline_param_size=2),  # inline string
    0x82: ControlCode(base_name="{DATE_LONG}", stack_param_size=[2]),
    0x83: ControlCode(base_name="{DATE_SHORT}", stack_param_size=[2]),
    0x84: ControlCode(base_name="{SPEED}", stack_param_size=[2]),
    0x85: ControlCode(stack_param_size=[2]),  # discard int16
    0x86: ControlCode(command_handler=TextRefStack.rotate_words),  # rotate 4 int16  (W4 W1 W2 W3)
    0x87: ControlCode(base_name="{VOLUME_LONG}", stack_param_size=[2]),
    0x88: ControlCode(base_name="{BLUE}"),
    0x89: ControlCode(base_name="{SILVER}"),
    0x8A: ControlCode(base_name="{GOLD}"),
    0x8B: ControlCode(base_name="{RED}"),
    0x8C: ControlCode(base_name="{PURPLE}"),
    0x8D: ControlCode(base_name="{LTBROWN}"),
    0x8E: ControlCode(base_name="{ORANGE}"),
    0x8F: ControlCode(base_name="{GREEN}"),
    0x90: ControlCode(base_name="{YELLOW}"),
    0x91: ControlCode(base_name="{DKGREEN}"),
    0x92: ControlCode(base_name="{CREAM}"),
    0x93: ControlCode(base_name="{BROWN}"),
    0x94: ControlCode(base_name="{WHITE}"),
    0x95: ControlCode(base_name="{LTBLUE}"),
    0x96: ControlCode(base_name="{GRAY}"),
    0x97: ControlCode(base_name="{DKBLUE}"),
    0x98: ControlCode(base_name="{BLACK}"),
    0x99: ControlCode(inline_param_size=1),  # inline company color
    0x9E: ControlCode(base_name="\u20ac"),  # Euro
    0x9F: ControlCode(base_name="\u0178"),  # Y with diaeresis
    0xA0: ControlCode(base_name="{UP_ARROW}"),
    0xAA: ControlCode(base_name="{DOWN_ARROW}"),
    0xAC: ControlCode(base_name="{CHECKMARK}"),
    0xAD: ControlCode(base_name="{CROSS}"),
    0xAF: ControlCode(base_name="{RIGHT_ARROW}"),
    0xB4: ControlCode(base_name="{TRAIN}"),
    0xB5: ControlCode(base_name="{LORRY}"),
    0xB6: ControlCode(base_name="{BUS}"),
    0xB7: ControlCode(base_name="{PLANE}"),
    0xB8: ControlCode(base_name="{SHIP}"),
    0xB9: ControlCode(base_name="\u208b\u2081"),  # Superscript m1
    0xBC: ControlCode(base_name="{SMALL_UP_ARROW}"),
    0xBD: ControlCode(base_name="{SMALL_DOWN_ARROW}"),
}

EXT_CTRL_CODES = {
    0x00: ControlCode(base_name="{CURRENCY_LONG}", stack_param_size=[8]),
    0x01: ControlCode(base_name="{CURRENCY_LONG}", stack_param_size=[8]),
    0x02: ControlCode(),  # skip color byte
    0x03: ControlCode(inline_param_size=2, command_handler=TextRefStack.push_word),  # PUSH_WORD
    0x04: ControlCode(inline_param_size=1),  # unprint
    0x06: ControlCode(base_name="{HEX}", stack_param_size=[1]),
    0x07: ControlCode(base_name="{HEX}", stack_param_size=[2]),
    0x08: ControlCode(base_name="{HEX}", stack_param_size=[4]),
    0x0B: ControlCode(base_name="{HEX}", stack_param_size=[8]),
    0x0C: ControlCode(base_name="{STATION}", stack_param_size=[2]),
    0x0D: ControlCode(base_name="{WEIGHT_LONG}", stack_param_size=[2]),
    0x0E: ControlCode(inline_param_size=1),  # TODO set gender
    0x0F: ControlCode(inline_param_size=1),  # TODO select case
    0x10: ControlCode(inline_param_size=1),  # TODO begin choice
    0x11: ControlCode(inline_param_size=1),  # TODO begin default
    0x12: ControlCode(),  # TODO end choice
    0x13: ControlCode(inline_param_size=1),  # TODO begin gender choice
    0x14: ControlCode(),  # TODO begin case choice
    0x15: ControlCode(inline_param_size=1),  # TODO begin plural choice
    0x16: ControlCode(base_name="{DATE_LONG}", stack_param_size=[4]),
    0x17: ControlCode(base_name="{DATE_SHORT}", stack_param_size=[4]),
    0x18: ControlCode(base_name="{POWER}", stack_param_size=[2]),
    0x19: ControlCode(base_name="{VOLUME_SHORT}", stack_param_size=[2]),
    0x1A: ControlCode(base_name="{WEIGHT_SHORT}", stack_param_size=[2]),
    0x1B: ControlCode(base_name="{CARGO_LONG}", stack_param_size=[2, 2]),
    0x1C: ControlCode(base_name="{CARGO_SHORT}", stack_param_size=[2, 2]),
    0x1D: ControlCode(base_name="{CARGO_TINY}", stack_param_size=[2, 2]),
    0x1E: ControlCode(base_name="{CARGO_NAME}", stack_param_size=[2]),
    0x1F: ControlCode(base_name="{PUSH_COLOUR}"),
    0x20: ControlCode(base_name="{POP_COLOUR}"),
    0x21: ControlCode(base_name="{FORCE}", stack_param_size=[4]),
}

ALIASES = {
    "\u000d": "{}",
    "{": "{{}",
    "\u00a0": "{NBSP}",
    "\u00a9": "{COPYRIGHT}",
    "\u200e": "{LRM}",
    "\u200f": "{RLM}",
    "\u202a": "{LRE}",
    "\u202b": "{RLE}",
    "\u202d": "{LRO}",
    "\u202e": "{RLO}",
    "\u202c": "{PDF}",
}


def getutf8(b: bytes, pos: int) -> tuple[int, Optional[int]]:
    if pos + 1 <= len(b) and (b[pos] & 0x80) == 0:
        return (1, b[pos])
    elif pos + 2 <= len(b) and (b[pos] & 0xE0) == 0xC0 and (b[pos + 1] & 0xC0) == 0x80:
        return (2, (b[pos] & 0x1F) << 6 | (b[pos + 1] & 0x3F))
    elif pos + 3 <= len(b) and (b[pos] & 0xF0) == 0xE0 and (b[pos + 1] & 0xC0) == 0x80 and (b[pos + 2] & 0xC0) == 0x80:
        return (3, (b[pos] & 0x0F) << 12 | (b[pos + 1] & 0x3F) << 6 | (b[pos + 2] & 0x3F))
    elif (
        pos + 4 <= len(b)
        and (b[pos] & 0xF8) == 0xF0
        and (b[pos + 1] & 0xC0) == 0x80
        and (b[pos + 2] & 0xC0) == 0x80
        and (b[pos + 3] & 0xC0) == 0x80
    ):
        return (
            4,
            (b[pos] & 0x07) << 18 | (b[pos + 1] & 0x3F) << 12 | (b[pos + 2] & 0x3F) << 6 | (b[pos + 3] & 0x3F),
        )
    else:
        return (0, None)


def decodestr(b: bytes) -> tuple[str, dict[int, tuple[CommandName, int]]]:
    pos = 0
    is_unicode = getutf8(b, pos) == (2, 0x00DE)
    if is_unicode:
        pos += 2
    result = ""
    stack = TextRefStack()
    while pos < len(b):
        if is_unicode:
            size, c = getutf8(b, pos)
            if size == 0:
                c = 0xE000 + b[pos]
                pos += 1
            else:
                assert c is not None
                pos += size
        else:
            c = b[pos]
            pos += 1
            if c in CTRL_CODES or c == 0x9A:
                c = 0xE000 + c

        if c == 0xE09A:
            c = b[pos]
            pos += 1
            cc = EXT_CTRL_CODES.get(c, ControlCode())
            cc.command_handler(stack, cc)
            pos += cc.inline_param_size
            result += cc.translation_name
        elif c >= 0xE000 and c <= 0xE0FF:
            cc = CTRL_CODES.get(c - 0xE000, ControlCode())
            cc.command_handler(stack, cc)
            pos += cc.inline_param_size
            result += cc.translation_name
        elif c >= 32 or c == 13:
            s = chr(c)
            result += ALIASES.get(s, s)

    return result, stack.get_stack_types()


def process_string(raw: dict[int, bytes]) -> dict[int, str]:
    if 0x7F not in raw:
        raise RuntimeError("Missing base language text")

    base_text, stack = decodestr(raw[0x7F])
    result = {0x7F: base_text}

    for lang_id, raw_text in raw.items():
        text, _ = decodestr(raw_text)
        result[lang_id] = text

    return result
