# coding: utf-8

from __future__ import print_function

import argparse
import os
import re
import sys
from collections import OrderedDict
from traceback import format_exc

import chardet
import pkg_resources
from guessit import guessit
from requests import exceptions

from .archive import extract_subtitle
from .constants import (
    sub_format_list,
    supportted_compression_extension,
    video_format_list,
)
from .subhd import SubHDDownloader
from .sys_global_var import prefix
from .utils import get_info_dict, get_keywords, get_type_score, video_match
from .zimuku import ZimukuDownloader
from .zimuzu import ZimuzuDownloader

try:
    __version__ = pkg_resources.get_distribution("getsubtitle").version
except pkg_resources.DistributionNotFound:
    __version__ = "dev"


class GetSubtitles(object):

    if sys.stdout.encoding == "cp936":
        output_encode = "gbk"
    else:
        output_encode = "utf8"

    def __init__(
        self,
        name,
        query,
        single,
        save_original,
        both,
        over,
        plex,
        debug,
        sub_num,
        downloader,
        sub_path,
    ):
        self.arg_name = name
        self.sub_store_path = sub_path
        self.both = both
        self.query, self.single = query, single
        self.save_original, self.over = save_original, over
        if not sub_num:
            self.sub_num = 2
        else:
            self.sub_num = int(sub_num)
        self.plex = plex
        self.debug = debug
        self.s_error = ""
        self.f_error = ""
        self.subhd = SubHDDownloader()
        self.zimuzu = ZimuzuDownloader()
        self.zimuku = ZimukuDownloader()
        if not downloader:
            self.downloader = [self.subhd, self.zimuzu, self.zimuku]
        elif downloader == "subhd":
            self.downloader = [self.subhd]
        elif downloader == "zimuzu":
            self.downloader = [self.zimuzu]
        elif downloader == "zimuku":
            self.downloader = [self.zimuku]
        else:
            print(
                "no such downloader, "
                "please choose from 'subhd','zimuzu' and 'zimuku'"
            )
            # print("no such downloader, please choose from 'zimuzu' and 'zimuku'")
        self.failed_list = []  # [{'name', 'path', 'error', 'trace_back'}

    def get_path_name(self, mix_str, store_path):

        """ 传入输入的视频名称或路径,
            构造一个包含视频路径和是否存在字幕信息的字典返回。
            video_dict: {'path': path, 'have_subtitle': sub_exists} """

        mix_str = mix_str.replace('"', "")
        store_path = (store_path or "").replace('"', "")
        store_path_files = []
        if not os.path.isdir(store_path):
            print("no valid path specfied,download sub file to video file location.")
            store_path = ""
        else:
            for root, dirs, files in os.walk(store_path):
                store_path_files.extend(files)
        video_dict = OrderedDict()
        if os.path.isdir(mix_str):  # 一个文件夹
            for root, dirs, files in os.walk(mix_str):
                for one_name in files:
                    suffix = os.path.splitext(one_name)[1]
                    # 检查后缀是否为视频格式
                    if suffix not in video_format_list:
                        continue
                    v_name_no_format = os.path.splitext(one_name)[0]
                    sub_exists = max(
                        list(
                            map(
                                lambda sub_type: int(
                                    v_name_no_format + sub_type
                                    in files + store_path_files
                                    or v_name_no_format + ".zh" + sub_type
                                    in files + store_path_files
                                ),
                                sub_format_list,
                            )
                        )
                    )
                    video_dict[one_name] = {
                        "path": next(
                            item
                            for item in [store_path, os.path.abspath(root)]
                            if item != ""
                        ),
                        "have_subtitle": sub_exists,
                    }

        elif os.path.isabs(mix_str):  # 视频绝对路径
            v_path, v_name = os.path.split(mix_str)
            v_name_no_format = os.path.splitext(v_name)[0]
            if os.path.isdir(store_path):
                s_path = os.path.abspath(store_path)
            else:
                s_path = v_path
            sub_exists = max(
                list(
                    map(
                        lambda sub_type: os.path.exists(
                            os.path.join(s_path, v_name_no_format + sub_type)
                        ),
                        sub_format_list,
                    )
                )
            )
            video_dict[v_name] = {"path": s_path, "have_subtitle": sub_exists}
        else:  # 单个视频名字，无路径
            if not os.path.isdir(store_path):
                video_dict[mix_str] = {"path": os.getcwd(), "have_subtitle": 0}
            else:
                video_dict[mix_str] = {
                    "path": os.path.abspath(store_path),
                    "have_subtitle": 0,
                }
        return video_dict

    def choose_subtitle(self, sub_dict):

        """ 传入候选字幕字典
            若为查询模式返回选择的字幕包名称，字幕包下载地址
            否则返回字幕字典第一个字幕包的名称，字幕包下载地址 """

        if not self.query:
            chosen_sub = list(sub_dict.keys())[0]
            link = sub_dict[chosen_sub]["link"]
            session = sub_dict[chosen_sub].get("session", None)
            return [[chosen_sub, link, session]]

        for i, key in enumerate(sub_dict.keys()):
            if i == self.sub_num:
                break
            lang_info = ""
            lang_info += "【简】" if 4 & sub_dict[key]["lan"] else "      "
            lang_info += "【繁】" if 2 & sub_dict[key]["lan"] else "      "
            lang_info += "【英】" if 1 & sub_dict[key]["lan"] else "      "
            lang_info += "【双】" if 8 & sub_dict[key]["lan"] else "      "
            a_sub_info = " %3s) %s  %s" % (i + 1, lang_info, key)
            a_sub_info = prefix + a_sub_info
            if "version" in sub_dict[key]:
                a_sub_info += f"({sub_dict[key]['version']})"
            print(a_sub_info)

        indexes = range(len(sub_dict.keys()))
        choices = None
        chosen_subs = []
        while not choices:
            try:
                print(prefix)
                choices = input(prefix + "  choose subtitle: ")
                choices = [int(c) for c in re.split(",|，", choices)]
            except ValueError:
                print(prefix + "  Error: only numbers accepted")
                continue
            for choice in choices:
                if not choice - 1 in indexes:
                    print(prefix + "  Error: choice %d not within the range" % choice)
                    choices.remove(choice)
                else:
                    chosen_sub = list(sub_dict.keys())[choice - 1]
                    link = sub_dict[chosen_sub]["link"]
                    session = sub_dict[chosen_sub].get("session", None)
                    chosen_subs.append([chosen_sub, link, session])
        return chosen_subs

    def process_archive(
        self,
        video_filename,
        video_info,
        sub_choice,
        link,
        session,
        info_dict,
        rename=True,
        delete=True,
    ):
        if self.query:
            print(prefix + " ")
        if "[ZMZ]" in sub_choice:
            datatype, sub_data_bytes = self.zimuzu.download_file(sub_choice, link)
        elif "[SUBHD]" in sub_choice:
            datatype, sub_data_bytes, msg = self.subhd.download_file(sub_choice, link)
            if msg == "false":
                print(
                    prefix + " error: "
                    "download too frequently "
                    "with subhd downloader, "
                    "please change to other downloaders"
                )
                return
        elif "[ZIMUKU]" in sub_choice:
            datatype, sub_data_bytes = self.zimuku.download_file(
                sub_choice, link, session=session
            )
        extract_sub_names = []

        if self.save_original:  # 保存原字幕压缩包
            if rename:
                archive_new_name = video_filename + datatype
            else:
                archive_new_name = sub_choice + datatype
            with open(archive_new_name, "wb") as f:
                f.write(sub_data_bytes)
            print(prefix + " save original file.")
        # 获得猜测字幕名称
        # 查询模式必有返回值，自动模式无猜测值返回None
        extract_sub_names = extract_subtitle(
            video_filename,
            video_info["path"],
            sub_choice,
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

        all_video_dict = self.get_path_name(self.arg_name, self.sub_store_path)

        for video_filename, video_info in all_video_dict.items():

            self.s_error = ""  # 重置错误记录
            self.f_error = ""

            try:
                info_dict = get_info_dict(video_filename)
                keywords = get_keywords(info_dict)
                print("\n" + prefix + " " + video_filename)  # 打印当前视频及其路径
                print(prefix + " " + video_info["path"] + "\n" + prefix)

                if video_info["have_subtitle"] and not self.over:
                    print(prefix + " subtitle already exists, add '-o' to replace it.")
                    continue

                sub_dict = OrderedDict()
                for i, downloader in enumerate(self.downloader):
                    try:
                        subtitles = downloader.get_subtitles(tuple(keywords))
                        for subtitle_name, payload in subtitles.items():
                            subtitle_version = payload.get("version", subtitle_name)
                            if not video_match(subtitle_version, info_dict):
                                continue
                            else:
                                sub_dict[subtitle_name] = payload
                    except ValueError as e:
                        if str(e) == "Zimuku搜索结果出现未知结构页面":
                            print(prefix + " warn: " + str(e))
                        else:
                            raise (e)
                    except (exceptions.Timeout, exceptions.ConnectionError):
                        print(prefix + " connect timeout, search next site.")
                        if i < (len(self.downloader) - 1):
                            continue
                        else:
                            print(prefix + " PLEASE CHECK YOUR NETWORK STATUS")
                            sys.exit(0)
                    if len(sub_dict) >= self.sub_num:
                        break
                if not sub_dict:
                    self.s_error += "no search results. "
                    continue

                extract_sub_names = []

                # 遍历字幕包直到有猜测字幕
                while not extract_sub_names and sub_dict:
                    sub_choices = self.choose_subtitle(sub_dict)
                    for i, choice in enumerate(sub_choices):
                        sub_choice, link, session = choice
                        sub_dict.pop(sub_choice)
                        if i == 0:
                            n_extract_sub_names = self.process_archive(
                                video_filename,
                                video_info,
                                sub_choice,
                                link,
                                session,
                                info_dict,
                            )
                        else:
                            n_extract_sub_names = self.process_archive(
                                video_filename,
                                video_info,
                                sub_choice,
                                link,
                                session,
                                info_dict,
                                rename=False,
                                delete=False,
                            )
                        if not n_extract_sub_names:
                            print(prefix + " no matched subtitle in this archive")
                            continue
                        else:
                            extract_sub_names += n_extract_sub_names
            finally:
                if (
                    "extract_sub_names" in dir()
                    and not extract_sub_names
                    and len(sub_dict) == 0
                ):
                    # 自动模式下所有字幕包均没有猜测字幕
                    self.s_error += " failed to guess one subtitle,"
                    self.s_error += "use '-q' to try query mode."

                if self.s_error and not self.debug:
                    self.s_error += "add --debug to get more info of the error"

                if self.s_error:
                    self.failed_list.append(
                        {
                            "name": video_filename,
                            "path": video_info["path"],
                            "error": self.s_error,
                            "trace_back": self.f_error,
                        }
                    )
                    print(prefix + " error:" + self.s_error)

        if len(self.failed_list):
            print("\n===============================", end="")
            print("FAILED LIST===============================\n")
            for i, one in enumerate(self.failed_list):
                print("%2s. name: %s" % (i + 1, one["name"]))
                print("%3s path: %s" % ("", one["path"]))
                print("%3s info: %s" % ("", one["error"]))
                if self.debug:
                    print("%3s TRACE_BACK: %s" % ("", one["trace_back"]))

        print(
            "\ntotal: %s  success: %s  fail: %s\n"
            % (
                len(all_video_dict),
                len(all_video_dict) - len(self.failed_list),
                len(self.failed_list),
            )
        )

        return {
            "total": len(all_video_dict),
            "success": len(all_video_dict) - len(self.failed_list),
            "fail": len(self.failed_list),
            "fail_videos": self.failed_list,
        }


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
        "-p", "--directory", action="store", help="set specified subtitle download path"
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
        "-n",
        "--number",
        action="store",
        help="set max number of subtitles to be choosen when in query mode",
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
        "--debug", action="store_true", help="show more info of the error"
    )
    arg_parser.add_argument(
        "--plex",
        action="store_true",
        help="add .zh to the subtitle's name for plex to recognize",
    )

    args = arg_parser.parse_args()

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
        args.debug,
        sub_num=args.number,
        downloader=args.downloader,
        sub_path=args.directory,
    ).start()


if __name__ == "__main__":
    main()
