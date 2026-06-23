---
name: video-edit
description: 動画素材のカット(不要部分の切り出し・結合)とテロップ(テキストオーバーレイ)の追加を行う。JSON設定ファイルでカット区間とテロップ内容・表示区間をまとめて指定し、ffmpegで処理する。「動画をカットして」「テロップを入れて」「動画編集」などの依頼があったときに使う。
---

# 動画カット & テロップ追加スキル

ffmpeg を使って、動画から指定区間を切り出して結合し、テロップ（テキスト）を合成する。

## 前提

- `ffmpeg` / `ffprobe` がインストールされていること（未インストールなら `apt-get install -y --no-install-recommends ffmpeg`）。
- 日本語テロップ用フォントとして `/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf` (IPAゴシック) を既定で使用する。

## 使い方

1. 作業用の設定ファイル（例: `video_config.json`）を作成する。スキーマは以下:

```json
{
  "input": "input.mp4",
  "output": "output.mp4",
  "cuts": [
    { "start": "00:00:10", "end": "00:00:25" },
    { "start": "00:01:00", "end": "00:01:30" }
  ],
  "telops": [
    {
      "start": "00:00:02",
      "end": "00:00:05",
      "text": "こんにちは！",
      "position": "bottom",
      "fontsize": 56,
      "color": "white"
    }
  ]
}
```

- `cuts`: 残したい区間のリスト。`start`/`end` は `HH:MM:SS` または秒数。複数指定すると、その順番で切り出して結合する（不要な部分は自動的に除外される）。省略した場合は元動画全体を使う。
- `telops`: テロップのリスト。`start`/`end` は **カット後（結合後）の出力動画の時間軸**で指定する。
  - `position`: `top` / `center` / `bottom`（既定 `bottom`）
  - `fontsize`: 既定 48
  - `color`: ffmpeg の色名（既定 `white`）
  - `font`: フォントファイルパス（既定は IPAゴシック）
  - `box`: 背景ボックスの有無（既定 `true`）

2. スクリプトを実行する:

```bash
python3 .claude/skills/video-edit/scripts/cut_and_telop.py video_config.json
```

3. `output` で指定したパスに完成動画が生成される。

## 注意点

- カットは再エンコード（libx264/aac）してから結合するため、フレーム単位で正確にカットできるが、素材が長い場合は処理時間がかかる。
- テロップ複数指定時は `drawtext` フィルタを `,` で連結して一括適用する。
- テロップのテキストに `:` や `'` が含まれる場合は自動でエスケープされる。
