#!/usr/bin/env python3
"""
動画の無音区間を自動でカットし、日本語のテロップ（字幕）を自動生成して
動画に焼き込むスクリプト。

使い方:
    python auto_edit.py 入力動画.mp4 出力動画.mp4

必要なもの:
    - ffmpeg / ffprobe（システムにインストール済みであること）
    - pip install -r requirements.txt
    - fonts/ ディレクトリに「M PLUS Rounded 1c」のフォントファイルを配置
      (例: fonts/MPLUSRounded1c-Bold.ttf)
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FONT_DIR = Path(__file__).parent / "fonts"
FONT_NAME = "M PLUS Rounded 1c"

# YouTube投稿向けの推奨出力設定
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_FPS = 30


@dataclass
class Segment:
    start: float
    end: float


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stderr + result.stdout


def detect_silence(input_path: Path, noise_db: str = "-30dB", min_silence: float = 0.6) -> list[Segment]:
    """ffmpegのsilencedetectで無音区間を検出し、しゃべっている区間(=残す区間)を返す"""
    output = run([
        "ffmpeg", "-i", str(input_path),
        "-af", f"silencedetect=noise={noise_db}:d={min_silence}",
        "-f", "null", "-",
    ])

    silence_starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", output)]
    silence_ends = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", output)]

    duration_match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", output)
    if not duration_match:
        raise RuntimeError("動画の長さを取得できませんでした")
    h, m, s = duration_match.groups()
    total_duration = int(h) * 3600 + int(m) * 60 + float(s)

    silences = list(zip(silence_starts, silence_ends))

    keep_segments: list[Segment] = []
    cursor = 0.0
    for start, end in silences:
        if start > cursor:
            keep_segments.append(Segment(cursor, start))
        cursor = end
    if cursor < total_duration:
        keep_segments.append(Segment(cursor, total_duration))

    # 短すぎる区間（0.2秒未満）は誤検出として除外
    return [s for s in keep_segments if s.end - s.start > 0.2]


def cut_and_concat(input_path: Path, segments: list[Segment], output_path: Path) -> None:
    """検出した区間だけを残してカット編集した動画を書き出す"""
    filter_parts = []
    concat_inputs = []
    for i, seg in enumerate(segments):
        filter_parts.append(
            f"[0:v]trim=start={seg.start}:end={seg.end},setpts=PTS-STARTPTS[v{i}];"
            f"[0:a]atrim=start={seg.start}:end={seg.end},asetpts=PTS-STARTPTS[a{i}];"
        )
        concat_inputs.append(f"[v{i}][a{i}]")

    filter_complex = "".join(filter_parts)
    filter_complex += "".join(concat_inputs) + f"concat=n={len(segments)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-vf", f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
        "-r", str(OUTPUT_FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def format_srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe_to_srt(video_path: Path, srt_path: Path) -> None:
    """faster-whisperで日本語の音声をテキスト化し、.srtファイルを作成する"""
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(video_path), language="ja")

    with srt_path.open("w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_srt_timestamp(seg.start)} --> {format_srt_timestamp(seg.end)}\n")
            f.write(f"{seg.text.strip()}\n\n")


def burn_subtitles(video_path: Path, srt_path: Path, output_path: Path) -> None:
    """テロップ（白文字・丸ゴシック・中央下寄り）を動画に焼き込む"""
    style = (
        f"FontName={FONT_NAME},FontSize=20,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=3,Outline=2,"
        "Alignment=2,MarginV=80"
    )
    subtitles_filter = f"subtitles={srt_path}:fontsdir={FONT_DIR}:force_style='{style}'"

    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", subtitles_filter,
        "-c:a", "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="動画の自動カット編集とテロップ焼き込み")
    parser.add_argument("input", type=Path, help="入力動画のパス")
    parser.add_argument("output", type=Path, help="出力動画のパス")
    parser.add_argument("--noise-db", default="-30dB", help="無音と判定する音量(デフォルト: -30dB)")
    parser.add_argument("--min-silence", type=float, default=0.6, help="無音と判定する最短秒数(デフォルト: 0.6秒)")
    args = parser.parse_args()

    if not args.input.exists():
        sys.exit(f"入力動画が見つかりません: {args.input}")

    work_dir = args.output.parent
    cut_path = work_dir / f"_cut_{args.output.name}"
    srt_path = work_dir / f"{args.output.stem}.srt"

    print("1/3 無音区間を検出してカット編集中...")
    segments = detect_silence(args.input, args.noise_db, args.min_silence)
    cut_and_concat(args.input, segments, cut_path)

    print("2/3 音声認識してテロップを生成中...")
    transcribe_to_srt(cut_path, srt_path)

    print("3/3 テロップを動画に焼き込み中...")
    burn_subtitles(cut_path, srt_path, args.output)

    cut_path.unlink(missing_ok=True)
    print(f"完成しました: {args.output}")


if __name__ == "__main__":
    main()
