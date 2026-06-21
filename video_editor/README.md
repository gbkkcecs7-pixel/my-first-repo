# 動画自動編集スクリプト

無音区間を自動カットし、日本語の音声認識でテロップを生成して動画に焼き込みます。
YouTube投稿向けに 1920x1080 / 30fps / H.264 で出力します。

## セットアップ

```bash
# ffmpegが未インストールの場合
sudo apt-get install ffmpeg

# Python依存パッケージ
pip install -r requirements.txt
```

`fonts/README.md` の指示に従い、`fonts/MPLUSRounded1c-Bold.ttf` を配置してください。

## 使い方

```bash
python auto_edit.py 入力動画.mp4 出力動画.mp4
```

オプション:
- `--noise-db`: 無音と判定する音量のしきい値（デフォルト: -30dB）
- `--min-silence`: 無音と判定する最短秒数（デフォルト: 0.6秒）

## テロップデザイン

- フォント: M PLUS Rounded 1c（丸ゴシック、読みやすい）
- 文字色: 白
- 位置: 中央下寄り
