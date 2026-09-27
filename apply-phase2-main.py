#!/usr/bin/env python3
"""Finish Phase 2: patch main.ts only, then commit + push all Phase 2 files."""
from pathlib import Path
import re
import subprocess
import sys

def run(cmd):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)

def patch_main(text: str) -> str:
    if "refreshMs" in text and "renderer.compile(scene, camera.active)" in text:
        print("main.ts already has Phase 2 adapt + compile")
        return text

    # Replace adaptResolution by anchoring on the function, not comment text (avoids \~ / unicode issues)
    new_adapt = '''let resolutionFrames = 0
let resolutionSettled = false
let resolutionCooldown = 0
let refreshMs = 16.67
let refreshSamples: number[] = []
function adaptResolution() {
  resolutionFrames = 0
  if (resolutionSettled || renderer.xr.isPresenting) return
  const recent = frameTimes.slice(-90)
  if (recent.length < 45) return
  if (refreshSamples.length < 120) {
    refreshSamples.push(...recent.slice(-30))
    if (refreshSamples.length >= 90) {
      const sorted = [...refreshSamples].sort((a, b) => a - b)
      const median = sorted[Math.floor(sorted.length / 2)]
      const candidates = [1000 / 60, 1000 / 90, 1000 / 120, 1000 / 144]
      refreshMs = candidates.reduce((best, c) => Math.abs(c - median) < Math.abs(best - median) ? c : best, median)
    }
  }
  if (resolutionCooldown > 0) { resolutionCooldown -= 1; return }
  const budget = refreshMs * 1.35
  const over = recent.filter(ms => ms > budget).length / recent.length
  if (over > 0.22 && pixelRatio() > 1.01) {
    const before = resolutionScale
    resolutionScale = Math.max(1 / Math.max(window.devicePixelRatio, 1.25), resolutionScale * 0.82)
    if (Math.abs(resolutionScale - before) < 0.01) { resolutionSettled = true; return }
    resolutionCooldown = 6
    if (pixelRatio() <= 1.05) resolutionSettled = true
    resize()
  } else if (over < 0.08 && resolutionScale < 1 && recent.every(ms => ms < refreshMs * 1.05)) {
    resolutionScale = Math.min(1, resolutionScale / 0.9)
    resolutionCooldown = 8
    resize()
  }
}
'''

    pattern = re.compile(
        r"let resolutionFrames = 0, resolutionTrial = 0, resolutionSettled = false\n"
        r"function adaptResolution\(\) \{\n"
        r"(?:.*\n)*?"
        r"  resize\(\)\n"
        r"\}\n",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        # Fallback: from "let resolutionFrames" through closing brace of adaptResolution
        pattern2 = re.compile(
            r"let resolutionFrames = 0.*?\nfunction adaptResolution\(\) \{.*?\n\}\n",
            re.DOTALL,
        )
        m = pattern2.search(text)
    if not m:
        raise SystemExit("main.ts: could not find adaptResolution block")
    text = text[: m.start()] + new_adapt + text[m.end() :]

    old_ready = "void mission?.initialized.then(() => { startupReady = true; invalidate() })"
    new_ready = """void mission?.initialized.then(() => {
  startupReady = true
  // Warm GPU programs for the loaded mission.
  try { renderer.compile(scene, camera.active) } catch { /* best-effort */ }
  invalidate()
})"""
    if old_ready not in text:
        if "renderer.compile(scene, camera.active)" in text:
            print("compile warm already present")
        else:
            raise SystemExit("main.ts: mission initialized hook not found")
    else:
        text = text.replace(old_ready, new_ready, 1)

    return text

def main():
    path = Path("src/main.ts")
    if not path.is_file():
        print("Run from operation-ink repo root")
        print("  cd $HOME/operation-ink")
        sys.exit(1)

    before = path.read_text(encoding="utf-8")
    after = patch_main(before)
    if after != before:
        path.write_text(after, encoding="utf-8")
        print("Patched src/main.ts")
    else:
        print("src/main.ts unchanged")

    # Stage all Phase 2 files (paper/ink may already be patched)
    files = [
        "src/render/paper.css",
        "src/render/ink.ts",
        "src/main.ts",
    ]
    run(["git", "add", *files])
    st = subprocess.run(["git", "status", "--porcelain"] + files, capture_output=True, text=True)
    if not st.stdout.strip():
        print("Nothing to commit; pushing…")
        run(["git", "push", "origin", "HEAD"])
        return

    run(["git", "commit", "-m", "Phase 2 render: paper vignette/grain, ink stroke scale, adaptive quality + compile warm"])
    run(["git", "pull", "--rebase", "origin", "main"])
    run(["git", "push", "origin", "HEAD"])
    print("Done.")
    print('Verify: grep -n refreshMs src/main.ts')

if __name__ == "__main__":
    main()
