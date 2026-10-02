import React from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";

const nodes: [number, number, number, string][] = [
  [-2.5, 1.25, 0, "#b978f3"],
  [-1.1, 0.25, 0.35, "#b7f45b"],
  [0.15, 1.35, -0.2, "#b7f45b"],
  [1.2, 0.05, 0.4, "#ff6679"],
  [2.45, 1.05, -0.15, "#ff6679"],
  [2.15, -1.3, 0.15, "#b978f3"],
  [0.25, -1.45, -0.1, "#ff6679"],
  [-2.1, -1.15, 0.25, "#b978f3"],
];

const connections: [number, number][] = [
  [0, 1], [0, 7], [1, 2], [1, 3], [1, 6], [2, 3], [3, 4], [3, 6], [4, 5], [5, 6], [6, 7],
];

function NetworkScene({ reduced }: { reduced: boolean }) {
  const group = React.useRef<THREE.Group>(null);
  const pulseA = React.useRef<THREE.Mesh>(null);
  const pulseB = React.useRef<THREE.Mesh>(null);
  useFrame((state, delta) => {
    if (!group.current || reduced) return;
    group.current.rotation.y = THREE.MathUtils.lerp(group.current.rotation.y, state.pointer.x * 0.12, 0.035);
    group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, -state.pointer.y * 0.08, 0.035);
    group.current.rotation.z += delta * 0.025;
    const t = (state.clock.elapsedTime * 0.28) % 1;
    const a = new THREE.Vector3(...nodes[1].slice(0, 3) as [number, number, number]);
    const b = new THREE.Vector3(...nodes[3].slice(0, 3) as [number, number, number]);
    pulseA.current?.position.copy(a.lerp(b, t));
    const c = new THREE.Vector3(...nodes[3].slice(0, 3) as [number, number, number]);
    const d = new THREE.Vector3(...nodes[6].slice(0, 3) as [number, number, number]);
    pulseB.current?.position.copy(c.lerp(d, (t + 0.45) % 1));
  });
  return (
    <group ref={group} rotation={[0.12, -0.08, -0.05]}>
      {connections.map(([from, to]) => (
        <Line
          key={`${from}-${to}`}
          points={[nodes[from].slice(0, 3) as [number, number, number], nodes[to].slice(0, 3) as [number, number, number]]}
          color={from === 3 || to === 3 ? "#ff6679" : "#9da0ad"}
          transparent
          opacity={from === 3 || to === 3 ? 0.72 : 0.38}
          lineWidth={from === 3 || to === 3 ? 1.6 : 0.8}
        />
      ))}
      {nodes.map(([x, y, z, color], index) => (
        <group key={index} position={[x, y, z]}>
          <mesh>
            <sphereGeometry args={[index === 3 ? 0.27 : 0.18, 24, 24]} />
            <meshStandardMaterial color={color} roughness={0.28} metalness={0.08} />
          </mesh>
          <mesh scale={1.7}>
            <sphereGeometry args={[index === 3 ? 0.27 : 0.18, 20, 20]} />
            <meshBasicMaterial color={color} transparent opacity={0.13} />
          </mesh>
        </group>
      ))}
      <mesh ref={pulseA}>
        <sphereGeometry args={[0.075, 16, 16]} />
        <meshBasicMaterial color="#ff6679" />
      </mesh>
      <mesh ref={pulseB}>
        <sphereGeometry args={[0.065, 16, 16]} />
        <meshBasicMaterial color="#b7f45b" />
      </mesh>
    </group>
  );
}

export default function LoginNetwork3D() {
  const [hidden, setHidden] = React.useState(document.hidden);
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  React.useEffect(() => {
    const onVisibility = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);
  return (
    <Canvas
      aria-hidden="true"
      camera={{ position: [0, 0, 7.4], fov: 42 }}
      dpr={[1, 1.5]}
      frameloop={hidden || reduced ? "demand" : "always"}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
    >
      <ambientLight intensity={1.25} />
      <directionalLight position={[3, 4, 5]} intensity={2.1} color="#fffaf2" />
      <pointLight position={[-3, -2, 3]} intensity={13} color="#b978f3" distance={8} />
      <NetworkScene reduced={reduced} />
    </Canvas>
  );
}
