#!/usr/bin/env python3
"""Apply Phase 2 render (paper grade, ink stroke scale, adaptive quality) and push."""
from pathlib import Path
import subprocess
import sys

def run(cmd):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)

def patch_paper(text: str) -> str:
    if "radial-gradient(ellipse 78%" in text:
        return text
    old = """/* A fixed, faint paper fibre texture. It never moves or obscures input. */
body::after {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 10;
  pointer-events: none;
  background: url('/textures/paper-grain.svg') repeat;
  opacity: 0.035;
  mix-blend-mode: multiply;
}
body[data-vr="active"]::after { display: none; }
"""
    new = """/* Fixed paper fibre + soft vignette (Summer Cycle grade idea, CSS-only — no post stack). */
body::before {
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
body[data-vr="active"]::before,
body[data-vr="active"]::after { display: none; }
"""
    if old not in text:
        raise SystemExit("paper.css: grain block not found")
    return text.replace(old, new, 1)

def patch_ink(text: str) -> str:
    if "height / 1080" in text and "strokeMaterial.linewidth = scale" in text:
        return text
    old = """export function resizeInk(width: number, height: number) {
  strokeMaterial.resolution.set(width, height)
  silhouette.uniforms.resolution.value.set(width, height)
}
"""
    new = """export function resizeInk(width: number, height: number) {
  strokeMaterial.resolution.set(width, height)
  silhouette.uniforms.resolution.value.set(width, height)
  // Keep stroke weight stable across resolutions (\~1px reference at 1080p).
  const scale = Math.max(0.85, Math.min(1.6, height / 1080))
  strokeMaterial.linewidth = scale
  silhouette.uniforms.width.value = 1.15 * scale
}
"""
    if old not in text:
        raise SystemExit("ink.ts: resizeInk not found")
    return text.replace(old, new, 1)

def patch_main(text: str) -> str:
    if "refreshMs" in text and "renderer.compile(scene, camera.active)" in text:
        return text
    old_adapt = """// Slow GPUs: when play stays under \~40 fps, shade fewer pixels (never below 1×). Stroke widths are in CSS px and keep their size.
// ponytail: one-way and frame-time based. Frame time cannot tell GPU- from CPU-bound, so a step that
// does not help is undone and adaptation stops; a reload restores full resolution. Add step-up if players ask.
let resolutionFrames = 0, resolutionTrial = 0, resolutionSettled = false
function adaptResolution() {
  const recent = frameTimes.slice(-90), average = recent.reduce((a, b) => a + b, 0) / recent.length
  resolutionFrames = 0
  if (resolutionTrial) {
    if (average > resolutionTrial * 0.9) { resolutionScale /= 0.8; resolutionSettled = true }
    resolutionTrial = 0
  } else if (average > 25 && pixelRatio() > 1) { resolutionTrial = average; resolutionScale *= 0.8 }
  else return
  resize()
}
"""
    new_adapt = """// Adaptive pixel ratio (Summer Cycle idea): measure display refresh, step down only on sustained
// over-budget frames, cooldown between steps, never below 1×. Stroke widths stay in CSS pixels.
let resolutionFrames = 0
let resolutionSettled = false
let resolutionCooldown = 0
let refreshMs = 16.67
let refreshSamples: number[] = []
function adaptResolution() {
  resolutionFrames = 0
  if (resolutionSettled || renderer.xr.isPresenting) return
  const recent = frameTimes.slice(-90)
  if (recent.length < 45) return
  // Estimate display interval once from early samples (snap to 60/90/120 Hz).
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
"""
    if old_adapt not in text:
        raise SystemExit("main.ts: adaptResolution block not found")
    text = text.replace(old_adapt, new_adapt, 1)

    old_ready = "void mission?.initialized.then(() => { startupReady = true; invalidate() })"
    new_ready = """void mission?.initialized.then(() => {
  startupReady = true
  // Warm GPU programs for the loaded mission (Summer Cycle precompile idea).
  try { renderer.compile(scene, camera.active) } catch { /* best-effort */ }
  invalidate()
})"""
    if old_ready not in text:
        raise SystemExit("main.ts: mission initialized hook not found")
    return text.replace(old_ready, new_ready, 1)

def main():
    if not Path("src/main.ts").is_file():
        print("Run from the operation-ink repo root")
        sys.exit(1)

    patches = {
        Path("src/render/paper.css"): patch_paper,
        Path("src/render/ink.ts"): patch_ink,
        Path("src/main.ts"): patch_main,
    }
    changed = []
    for path, fn in patches.items():
        if not path.is_file():
            print(f"Missing {path}")
            sys.exit(1)
        before = path.read_text(encoding="utf-8")
        after = fn(before)
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed.append(str(path))
            print(f"Patched {path}")
        else:
            print(f"Already applied: {path}")

    if not changed:
        print("No file changes; pushing existing commits if any…")
        run(["git", "push", "origin", "HEAD"])
        return

    run(["git", "add", *changed])
    run(["git", "commit", "-m", "Phase 2 render: paper vignette/grain, ink stroke scale, adaptive quality + compile warm"])
    run(["git", "pull", "--rebase", "origin", "main"])
    run(["git", "push", "origin", "HEAD"])
    print("Done.")
    print("Verify:")
    print('  curl -sL "https://raw.githubusercontent.com/olekariamunyororo-crypto/operation-ink/main/src/render/paper.css" | grep -c radial-gradient')
    print('  curl -sL "https://raw.githubusercontent.com/olekariamunyororo-crypto/operation-ink/main/src/render/ink.ts" | grep -c "height / 1080"')
    print('  curl -sL "https://raw.githubusercontent.com/olekariamunyororo-crypto/operation-ink/main/src/main.ts" | grep -c refreshMs')

if __name__ == "__main__":
    main()
