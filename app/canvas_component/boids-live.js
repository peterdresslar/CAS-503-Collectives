// boids-live.js

(() => {
  // --- mutable params (defaults) ---
  let params = {
    attractiveFactor: 0.005,
    alignmentFactor: 0.05,
    avoidFactor: 0.05,
    visualRange: 75,
    numBoids: 100,
    drawTrail: false,
    minDistance: 20,
    speedLimit: 15,
    margin: 200,
    turnFactor: 1,
  };

  // --- sim state ---
  let canvas = null;
  let ctx = null;
  let width = 150;
  let height = 150;
  let boids = [];
  let running = false;
  let rafId = null;

  // optional telemetry hook (call sparingly)
  let sendTelemetry = null;

  function setParams(next) {
    params = { ...params, ...next };
  }

  function sizeCanvasToElement() {
    // Use element size instead of window.innerWidth/Height
    // (better inside Streamlit iframe)
    width = canvas.width;
    height = canvas.height;
  }

  function initBoids() {
    boids = [];
    for (let i = 0; i < params.numBoids; i += 1) {
      boids.push({
        x: Math.random() * width,
        y: Math.random() * height,
        dx: Math.random() * 10 - 5,
        dy: Math.random() * 10 - 5,
        history: [],
      });
    }
  }

  function distance(b1, b2) {
    return Math.sqrt((b1.x - b2.x) ** 2 + (b1.y - b2.y) ** 2);
  }

  function keepWithinBounds(boid) {
    const { margin, turnFactor } = params;
    if (boid.x < margin) boid.dx += turnFactor;
    if (boid.x > width - margin) boid.dx -= turnFactor;
    if (boid.y < margin) boid.dy += turnFactor;
    if (boid.y > height - margin) boid.dy -= turnFactor;
  }

  function flyTowardsCenter(boid) {
    let centerX = 0, centerY = 0, numNeighbors = 0;
    for (let other of boids) {
      if (distance(boid, other) < params.visualRange) {
        centerX += other.x; centerY += other.y; numNeighbors += 1;
      }
    }
    if (numNeighbors) {
      centerX /= numNeighbors; centerY /= numNeighbors;
      boid.dx += (centerX - boid.x) * params.attractiveFactor;
      boid.dy += (centerY - boid.y) * params.attractiveFactor;
    }
  }

  function avoidOthers(boid) {
    let moveX = 0, moveY = 0;
    for (let other of boids) {
      if (other !== boid && distance(boid, other) < params.minDistance) {
        moveX += boid.x - other.x;
        moveY += boid.y - other.y;
      }
    }
    boid.dx += moveX * params.avoidFactor;
    boid.dy += moveY * params.avoidFactor;
  }

  function matchVelocity(boid) {
    let avgDX = 0, avgDY = 0, numNeighbors = 0;
    for (let other of boids) {
      if (distance(boid, other) < params.visualRange) {
        avgDX += other.dx; avgDY += other.dy; numNeighbors += 1;
      }
    }
    if (numNeighbors) {
      avgDX /= numNeighbors; avgDY /= numNeighbors;
      boid.dx += (avgDX - boid.dx) * params.alignmentFactor;
      boid.dy += (avgDY - boid.dy) * params.alignmentFactor;
    }
  }

  function limitSpeed(boid) {
    const speed = Math.sqrt(boid.dx * boid.dx + boid.dy * boid.dy);
    if (speed > params.speedLimit) {
      boid.dx = (boid.dx / speed) * params.speedLimit;
      boid.dy = (boid.dy / speed) * params.speedLimit;
    }
  }

  function drawBoid(boid) {
    const angle = Math.atan2(boid.dy, boid.dx);
    ctx.translate(boid.x, boid.y);
    ctx.rotate(angle);
    ctx.translate(-boid.x, -boid.y);
    ctx.fillStyle = "#558cf4";
    ctx.beginPath();
    ctx.moveTo(boid.x, boid.y);
    ctx.lineTo(boid.x - 15, boid.y + 5);
    ctx.lineTo(boid.x - 15, boid.y - 5);
    ctx.lineTo(boid.x, boid.y);
    ctx.fill();
    ctx.setTransform(1, 0, 0, 1, 0, 0);

    if (params.drawTrail && boid.history.length) {
      ctx.strokeStyle = "#558cf466";
      ctx.beginPath();
      ctx.moveTo(boid.history[0][0], boid.history[0][1]);
      for (const p of boid.history) ctx.lineTo(p[0], p[1]);
      ctx.stroke();
    }
  }

  function step() {
    for (let boid of boids) {
      flyTowardsCenter(boid);
      avoidOthers(boid);
      matchVelocity(boid);
      limitSpeed(boid);
      keepWithinBounds(boid);

      boid.x += boid.dx;
      boid.y += boid.dy;
      boid.history.push([boid.x, boid.y]);
      boid.history = boid.history.slice(-50);
    }
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);
    for (let boid of boids) drawBoid(boid);
  }

  function loop() {
    if (!running) return;
    step();
    draw();
    rafId = window.requestAnimationFrame(loop);
  }

  function start() {
    if (running) return;
    running = true;
    rafId = window.requestAnimationFrame(loop);
  }

  function stop() {
    running = false;
    if (rafId != null) window.cancelAnimationFrame(rafId);
    rafId = null;
  }

  function reload() {
    // reset state using current params
    sizeCanvasToElement();
    initBoids();
  }

  function resize() {
    // Match canvas drawing buffer to its displayed size (panel size)
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
  
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
  
    // Update simulation bounds to match the buffer size
    width = canvas.width;
    height = canvas.height;
  }
  
  // OPTIONAL: keep this if you like the name, but make it correct:
  function sizeCanvasToElement() {
    resize();
  }

  function init({ canvasId, sendTelemetry: sendFn }) {
    canvas = document.getElementById(canvasId);
    ctx = canvas.getContext("2d");
    sendTelemetry = sendFn || null;

    resize();
    initBoids();
    draw(); // show initial state without running
  }

  window.BOIDS = { init, setParams, start, stop, reload, resize };
})();