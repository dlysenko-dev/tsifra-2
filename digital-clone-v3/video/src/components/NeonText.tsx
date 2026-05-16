import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

interface Props {
  text: string;
}

export const NeonText: React.FC<Props> = ({ text }) => {
  const frame = useCurrentFrame();

  const flicker = interpolate(
    frame,
    [0, 5, 10, 15, 20, 25, 30],
    [0, 1, 0.3, 1, 0.5, 1, 1],
    { extrapolateRight: 'clamp' }
  );

  const glow = interpolate(frame, [0, 30], [0, 20], {
    extrapolateLeft: 'clamp',
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
          opacity: flicker,
          fontFamily: 'Arial, sans-serif',
          fontSize: 96,
          fontWeight: 'bold',
          color: '#ff00ff',
          textShadow: `0 0 ${glow}px #ff00ff, 0 0 ${glow * 2}px #ff00ff`,
          letterSpacing: '0.2em',
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
