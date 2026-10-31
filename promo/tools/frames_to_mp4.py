"""把 record_game.mjs 录的帧序列按真实时间戳合成 60fps 恒定帧率视频，镜头时间点换算成视频里的秒数。
用法：python frames_to_mp4.py <录制目录> <输出.mp4>
"""
import json, subprocess, sys
from pathlib import Path

rec, out = Path(sys.argv[1]), Path(sys.argv[2])
FF = str(Path.home() / "socialmedia/tools/bin/ffmpeg")
frames = json.loads((rec / "frames.json").read_text())
t0 = frames[0]["t"]
lines = []
for a, b in zip(frames, frames[1:] + [None]):
    lines.append(f"file '{(rec / 'frames' / a['f']).as_posix()}'")
    lines.append(f"duration {((b['t'] if b else a['t'] + 1/60) - a['t']):.6f}")
lines.append(f"file '{(rec / 'frames' / frames[-1]['f']).as_posix()}'")
lst = rec / "concat.txt"; lst.write_text("\n".join(lines))
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", "fps=60,format=yuv420p",
                "-c:v", "libx264", "-preset", "medium", "-crf", "14", str(out)], check=True)
marks = {m["name"]: round(m["t"] - t0, 2) for m in json.loads((rec / "markers.json").read_text())}
out.with_suffix(".markers.json").write_text(json.dumps(marks, ensure_ascii=False, indent=1))
print(out, marks)
