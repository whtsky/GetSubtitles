import os
import os.path
from io import BytesIO

import archi

from .constants import sub_format_list, supportted_compression_extension
from .sys_global_var import prefix
from .utils import get_best_subtitle


def extract_subtitle(
    v_name,
    v_path,
    archive_name,
    sub_data_b,
    v_info_d,
    rename,
    single,
    both,
    plex,
    delete=True,
):
    """ 接受下载好的字幕包字节数据， 猜测字幕并解压。 """

    sub_buff = BytesIO(sub_data_b)
    ar = archi.Archive(sub_buff)
    files = {a.filename: a.read() for a in ar}

    if not single:
        sub_name = get_best_subtitle(files.keys(), v_info_d)
    else:
        print(prefix)
        for i, single_subtitle in enumerate(files.keys()):
            single_subtitle = single_subtitle.split("/")[-1]
            try:
                # zipfile: Historical ZIP filename encoding
                # try cp437 encoding
                single_subtitle = single_subtitle.encode("cp437").decode("gbk")
            except:
                pass
            info = " %3s)  %s" % (str(i + 1), single_subtitle)
            print(prefix + info)

        indexes = range(len(files.keys()))
        choice = None
        while not choice:
            try:
                print(prefix)
                choice = int(input(prefix + "  choose subtitle: "))
            except ValueError:
                print(prefix + "  Error: only numbers accepted")
                continue
            if not choice - 1 in indexes:
                print(prefix + "  Error: numbers not within the range")
                choice = None
        sub_name = list(files.keys())[choice - 1]

    if not sub_name:  # 自动模式下无最佳猜测
        return None

    os.chdir(v_path)  # 切换到视频所在文件夹

    v_name_without_format = os.path.splitext(v_name)[0]
    # video_name + sub_type
    to_extract_types = []
    sub_title, sub_type = os.path.splitext(sub_name)
    to_extract_subs = [[sub_name, sub_type]]
    if both:
        another_sub_type = ".srt" if sub_type == ".ass" else ".ass"
        another_sub = sub_name.replace(sub_type, another_sub_type)
        if another_sub in files:
            to_extract_subs.append([another_sub, another_sub_type])
        else:
            print(prefix + " no %s subtitles in this archive" % another_sub_type)

    if delete:
        for one_sub_type in sub_format_list:  # 删除若已经存在的字幕
            if os.path.exists(v_name_without_format + one_sub_type):
                os.remove(v_name_without_format + one_sub_type)
            if os.path.exists(v_name_without_format + ".zh" + one_sub_type):
                os.remove(v_name_without_format + ".zh" + one_sub_type)

    for one_sub, one_sub_type in to_extract_subs:
        if rename:
            if plex:
                sub_new_name = v_name_without_format + ".zh" + one_sub_type
            else:
                sub_new_name = v_name_without_format + one_sub_type
        else:
            sub_new_name = one_sub
        with open(sub_new_name, "wb") as sub:  # 保存字幕
            sub.write(files[sub_name])

    return to_extract_subs
