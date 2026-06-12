'use client'

import { useEffect, useState } from 'react'

/**
 * GLSL water-ripple cursor layer — fixed full-viewport canvas above all
 * content, pointer-events none. Classic two-buffer height-field sim:
 *
 *   next = (avg of 4 neighbours) * 2 - prev, damped ×0.985
 *
 * Rendered as a specular layer only (we can't sample the DOM): height
 * gradient → fake normal → light dot → cream highlights (≤0.10 alpha)
 * + faint celadon tint on crests (~0.04). Premultiplied alpha.
 *
 * Guards: DPR 1.0 · sim at viewport/2 (drops to /3 if >2ms/frame) ·
 * paused when hidden · rebuilt on resize (debounced 200ms) · disabled
 * on touch + prefers-reduced-motion · null on any WebGL failure.
 */

const VERT = `
attribute vec2 aPos;
varying vec2 vUv;
void main() { vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0., 1.); }
`

// heights packed into bytes: stored = h*0.5+0.5  (PACK/UNPACK)
const SIM_FRAG = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uPrev;
uniform vec2 uTexel;
uniform vec2 uDrop;      // uv of new drop; x<0 → none
uniform float uStrength; // drop amplitude
uniform float uRadius;   // drop radius in uv (x-axis units)
uniform float uAspect;
float H(vec2 uv) { return texture2D(uPrev, uv).r * 2. - 1.; }
void main() {
  float hl = H(vUv - vec2(uTexel.x, 0.));
  float hr = H(vUv + vec2(uTexel.x, 0.));
  float ht = H(vUv + vec2(0., uTexel.y));
  float hb = H(vUv - vec2(0., uTexel.y));
  vec2 c = texture2D(uPrev, vUv).rg;
  float h = c.r * 2. - 1.;
  float prev = c.g * 2. - 1.;
  // wave equation: neighbours' mean*2 − previous, then damping
  float next = (hl + hr + ht + hb) * 0.5 - prev;
  next *= 0.985;
  if (uDrop.x >= 0.) {
    vec2 d = vUv - uDrop;
    d.y /= uAspect;
    next += uStrength * exp(-dot(d, d) / (uRadius * uRadius));
  }
  next = clamp(next, -1., 1.);
  gl_FragColor = vec4(next * 0.5 + 0.5, h * 0.5 + 0.5, 0., 1.);
}
`

const DRAW_FRAG = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uField;
uniform vec2 uTexel;
uniform float uMax;   // max specular alpha — 0.13 over imagery, 0.08 elsewhere
float H(vec2 uv) { return texture2D(uField, uv).r * 2. - 1.; }
void main() {
  float hx = H(vUv + vec2(uTexel.x, 0.)) - H(vUv - vec2(uTexel.x, 0.));
  float hy = H(vUv + vec2(0., uTexel.y)) - H(vUv - vec2(0., uTexel.y));
  vec3 n = normalize(vec3(-hx * 3., -hy * 3., 1.));
  vec3 light = normalize(vec3(-0.35, 0.5, 0.8));
  float spec = pow(max(dot(n, light), 0.), 24.);
  float h = H(vUv);
  float crest = smoothstep(0.004, 0.05, h);
  // premultiplied: teal-tinted specular (teal 70 / white 30) + teal crest
  vec3 tealMix = vec3(0.30, 0.93, 0.86);
  vec3 teal = vec3(0.0, 0.90, 0.80);
  float a = spec * uMax + crest * 0.04;
  gl_FragColor = vec4(tealMix * spec * uMax + teal * crest * 0.04, a);
}
`

function boot(canvas: HTMLCanvasElement, simDiv: number): (() => void) | null {
  const gl = canvas.getContext('webgl', {
    alpha: true,
    premultipliedAlpha: true,
    antialias: false,
    depth: false,
    stencil: false,
  })
  if (!gl) return null

  const W = window.innerWidth
  const H = window.innerHeight
  canvas.width = W // DPR capped at 1.0 for this layer
  canvas.height = H
  const sw = Math.max(2, Math.floor(W / simDiv))
  const sh = Math.max(2, Math.floor(H / simDiv))

  const compile = (type: number, src: string) => {
    const s = gl.createShader(type)!
    gl.shaderSource(s, src)
    gl.compileShader(s)
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) return null
    return s
  }
  const link = (fs: string) => {
    const p = gl.createProgram()!
    const v = compile(gl.VERTEX_SHADER, VERT)
    const f = compile(gl.FRAGMENT_SHADER, fs)
    if (!v || !f) return null
    gl.attachShader(p, v)
    gl.attachShader(p, f)
    gl.linkProgram(p)
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) return null
    return p
  }
  const simProg = link(SIM_FRAG)
  const drawProg = link(DRAW_FRAG)
  if (!simProg || !drawProg) return null

  // fullscreen quad
  const buf = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buf)
  gl.bufferData(
    gl.ARRAY_BUFFER,
    new Float32Array([-1, -1, 3, -1, -1, 3]),
    gl.STATIC_DRAW
  )

  // ping-pong byte targets (mid-gray = zero height)
  const mkTarget = () => {
    const tex = gl.createTexture()!
    gl.bindTexture(gl.TEXTURE_2D, tex)
    const zero = new Uint8Array(sw * sh * 4).fill(128)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, sw, sh, 0, gl.RGBA, gl.UNSIGNED_BYTE, zero)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    const fbo = gl.createFramebuffer()!
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo)
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0)
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE
    return ok ? { tex, fbo } : null
  }
  let a = mkTarget()
  let b = mkTarget()
  gl.bindFramebuffer(gl.FRAMEBUFFER, null)
  if (!a || !b) return null

  const setupAttrib = (prog: WebGLProgram) => {
    const loc = gl.getAttribLocation(prog, 'aPos')
    gl.enableVertexAttribArray(loc)
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)
  }

  const pointer = { x: -1, y: -1, px: -1, py: -1, moved: false }
  const onMove = (e: MouseEvent) => {
    pointer.px = pointer.x
    pointer.py = pointer.y
    pointer.x = e.clientX / W
    pointer.y = 1 - e.clientY / H
    pointer.moved = true
  }
  window.addEventListener('mousemove', onMove, { passive: true })

  let nextIdle = performance.now() + 5000 + Math.random() * 3000
  let raf = 0
  let frameCost = 0
  let frameCount = 0
  let degraded = simDiv > 2
  let rebooted: (() => void) | null = null

  // specular ceiling — 0.13 while an imagery section crosses the
  // viewport centre, 0.08 elsewhere; lerped so the change is invisible
  let specMax = 0.08
  let specTarget = 0.08
  const imagery = Array.from(document.querySelectorAll('[data-imagery]'))
  const checkImagery = () => {
    const mid = window.innerHeight / 2
    specTarget = imagery.some((el) => {
      const r = el.getBoundingClientRect()
      return r.top < mid && r.bottom > mid
    })
      ? 0.13
      : 0.08
  }
  checkImagery()
  window.addEventListener('scroll', checkImagery, { passive: true })

  const tick = () => {
    raf = requestAnimationFrame(tick)
    if (document.hidden) return
    const t0 = performance.now()

    // decide this frame's drop
    let dx = -1
    let dy = -1
    let strength = 0
    if (pointer.moved) {
      const v = Math.hypot(pointer.x - pointer.px, pointer.y - pointer.py)
      dx = pointer.x
      dy = pointer.y
      strength = Math.min(0.06 + v * 6, 0.55)
      pointer.moved = false
    } else if (t0 >= nextIdle) {
      dx = Math.random()
      dy = Math.random()
      strength = 0.0825 // ambient drop — 15% of full
      nextIdle = t0 + 5000 + Math.random() * 3000
    }

    // sim step: read a → write b
    gl.useProgram(simProg)
    gl.bindFramebuffer(gl.FRAMEBUFFER, b!.fbo)
    gl.viewport(0, 0, sw, sh)
    gl.bindTexture(gl.TEXTURE_2D, a!.tex)
    gl.uniform1i(gl.getUniformLocation(simProg, 'uPrev'), 0)
    gl.uniform2f(gl.getUniformLocation(simProg, 'uTexel'), 1 / sw, 1 / sh)
    gl.uniform2f(gl.getUniformLocation(simProg, 'uDrop'), dx, dy)
    gl.uniform1f(gl.getUniformLocation(simProg, 'uStrength'), strength)
    gl.uniform1f(gl.getUniformLocation(simProg, 'uRadius'), 14 / sw)
    gl.uniform1f(gl.getUniformLocation(simProg, 'uAspect'), sw / sh)
    setupAttrib(simProg)
    gl.drawArrays(gl.TRIANGLES, 0, 3)

    // render pass to screen
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    gl.viewport(0, 0, W, H)
    gl.useProgram(drawProg)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
    gl.bindTexture(gl.TEXTURE_2D, b!.tex)
    gl.uniform1i(gl.getUniformLocation(drawProg, 'uField'), 0)
    gl.uniform2f(gl.getUniformLocation(drawProg, 'uTexel'), 1 / sw, 1 / sh)
    specMax += (specTarget - specMax) * 0.05
    gl.uniform1f(gl.getUniformLocation(drawProg, 'uMax'), specMax)
    setupAttrib(drawProg)
    gl.drawArrays(gl.TRIANGLES, 0, 3)

    // swap ping-pong
    const t = a
    a = b
    b = t

    // budget check over the first ~120 frames: >2ms avg → drop to /3
    if (!degraded && frameCount < 120) {
      frameCost += performance.now() - t0
      frameCount += 1
      if (frameCount === 120 && frameCost / 120 > 2) {
        degraded = true
        cleanup()
        rebooted = boot(canvas, 3)
      }
    }
  }
  tick()

  const cleanup = () => {
    cancelAnimationFrame(raf)
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('scroll', checkImagery)
    if (a) {
      gl.deleteTexture(a.tex)
      gl.deleteFramebuffer(a.fbo)
    }
    if (b) {
      gl.deleteTexture(b.tex)
      gl.deleteFramebuffer(b.fbo)
    }
    gl.deleteProgram(simProg)
    gl.deleteProgram(drawProg)
    gl.deleteBuffer(buf)
  }

  return () => {
    cleanup()
    rebooted?.()
  }
}

export default function WaterCursor() {
  const [enabled, setEnabled] = useState(false)

  useEffect(() => {
    const fine = window.matchMedia('(pointer: fine)').matches
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!fine || reduced) return
    // ambient layer — boot after idle so it never competes with hydration
    const enable = () => setEnabled(true)
    if ('requestIdleCallback' in window) {
      const id = (window as Window & typeof globalThis).requestIdleCallback(enable, { timeout: 2500 })
      return () => cancelIdleCallback(id)
    }
    const t = setTimeout(enable, 1500)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!enabled) return
    const canvas = document.getElementById('water-cursor') as HTMLCanvasElement | null
    if (!canvas) return

    let destroy = boot(canvas, 2)
    if (!destroy) {
      setEnabled(false) // WebGL unavailable — vanish silently
      return
    }

    // destroy + recreate on resize, debounced 200ms
    let timer: ReturnType<typeof setTimeout>
    const onResize = () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        destroy?.()
        destroy = boot(canvas, 2)
        if (!destroy) setEnabled(false)
      }, 200)
    }
    window.addEventListener('resize', onResize)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', onResize)
      destroy?.()
    }
  }, [enabled])

  if (!enabled) return null
  return (
    <canvas
      id="water-cursor"
      aria-hidden
      className="pointer-events-none fixed inset-0 z-[80]"
      style={{ width: '100vw', height: '100vh' }}
    />
  )
}
