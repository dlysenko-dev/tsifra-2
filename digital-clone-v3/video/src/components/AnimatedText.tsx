import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

interface Props {
  text: string;
  subtitle?: string;
}

export const AnimatedText: React.FC<Props> = ({ text, subtitle }) => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20, 120, 150], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const titleY = interpolate(frame, [0, 30], [50, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const subtitleOpacity = interpolate(frame, [20, 40], [0, 1], {
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
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          fontFamily: 'Arial, sans-serif',
          fontSize: 80,
          fontWeight: 'bold',
          color: '#00ff88',
          textShadow: '0 0 40px #00ff88',
        }}
      >
        {text}
      </div>
      {subtitle && (
        <div
          style={{
            opacity: subtitleOpacity,
            marginTop: 24,
            fontFamily: 'Arial, sans-serif',
            fontSize: 36,
            color: '#888888',
          }}
        >
          {subtitle}
        </div>
      )}
    </AbsoluteFill>
  );
};
