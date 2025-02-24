## Extract language files from NewGRF

This CLI tool extracts `.txt` language files from `.grf` files.
See OpenTTD/OpenTTD#13541 for context.


### Usage

```
Usage: python -m grf2txt [OPTIONS] GRF_FILE

  Extract language files from NewGRF.

Options:
  --lang-info-cache FILE    File path for caching downloaded language infos
                            [default:
                            /.../grf2text/langinfos.json]
  -l, --lang-dir DIRECTORY  Sub directory for output language files  [default:
                            lang]
  -u, --unnamed-strings     Extract strings without string id
  --help                    Show this message and exit.
```


### Development

There is a `Makefile` to setup a venv, run formatting, tests, ...

```
make
```
