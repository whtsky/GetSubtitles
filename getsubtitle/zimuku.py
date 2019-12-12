#!/usr/bin/python3
# coding: utf-8

from collections import OrderedDict as order_dict
from contextlib import closing
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import (Subtitle, SubtitleFile, SubtitleLanguage,
                     get_subtitle_languages)
from .progress_bar import ProgressBar
from .sys_global_var import prefix

""" Zimuku 字幕下载器
"""
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5)\
                            AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
    "Accept-Language": "zh-CN,zh;q=0.8",
    "Accept": "text/html,application/xhtml+xml,\
                        application/xml;q=0.9,image/webp,*/*;q=0.8",
}
site_url = "http://www.zimuku.la"
search_url = "http://www.zimuku.la/search?q="


def download_file(file_name, download_link, session):
    try:
        if not session:
            session = requests.session()
        with closing(session.get(download_link, stream=True)) as response:
            filename = response.headers["Content-Disposition"]
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
    if ".rar" in filename:
        datatype = ".rar"
    elif ".zip" in filename:
        datatype = ".zip"
    elif ".7z" in filename:
        datatype = ".7z"
    else:
        datatype = "Unknown"

    return SubtitleFile(datatype=datatype, content=sub_data_bytes)


def get_subtitles(keyword: str):
    print(prefix + " Searching ZIMUKU...")
    subs = []
    s = requests.session()
    s.headers.update(headers)

    # 当前关键字搜索
    r = s.get(search_url + keyword, timeout=10)
    html = r.text

    if "搜索不到相关字幕" in html:
        return []

    bs_obj = BeautifulSoup(r.text, "html.parser")

    if bs_obj.find("div", {"class": "item"}):
        # 综合搜索页面
        for item in bs_obj.find_all("div", {"class": "item"}):
            title_boxes = item.find("div", {"class": "title"}).find_all("p")
            title_box = title_boxes[0]
            sub_title_box = title_boxes[1]
            item_title = title_box.text
            item_sub_title = sub_title_box.text
            for a in item.find_all("td", {"class": "first"})[:3]:
                a = a.a
                a_link = site_url + a.attrs["href"]
                a_title = a.text
                r = s.get(a_link, timeout=60)
                bs_obj = BeautifulSoup(r.text, "html.parser")
                lang_box = bs_obj.find("ul", {"class": "subinfo"}).find("li")
                type_score = 0
                language = SubtitleLanguage()
                for lang in lang_box.find_all("img"):
                    if "uk" in lang.attrs["src"]:
                        language.eng = True
                    elif "hongkong" in lang.attrs["src"]:
                        language.zh_hant = True
                    elif "china" in lang.attrs["src"]:
                        language.zh_hans = True
                download_link = bs_obj.find("a", {"id": "down1"}).attrs["href"]
                download_link = urljoin(site_url, download_link)
                r = s.get(download_link, timeout=60)
                bs_obj = BeautifulSoup(r.text, "html.parser")
                download_link = bs_obj.find("a", {"rel": "nofollow"})
                download_link = download_link.attrs["href"]
                download_link = urljoin(site_url, download_link)
                backup_session = requests.session()
                backup_session.headers.update(s.headers)
                backup_session.headers["Referer"] = a_link
                backup_session.cookies.update(s.cookies)
                subs.append(
                    Subtitle(
                        title=a_title,
                        version=a_title,
                        language=language,
                        link=download_link,
                        download=lambda: download_file(
                            a_title, download_link, backup_session
                        ),
                    )
                )
    elif bs_obj.find("div", {"class": "persub"}):
        # 射手字幕页面
        for persub in bs_obj.find_all("div", {"class": "persub"}):
            a_title = persub.h1.text
            a_link = site_url + persub.h1.a.attrs["href"]
            a_title = "[ZIMUKU]" + a_title

            # 射手字幕页面
            r = s.get(a_link, timeout=60)
            bs_obj = BeautifulSoup(r.text, "html.parser")
            lang_box = bs_obj.find("ul", {"class": "subinfo"}).find("li")
            text = lang_box.text
            download_link = bs_obj.find("a", {"id": "down1"}).attrs["href"]

            backup_session = requests.session()
            backup_session.headers.update(s.headers)
            backup_session.headers["Referer"] = a_link
            backup_session.cookies.update(s.cookies)
            subs.append(
                Subtitle(
                    title=a_title,
                    version=a_title,
                    language=get_subtitle_languages(text),
                    link=download_link,
                    download=lambda: download_file(
                        a_title, download_link, backup_session
                    ),
                )
            )
    else:
        raise ValueError("Zimuku搜索结果出现未知结构页面")
    return subs


if __name__ == "__main__":
    from main import GetSubtitles

    keywords, info_dict = GetSubtitles("", 1, 2, 3, 4, 5, 6, 7, 8, 9).sort_keyword(
        "the expanse s01e01"
    )
    zimuku = ZimukuDownloader()
    sub_dict = zimuku.get_subtitles(keywords)
    print("\nResult:")
    for k, v in sub_dict.items():
        print(k, v)
