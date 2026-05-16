import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import path from 'path';

async function render(id: string, outputPath: string) {
  const bundled = await bundle(path.join(__dirname, 'index.tsx'));
  const composition = await selectComposition({
    serveUrl: bundled,
    id,
  });
  await renderMedia({
    composition,
    serveUrl: bundled,
    codec: 'h264',
    outputLocation: outputPath,
  });
  console.log(`Rendered ${id} to ${outputPath}`);
}

const compositionId = process.argv[2] || 'FinalComposition';
const outputFile = process.argv[3] || './out/video.mp4';

render(compositionId, outputFile).catch((err) => {
  console.error('Render failed:', err);
  process.exit(1);
});
