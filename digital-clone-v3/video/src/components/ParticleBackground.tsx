import React, { useMemo } from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

interface Particle {
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  opacity: number;
}

export const ParticleBackground: React.FC = () => {
  const frame = useCurrentFrame();

  const particles = useMemo<Particle[]>(() => {
    const seed = 12345;
    const result: Particle[] = [];
    for (let i = 0; i < 80; i++) {
      const pseudoRandom = (n: number) => {
        const x = Math.sin(seed + n) * 10000;
        return x - Math.floor(x);
      };
      result.push({
        x: pseudoRandom(i * 3) * 1920,
        y: pseudoRandom(i * 3 + 1) * 1080,
        size: 2 + pseudoRandom(i * 3 + 2) * 4,
        speedX: (pseudoRandom(i * 7) - 0.5) * 2,
        speedY: (pseudoRandom(i * 7 + 1) - 0.5) * 2,
        opacity: 0.3 + pseudoRandom(i * 11) * 0.7,
      });
    }
    return result;
  }, []);

  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#050510',
        opacity,
      }}
    >
      {particles.map((p, i) => {
        const x = (p.x + p.speedX * frame) % 1920;
        const y = (p.y + p.speedY * frame) % 1080;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: p.size,
              height: p.size,
              borderRadius: '50%',
              backgroundColor: '#00ff88',
              opacity: p.opacity,
              boxShadow: `0 0 ${p.size * 2}px #00ff88`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
