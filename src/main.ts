import * as THREE from 'three'
import { EnvironmentCamera, views, type ViewName } from './camera'
import { palette, resizeInk } from './render/ink'
import { applyPaperFog, createPaperSky } from './render/sky'
import { createCompound } from './world/compound'
import { EnvironmentInteractions } from './interactions'
import { FirstPersonController } from './player/controller'
import { VRWalkthrough } from './vr/walkthrough'
import { createMissionWorld, prepareCompound } from './game/world'
import { MissionRuntime } from './game/runtime'
import './style.css'

const canvas = document.querySelector<HTMLCanvasElement>('#world')!
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' })
// A small supersampling floor keeps sub-pixel details clean on non-Retina displays.
// 1.25 is indistinguishable from 1.5 at 100% zoom and shades 31% fewer pixels; 1.0 visibly hardens far strokes.
let resolutionScale = 1
const pixelRatio = () => Math.max(1, Math.min(Math.max(window.devicePixelRatio, 1.25), 2) * resolutionScale)
renderer.setPixelRatio(pixelRatio())
renderer.outputColorSpace = THREE.SRGBColorSpace
renderer.toneMapping = THREE.NoToneMapping
renderer.setClearColor(palette.paper)
renderer.shadowMap.enabled = false

const scene = new THREE.Scene()
scene.name = 'Black ballpoint compound'
// Paper gradient dome instead of a flat void; clear color still matches the horizon.
scene.background = null
scene.add(createPaperSky())
applyPaperFog(scene)
const compound = createCompound()
const missionWorld = new URLSearchParams(location.search).get('explore') === '1' ? null : createMissionWorld(compound)
if (missionWorld) prepareCompound(compound)
scene.add(compound)
if (missionWorld) scene.add(missionWorld.root)

let frame = 0
let lastTime = performance.now()
let rendering = false
let contextLost = false
let disposed = false
const invalidate = () => {
  if (!frame && !renderer.xr.isPresenting && !contextLost && !disposed) {
    if (!rendering) lastTime = performance.now()
    frame = requestAnimationFrame(render)
  }
}
const camera = new EnvironmentCamera(canvas, invalidate)
const interactions = new EnvironmentInteractions(canvas, scene, () => camera.active, invalidate, () => camera.walking)
const player = new FirstPersonController(canvas, scene, camera, interactions, invalidate)
const vr = new VRWalkthrough(renderer, scene, camera, player, invalidate)
const mission = missionWorld ? new MissionRuntime(scene, camera, player, missionWorld, invalidate) : null
const frameTimes: number[] = []
let startupReady = !mission
// Initialization positions the mission camera and settles the menu (including
// load errors). Reveal only after that state has actually been rendered.
void mission?.initialized.then(() => {
  startupReady = true
  // Warm GPU programs for the loaded mission.
  try { renderer.compile(scene, camera.active) } catch { /* best-effort */ }
  invalidate()
})

renderer.xr.addEventListener('sessionstart', () => {
  cancelAnimationFrame(frame)
  frame = 0
  lastTime = performance.now()
  renderer.setAnimationLoop(render)
})
renderer.xr.addEventListener('sessionend', () => {
  renderer.setAnimationLoop(null)
  if (!disposed) resize()
})

function render(now: number, xrFrame?: XRFrame) {
  if (disposed || contextLost) return
  frame = 0
  rendering = true
  const elapsed = (now - lastTime) / 1000
  const dt = Math.min(elapsed, 0.05)
  if (player.playing && elapsed < 1) {
    frameTimes.push(elapsed * 1000); if (frameTimes.length > 600) frameTimes.shift()
    if (!resolutionSettled && !renderer.xr.isPresenting && ++resolutionFrames >= 90) adaptResolution()
  }
  lastTime = now
  // Door travel uses real elapsed time even when low FPS caps the physics step.
  const doorsMoving = interactions.update(elapsed)
  let moving = false
  if (vr.active && xrFrame) vr.update(dt, xrFrame)
  else moving = player.update(dt) || camera.update(dt)
  let missionMoving = false
  try {
    // Cinematic travel follows real frame time; physics keeps its safe step cap.
    missionMoving = mission?.update(dt, elapsed) ?? false
    renderer.render(scene, vr.active ? vr.rig.camera : camera.active)
  }
  finally { mission?.finishFrame() }
  if (startupReady) {
    canvas.dataset.ready = 'true'
    if (document.documentElement.hasAttribute('data-loading')) {
      document.documentElement.removeAttribute('data-loading')
      document.querySelector<HTMLButtonElement>('#walk-start:not(:disabled)')?.focus({ preventScroll: true })
    }
  }
  if (moving || doorsMoving || missionMoving) invalidate()
  rendering = false
}

// Slow GPUs: when play stays under ~40 fps, shade fewer pixels (never below 1×). Stroke widths are in CSS px and keep their size.
// ponytail: one-way and frame-time based. Frame time cannot tell GPU- from CPU-bound, so a step that
// does not help is undone and adaptation stops; a reload restores full resolution. Add step-up if players ask.
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

function resize() {
  if (renderer.xr.isPresenting) return
  const width = window.innerWidth, height = window.innerHeight
  renderer.setPixelRatio(pixelRatio())
  renderer.setSize(width, height, false)
  camera.resize(width, height)
  resizeInk(width, height)
  invalidate()
}
window.addEventListener('resize', resize)
const visibilityChanged = () => {
  lastTime = performance.now()
  if (!document.hidden) invalidate()
}
document.addEventListener('visibilitychange', visibilityChanged)
canvas.addEventListener('webglcontextlost', event => {
  event.preventDefault()
  contextLost = true
  cancelAnimationFrame(frame)
  frame = 0
  renderer.setAnimationLoop(null)
  void vr.exit().catch(() => {})
  canvas.dataset.ready = 'false'
})
canvas.addEventListener('webglcontextrestored', () => {
  contextLost = false
  resize()
})
resize()
const initialView = new URLSearchParams(location.search).get('view')
if (initialView && initialView in views) camera.setView(initialView as ViewName)
else player.enable()

// Development inspection surface, intentionally absent from production builds and the page UI.
if (import.meta.env.DEV) {
  Object.assign(window, {
    __environment: {
      scene, renderer, camera,
      interactions, player, vr, mission,
      setView: (name: ViewName) => camera.setView(name),
      invalidate,
      stats: () => ({
        drawCalls: renderer.info.render.calls,
        triangles: renderer.info.render.triangles,
        geometries: renderer.info.memory.geometries,
        textures: renderer.info.memory.textures,
        view: camera.view,
        fps: frameTimes.length ? 1000 / (frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length) : null,
        frameP95: frameTimes.length ? [...frameTimes].sort((a,b)=>a-b)[Math.floor(frameTimes.length*0.95)] : null,
        camera: camera.active.position.toArray(),
        objects: scene.children[0].children.map(object => ({ name: object.name, kind: object.userData.kind ?? 'environment' })),
      }),
    },
  })
}

import.meta.hot?.dispose(() => {
  disposed = true
  cancelAnimationFrame(frame)
  renderer.setAnimationLoop(null)
  window.removeEventListener('resize', resize)
  document.removeEventListener('visibilitychange', visibilityChanged)
  vr.dispose()
  mission?.dispose()
  player.dispose()
  camera.dispose()
  interactions.dispose()
  const materials = new Set<THREE.Material>()
  scene.traverse(object => {
    if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
      object.geometry.dispose()
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material)
    }
  })
  materials.forEach(material => material.dispose())
  renderer.dispose()
})
