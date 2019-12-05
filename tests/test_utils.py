from typing import List

import pytest

from getsubtitle.utils import get_info_dict, get_keywords


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
