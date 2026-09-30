# free-music-downloader

> 网易云音乐 **非 VIP** 免费无损 / 标准下载器 + 元数据/封面补全工具
> 支持「歌单链接」和「单首分享链接」两种入口

## 这是什么

一个小工具，帮**没有 VIP** 的网易云音乐用户，把歌曲下载成真正的 **FLAC 无损**，
并顺手把 **标题 / 歌手 / 专辑 / 封面** 写进文件标签，任何播放器都能正确显示。

- 下载不到无损的歌，就退一步下 **320k 标准音质**，把整张歌单凑齐、不留缺口。
- 下载完自动补元数据 + 封面（两步脚本，走官方 API，不需要 VIP 解析站代理）。
- 支持**歌单链接**：`https://music.163.com/playlist?id=310049166`
- 支持**单首分享链接**：`https://music.163.com/song?id=487587153`
- 单线程、带间隔、断点续下、**防封**设计

## 原理（说人话）

非 VIP 在网易云官方只能拿到 320k 的 MP3，很多歌还直接拿不到。

下载这一步走「第三方解析站」——它们手里有一批**轮换的 VIP 账号**，替你向网易云 CDN
（`music.126.net`）要一个带签名的 `.flac` 直链，再用这个直链把文件拉到本地。
一句话：**借别人的 VIP 通道，拿无损文件做个人备份。**

元数据/封面这一步走 `music.163.com` **官方 API**（直连即可，免费、不限 VIP），
把歌曲信息和专辑封面抓回来写进标签。

## 用法

用本机自带的托管 Python（已装 `requests` / `mutagen`）运行：

### 1. 下载

```bash
python music_dl.py --playlist "https://music.163.com/playlist?id=310049166" --out "F:/music"
```

单首：

```bash
python music_dl.py --song "https://music.163.com/song?id=487587153" --out "F:/music"
```

先预览（只解析、不下载，安全）：

```bash
python music_dl.py --playlist "https://music.163.com/playlist?id=310049166" --dry-run
```

### 2. 抓元数据 + 封面

```bash
python fetch_meta.py 310049166
```

生成 `songs_meta.json`（标题/歌手/专辑）和 `covers_b64.json`（真实封面 base64）：

- 走 `music.163.com` 官方 API，直连即可，**不需要 VIP 解析站代理**。
- 封面按 `picUrl` 直抓 JPEG，校验 `ff d8 ff` 魔数，失败留空（不污染标签）。
- 遇限流部分封面抓不到会留空；过一会儿重跑本脚本即可补回已有空缺。

### 3. 写标签（标题/歌手/专辑/封面）

```bash
python tag_all.py --out "F:/music"
```

用 mutagen 把元数据 + 封面嵌进本地文件：

- FLAC 写 `title/artist/album` + 内嵌封面；MP3 写 ID3 `TIT2/TPE1/TALB` + `APIC` 封面。
- 先写临时文件再原子替换；被播放器/索引器锁住的文件会跳过、原文件不动。
- `tag_all.py` 需要 `mutagen`：`pip install mutagen`（托管 venv 已自带）。

> 三步都建议用托管 venv python：
> `C:\Users\licangshu\.workbuddy\binaries\python\envs\default\Scripts\python.exe fetch_meta.py 310049166`

## 重要提醒

- **下载有网络前置条件**：依赖本地代理（`HTTPS_PROXY=http://127.0.0.1:11417`）才能访问解析站；直连会被墙。
  元数据/封面抓取**不需要**这个代理（走官方 API 直连）。
- **请克制使用、防封**：单线程、每首间隔 2.5–4.5 秒、三源轮询分摊。解析站明确禁止批量下载，VIP 共享 Key 被刷多了会被封。
- **仅限个人备份**：这些直链属灰色地带，请勿传播或商用。
- 无损优先、标准兜底；**从不会把 MP3 冒充成 FLAC**。每首下载完会校验文件头（`fLaC` / `ID3`）。

## 鸣谢 / Credits

本工具的方法与思路建立在以下开源项目与解析服务之上，特此致谢：

- **[@metowolf/Meting](https://github.com/metowolf/Meting)** —— 音乐 API 框架（MIT 许可证），是整个思路的源头。
- **[@mengkunsoft/MKOnlineMusicPlayer](https://github.com/mengkunsoft/MKOnlineMusicPlayer)** —— 基于 Meting 的网页播放器。
- **[@CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl)** —— 多平台音乐下载器，提供了大量可用的解析接口思路。
- **gdstudio / ffapi / haitangw** 等第三方解析站 —— 提供 VIP 代理直链，使非 VIP 用户也能取到无损文件。

## 许可证

[MIT](LICENSE)
