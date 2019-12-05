from typing import Callable, Optional

from pydantic import BaseModel


class SubtitleLanguage(BaseModel):
    zh_hans: bool = False
    zh_hant: bool = False
    eng: bool = False


def get_subtitle_languages(name: str) -> SubtitleLanguage:
    language = SubtitleLanguage()
    if "英文" in name or "eng" in name:
        language.eng = True
    if "简体" in name or "chs" in name:
        language.zh_hans = True
    if "繁体" in name or "cht" in name:
        language.zh_hant = True
    return language


class SubtitleFile(BaseModel):
    datatype: str
    content: bytes


class Subtitle(BaseModel):
    title: str
    version: str
    language: SubtitleLanguage
    link: str
    download: Callable[[], Optional[SubtitleFile]]
