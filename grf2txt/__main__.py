from typing import cast, BinaryIO
from pathlib import Path
import click
import platformdirs
from collections import defaultdict
from .newgrf import NewGRF
from .langdata import init_langinfo, get_from_grflangid
from .grfstrings import process_string


@click.command()
@click.option(
    "--lang-info-cache",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, path_type=Path),
    default=platformdirs.user_cache_path("grf2text", False) / "langinfos.json",
    show_default=True,
    help="File path for caching downloaded language infos",
)
@click.option(
    "-l",
    "--lang-dir",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default="lang",
    show_default=True,
    help="Sub directory for output language files",
)
@click.option(
    "-u", "--unnamed-strings", type=bool, is_flag=True, default=False, help="Extract strings without string id"
)
@click.argument("grf-file", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path))
def extract(grf_file: Path, lang_dir: Path, unnamed_strings: bool, lang_info_cache: Path) -> None:
    """
    Extract language files from NewGRF.
    """

    init_langinfo(lang_info_cache)

    newgrf = NewGRF()
    with grf_file.open("rb") as f:
        newgrf.read(cast(BinaryIO, f))

    num_unnamed_strings = 0
    num_named_strings = 0
    languages = defaultdict(list)
    indent = 40
    for key, raw_string in newgrf.strings.items():
        if not raw_string.str_name:
            num_unnamed_strings += 1
            if not unnamed_strings:
                continue
        else:
            num_named_strings += 1
            key = raw_string.str_name

        if len(key) > indent:
            indent = len(key)

        lang_string = process_string(raw_string.translations)
        if 0x7F in lang_string:
            base_text = lang_string[0x7F]
            del lang_string[0x7F]
            if 0x01 not in lang_string:
                lang_string[0x01] = base_text
            elif 0x00 not in lang_string:
                lang_string[0x00] = base_text
        for lang_id, text in lang_string.items():
            languages[lang_id].append((key, text))

    for lang_id, texts in languages.items():
        plural = newgrf.plurals.get(lang_id)
        cases = " ".join("=".join(v) for k, v in sorted(newgrf.cases.get(lang_id, dict()).items()))
        genders = " ".join("=".join(v) for k, v in sorted(newgrf.genders.get(lang_id, dict()).items()))
        file_path = grf_file.parent / lang_dir / (get_from_grflangid(lang_id).filename + ".txt")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w") as f:
            f.write(f"##grflangid 0x{lang_id:02X}\n")
            if plural is not None:
                f.write(f"##plural {plural}\n")
            if cases:
                f.write(f"##case {cases}\n")
            if genders:
                f.write(f"##gender {genders}\n")
            f.write("\n")
            for key, value in texts:
                f.write(f"{key:<{indent}}:{value}\n")

    print(f"Translations: {len(languages)}\nNamed strings: {num_named_strings}\nUnnamed strings: {num_unnamed_strings}")


if __name__ == "__main__":
    extract()
