#!/usr/bin/env python3
"""動画から音声を抽出し、Whisperでタイムコード付き文字起こしを行う。
無音区間の検出も行い、カット判定の材料にする。

使い方:
    python3 transcribe.py input.mp4 transcript.json [--model small]

出力 (transcript.json):
{
  "segments": [{"start": 0.0, "end": 2.3, "text": "..."}],
  "silences": [{"start": 5.0, "end": 6.2}]
}
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import os

SILENCE_RE = re.compile(r"silence_(start|end): ([0-9.]+)")


def extract_audio(input_path, audio_path):
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-vn", "-ac", "1", "-ar", "16000", audio_path],
        check=True,
        capture_output=True,
    )


def detect_silences(input_path, noise_db="-30dB", min_duration=0.6):
    result = subprocess.run(
        [
            "ffmpeg", "-i", input_path, "-af",
            f"silencedetect=noise={noise_db}:d={min_duration}",
            "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    events = SILENCE_RE.findall(result.stderr)
    silences = []
    start = None
    for kind, value in events:
        if kind == "start":
            start = float(value)
        elif kind == "end" and start is not None:
            silences.append({"start": start, "end": float(value)})
            start = None
    return silences


def transcribe(audio_path, model_size):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="ja")
    return [
        {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
        for s in segments
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--model", default="small")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as workdir:
        audio_path = os.path.join(workdir, "audio.wav")
        extract_audio(args.input, audio_path)
        segments = transcribe(audio_path, args.model)

    silences = detect_silences(args.input)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"segments": segments, "silences": silences}, f, ensure_ascii=False, indent=2)

    print(f"完了: {args.output} (segments={len(segments)}, silences={len(silences)})")


if __name__ == "__main__":
    main()
