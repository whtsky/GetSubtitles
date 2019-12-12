# coding: utf-8

import json
from contextlib import closing

import requests
from bs4 import BeautifulSoup

from .models import Subtitle, SubtitleFile, get_subtitle_languages
from .progress_bar import ProgressBar
from .sys_global_var import prefix

""" Zimuzu 字幕下载器
"""

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5)\
                    AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
    "Accept-Language": "zh-CN,zh;q=0.8",
    "Accept": "text/html,application/xhtml+xml,\
                application/xml;q=0.9,image/webp,*/*;q=0.8",
}
site_url = "http://www.zmz2019.com"
search_url = "http://www.zmz2019.com/search?\
                    keyword={0}&type=subtitle"


def download_file(file_name, sub_url):
    """ 传入字幕页面链接， 字幕包标题， 返回压缩包类型，压缩包字节数据 """
    s = requests.session()
    r = s.get(sub_url, headers=headers)
    bs_obj = BeautifulSoup(r.text, "html.parser")
    a = bs_obj.find("div", {"class": "subtitle-links"}).a
    download_link = a.attrs["href"]
    headers["Referer"] = download_link
    ajax_url = "http://got001.com/api/v1/static/subtitle/detail?"
    ajax_url += download_link.split("?")[-1]
    r = s.get(ajax_url, headers=headers)
    json_obj = json.loads(r.text)
    download_link = json_obj["data"]["info"]["file"]

    try:
        with closing(requests.get(download_link, stream=True)) as response:
            chunk_size = 1024  # 单次请求最大值
            if response.headers.get("content-length"):
                # 内容体总大小
                content_size = int(response.headers["content-length"])
                bar = ProgressBar(prefix + " Get", file_name.strip(), content_size)
                sub_data_bytes = b""
                for data in response.iter_content(chunk_size=chunk_size):
                    sub_data_bytes += data
                    bar.refresh(len(sub_data_bytes))
            else:
                bar = ProgressBar(prefix + " Get", file_name.strip())
                sub_data_bytes = b""
                for data in response.iter_content(chunk_size=chunk_size):
                    sub_data_bytes += data
                    bar.point_wait()
                bar.point_wait(end=True)
        # sub_data_bytes = requests.get(download_link, timeout=10).content
    except requests.Timeout:
        return None
    if "rar" in download_link:
        datatype = ".rar"
    elif "zip" in download_link:
        datatype = ".zip"
    elif "7z" in download_link:
        datatype = ".7z"
    else:
        if ".rar" in file_name:
            datatype = ".rar"
        elif ".zip" in file_name:
            datatype = ".zip"
        elif ".7z" in file_name:
            datatype = ".7z"
        else:
            datatype = "Unknown"

    return SubtitleFile(datatype=datatype, content=sub_data_bytes)


def get_subtitles(keyword):

    print(prefix + " Searching ZIMUZU...")

    subs = []
    s = requests.session()
    while True:
        # 当前关键字查询
        r = s.get(search_url.format(keyword), headers=headers, timeout=10)
        bs_obj = BeautifulSoup(r.text, "html.parser")
        tab_text = bs_obj.find("div", {"class": "article-tab"}).text
        tab_text = tab_text
        if "字幕(0)" not in tab_text:
            for one_box in bs_obj.find_all("div", {"class": "search-item"}):
                sub_name = "[ZMZ]" + one_box.find("p").find("font").text
                a = one_box.find("a")
                text = a.text
                sub_url = site_url + a.attrs["href"]
                subs.append(
                    Subtitle(
                        language=get_subtitle_languages(text),
                        link=sub_url,
                        version=one_box.find("font", "f4").text,
                        title=sub_name,
                        download=lambda: download_file(sub_name, sub_url),
                    )
                )
        break

    return subs
