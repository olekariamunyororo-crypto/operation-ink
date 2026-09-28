import * as THREE from 'three'
import { palette } from './ink'

/**
 * Soft paper sky — gradient dome, no photo textures.
 * Horizon stays near pure paper white; zenith is a cool gray wash so the compound
 * does not float in a hard void. Kept unlit and behind everything (depthWrite off).
 */
export function createPaperSky(radius = 480) {
  const geometry = new THREE.SphereGeometry(radius, 48, 24)
  const material = new THREE.ShaderMaterial({
    name: 'PaperSky',
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      topColor: { value: new THREE.Color(0xdcdce0) },
      midColor: { value: new THREE.Color(0xf2f2f4) },
      bottomColor: { value: new THREE.Color(palette.paper) },
      // Soft sun disc — barely there, ink-world overcast
      sunColor: { value: new THREE.Color(0xf7f7f5) },
      sunDirection: { value: new THREE.Vector3(0.35, 0.55, 0.4).normalize() },
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.0);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 topColor;
      uniform vec3 midColor;
      uniform vec3 bottomColor;
      uniform vec3 sunColor;
      uniform vec3 sunDirection;
      varying vec3 vWorld;
      void main() {
        vec3 dir = normalize(vWorld);
        float h = dir.y;
        float horizon = smoothstep(-0.05, 0.35, h);
        float zenith = smoothstep(0.25, 0.95, h);
        vec3 col = mix(bottomColor, midColor, horizon);
        col = mix(col, topColor, zenith * 0.85);
        float sun = pow(max(dot(dir, sunDirection), 0.0), 32.0) * 0.35;
        col = mix(col, sunColor, sun);
        float g = fract(sin(dot(dir.xz * 40.0, vec2(12.9898, 78.233))) * 43758.5453);
        col *= 1.0 - g * 0.03;
        gl_FragColor = vec4(col, 1.0);
      }
    `,
  })
  const mesh = new THREE.Mesh(geometry, material)
  mesh.name = 'Paper sky'
  mesh.frustumCulled = false
  mesh.renderOrder = -1000
  return mesh
}

/** Optional distance haze so far fence lines soften into the page. */
export function applyPaperFog(scene: THREE.Scene, near = 90, far = 260) {
  scene.fog = new THREE.Fog(palette.paper, near, far)
}
