import re
from typing import List

from .models import Subtitle
from .sys_global_var import prefix


def choose_subtitle(subs: List[Subtitle], interactive: bool = False) -> Subtitle:
    """ 传入候选字幕字典
        若为查询模式返回选择的字幕包名称，字幕包下载地址
        否则返回字幕字典第一个字幕包的名称，字幕包下载地址 """

    if not interactive:
        return subs[0]

    for i, subtitle in enumerate(subs):
        lang_info = ""
        lang_info += "【简】" if subtitle.language.zh_hans else "      "
        lang_info += "【繁】" if subtitle.language.zh_hant else "      "
        lang_info += "【英】" if subtitle.language.eng else "      "
        a_sub_info = " %3s) %s  %s" % (i + 1, lang_info, subtitle.title)
        a_sub_info = prefix + a_sub_info
        a_sub_info += f"({subtitle.version})"
        print(a_sub_info)

    while True:
        try:
            print(prefix)
            choice = int(input(prefix + "  choose subtitle: "))
            return subs[choice - 1]
        except ValueError:
            print(prefix + "  Error: only numbers accepted")
        except IndexError:
            print(prefix + "  Error: choice %d not within the range" % choice)
