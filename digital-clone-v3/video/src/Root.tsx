import React from 'react';
import { Composition } from 'remotion';
import { MinimalVideo } from './components/MinimalVideo';
import { AnimatedText } from './components/AnimatedText';
import { DataCounter } from './components/DataCounter';
import { NeonText } from './components/NeonText';
import { ParticleBackground } from './components/ParticleBackground';
import { FinalComposition } from './components/FinalComposition';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MinimalVideo"
        component={MinimalVideo}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="AnimatedText"
        component={AnimatedText}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ text: 'Digital Clone V3', subtitle: 'AI-Powered Automation' }}
      />
      <Composition
        id="DataCounter"
        component={DataCounter}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ value: 12847, label: 'Tasks Completed' }}
      />
      <Composition
        id="NeonText"
        component={NeonText}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ text: 'NEON FUTURE' }}
      />
      <Composition
        id="ParticleBackground"
        component={ParticleBackground}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="FinalComposition"
        component={FinalComposition}
        durationInFrames={600}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          title: 'Digital Clone V3',
          subtitle: 'Autonomous AI Agent',
          stats: [
            { label: 'Tasks', value: 12847 },
            { label: 'Sources', value: 42 },
            { label: 'Uptime', value: 99.9 },
          ],
        }}
      />
    </>
  );
};
