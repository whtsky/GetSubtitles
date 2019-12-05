import os
import os.path
import re
from typing import List, Tuple

from guessit import guessit

from .constants import service_short_names
from .sys_global_var import prefix


def get_type_score(text: str) -> int:
    type_score = 0
    type_score += ("英文" in text) * 1
    type_score += ("eng" in text) * 1
    type_score += ("简体" in text) * 2
    type_score += ("chs" in text) * 2
    type_score += ("cht" in text) * 4
    type_score += ("繁体" in text) * 4
    type_score += ("中英" in text) * 8
    return type_score


c_pattern = re.compile("[\u4e00-\u9fff]")
e_pattern = re.compile("[a-zA-Z]")


def get_info_dict(name: str):
    name = name.replace("[", "")
    name = name.replace("]", "")
    info_dict = guessit(name)

    # 若视频名中英混合，去掉字少的语言
    title = info_dict.get("title", "")

    c_num = len(c_pattern.findall(title))
    e_num = len(e_pattern.findall(title))
    if c_num > e_num:
        title = e_pattern.sub("", title)
    else:
        title = c_pattern.sub("", title)
    info_dict["title"] = title.strip()
    return info_dict


must_matches = ["title", "streaming_service", "season", "episode", "source"]


def video_match(a: Tuple[str, dict], b: Tuple[str, dict]):
    if not isinstance(a, dict):
        a = get_info_dict(a)
    if not isinstance(b, dict):
        b = get_info_dict(b)

    for keyword in must_matches:
        if a.get(keyword) != b.get(keyword):
            return False
    return True


def get_best_subtitle(subtitle_names: List[str], video_info: dict):
    """ 传入字幕列表，视频信息，返回最佳字幕名称。
        若没有符合字幕，查询模式下返回第一条字幕， 否则返回None """

    if not subtitle_names:
        print(prefix + " warn: " + "no subtitle in this archive")
        return None
    current_max_score = 0
    current_max_subtitle = None
    for subtitle_name in subtitle_names:
        filename = os.path.split(subtitle_name)[-1]  # 提取文件名
        try:
            filename = filename.encode("cp437").decode("gbk")
        except:
            pass
        if not video_match(subtitle_name, video_info):
            print(f"{subtitle_name} dismatch, continue")
            continue
        score = get_type_score(filename)
        score += ("ass" in filename or "ssa" in filename) * 2
        score += ("srt" in filename) * 1

        if score > current_max_score:
            current_max_score = score
            current_max_subtitle = subtitle_name
    return current_max_subtitle


def get_keywords(info_dict):
    """ 解析视频名
        返回将各个关键字按重要度降序排列的列表，原始视频信息 """

    keywords = []

    # 若视频名中英混合，去掉字少的语言
    title = info_dict["title"]

    base_keyword = title
    # if info_dict.get('year') and info_dict.get('type') == 'movie':
    #    base_keyword += (' ' + str(info_dict['year']))  # 若为电影添加年份
    if info_dict.get("season"):
        base_keyword += " s%s" % str(info_dict["season"]).zfill(2)
    keywords.append(base_keyword)
    if info_dict.get("episode"):
        keywords.append(" e%s" % str(info_dict["episode"]).zfill(2))
    if info_dict.get("format"):
        keywords.append(info_dict["format"])
    if info_dict.get("release_group"):
        keywords.append(info_dict["release_group"])
    if info_dict.get("streaming_service"):
        service_name = info_dict["streaming_service"]
        short_names = service_short_names.get(service_name.lower())
        if short_names:
            keywords.append(short_names)
    if info_dict.get("screen_size"):
        keywords.append(str(info_dict["screen_size"]))
    return keywords
