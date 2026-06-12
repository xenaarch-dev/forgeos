'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

/**
 * The constellation — geometry-only Three.js scene. No OrbitControls,
 * no postprocessing, no loaders, zero external assets.
 *
 * Guards: DPR capped 1.5 · RAF pauses when tab hidden or off-screen ·
 * full dispose on unmount · FPS watchdog (3s avg < 30fps → onFail,
 * parent swaps to the SVG fallback permanently for the session).
 */
export default function LoopScene({ onFail }: { onFail: () => void }) {
  const hostRef = useRef<HTMLDivElement>(null)
  const failRef = useRef(onFail)
  failRef.current = onFail

  useEffect(() => {
    const host = hostRef.current
    if (!host) return

    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    } catch {
      failRef.current()
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
    renderer.setClearColor(0x000000, 0)
    host.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100)
    camera.position.z = 10

    scene.add(new THREE.AmbientLight(0xe8e3d2, 0.4))
    const coreLight = new THREE.PointLight(0xd9832a, 28, 30)
    scene.add(coreLight)

    // central icosahedron — the ember, in 3D
    const coreGeo = new THREE.IcosahedronGeometry(1.25, 0)
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0xd9832a,
      emissive: 0xd9832a,
      emissiveIntensity: 0.55,
      metalness: 0.2,
      roughness: 0.4,
    })
    const core = new THREE.Mesh(coreGeo, coreMat)
    scene.add(core)

    // 7 orbiters — varied radii, speeds, inclinations
    const orbGeo = new THREE.IcosahedronGeometry(0.16, 0)
    const orbMat = new THREE.MeshStandardMaterial({
      color: 0x3eb489,
      emissive: 0x3eb489,
      emissiveIntensity: 0.45,
      metalness: 0.1,
      roughness: 0.5,
    })
    const orbiters = Array.from({ length: 7 }, (_, i) => {
      const mesh = new THREE.Mesh(orbGeo, orbMat)
      scene.add(mesh)
      return {
        mesh,
        radius: 2.7 + (i % 4) * 0.55,
        speed: 0.12 + (i % 3) * 0.07,
        phase: (i / 7) * Math.PI * 2,
        incline: ((i % 5) - 2) * 0.18,
      }
    })

    // ~800 background points, celadon, 10% opacity
    const ptsGeo = new THREE.BufferGeometry()
    const positions = new Float32Array(800 * 3)
    for (let i = 0; i < 800; i++) {
      const r = 6 + Math.random() * 7
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = r * Math.cos(phi) - 4
    }
    ptsGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const ptsMat = new THREE.PointsMaterial({
      color: 0x3eb489,
      size: 0.04,
      transparent: true,
      opacity: 0.1,
      depthWrite: false,
    })
    scene.add(new THREE.Points(ptsGeo, ptsMat))

    // bezier arcs orbiter→core, rebuilt each frame from live positions
    const ARC_SEGS = 22
    const arcMat = new THREE.LineBasicMaterial({
      color: 0x3eb489,
      transparent: true,
      opacity: 0.22,
    })
    const arcs = orbiters.map(() => {
      const geo = new THREE.BufferGeometry()
      geo.setAttribute(
        'position',
        new THREE.BufferAttribute(new Float32Array((ARC_SEGS + 1) * 3), 3)
      )
      const line = new THREE.Line(geo, arcMat)
      scene.add(line)
      return geo
    })
    const curve = new THREE.QuadraticBezierCurve3()
    const tmp = new THREE.Vector3()

    // light pulse travelling a random arc every ~2s
    const pulseMat = new THREE.MeshBasicMaterial({
      color: 0xe8e3d2,
      transparent: true,
      opacity: 0,
    })
    const pulse = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 8), pulseMat)
    scene.add(pulse)
    let pulseArc = 0
    let pulseT = 1.5 // >1 means idle

    const setCurve = (i: number) => {
      const o = orbiters[i].mesh.position
      curve.v0.copy(o)
      curve.v1.set(o.x * 0.5, o.y * 0.5 + 1.2, o.z * 0.5 + 0.6)
      curve.v2.set(0, 0, 0)
    }

    // sizing
    const resize = () => {
      const w = host.clientWidth
      const h = host.clientHeight
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    resize()
    window.addEventListener('resize', resize)

    // cursor parallax ≤6°, lerped
    const targetRot = { x: 0, y: 0 }
    const MAX = THREE.MathUtils.degToRad(6)
    const onPointer = (e: MouseEvent) => {
      targetRot.y = ((e.clientX / window.innerWidth) * 2 - 1) * MAX
      targetRot.x = ((e.clientY / window.innerHeight) * 2 - 1) * MAX
    }
    window.addEventListener('mousemove', onPointer, { passive: true })

    // visibility guards
    let inView = true
    const io = new IntersectionObserver(([e]) => {
      inView = e.isIntersecting
    })
    io.observe(host)

    // FPS watchdog — 3s rolling window
    let frames = 0
    let windowStart = performance.now()
    let raf = 0
    const clock = new THREE.Clock()

    const tick = () => {
      raf = requestAnimationFrame(tick)
      if (!inView || document.hidden) {
        clock.getDelta() // swallow the gap so motion doesn't jump
        windowStart = performance.now()
        frames = 0
        return
      }
      const dt = clock.getDelta()
      const t = clock.elapsedTime

      core.rotation.x += dt * 0.12
      core.rotation.y += dt * 0.18

      orbiters.forEach((o, i) => {
        const a = o.phase + t * o.speed
        o.mesh.position.set(
          Math.cos(a) * o.radius,
          Math.sin(a) * o.radius * Math.sin(o.incline),
          Math.sin(a) * o.radius * Math.cos(o.incline) * 0.6
        )
        o.mesh.rotation.y += dt * 0.8

        setCurve(i)
        const attr = arcs[i].getAttribute('position') as THREE.BufferAttribute
        for (let s = 0; s <= ARC_SEGS; s++) {
          curve.getPoint(s / ARC_SEGS, tmp)
          attr.setXYZ(s, tmp.x, tmp.y, tmp.z)
        }
        attr.needsUpdate = true
      })

      // pulse
      pulseT += dt / 0.9
      if (pulseT >= 1) {
        pulseMat.opacity = 0
        if (pulseT > 2.2) {
          pulseArc = Math.floor(Math.random() * orbiters.length)
          pulseT = 0
        }
      } else {
        setCurve(pulseArc)
        curve.getPoint(pulseT, tmp)
        pulse.position.copy(tmp)
        pulseMat.opacity = Math.sin(pulseT * Math.PI) * 0.9
      }

      // parallax lerp
      scene.rotation.x += (targetRot.x - scene.rotation.x) * 0.05
      scene.rotation.y += (targetRot.y - scene.rotation.y) * 0.05

      renderer.render(scene, camera)

      frames += 1
      const now = performance.now()
      if (now - windowStart >= 3000) {
        const fps = (frames / (now - windowStart)) * 1000
        if (fps < 30) {
          try {
            sessionStorage.setItem('forgeos-loop3d', 'failed')
          } catch {}
          failRef.current()
          return
        }
        frames = 0
        windowStart = now
      }
    }
    tick()

    return () => {
      cancelAnimationFrame(raf)
      io.disconnect()
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onPointer)
      coreGeo.dispose()
      coreMat.dispose()
      orbGeo.dispose()
      orbMat.dispose()
      ptsGeo.dispose()
      ptsMat.dispose()
      arcs.forEach((g) => g.dispose())
      arcMat.dispose()
      pulse.geometry.dispose()
      pulseMat.dispose()
      renderer.dispose()
      if (renderer.domElement.parentElement === host) {
        host.removeChild(renderer.domElement)
      }
    }
  }, [])

  return (
    <div
      ref={hostRef}
      aria-hidden
      className="mx-auto w-full max-w-[640px]"
      style={{ height: 'min(560px, 70vw)' }}
    />
  )
}
