from collections import OrderedDict
from pathlib import Path
from typing import List

from pydantic import BaseModel

from .constants import sub_format_list, video_format_list


class VideoInfo(BaseModel):
    video_name: str
    subtitle_path: str
    video_path: Path
    have_subtitle: bool


def have_subtitle(video: Path) -> bool:
    video_path = video.resolve().parent
    video_stem = video.stem
    for sub_ext in sub_format_list:
        if (video_path / f"{video_stem}{sub_ext}").exists():
            return True
        if (video_path / f"{video_stem}.zh{sub_ext}").exists():
            return True
    return False


def get_path_name(input_str: str) -> List[VideoInfo]:
    """ 传入输入的视频名称或路径"""
    input_path = Path(input_str)
    if input_path.is_dir():
        return [v for f in input_path.iterdir() for v in get_path_name(f)]
    elif input_path.suffix.lower() not in video_format_list:
        return []
    else:
        return [
            VideoInfo(
                video_name=input_path.name,
                subtitle_path=str(input_path.parent.resolve()),
                video_path=input_path,
                have_subtitle=have_subtitle(input_path),
            )
        ]
