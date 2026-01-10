node -e "
const {run} = require('./boids-headless.js');
const result = run({
  attractiveFactor: 0.005,
  alignmentFactor: 0.05,
  avoidFactor: 0.05,
  visualRange: 75,
  numBoids: 10,
  width: 500,
  height: 500,
  steps: 100,
  verbose: true
});
console.log('stepCount:', result.stepCount);
console.log('frames:', result.frames.length);
console.log('boids per frame:', result.frames[0].length);
console.log('values per boid:', result.frames[0][0].length);
console.log('sample frame 0, boid 0:', result.frames[0][0]);
console.log('sample frame 99, boid 0:', result.frames[99][0]);
"