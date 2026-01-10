// boids-headless.js
// a modification of boids.js to be used in a headless context fot the purpose of experimentation.

// it will be very difficult to completely verify the correctness of modifified code, but we will do our best to
// make minimal changes, focusing simply on adding a control plane and return, as well as excising the canvas interaction.

// this is science, so we are going to limit defaults.

let attractiveFactor;
let alignmentFactor;
let avoidFactor;
let visualRange;
let numBoids;

let width;
let height;

let stepCount;
let frames = []; // this will be a per-frame history of all boid positions and velocities
let verbose = false; // just a setting, not a param.


var boids = [];

function initBoids() {
  for (var i = 0; i < numBoids; i += 1) {
    boids[boids.length] = {
      x: Math.random() * width,
      y: Math.random() * height,
      dx: Math.random() * 10 - 5,
      dy: Math.random() * 10 - 5,
      // not using boid history in headless mode.
      //history: [],
    };
  }
}

function distance(boid1, boid2) {
  return Math.sqrt(
    (boid1.x - boid2.x) * (boid1.x - boid2.x) +
      (boid1.y - boid2.y) * (boid1.y - boid2.y),
  );
}

// note, nClosestBoids is not called in the original, nor here.
// function nClosestBoids(boid, n) {
//   ...
// }

// Called initially and whenever the window resizes to update the canvas
// size and width/height variables.

// There is no canvas in headless mode.
// function sizeCanvas() {
//   ...
// }

// Constrain a boid to within the window. If it gets too close to an edge,
// nudge it back in and reverse its direction.
function keepWithinBounds(boid) {
  const margin = 200;
  const turnFactor = 1;

  if (boid.x < margin) {
    boid.dx += turnFactor;
  }
  if (boid.x > width - margin) {
    boid.dx -= turnFactor
  }
  if (boid.y < margin) {
    boid.dy += turnFactor;
  }
  if (boid.y > height - margin) {
    boid.dy -= turnFactor;
  }
}

// Find the center of mass of the other boids and adjust velocity slightly to
// point towards the center of mass.
function flyTowardsCenter(boid) {
  //const attractiveFactor = 0.005; // adjust velocity by this %

  let centerX = 0;
  let centerY = 0;
  let numNeighbors = 0;

  for (let otherBoid of boids) {
    if (distance(boid, otherBoid) < visualRange) {
      centerX += otherBoid.x;
      centerY += otherBoid.y;
      numNeighbors += 1;
    }
  }

  if (numNeighbors) {
    centerX = centerX / numNeighbors;
    centerY = centerY / numNeighbors;

    boid.dx += (centerX - boid.x) * attractiveFactor;
    boid.dy += (centerY - boid.y) * attractiveFactor;
  }
}

// Move away from other boids that are too close to avoid colliding
function avoidOthers(boid) {
  const minDistance = 20; // The distance to stay away from other boids
  //const avoidFactor = 0.05; // Adjust velocity by this %
  let moveX = 0;
  let moveY = 0;
  for (let otherBoid of boids) {
    if (otherBoid !== boid) {
      if (distance(boid, otherBoid) < minDistance) {
        moveX += boid.x - otherBoid.x;
        moveY += boid.y - otherBoid.y;
      }
    }
  }

  boid.dx += moveX * avoidFactor;
  boid.dy += moveY * avoidFactor;
}

// Find the average velocity (speed and direction) of the other boids and
// adjust velocity slightly to match.
function matchVelocity(boid) {
  //const alignmentFactor = 0.05; // Adjust by this % of average velocity

  let avgDX = 0;
  let avgDY = 0;
  let numNeighbors = 0;

  for (let otherBoid of boids) {
    if (distance(boid, otherBoid) < visualRange) {
      avgDX += otherBoid.dx;
      avgDY += otherBoid.dy;
      numNeighbors += 1;
    }
  }

  if (numNeighbors) {
    avgDX = avgDX / numNeighbors;
    avgDY = avgDY / numNeighbors;

    boid.dx += (avgDX - boid.dx) * alignmentFactor;
    boid.dy += (avgDY - boid.dy) * alignmentFactor;
  }
}

// Speed will naturally vary in flocking behavior, but real animals can't go
// arbitrarily fast.
function limitSpeed(boid) {
  const speedLimit = 15;

  const speed = Math.sqrt(boid.dx * boid.dx + boid.dy * boid.dy);
  if (speed > speedLimit) {
    boid.dx = (boid.dx / speed) * speedLimit;
    boid.dy = (boid.dy / speed) * speedLimit;
  }
}

// No drawing in headless mode.
// function drawBoid(ctx, boid) {
//   ...
// }

// Main animation loop with no drawing
function animationLoop() {
  // Update each boid
  for (let boid of boids) {
    // Update the velocities according to each rule
    flyTowardsCenter(boid);
    avoidOthers(boid);
    matchVelocity(boid);
    limitSpeed(boid);
    keepWithinBounds(boid);

    // Update the position based on the current velocity
    boid.x += boid.dx;
    boid.y += boid.dy;
    // we are not using boid history in headless mode.
    // boid.history.push([boid.x, boid.y])
    // boid.history = boid.history.slice(-50);  
  }

}

function run(simConfig) {
  attractiveFactor = simConfig.attractiveFactor;
  alignmentFactor = simConfig.alignmentFactor;
  avoidFactor = simConfig.avoidFactor;
  visualRange = simConfig.visualRange;
  numBoids = simConfig.numBoids;
  drawTrail = simConfig.drawTrail;
  width = simConfig.width;
  height = simConfig.height;
  const steps = simConfig.steps;
  verbose = simConfig.verbose;
  if (verbose) {
    console.log(`Running simulation with config:`, simConfig);
  }

  stepCount = 0;

  boids = [];
  initBoids();

  for (let i = 0; i < steps; i++) {
    stepCount += 1;
    if (verbose && stepCount % 100 === 0) {
      console.log(`Step ${stepCount} of ${steps}`);
    }
    animationLoop();
    frames.push(boids.map(b => [b.x, b.y, b.dx, b.dy]));

    // frame_i = [
    //   [x, y, dx, dy],   // boid 0
    //   [x, y, dx, dy],   // boid 1
    //   ...
    //   [x, y, dx, dy]    // boid (numBoids-1)
    // ]

  }

  return {
    // just the frames.. we also send back
    // the last step count, though this could be pulled from history.
    stepCount,
    frames // see above
  }

}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { run };
}
