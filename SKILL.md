---
name: free-music-downloader
description: Download NetEase Cloud Music (网易云音乐) tracks as genuine FLAC lossless (or 320k standard fallback) WITHOUT a VIP account, using free third-party parse APIs reachable from a CN network via the local proxy. Supports BOTH a playlist link and a single-song share link. Use when the user wants lossless/standard music downloads from NetEase and is NOT a VIP.
---

# NetEase Free FLAC / Standard Downloader (no VIP)

## When to use
User wants to download NetEase Cloud Music tracks and is NOT a VIP. Non-VIP official API caps
at 320k MP3 and returns `null` for `fee:1` songs — so you MUST use third-party parse APIs that
proxy pooled VIP access to get a real `.flac` from `music.126.net`.

## Two input modes
- **Playlist:** `--playlist "https://music.163.com/playlist?id=310049166&uct2=..."`
  (or just the id `310049166`). The `uct2` token is ignored; only the `id` matters.
- **Single song:** `--song "https://music.163.com/song?id=487587153&uct2=..."`
  (or just the id `487587153`). The `uct2` token is ignored; only the `id` matters.

## How to run (script included)
The skill ships `scripts/music_dl.py`. Run with the **managed venv python** (has `requests`):
```
C:\Users\licangshu\.workbuddy\binaries\python\envs\default\Scripts\python.exe ^
  C:\Users\licangshu\.workbuddy\skills\netease-free-flac\scripts\music_dl.py ^
  --playlist "https://music.163.com/playlist?id=310049166" --out "F:/music"
```
Single song:
```
... music_dl.py --song "https://music.163.com/song?id=487587153" --out "F:/music"
```
Safe preview (parses + lists what it WOULD download, hits only music.163.com, NO parse-station
calls, NO downloads) — always run this first to confirm the track list / dedup before a bulk run:
```
... music_dl.py --playlist "<url>" --dry-run
```

## Hard rules
1. **Lossless preferred, standard as fallback (user rule 2026-09-30).** Download FLAC when a
   genuine lossless source exists. For tracks that have NO lossless anywhere, download the highest
   available **standard** quality (320k MP3) so the playlist stays complete — do NOT skip them, and
   never label an MP3 as lossless. Verify each file: FLAC must have first 4 bytes == `b'fLaC'`;
   standard MP3 should start with `ID3` or `\xff\xfb`. Name lossless `.flac`, standard `.mp3`.
2. **CDN URLs** (`music.126.net/.../*.flac`) are time-limited signed URLs — fetch the URL then
   download promptly in the same run.
3. **Rate-limit / 防封 (critical):** single-threaded, sequential; sleep 2.5–4.5s between tracks;
   round-robin the 3 sources to spread load; **resumable** (existing files are skipped, so a
   restart continues where it left off); back off 60s after 5 consecutive failures (throttle).
   Do NOT parallelize or hammer — these parse stations explicitly forbid bulk downloading and
   their shared VIP keys get banned for over-downloading (seen: Spotify source banned).

## Network (critical)
- This machine's **direct** connection is GFW-blocked for these APIs. ALL requests must go through
  the local proxy `HTTPS_PROXY=http://127.0.0.1:11417` (requests reads it from env). Direct =
  RemoteDisconnected / blocked.
- The proxy does MITM TLS → use `verify=False` + `requests.packages.urllib3.disable_warnings()`.
- Use the managed python venv:
  `C:\Users\licangshu\.workbuddy\binaries\python\envs\default\Scripts\python.exe`

## Working free endpoints (verified 2026-09-30)
Pass the NetEase song id (`neid`) as `id`:
- **gdstudio (primary):** `GET https://music-api.gdstudio.xyz/api.php?types=url&id={neid}&source=netease&br=999`
  → JSON `{"url":"...flac","br":<kbps>,"size":<bytes>}`. This is the **full international** API
  (`music.gdstudio.xyz`); the crippled domestic `.org` may not serve FLAC.
- **ffapi (fallback):** `GET https://ffapi.cn/int/v1/netease_url?id={neid}&quality=lossless`
  → JSON `{"url":"...","level":<kbps>}`.
- **haitangw (fallback):** `GET https://musicapi.haitangw.net/music/wy.php?id={neid}&level=lossless&type=json`
  with headers `Origin: https://wyapi.toubiec.cn`, `Referer: https://wyapi.toubiec.cn/`
  → JSON `{"data":{"url":"...","quality":"FLAC 无损"}}`.

For each song the script tries gdstudio → ffapi → haitangw (rotated per index) until one returns a
URL whose first 4 bytes are `fLaC`; if none, it falls back to 320k standard from gdstudio.

## Dead / blocked (do NOT use)
- **ikun** (`api.ikunshare.com` / `music.ikun0014.top` / IP `160.202.237.98:9000`):
  HTTPS = SSL EOF (cert dead); HTTP IP = 403. Unreachable from this network.
- **bileizhen.top**: flagged by Security Center as 黑灰产 / ClearFake — BLOCKED, never retry.
- rxtool → 403; chksz / xcvts → require paid apikey; ceseet → returns HTML landing page;
  bugpk / lzmhhh → return 320k `.mp3` only.

## Gotchas learned the hard way
- NetEase `/api/v3/playlist/detail` returns only the **first 10 tracks** in `playlist.tracks`
  (sampling cap). The FULL list is in `playlist.trackIds` (all ids). Use `trackIds`, then resolve
  names via the OLD `/api/song/detail/` endpoint (the v3 `/api/v3/song/detail` returns 400).
- The gdstudio / ffapi / haitangw links are proxied VIP access — treat as gray-area; personal
  backup only. TG status channel if a source dies: `https://t.me/gdstudio_music`.

## Quick verification snippet
```python
import requests
requests.packages.urllib3.disable_warnings()
P = {"http": "http://127.0.0.1:11417", "https": "http://127.0.0.1:11417"}
def is_flac(u):
    if not u:
        return False
    r = requests.get(u, headers={"Range": "bytes=0-3"}, proxies=P,
                     timeout=25, verify=False, allow_redirects=True)
    return r.content[:4] == b"fLaC"
```
