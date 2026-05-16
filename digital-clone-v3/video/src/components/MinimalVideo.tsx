import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

export const MinimalVideo: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const scale = interpolate(frame, [0, 60], [0.8, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0a0a0a',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          fontFamily: 'Arial, sans-serif',
          fontSize: 72,
          fontWeight: 'bold',
          color: '#00ff88',
          textShadow: '0 0 40px #00ff88',
        }}
      >
        DIGITAL CLONE V3
      </div>
    </AbsoluteFill>
  );
};
