#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetEase (网易云音乐) 免费无损/标准下载器 —— 非 VIP 黑科技通道
两种入口：
  --playlist "https://music.163.com/playlist?id=XXXX&uct2=..."   歌单
  --song      "https://music.163.com/song?id=XXXX&uct2=..."      单首分享链接
  （也可直接传纯数字 id）

特性：无损优先；某首无无损则下标准 320k；断点续下；三源轮询分摊；单线程+间隔防封。
运行：托管 venv python（自带 requests）
"""
import requests, os, re, json, time, random, argparse
requests.packages.urllib3.disable_warnings()

PROXY = {"http": "http://127.0.0.1:11417", "https": "http://127.0.0.1:11417"}
H = {"User-Agent": "Mozilla/5.0", "Accept": "*/*", "Referer": "https://music.163.com/"}
GD = "https://music-api.gdstudio.xyz/api.php"
NETEASE = "https://music.163.com"

# 繁->简（保证与已下文件命名一致、不重复下）
T2S = {"風":"风","雲":"云","愛":"爱","東":"东","實":"实","產":"产","國":"国","樂":"乐",
       "會":"会","門":"门","開":"开","關":"关","車":"车","鳥":"鸟","魚":"鱼","馬":"马",
       "華":"华","語":"语","聖":"圣","師":"师","時":"时","來":"来","員":"员","則":"则",
       "義":"义","無":"无","雙":"双","願":"愿","點":"点","體":"体","條":"条","處":"处",
       "當":"当","學":"学","後":"后","這":"这","個":"个","親":"亲","長":"长","發":"发",
       "飛":"飞","說":"说","話":"话","歲":"岁","夢":"梦","麗":"丽","異":"异","聲":"声",
       "廣":"广","與":"与","係":"系","圖":"图","書":"书","館":"馆","對":"对","總":"总"}
def norm(s):
    for k, v in T2S.items():
        s = s.replace(k, v)
    return s
def san(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()

# ---------------- 输入解析 ----------------
def parse_input(text):
    """返回 ('playlist', pid) / ('song', sid) / ('id', int) / None"""
    if text is None:
        return None
    t = text.strip()
    m = re.search(r"playlist\?id=(\d+)", t)
    if m:
        return ("playlist", int(m.group(1)))
    m = re.search(r"song\?id=(\d+)", t)
    if m:
        return ("song", int(m.group(1)))
    m = re.search(r"[?&]id=(\d+)", t)
    if m:
        return ("id", int(m.group(1)))
    if re.fullmatch(r"\d+", t):
        return ("id", int(t))
    return None

# ---------------- 网易元数据 ----------------
def playlist_track_ids(pid):
    r = requests.get(f"{NETEASE}/api/v3/playlist/detail", params={"id": pid},
                     headers=H, proxies=PROXY, timeout=20, verify=False)
    return [t["id"] for t in r.json().get("playlist", {}).get("trackIds", [])]

def resolve_names(ids):
    songs = []
    for i in range(0, len(ids), 200):
        batch = ids[i:i+200]
        r = requests.get(f"{NETEASE}/api/song/detail/", params={"id": batch[0], "ids": str(batch)},
                         headers=H, proxies=PROXY, timeout=25, verify=False)
        for s in r.json().get("songs", []):
            ar = " / ".join(a["name"] for a in s.get("artists", s.get("ar", [])))
            songs.append({"id": s["id"], "name": s["name"], "artist": ar})
        time.sleep(0.4)
    return songs

# ---------------- 解析站源（代理会员接口拿网易 CDN 的 flac 链接）----------------
def gd_url(sid, br=999):
    try:
        r = requests.get(f"{GD}?types=url&id={sid}&source=netease&br={br}", proxies=PROXY, timeout=20, verify=False)
        return r.json().get("url", "")
    except Exception:
        return ""
def ffapi_url(sid):
    try:
        r = requests.get(f"https://ffapi.cn/int/v1/netease_url?id={sid}&quality=lossless", proxies=PROXY, timeout=20, verify=False)
        return r.json().get("url", "")
    except Exception:
        return ""
def haitang_url(sid):
    try:
        hdr = {**H, "Origin": "https://wyapi.toubiec.cn", "Referer": "https://wyapi.toubiec.cn/"}
        r = requests.get(f"https://musicapi.haitangw.net/music/wy.php?id={sid}&level=lossless&type=json",
                         headers=hdr, proxies=PROXY, timeout=20, verify=False)
        return r.json().get("data", {}).get("url", "")
    except Exception:
        return ""
SRC = [("gdstudio", gd_url), ("ffapi", ffapi_url), ("haitangw", haitang_url)]

def head4(u):
    if not u:
        return b""
    try:
        r = requests.get(u, headers={"Range": "bytes=0-3"}, proxies=PROXY, timeout=25, verify=False, allow_redirects=True)
        return r.content[:4]
    except Exception:
        return b""
def is_flac(u):
    return head4(u) == b"fLaC"
def is_mp3(u):
    h = head4(u)
    return h[:3] == b"ID3" or h[:2] == b"\xff\xfb"
def download(url, path):
    try:
        with requests.get(url, proxies=PROXY, timeout=300, verify=False, stream=True) as r, open(path, "wb") as f:
            for c in r.iter_content(1 << 16):
                if c:
                    f.write(c)
        return os.path.getsize(path)
    except OSError as e:
        # 写入被锁（OneDrive / 杀软 / 同名重复文件）-> 删残管、记日志、返回 0 由上层跳过
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        print(f"[WRITE-ERR] {os.path.basename(path)}: {e}")
        return 0

# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser(description="网易云 免费 无损/标准 下载器（非VIP）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--playlist", help="歌单 URL 或 id")
    g.add_argument("--song", help="单首分享链接 或 id")
    ap.add_argument("--out", default="F:/music", help="输出目录（默认 F:\\music）")
    ap.add_argument("--dry-run", action="store_true", help="只解析列出、不下载（安全预览）")
    args = ap.parse_args()

    parsed = parse_input(args.playlist or args.song)
    if not parsed:
        ap.error("无法从输入解析出 id，请检查链接")
    kind, val = parsed
    # 用显式 flag 决定模式：--playlist 一定是歌单，--song 一定是单首
    # （这样裸数字 id 也能被正确识别，不必带 playlist?id= 前缀）
    kind = "playlist" if args.playlist is not None else "song"

    if kind == "playlist":
        print(f"[模式] 歌单 id={val}")
        ids = playlist_track_ids(val)
        songs = resolve_names(ids)
    else:  # song / id
        print(f"[模式] 单首 id={val}")
        songs = resolve_names([val])

    print(f"曲目总数: {len(songs)}")
    os.makedirs(args.out, exist_ok=True)
    def done(s):
        b = san(f"{norm(s['name'])} - {norm(s['artist'])}")
        return os.path.exists(os.path.join(args.out, f"{b}.flac")) or os.path.exists(os.path.join(args.out, f"{b}.mp3"))

    logpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_log.jsonl")
    def log(d):
        with open(logpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    done_cnt = sum(1 for s in songs if done(s))
    print(f"本地已存在: {done_cnt} | 待处理: {len(songs)-done_cnt}" + ("  [dry-run]" if args.dry_run else ""))

    consec_fail = 0
    for idx, s in enumerate(songs):
        if done(s):
            if not args.dry_run:
                pass
            else:
                print(f"[跳过] {s['name']} - {s['artist']}")
            continue
        if args.dry_run:
            print(f"[将下] {s['name']} - {s['artist']} (id={s['id']})")
            continue

        base = san(f"{norm(s['name'])} - {norm(s['artist'])}")
        # 1) 轮询三源找无损
        flac_url, used = None, None
        for k in range(len(SRC)):
            name, fn = SRC[(idx + k) % len(SRC)]
            u = fn(s["id"])
            if is_flac(u):
                flac_url, used = u, name
                break
        if flac_url:
            path = os.path.join(args.out, f"{base}.flac")
            sz = download(flac_url, path)
            if sz == 0:
                consec_fail += 1
                log({"id": s["id"], "name": base, "status": "FAIL-写失败", "src": used})
                print(f"[FAIL] {base}: 写入失败（文件被锁？）")
            elif open(path, "rb").read(4) != b"fLaC":
                os.remove(path)
                log({"id": s["id"], "name": base, "status": "DEL-非FLAC", "src": used})
                print(f"[DEL] {base}: 校验失败已删")
            else:
                done_cnt += 1
                log({"id": s["id"], "name": base, "status": "OK-FLAC", "src": used, "mb": sz//1024//1024})
                print(f"[FLAC {done_cnt}/{len(songs)}] {base} ({sz//1024//1024}MB) via {used}")
        else:
            # 2) 无无损 -> 标准 320k
            u = gd_url(s["id"], br=320)
            if is_mp3(u):
                path = os.path.join(args.out, f"{base}.mp3")
                sz = download(u, path)
                if sz == 0:
                    consec_fail += 1
                    log({"id": s["id"], "name": base, "status": "FAIL-写失败", "src": "gdstudio"})
                    print(f"[FAIL] {base}: 写入失败（文件被锁？）")
                elif not is_mp3(u) and open(path, "rb").read(4)[:3] != b"ID3":
                    os.remove(path)
                    log({"id": s["id"], "name": base, "status": "DEL-非MP3", "src": "gdstudio"})
                else:
                    done_cnt += 1
                    log({"id": s["id"], "name": base, "status": "OK-MP3", "src": "gdstudio", "kb": sz//1024})
                    print(f"[MP3  {done_cnt}/{len(songs)}] {base} ({sz//1024}KB) via gdstudio")
            else:
                consec_fail += 1
                log({"id": s["id"], "name": base, "status": "FAIL-无链接", "src": "all"})
                print(f"[FAIL] {base}: 三源均无链接")
        # 节奏控制
        time.sleep(2.5 + random.random() * 2)
        if consec_fail >= 5:
            print("!! 连续 5 次失败，疑似被限流，退避 60s")
            time.sleep(60)
            consec_fail = 0

    if not args.dry_run:
        print(f"\n===== 完成：{done_cnt}/{len(songs)} 首已就位 -> {args.out} =====")

if __name__ == "__main__":
    main()
