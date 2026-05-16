import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  Sequence,
} from 'remotion';
import { AnimatedText } from './AnimatedText';
import { DataCounter } from './DataCounter';
import { NeonText } from './NeonText';
import { ParticleBackground } from './ParticleBackground';

interface Stat {
  label: string;
  value: number;
}

interface Props {
  title: string;
  subtitle: string;
  stats: Stat[];
}

export const FinalComposition: React.FC<Props> = ({ title, subtitle, stats }) => {
  const frame = useCurrentFrame();

  const bgOpacity = interpolate(frame, [0, 60], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill>
      {/* Background particles */}
      <div style={{ opacity: bgOpacity }}>
        <ParticleBackground />
      </div>

      {/* Title sequence */}
      <Sequence from={0} durationInFrames={150}>
        <AbsoluteFill
          style={{
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          <AnimatedText text={title} subtitle={subtitle} />
        </AbsoluteFill>
      </Sequence>

      {/* Stats sequence */}
      {stats.map((stat, index) => (
        <Sequence
          key={stat.label}
          from={120 + index * 120}
          durationInFrames={150}
        >
          <AbsoluteFill
            style={{
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            <DataCounter value={stat.value} label={stat.label} />
          </AbsoluteFill>
        </Sequence>
      ))}

      {/* Outro */}
      <Sequence from={480} durationInFrames={120}>
        <AbsoluteFill
          style={{
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          <NeonText text="POWERED BY AI" />
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
