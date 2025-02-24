from typing import Optional
from dataclasses import dataclass, field, asdict
from csv import DictReader
from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests
import json
import dacite


@dataclass
class LangInfo:
    isocode: str = ""
    grflangid: int = -1
    filename: str = ""
    name: str = ""
    ownname: str = ""
    plural: int = 0
    gender: list[str] = field(default_factory=list)
    case: list[str] = field(default_factory=list)


LANGINFO: list[LangInfo] = []


def _fetch_data() -> str:
    r = requests.get("https://translator.openttd.org/language-list")
    r.raise_for_status()
    assert r.status_code == 200
    return r.text


def _parse_csv(raw: str) -> list[LangInfo]:
    result = []
    reader = DictReader(StringIO(raw))
    for row in reader:
        row = dict(row)
        if "grflangid" in row:
            row["grflangid"] = int(row["grflangid"], 0)
        if "plural" in row:
            row["plural"] = int(row["plural"])
        if "gender" in row:
            row["gender"] = row["gender"].split()
        if "case" in row:
            row["case"] = row["case"].split()
        result.append(dacite.from_dict(data_class=LangInfo, data=row))
    return result


def _load_cache(filename: Path) -> Optional[list[LangInfo]]:
    try:
        result = []
        with filename.open() as f:
            raw = json.load(f)
            for row in raw:
                result.append(dacite.from_dict(data_class=LangInfo, data=row))
        return result
    except Exception:
        return None


def _store_cache(filename: Path, data: list[LangInfo]) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w") as f:
        ddata = [asdict(li) for li in data]
        json.dump(ddata, f)


def init_langinfo(cache_filename: Path) -> None:
    global LANGINFO
    if cache_filename.is_file():
        stat = cache_filename.stat()
        now = datetime.now(tz=timezone.utc)
        mtime = datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        )  # works for filesystems from this millenium, fails for ancient FAT systems
        if now < mtime + timedelta(hours=16):
            data = _load_cache(cache_filename)
            if data:
                LANGINFO = data
                return

    LANGINFO = _parse_csv(_fetch_data())
    _store_cache(cache_filename, LANGINFO)


def get_from_isocode(isocode: str) -> LangInfo:
    for info in LANGINFO:
        if info.isocode == isocode:
            return info
    raise KeyError(f"Unknown isocode '{isocode}'")


def get_from_grflangid(lang_id: int) -> LangInfo:
    for info in LANGINFO:
        if info.grflangid == lang_id:
            return info
    raise KeyError(f"Unknown grflangid '{lang_id}'")


def get_from_filename(filename: str) -> LangInfo:
    for info in LANGINFO:
        if info.filename == filename:
            return info
    raise KeyError(f"Unknown lang filename '{filename}'")
