#!/usr/bin/env python3
"""Apply Phase 1 audio (master bus + zone ambience) to src/game/audio.ts and push."""
from pathlib import Path
import subprocess
import sys

AI = Path("src/game/audio.ts")

def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)

def main() -> None:
    if not Path("src/game").is_dir():
        print("Run from the operation-ink repo root (folder that contains src/)")
        sys.exit(1)
    if not AI.is_file():
        print(f"Missing {AI}")
        sys.exit(1)

    text = AI.read_text(encoding="utf-8")
    if "applyZone" in text and "DynamicsCompressorNode" in text and "private bus:" in text:
        print("Phase 1 audio already present — skipping patch.")
    else:
        old = """  private context: AudioContext | null = null
  private master: GainNode | null = null
"""
        new = """  private context: AudioContext | null = null
  /** Entry for every voice; routes through EQ → compressor → limiter → master. */
  private bus: GainNode | null = null
  private warmEq: BiquadFilterNode | null = null
  private compressor: DynamicsCompressorNode | null = null
  private limiter: DynamicsCompressorNode | null = null
  private master: GainNode | null = null
  private ambientFilter: BiquadFilterNode | null = null
  private ambientGain: GainNode | null = null
  private zoneHum: OscillatorNode | null = null
  private zoneHumGain: GainNode | null = null
  private audioZone: 'outdoor' | 'cells' = 'outdoor'
"""
        if old not in text:
            print("ERROR: expected master field block not found")
            sys.exit(1)
        text = text.replace(old, new, 1)

        old = """        this.context = new AudioContext()
        this.master = this.context.createGain()
        this.master.connect(this.context.destination)
        this.setVolume(this.volume)
"""
        new = """        this.context = new AudioContext()
        this.bus = this.context.createGain()
        this.warmEq = this.context.createBiquadFilter()
        this.warmEq.type = 'highshelf'
        this.warmEq.frequency.value = 3200
        this.warmEq.gain.value = -3.5
        this.compressor = this.context.createDynamicsCompressor()
        this.compressor.threshold.value = -18
        this.compressor.knee.value = 12
        this.compressor.ratio.value = 3.5
        this.compressor.attack.value = 0.008
        this.compressor.release.value = 0.18
        this.limiter = this.context.createDynamicsCompressor()
        this.limiter.threshold.value = -4
        this.limiter.knee.value = 0
        this.limiter.ratio.value = 20
        this.limiter.attack.value = 0.003
        this.limiter.release.value = 0.08
        this.master = this.context.createGain()
        this.bus.connect(this.warmEq)
        this.warmEq.connect(this.compressor)
        this.compressor.connect(this.limiter)
        this.limiter.connect(this.master)
        this.master.connect(this.context.destination)
        this.setVolume(this.volume)
"""
        if old not in text:
            print("ERROR: unlock AudioContext block not found")
            sys.exit(1)
        text = text.replace(old, new, 1)

        text = text.replace("connect(this.master!)", "connect(this.bus!)")
        text = text.replace("connect(this.master)", "connect(this.bus)")
        text = text.replace("this.limiter.connect(this.bus)", "this.limiter.connect(this.master)")

        old = """    if (this.active && !this.ambience) this.startAmbience()
  }
"""
        new = """    if (this.active && !this.ambience) this.startAmbience()
    this.applyZone(p.y)
  }

  /** Outdoor yard vs underground cells — smooth ambient colour without hard cuts. */
  private applyZone(y: number) {
    if (!this.context) return
    const zone: 'outdoor' | 'cells' = y < -2 ? 'cells' : 'outdoor'
    this.audioZone = zone
    const t = this.context.currentTime
    const freq = zone === 'cells' ? 170 : 400
    const bed = zone === 'cells' ? 0.05 : 0.03
    const hum = zone === 'cells' ? 0.014 : 0.0025
    if (this.ambientFilter) this.ambientFilter.frequency.setTargetAtTime(freq, t, 0.45)
    if (this.ambientGain) this.ambientGain.gain.setTargetAtTime(bed, t, 0.55)
    if (this.zoneHumGain) this.zoneHumGain.gain.setTargetAtTime(hum, t, 0.6)
  }
"""
        if old not in text:
            print("ERROR: update() tail not found")
            sys.exit(1)
        text = text.replace(old, new, 1)

        i0 = text.index("  private startAmbience() {")
        i1 = text.index("  /** Original 16-second D-minor ambient phrase", i0)
        new_start = """  private startAmbience() {
    if (!this.active || this.dying || this.disposed || !this.context || !this.noise || !this.bus || this.ambience) return
    const source = this.context.createBufferSource()
    const filter = this.context.createBiquadFilter()
    const gain = this.context.createGain()
    source.buffer = this.noise
    source.loop = true
    filter.type = 'lowpass'
    filter.frequency.value = this.audioZone === 'cells' ? 180 : 380
    gain.gain.value = this.audioZone === 'cells' ? 0.048 : 0.032
    source.connect(filter).connect(gain).connect(this.bus)
    this.track(source, [filter, gain])
    source.start()
    this.ambience = source
    this.ambientFilter = filter
    this.ambientGain = gain
    if (!this.zoneHum) {
      const hum = this.context.createOscillator()
      const humGain = this.context.createGain()
      const humFilter = this.context.createBiquadFilter()
      hum.type = 'sine'
      hum.frequency.value = 58
      humFilter.type = 'lowpass'
      humFilter.frequency.value = 120
      humGain.gain.value = this.audioZone === 'cells' ? 0.012 : 0.003
      hum.connect(humFilter).connect(humGain).connect(this.bus)
      this.track(hum, [humFilter, humGain])
      hum.start()
      this.zoneHum = hum
      this.zoneHumGain = humGain
    }
    if (this.musicBuffer) {
      const music = this.context.createBufferSource(), musicGain = this.context.createGain()
      music.buffer = this.musicBuffer; music.loop = true; musicGain.gain.value = 0.024
      music.connect(musicGain).connect(this.bus)
      this.track(music, [musicGain]); music.start(); this.music = music; this.musicGain = musicGain
    }
  }

"""
        text = text[:i0] + new_start + text[i1:]

        old = """    this.ambience = null; this.music = null; this.musicGain = null; this.alarmSource = null; this.voiceUntil = 0; this.whizUntil = 0; this.bulletHitUntil = 0
"""
        new = """    this.ambience = null; this.music = null; this.musicGain = null; this.alarmSource = null
    this.ambientFilter = null; this.ambientGain = null; this.zoneHum = null; this.zoneHumGain = null
    this.voiceUntil = 0; this.whizUntil = 0; this.bulletHitUntil = 0
"""
        if old not in text:
            print("ERROR: clear() ambient reset not found")
            sys.exit(1)
        text = text.replace(old, new, 1)

        old = """    this.master?.disconnect(); this.master = null; void this.context?.close().catch(() => {}); this.context = null
"""
        new = """    this.bus?.disconnect(); this.warmEq?.disconnect(); this.compressor?.disconnect()
    this.limiter?.disconnect(); this.master?.disconnect()
    this.bus = null; this.warmEq = null; this.compressor = null; this.limiter = null; this.master = null
    void this.context?.close().catch(() => {}); this.context = null
"""
        if old not in text:
            print("ERROR: dispose() not found")
            sys.exit(1)
        text = text.replace(old, new, 1)

        text = text.replace(
            "if (!context || !this.master || !this.active || this.muted || this.volume <= 0 || this.dying || this.disposed || !this.reserveSources(1)) return",
            "if (!context || !this.bus || !this.active || this.muted || this.volume <= 0 || this.dying || this.disposed || !this.reserveSources(1)) return",
        )
        text = text.replace(
            "if (!context || !this.master || !this.active || this.muted || this.volume <= 0 || this.disposed) return",
            "if (!context || !this.bus || !this.active || this.muted || this.volume <= 0 || this.disposed) return",
        )

        if "applyZone" not in text or "this.bus.connect(this.warmEq)" not in text:
            print("ERROR: patch incomplete")
            sys.exit(1)
        AI.write_text(text, encoding="utf-8")
        print(f"Patched {AI} ({len(text)} bytes)")

    run(["git", "add", "src/game/audio.ts"])
    st = subprocess.run(["git", "status", "--porcelain", "src/game/audio.ts"], capture_output=True, text=True)
    if not st.stdout.strip():
        print("No local changes; pushing any existing commits…")
        run(["git", "push", "origin", "HEAD"])
        return
    run(["git", "commit", "-m", "Phase 1 audio: master bus (EQ/compressor/limiter) + zone ambience"])
    run(["git", "pull", "--rebase", "origin", "main"])
    run(["git", "push", "origin", "HEAD"])
    print("Done.")
    print('Verify: curl -sL "https://raw.githubusercontent.com/olekariamunyororo-crypto/operation-ink/main/src/game/audio.ts" | grep -c applyZone')

if __name__ == "__main__":
    main()
