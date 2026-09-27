#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

path = Path("src/render/paper.css")
if not path.is_file():
    print("Run from operation-ink repo root")
    sys.exit(1)

text = path.read_text(encoding="utf-8")
old = """body::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 9;
  pointer-events: none;
  background: radial-gradient(ellipse 78% 72% at 50% 45%, transparent 55%, rgba(0, 0, 0, 0.055) 100%);
}
body::after {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 10;
  pointer-events: none;
  background: url('/textures/paper-grain.svg') repeat;
  opacity: 0.055;
  mix-blend-mode: multiply;
}
"""
new = """body::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 9;
  pointer-events: none;
  background: radial-gradient(ellipse 85% 80% at 50% 46%, transparent 62%, rgba(0, 0, 0, 0.038) 100%);
}
body::after {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 10;
  pointer-events: none;
  background: url('/textures/paper-grain.svg') repeat;
  opacity: 0.042;
  mix-blend-mode: multiply;
}
"""
if "rgba(0, 0, 0, 0.038)" in text and "opacity: 0.042" in text:
    print("Already tuned")
else:
    if old not in text:
        print("Unexpected paper.css — paste current body::before/::after if this fails")
        sys.exit(1)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("Tuned paper.css")

def run(cmd):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)

run(["git", "add", "src/render/paper.css"])
st = subprocess.run(["git", "status", "--porcelain", "src/render/paper.css"], capture_output=True, text=True)
if not st.stdout.strip():
    print("No changes to commit")
    sys.exit(0)
run(["git", "commit", "-m", "Tune paper grade: softer vignette and lighter grain"])
run(["git", "pull", "--rebase", "origin", "main"])
run(["git", "push", "origin", "HEAD"])
print("Done. Hard-refresh the live site after Vercel deploys.")
