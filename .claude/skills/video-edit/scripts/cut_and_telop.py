#!/usr/bin/env python3
"""動画を設定ファイル(JSON)に従ってカットし、テロップを合成する。

使い方:
    python3 cut_and_telop.py config.json

config.json の形式は SKILL.md を参照。
"""
import json
import subprocess
import sys
import tempfile
import os

DEFAULT_FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

POSITION_Y = {
    "top": "h*0.08",
    "center": "(h-text_h)/2",
    "bottom": "h-h*0.12-text_h",
}


def run(cmd):
    subprocess.run(cmd, check=True)


def cut_segments(input_path, cuts, workdir):
    segment_paths = []
    for i, cut in enumerate(cuts):
        seg_path = os.path.join(workdir, f"segment_{i:03d}.mp4")
        cmd = [
            "ffmpeg", "-y", "-ss", str(cut["start"]), "-to", str(cut["end"]),
            "-i", input_path,
            "-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "make_zero",
            seg_path,
        ]
        run(cmd)
        segment_paths.append(seg_path)
    return segment_paths


def concat_segments(segment_paths, workdir, output_path):
    list_path = os.path.join(workdir, "concat_list.txt")
    with open(list_path, "w") as f:
        for p in segment_paths:
            f.write(f"file '{p}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
        "-c", "copy", output_path,
    ]
    run(cmd)


def escape_drawtext(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_drawtext_filters(telops):
    filters = []
    for t in telops:
        position = t.get("position", "bottom")
        y_expr = POSITION_Y.get(position, POSITION_Y["bottom"])
        font = t.get("font", DEFAULT_FONT)
        fontsize = t.get("fontsize", 48)
        color = t.get("color", "white")
        box = t.get("box", True)
        text = escape_drawtext(t["text"])
        filt = (
            f"drawtext=fontfile='{font}':text='{text}':"
            f"fontsize={fontsize}:fontcolor={color}:"
            f"x=(w-text_w)/2:y={y_expr}:"
            f"enable='between(t,{t['start']},{t['end']})'"
        )
        if box:
            filt += ":box=1:boxcolor=black@0.5:boxborderw=10"
        filters.append(filt)
    return filters


def apply_telops(input_path, telops, output_path):
    if not telops:
        if input_path != output_path:
            run(["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path])
        return
    filters = build_drawtext_filters(telops)
    vf = ",".join(filters)
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-c:a", "copy",
        output_path,
    ]
    run(cmd)


def main():
    if len(sys.argv) != 2:
        print("usage: cut_and_telop.py config.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        config = json.load(f)

    input_path = config["input"]
    output_path = config["output"]
    cuts = config.get("cuts", [])
    telops = config.get("telops", [])

    with tempfile.TemporaryDirectory() as workdir:
        if cuts:
            segments = cut_segments(input_path, cuts, workdir)
            cut_output = os.path.join(workdir, "cut_result.mp4")
            concat_segments(segments, workdir, cut_output)
        else:
            cut_output = input_path

        apply_telops(cut_output, telops, output_path)

    print(f"完了: {output_path}")


if __name__ == "__main__":
    main()
