"use client";

import { useRef, useMemo, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Float, Stars, MeshDistortMaterial, Sphere } from "@react-three/drei";
import * as THREE from "three";

// ─── Mouse-responsive camera ─────────────────────────────────────────────────
function CameraRig({ mouse }: { mouse: React.MutableRefObject<[number, number]> }) {
  const { camera } = useThree();
  useFrame(() => {
    camera.position.x += (mouse.current[0] * 1.2 - camera.position.x) * 0.04;
    camera.position.y += (mouse.current[1] * 0.6 - camera.position.y) * 0.04;
    camera.lookAt(0, 0, 0);
  });
  return null;
}

// ─── Central morphic forge core ──────────────────────────────────────────────
function ForgeCore() {
  const meshRef = useRef<THREE.Mesh>(null!);
  const innerRef = useRef<THREE.Mesh>(null!);

  useFrame((_, delta) => {
    meshRef.current.rotation.x += delta * 0.08;
    meshRef.current.rotation.y += delta * 0.13;
    innerRef.current.rotation.x -= delta * 0.12;
    innerRef.current.rotation.z += delta * 0.09;
  });

  return (
    <Float speed={1.2} rotationIntensity={0.3} floatIntensity={0.5}>
      <group>
        <mesh ref={meshRef}>
          <torusKnotGeometry args={[1, 0.32, 200, 20, 2, 3]} />
          <MeshDistortMaterial
            color="#7c3aed"
            emissive="#a855f7"
            emissiveIntensity={0.9}
            distort={0.25}
            speed={2}
            roughness={0}
            metalness={1}
          />
        </mesh>

        <mesh ref={innerRef} scale={0.55}>
          <torusKnotGeometry args={[1, 0.2, 120, 16, 3, 5]} />
          <MeshDistortMaterial
            color="#e879f9"
            emissive="#c026d3"
            emissiveIntensity={0.6}
            distort={0.4}
            speed={3}
            roughness={0.1}
            metalness={0.9}
            transparent
            opacity={0.7}
          />
        </mesh>

        <Sphere args={[2.2, 16, 16]}>
          <meshBasicMaterial color="#7c3aed" transparent opacity={0.04} />
        </Sphere>
        <Sphere args={[2.8, 16, 16]}>
          <meshBasicMaterial color="#a855f7" transparent opacity={0.02} />
        </Sphere>
      </group>
    </Float>
  );
}

// ─── Agent node ───────────────────────────────────────────────────────────────
const AGENTS = [
  { color: "#6366f1", emissive: "#4338ca", size: 0.18 },
  { color: "#34d399", emissive: "#059669", size: 0.15 },
  { color: "#a855f7", emissive: "#7c3aed", size: 0.17 },
  { color: "#f87171", emissive: "#dc2626", size: 0.14 },
  { color: "#fbbf24", emissive: "#d97706", size: 0.16 },
];

function AgentNode({ agent, index, total }: { agent: typeof AGENTS[0]; index: number; total: number }) {
  const groupRef = useRef<THREE.Group>(null!);
  const meshRef = useRef<THREE.Mesh>(null!);
  const angle = useRef((index / total) * Math.PI * 2);

  useFrame((_, delta) => {
    angle.current += delta * (0.35 - index * 0.04);
    const r = 3.2 + index * 0.15;
    groupRef.current.position.x = Math.cos(angle.current) * r;
    groupRef.current.position.z = Math.sin(angle.current) * r;
    groupRef.current.position.y = Math.sin(angle.current * 1.3) * 0.4;
    meshRef.current.rotation.x += delta * 1.2;
    meshRef.current.rotation.y += delta * 0.8;
  });

  return (
    <group ref={groupRef}>
      <mesh ref={meshRef}>
        <octahedronGeometry args={[agent.size]} />
        <meshStandardMaterial
          color={agent.color}
          emissive={agent.emissive}
          emissiveIntensity={0.8}
          roughness={0.1}
          metalness={0.9}
        />
      </mesh>
      <Sphere args={[agent.size * 2.2, 8, 8]}>
        <meshBasicMaterial color={agent.color} transparent opacity={0.06} />
      </Sphere>
    </group>
  );
}

// ─── Orbital ring ─────────────────────────────────────────────────────────────
function OrbitalRing({ radius, opacity = 0.15 }: { radius: number; opacity?: number }) {
  const geo = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 160; i++) {
      const t = (i / 160) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(t) * radius, 0, Math.sin(t) * radius));
    }
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [radius]);

  return (
    <line geometry={geo}>
      <lineBasicMaterial color="#6d28d9" transparent opacity={opacity} />
    </line>
  );
}

// ─── Particle field ───────────────────────────────────────────────────────────
function ParticleField({ count = 400 }: { count?: number }) {
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 4 + Math.random() * 14;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);
    }
    return pos;
  }, [count]);

  const ref = useRef<THREE.Points>(null!);
  useFrame((_, delta) => { ref.current.rotation.y += delta * 0.02; });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#a855f7" size={0.025} transparent opacity={0.6} sizeAttenuation />
    </points>
  );
}

// ─── Scene ────────────────────────────────────────────────────────────────────
function Scene({ mouse }: { mouse: React.MutableRefObject<[number, number]> }) {
  return (
    <>
      <CameraRig mouse={mouse} />
      <ambientLight intensity={0.1} />
      <pointLight position={[0, 0, 0]}   color="#a855f7" intensity={8}  distance={12} />
      <pointLight position={[5, 3, -3]}  color="#e879f9" intensity={4}  distance={15} />
      <pointLight position={[-5, -2, 4]} color="#6366f1" intensity={3}  distance={12} />
      <pointLight position={[0, -4, 0]}  color="#7c3aed" intensity={2}  distance={10} />

      <Stars radius={40} depth={30} count={1200} factor={2} fade speed={0.3} />
      <ParticleField count={400} />

      <ForgeCore />

      {AGENTS.map((agent, i) => (
        <AgentNode key={i} agent={agent} index={i} total={AGENTS.length} />
      ))}

      <OrbitalRing radius={3.3} opacity={0.12} />
      <OrbitalRing radius={3.8} opacity={0.07} />
    </>
  );
}

// ─── Public component ─────────────────────────────────────────────────────────
export function HeroScene({ className }: { className?: string }) {
  const mouse = useRef<[number, number]>([0, 0]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      mouse.current = [
        (e.clientX / window.innerWidth - 0.5) * 2,
        -(e.clientY / window.innerHeight - 0.5) * 2,
      ];
    };
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, []);

  return (
    <div className={className} aria-hidden>
      <Canvas
        camera={{ position: [0, 1.5, 7], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <Scene mouse={mouse} />
      </Canvas>
    </div>
  );
}
