from grf2txt.newgrf import NewGRF
from pathlib import Path


def test_decode():
    fn = Path(__file__).parent / "test_data" / "test.grf"
    n = NewGRF()
    with open(fn, "rb") as f:
        n.read(f)

    assert n.plurals == {1: 0, 2: 0}
    assert n.genders == {2: {1: ["m"], 2: ["f"], 3: ["n"]}}
    assert n.cases == {}

    strids = (
        "STR_GRF_NAME",
        "STR_GRF_DESCRIPTION",
        "STR_GRF_URL",
        "STR_PARAM_0_NAME",
        "STR_PARAM_0_DESCRIPTION",
        "STR_ERROR_19",
        "STR_ERROR_21",
        "STR_TRAIN_256",
        "STR_GENERIC_D000",
        "STR_STATION_CLASS_0_NAME",
        "STR_STATION_0_NAME",
    )
    assert len(strids) == len(n.strings)
    for strid in strids:
        s = n.strings[strid]
        assert 0x02 in s.translations
        assert 0x7F in s.translations
