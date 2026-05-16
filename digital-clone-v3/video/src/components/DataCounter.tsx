import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

interface Props {
  value: number;
  label: string;
}

export const DataCounter: React.FC<Props> = ({ value, label }) => {
  const frame = useCurrentFrame();

  const displayValue = Math.floor(
    interpolate(frame, [0, 90], [0, value], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    })
  );

  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const scale = interpolate(frame, [60, 90], [1, 1.1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0a0a0a',
        justifyContent: 'center',
        alignItems: 'center',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          fontFamily: 'Arial, sans-serif',
          fontSize: 120,
          fontWeight: 'bold',
          color: '#00ff88',
          textShadow: '0 0 60px #00ff88',
        }}
      >
        {displayValue.toLocaleString()}
      </div>
      <div
        style={{
          opacity,
          marginTop: 24,
          fontFamily: 'Arial, sans-serif',
          fontSize: 36,
          color: '#888888',
        }}
      >
        {label}
      </div>
    </AbsoluteFill>
  );
};
