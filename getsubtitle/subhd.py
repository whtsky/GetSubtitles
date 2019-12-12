# coding: utf-8
# !/usr/bin/env python3

import json
import logging
import re
import time
from collections import OrderedDict as order_dict
from contextlib import closing

import requests
from bs4 import BeautifulSoup

from .models import Subtitle, SubtitleFile, get_subtitle_languages
from .progress_bar import ProgressBar
from .sys_global_var import prefix

""" SubHD 字幕下载器
"""

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5)\
                            AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
    "Accept-Language": "zh-CN,zh;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,\
                            image/webp,*/*;q=0.8",
}
site_url = "https://subhd.tv"
search_url = "https://subhd.tv/search0/"


def download_file(file_name, sub_url):

    """ 传入字幕页面链接， 字幕包标题， 返回压缩包类型，压缩包字节数据 """

    sid = sub_url.split("/")[-1]
    r = requests.get(sub_url, headers=headers)
    bs_obj = BeautifulSoup(r.text, "html.parser")
    dtoken = bs_obj.find("button", {"id": "down"})["dtoken"]

    r = requests.post(
        site_url + "/ajax/down_ajax",
        data={"sub_id": sid, "dtoken": dtoken},
        headers=headers,
    )

    content = r.content.decode("unicode-escape")
    if json.loads(content)["success"] is False:
        return None
    res = re.search('http:.*(?=")', r.content.decode("unicode-escape"))
    download_link = res.group(0).replace("\\/", "/")
    try:
        with closing(requests.get(download_link, stream=True)) as response:
            chunk_size = 1024  # 单次请求最大值
            # 内容体总大小
            content_size = int(response.headers["content-length"])
            bar = ProgressBar(prefix + " Get", file_name.strip(), content_size)
            sub_data_bytes = b""
            for data in response.iter_content(chunk_size=chunk_size):
                sub_data_bytes += data
                bar.refresh(len(sub_data_bytes))
    except requests.Timeout:
        return None
    if "rar" in download_link:
        datatype = ".rar"
    elif "zip" in download_link:
        datatype = ".zip"
    elif "7z" in download_link:
        datatype = ".7z"
    else:
        datatype = "Unknown"

    return SubtitleFile(datatype=datatype, content=sub_data_bytes)


def get_subtitles(keyword: str):

    print(prefix + " Searching SUBHD...", end="\r")

    s = requests.session()
    subs = []
    r = s.get(search_url + keyword, headers=headers, timeout=10)
    bs_obj = BeautifulSoup(r.text, "html.parser")
    try:
        small_text = bs_obj.find("small").text
    except AttributeError as e:
        char_error = "The URI you submitted has disallowed characters"
        if char_error in bs_obj.text:
            print(prefix + " [SUBHD ERROR] " + char_error + ": " + keyword)
        # 搜索验证按钮
        return []

    if "总共 0 条" in small_text:
        logging.debug("No result for subhd")
        logging.debug(small_text)
        logging.debug(r.text)
    for one_box in bs_obj.find_all("div", {"class": "box"}):
        print(one_box)
        a = one_box.find("div", {"class": "d_title"}).find("a")
        sub_url = site_url + a.attrs["href"]
        sub_name = "[SUBHD]" + a.text
        text = one_box.text
        if "/ar" in a.attrs["href"]:
            subs.append(
                Subtitle(
                    title=sub_name,
                    version=a.attrs["title"],
                    language=get_subtitle_languages(text),
                    link=sub_url,
                    download=lambda: download_file(sub_name, sub_url),
                )
            )
    return subs
