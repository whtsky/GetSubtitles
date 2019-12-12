# coding: utf-8


import argparse
import logging
import os
import re
import sys
from collections import OrderedDict
from traceback import format_exc
from typing import List

import chardet
import pkg_resources
from requests import exceptions

import getsubtitle.subhd
import getsubtitle.zimuku
import getsubtitle.zimuzu

from .archive import extract_subtitle
from .constants import (sub_format_list, supportted_compression_extension,
                        video_format_list)
from .models import Subtitle
from .path import VideoInfo, get_path_name
from .subtitle import choose_subtitle
from .sys_global_var import prefix
from .utils import get_info_dict, get_keywords, video_match

try:
    __version__ = pkg_resources.get_distribution("getsubtitle").version
except pkg_resources.DistributionNotFound:
    __version__ = "dev"


class GetSubtitles(object):
    def __init__(
        self, name, query, single, save_original, both, over, plex, sub_num, downloader,
    ):
        self.sub_num = int(sub_num)
        self.arg_name = name
        self.both = both
        self.query, self.single = query, single
        self.save_original, self.over = save_original, over
        self.plex = plex
        self.s_error = ""
        if not downloader:
            self.downloader = [
                getsubtitle.subhd.get_subtitles,
                getsubtitle.zimuzu.get_subtitles,
                getsubtitle.zimuku.get_subtitles,
            ]
        elif downloader == "subhd":
            self.downloader = [getsubtitle.subhd.get_subtitles]
        elif downloader == "zimuzu":
            self.downloader = [getsubtitle.zimuzu.get_subtitles]
        elif downloader == "zimuku":
            self.downloader = [getsubtitle.zimuku.get_subtitles]
        else:
            print("no such downloader")
            sys.exit(1)
        self.failed_list = []  # [{'name', 'path', 'error', 'trace_back'}

    def process_archive(
        self,
        video_info: VideoInfo,
        choosen_subtitle: Subtitle,
        link,
        info_dict,
        rename=True,
        delete=True,
    ):
        subtitle_file = choosen_subtitle.download()
        if not subtitle_file:
            return None
        datatype = subtitle_file.datatype
        sub_data_bytes = subtitle_file.content
        extract_sub_names = []

        if self.save_original:  # 保存原字幕压缩包
            if rename:
                archive_new_name = video_info.video_name + datatype
            else:
                archive_new_name = choosen_subtitle.title + datatype
            with open(archive_new_name, "wb") as f:
                f.write(sub_data_bytes)
            print(prefix + " save original file.")
        # 获得猜测字幕名称
        # 查询模式必有返回值，自动模式无猜测值返回None
        extract_sub_names = extract_subtitle(
            video_info.video_name,
            video_info.subtitle_path,
            choosen_subtitle.title,
            sub_data_bytes,
            info_dict,
            rename,
            self.single,
            self.both,
            self.plex,
            delete=delete,
        )
        if not extract_sub_names:
            return None
        for extract_sub_name, extract_sub_type in extract_sub_names:
            extract_sub_name = extract_sub_name.split("/")[-1]
            try:
                # zipfile: Historical ZIP filename encoding
                # try cp437 encoding
                extract_sub_name = extract_sub_name.encode("cp437").decode("gbk")
            except:
                pass
            try:
                print(prefix + " " + extract_sub_name)
            except UnicodeDecodeError:
                print(prefix + " " + extract_sub_name.encode("gbk"))
        return extract_sub_names

    def start(self):
        videos = get_path_name(self.arg_name)
        for video_info in videos:
            logging.debug(video_info)

            self.s_error = ""  # 重置错误记录

            info_dict = get_info_dict(video_info.video_name)
            keywords = get_keywords(info_dict)
            print("\n" + prefix + " " + video_info.video_name)  # 打印当前视频及其路径
            print(prefix + " " + video_info.subtitle_path + "\n" + prefix)

            if video_info.have_subtitle and not self.over:
                print(prefix + " subtitle already exists, add '-o' to replace it.")
                continue

            subs: List[Subtitle] = []
            while keywords and not subs:
                keyword = " ".join(keywords)
                print(f"{prefix} Searching use keyword: {keyword}")
                for downloader in self.downloader:
                    try:
                        subtitles = downloader(keyword)
                        for subtitle in subtitles:
                            logging.debug(subtitle.version)
                            if not video_match(subtitle.version, info_dict):
                                continue
                            subs.append(subtitle)
                    except (exceptions.Timeout, exceptions.ConnectionError):
                        print(prefix + " connect timeout, search next site.")
                logging.debug(subs)
                keywords = keywords[:-1]
            if not subs:
                self.s_error += "no search results. "
                continue

            extract_sub_names = []

            # 遍历字幕包直到有猜测字幕
            while not extract_sub_names and subs:
                chosen_subtitle = choose_subtitle(subs, interactive=self.query)
                link = chosen_subtitle.link
                try:
                    n_extract_sub_names = self.process_archive(
                        video_info, chosen_subtitle, link, info_dict,
                    )
                except:
                    logging.exception("failed to extract sub")
                    subs.remove(chosen_subtitle)
                else:
                    if not n_extract_sub_names:
                        print(prefix + " no matched subtitle in this archive")
                        continue
                    else:
                        extract_sub_names += n_extract_sub_names
            if not extract_sub_names and not subs:
                # 自动模式下所有字幕包均没有猜测字幕
                self.s_error += " failed to guess one subtitle,"
                self.s_error += "use '-q' to try query mode."

            if self.s_error:
                self.failed_list.append(
                    {
                        "video": video_info,
                        "error": self.s_error,
                    }
                )
                print(prefix + " error:" + self.s_error)

        if len(self.failed_list):
            print("\n===============================", end="")
            print("FAILED LIST===============================\n")
            for i, data in enumerate(self.failed_list):
                video_info = data["video"]
                print("%2s. name: %s" % (i + 1, video_info.video_name))
                print("%3s path: %s" % ("", video_info.subtitle_path))
                print("%3s info: %s" % ("", data["error"]))
        print(
            "\ntotal: %s  success: %s  fail: %s\n"
            % (
                len(videos),
                len(videos) - len(self.failed_list),
                len(self.failed_list),
            )
        )


def main():

    arg_parser = argparse.ArgumentParser(
        description="download subtitles easily",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    arg_parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )
    arg_parser.add_argument(
        "name", help="the video's name or full path or a dir with videos"
    )
    arg_parser.add_argument(
        "-q",
        "--query",
        action="store_true",
        help="show search results and choose one to download",
    )
    arg_parser.add_argument(
        "-s",
        "--single",
        action="store_true",
        help="show subtitles in the compacted file and choose one to download",
    )
    arg_parser.add_argument(
        "-o", "--over", action="store_true", help="replace the subtitle already exists"
    )
    arg_parser.add_argument(
        "--save_original", action="store_true", help="save original download file."
    )
    arg_parser.add_argument(
        "-b",
        "--both",
        action="store_true",
        help="save .srt and .ass subtitles at the same time "
        "if two types exist in the same archive",
    )
    arg_parser.add_argument(
        "-d", "--downloader", action="store", help="choose downloader"
    )
    arg_parser.add_argument(
        "-n",
        "--number",
        action="store",
        help="set max number of subtitles to be choosen when in query mode",
    )
    arg_parser.add_argument(
        "--debug", action="store_true", help="show more info of the error"
    )
    arg_parser.add_argument(
        "--plex",
        action="store_true",
        help="add .zh to the subtitle's name for plex to recognize",
    )
    args = arg_parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.over:
        print("\nThe script will replace the old subtitles if exist...\n")

    GetSubtitles(
        args.name,
        args.query,
        args.single,
        args.save_original,
        args.both,
        args.over,
        args.plex,
        downloader=args.downloader,
        sub_num=args.number or "5",
    ).start()


if __name__ == "__main__":
    main()
