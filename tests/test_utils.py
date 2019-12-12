from typing import List

import pytest

from getsubtitle.utils import get_info_dict, get_jaccard_sim, get_keywords


@pytest.mark.parametrize(
    "filename,must_includes",
    [
        [
            "The.Morning.Show.S01E06.The.Pendulum.Swings.1080p.WEB-DL.DD5.1.H264-MZABI[rarbg].mkv",
            ["The Morning Show", "s01", "e06"],
        ]
    ],
)
def test_get_keywords(filename: str, must_includes: List[str]):
    info_dict = get_info_dict(filename)
    keywords = get_keywords(info_dict)
    for must_include in must_includes:
        for keyword in keywords:
            if must_include in keyword:
                break
        else:
            raise Exception(f"not include: {must_include}", keywords)


def test_get_jaccard_sim():
    target = "The.Morning.Show.S01E03.Chaos.is.the.New.Cocaine.1080p.WEB-DL.DD5.1.H264-MZABI[rarbg]"
    file_a = "The.Morning.Show.S01E03.Chaos.Is.the.New.Cocaine.720p.WEB-DL.DD5.1.H264-MZABI[rartv]"
    file_b = "The.Morning.Show.2019.S01E03.PROPER.1080p.WEB.H264-ELiMiNATE[rartv]"
    assert get_jaccard_sim(target, file_a) > get_jaccard_sim(target, file_b)
