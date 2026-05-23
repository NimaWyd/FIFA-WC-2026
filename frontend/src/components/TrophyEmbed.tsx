"use client";

import { Suspense, useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF, OrbitControls, Environment } from "@react-three/drei";
import * as THREE from "three";

function Trophy() {
  const { scene } = useGLTF("/trophy.glb");
  const ref = useRef<THREE.Group>(null);

  // Clone so each Canvas instance owns its own copy of the scene graph.
  // useGLTF caches by URL — sharing the same object across two <Canvas> elements
  // causes Three.js to move the object to the most-recently-committing parent,
  // leaving the other canvas with scrambled transforms.
  const clonedScene = useMemo(() => scene.clone(true), [scene]);

  const [scale, position] = useMemo(() => {
    const box = new THREE.Box3().setFromObject(clonedScene);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);
    const maxDim = Math.max(size.x, size.y, size.z);
    const s = 3 / maxDim;
    const p: [number, number, number] = [-center.x * s, -center.y * s, -center.z * s];
    return [s, p];
  }, [clonedScene]);

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.25;
  });

  return <primitive ref={ref} object={clonedScene} scale={scale} position={position} />;
}

useGLTF.preload("/trophy.glb");

export default function TrophyEmbed({ className }: { className?: string }) {
  return (
    <div className={className}>
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [0, 0, 6], fov: 40 }}
        gl={{ alpha: true, antialias: true }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[4, 8, 4]} intensity={1.4} />
        <directionalLight position={[-4, 2, -2]} intensity={0.4} color="#f5c842" />
        <Suspense fallback={null}>
          <Trophy />
          <Environment preset="studio" />
        </Suspense>
        <OrbitControls enableZoom={false} enablePan={false} minPolarAngle={Math.PI / 4} maxPolarAngle={Math.PI / 1.8} />
      </Canvas>
    </div>
  );
}
