#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tag_all.py — 给下载好的音乐文件补写 标题/歌手/专辑/封面。
读取 songs_meta.json(元数据) + covers_b64.json(真实封面 base64)，按文件名匹配，
用 mutagen 写入 FLAC/MP3。原子替换，失败不破坏原文件。
用法: python tag_all.py [--out F:/music]
依赖: mutagen（托管 venv python 已自带）；requests 不需要。
"""
import os, sys, json, base64, subprocess, time, uuid
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, ID3NoHeaderError, APIC, TIT2, TPE1, TALB

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("MUSIC_OUT", "F:/music")
META = os.path.join(HERE, "songs_meta.json")
COV = os.path.join(HERE, "covers_b64.json")


def norm(b):
    return b.replace(" (Live)", "(Live)")


def cat_read(f, retries=6):
    """读文件全部字节；用 cat 以兼容沙箱/只读挂载环境，校验长度防截断。"""
    for _ in range(retries):
        rr = subprocess.run(["cat", f], capture_output=True)
        if rr.returncode == 0 and len(rr.stdout) == os.path.getsize(f):
            return rr.stdout
        time.sleep(0.3)
    return None


def main():
    meta = json.load(open(META, encoding="utf-8"))
    cov = json.load(open(COV, encoding="utf-8")) if os.path.exists(COV) else {}
    by_base = {s["base"]: s for s in meta["songs"]}
    files = sorted(x for x in os.listdir(OUT)
                   if x.lower().endswith((".flac", ".mp3")) and not x.startswith("_"))
    ok = miss = locked = nopic = 0
    for fn in files:
        base = os.path.splitext(fn)[0]
        s = by_base.get(base) or by_base.get(norm(base))
        if not s:
            miss += 1
            continue
        p = os.path.join(OUT, fn)
        data = cat_read(p)
        if data is None:
            locked += 1
            continue
        ext = os.path.splitext(fn)[1].lower()
        tmp = os.path.join(OUT, "_tag_%d_%s%s" % (os.getpid(), uuid.uuid4().hex[:8], ext))
        open(tmp, "wb").write(data)
        cover = base64.b64decode(cov[s["pic"]]) if (s.get("pic") and cov.get(s["pic"])) else b""
        try:
            if ext == ".flac":
                f = FLAC(tmp)
                f["title"] = [s["title"]]
                f["artist"] = [s["artist"]]
                f["album"] = [s["album"]]
                f.clear_pictures()
                if cover:
                    pic = Picture()
                    pic.type = 3
                    pic.desc = "cover"
                    pic.mime = "image/jpeg"
                    pic.data = cover
                    f.add_picture(pic)
                f.save()
            else:
                try:
                    t = ID3(tmp)
                except ID3NoHeaderError:
                    t = ID3()
                t["TIT2"] = TIT2(encoding=3, text=s["title"])
                t["TPE1"] = TPE1(encoding=3, text=s["artist"])
                t["TALB"] = TALB(encoding=3, text=s["album"])
                if cover:
                    t["APIC"] = APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover)
                t.save(tmp, v2_version=3)
        except Exception as e:
            try:
                os.remove(tmp)
            except Exception:
                pass
            print("ERR", fn, e)
            continue
        if os.path.getsize(tmp) < 1000:
            try:
                os.remove(tmp)
            except Exception:
                pass
            continue
        try:
            os.replace(tmp, p)
        except PermissionError:
            try:
                os.remove(tmp)
            except Exception:
                pass
            locked += 1
            continue
        ok += 1
        if not cover:
            nopic += 1
    print("done ok=%d miss=%d locked=%d no_cover=%d total=%d" % (ok, miss, locked, nopic, len(files)))


if __name__ == "__main__":
    if "--out" in sys.argv:
        OUT = sys.argv[sys.argv.index("--out") + 1]
    main()
