import { Draft, type Fill } from '../render/ink'

/** Low concrete vehicle barrier. */
export function jerseyBarrier(g: Draft, x: number, z: number, yaw = 0, length = 2.4) {
  const h = 0.85, w = 0.55
  g.box(length, h, w, x, h / 2, z, 'concrete', 'detail', [0, yaw, 0])
  const half = length / 2 - 0.08
  for (const side of [-1, 1] as const) {
    const px = x + Math.cos(yaw) * side * half
    const pz = z + Math.sin(yaw) * side * half
    g.line([[px, 0.12, pz], [px, h - 0.08, pz]], 'detail')
  }
  g.line([
    [x - Math.cos(yaw) * half, h - 0.05, z - Math.sin(yaw) * half],
    [x + Math.cos(yaw) * half, h - 0.05, z + Math.sin(yaw) * half],
  ], 'mesh')
}

/** Stacked sandbags. */
export function sandbagStack(g: Draft, x: number, z: number, bags = 5, yaw = 0) {
  const bw = 0.55, bd = 0.35, bh = 0.22
  for (let i = 0; i < bags; i++) {
    const row = Math.floor(i / 2)
    const col = i % 2
    const ox = (col - 0.5) * 0.5
    const oy = row * bh + bh / 2
    const oz = (row % 2) * 0.08
    const px = x + Math.cos(yaw) * ox - Math.sin(yaw) * oz
    const pz = z + Math.sin(yaw) * ox + Math.cos(yaw) * oz
    g.box(bw, bh * 0.92, bd, px, oy, pz, 'paper', 'detail', [0, yaw, 0])
    g.hatch(
      [px - 0.2, oy - 0.05, pz + bd / 2 + 0.01],
      [0.35, 0, 0],
      [0, 0.12, 0],
      { spacing: 0.07, inset: 0.02, seed: i + 11 },
    )
  }
}

/** Wooden pallet. */
export function pallet(g: Draft, x: number, z: number, yaw = 0) {
  const w = 1.2, d = 1.0, h = 0.14
  g.box(w, 0.04, d, x, 0.12, z, 'paper', 'detail', [0, yaw, 0])
  for (const side of [-1, 1] as const) {
    const ox = side * (w / 2 - 0.08)
    const px = x + Math.cos(yaw) * ox
    const pz = z + Math.sin(yaw) * ox
    g.box(0.1, h, d * 0.9, px, h / 2, pz, 'paper', 'detail', [0, yaw, 0])
  }
  for (let i = -1; i <= 1; i++) {
    const oz = i * 0.32
    const px = x - Math.sin(yaw) * oz
    const pz = z + Math.cos(yaw) * oz
    g.box(w * 0.92, 0.03, 0.08, px, 0.15, pz, 'paper', 'mesh', [0, yaw, 0])
  }
}

/** Oil drums clustered together. */
export function barrelCluster(g: Draft, x: number, z: number, count = 3, fill: Fill = 'roof') {
  const offsets: [number, number][] = [[0, 0], [0.85, 0.15], [0.35, 0.75], [-0.55, 0.55]]
  for (let i = 0; i < count; i++) {
    const [ox, oz] = offsets[i % offsets.length]
    const bx = x + ox, bz = z + oz
    const h = 1.0 + (i % 2) * 0.08
    g.cylinder(0.38, h, bx, h / 2, bz, fill)
    for (const y of [0.2, h - 0.15]) g.ring(0.385, y, bx, bz, 'detail', 32)
    g.line([[bx - 0.2, h + 0.02, bz], [bx + 0.2, h + 0.02, bz]], 'mesh')
    g.line([[bx, h + 0.02, bz - 0.2], [bx, h + 0.02, bz + 0.2]], 'mesh')
  }
}

/** Vertical cable / wire spool. */
export function cableSpool(g: Draft, x: number, z: number) {
  const r = 0.55, h = 0.75
  g.cylinder(r, 0.08, x, 0.06, z, 'paper')
  g.cylinder(0.18, h, x, h / 2 + 0.06, z, 'paper')
  g.cylinder(r, 0.08, x, h + 0.06, z, 'paper')
  for (const y of [0.1, h + 0.02]) g.ring(r + 0.01, y, x, z, 'detail', 28)
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2
    g.line([
      [x + Math.cos(a) * 0.2, 0.12, z + Math.sin(a) * 0.2],
      [x + Math.cos(a) * 0.2, h, z + Math.sin(a) * 0.2],
    ], 'mesh')
  }
}
