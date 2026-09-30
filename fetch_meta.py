#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_meta.py — 抓取网易云歌单的 标题/歌手/专辑/封面，落盘 songs_meta.json + covers_b64.json。
只做网络请求与写文件，不读取本地音频。
依赖: requests, music_dl.py(同目录)
用法: python fetch_meta.py [歌单ID]
"""
import sys, os, time, base64, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
import music_dl as nd

nd.PROXY = None  # 元数据/封面走 music.163.com 官方直连，不需要 VIP 解析站代理
HERE = os.path.dirname(os.path.abspath(__file__))
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 310049166
META = os.path.join(HERE, "songs_meta.json")
COV = os.path.join(HERE, "covers_b64.json")
HDR = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}

ids = nd.playlist_track_ids(PID)
songs, cover_map = [], {}
for i in range(0, len(ids), 200):
    batch = ids[i:i + 200]
    r = requests.get("https://music.163.com/api/song/detail/",
                     params={"id": batch[0], "ids": str(batch)},
                     headers=nd.H, timeout=25, verify=False)
    for s in r.json().get("songs", []):
        ar = " / ".join(a["name"] for a in s.get("artists", s.get("ar", [])))
        al = (s.get("album") or {})
        name = s["name"]; artist = ar; album = al.get("name", ""); pic = al.get("picUrl", "")
        if pic and pic not in cover_map:
            try:
                rr = requests.get(pic, timeout=20, verify=False, headers=HDR)
                cover_map[pic] = base64.b64encode(rr.content).decode() if (rr.status_code == 200 and rr.content[:3] == b"\xff\xd8\xff") else ""
            except Exception:
                cover_map[pic] = ""
            time.sleep(0.25)
        base = nd.san(f"{nd.norm(name)} - {nd.norm(artist)}")
        songs.append({"base": base, "title": nd.norm(name), "artist": nd.norm(artist),
                      "album": nd.norm(album), "pic": pic})
    time.sleep(0.4)
json.dump({"songs": songs, "cover_map": cover_map},
          open(META, "w", encoding="utf-8"), ensure_ascii=False)
real = {k: v for k, v in cover_map.items() if v}
json.dump(real, open(COV, "w", encoding="utf-8"), ensure_ascii=False)
print(f"已存 {len(songs)} 首 -> {META}; 真实封面 {len(real)}/{len(cover_map)} 张 -> {COV}")
