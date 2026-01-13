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
    // Telemetry rate back to Python (Streamlit component value). 0 disables telemetry.
    // NOTE: this is a *rate* in Hz, not "every N frames".
    teleThrottle: 0,
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

  // optional telemetry hook (call sparingly): function(data) -> posts value to Streamlit
  let postTelemetry = null;
  let stepCount = 0;
  let lastTelemetryMs = 0;
  let telemetryHz = 0;
  let simStartMs = 0;

  function setParams(next) {
    params = { ...params, ...next };
    telemetryHz = Number(params.teleThrottle) || 0;
  }

  // --TELEMETRY FUNCTIONS: ATTEMPTING TO DEAL WITH COMPRESSING HIGH VOLUME DATA INTO A PAYLOAD FOR STREAMLIT --//
  function clamp01(x) {
    return Math.max(0, Math.min(1, x));
  }

  // Pack x/y positions into a compact base64 payload:
  // - Interleaved [x0,y0,x1,y1,...] as uint16 quantized into [0..65535]
  // - JSON carries: { format: "u16xy", data: "<base64>" }
  function positionsToBase64U16XY() {
    const n = boids.length;
    const arr = new Uint16Array(n * 2);
    const denomX = Math.max(1, width);
    const denomY = Math.max(1, height);
    for (let i = 0; i < n; i += 1) {
      const b = boids[i];
      const xq = Math.round(clamp01(b.x / denomX) * 65535);
      const yq = Math.round(clamp01(b.y / denomY) * 65535);
      arr[i * 2] = xq;
      arr[i * 2 + 1] = yq;
    }
    const bytes = new Uint8Array(arr.buffer);

    // Convert to base64 in chunks to avoid call-stack / argument limits.
    let binary = "";
    const CHUNK = 0x8000;
    for (let i = 0; i < bytes.length; i += CHUNK) {
      const sub = bytes.subarray(i, i + CHUNK);
      binary += String.fromCharCode(...sub);
    }
    return btoa(binary);
  }

  function calculateMeanVelocity() {
    const n = boids.length;
    let sumDX = 0;
    let sumDY = 0;
    for (let i = 0; i < n; i += 1) {
      const b = boids[i];
      sumDX += b.dx;
      sumDY += b.dy;
    }

    // return as an absolute velocity and a vector
    const velocity = Math.sqrt(sumDX * sumDX + sumDY * sumDY);
    const vector = {  // normalized vector
      dx: sumDX / n,
      dy: sumDY / n,
    };
    return { velocity, vector };
  }

  function calculatePolarization() {
    // from Tunstrøm et al. 2013:
    // First, the polarization order parameter Op, which provides a measure of how aligned the individuals in a group are. It is defined as the absolute value of the mean individual heading,
    // O_sub_p = 1/N * abs(sum(u_i) where u_i is the unit direction of the individual's heading)
    // note: not a vector! just a scalar

    let sumU_x = 0;
    let sumU_y = 0;
    for (let boid of boids) {
      const speed = Math.sqrt(boid.dx * boid.dx + boid.dy * boid.dy);
      if (speed > 0) {
        const unitDirection = {
          dx: boid.dx / speed,
          dy: boid.dy / speed,
        };
        sumU_x += unitDirection.dx;
        sumU_y += unitDirection.dy;
      } else {
        // if the boid is not moving, we add nothing
        continue;
      }
    }

    const n = boids.length;
    const O_p = Math.sqrt(sumU_x * sumU_x + sumU_y * sumU_y) / n;
    return O_p;
  }

  function calculateCenterOfMass() {
    let centerX = 0;
    let centerY = 0;
    for (let boid of boids) {
      centerX += boid.x;
      centerY += boid.y;
    }
    const n = boids.length;
    centerX /= n;
    centerY /= n;
    return { centerX, centerY };
  }

  function calculateRotationOrder() {
    // from Tunstrøm et al. 2013:
    // The rotation order parameter Or is then defined by the mean (normalized) angular momentum
    // which, by construction also takes values between 0 (no rotation) and 1 (strong rotation).
    // (angular momentum)
    // Or = 1/N * abs(sum(u_i x r_i)
    // this one is a little questionable, since we don't always have shoals, but let's try

    const {centerX, centerY} = calculateCenterOfMass();
    const n = boids.length;
    let O_r = 0;
    let sum_u_r = 0;
    for (let boid of boids) { 
      const speed = Math.sqrt(boid.dx * boid.dx + boid.dy * boid.dy);
        if (speed > 0) {
          const unitDirection = {
            dx: boid.dx / speed,
            dy: boid.dy / speed,
          };
          this_u_x = unitDirection.dx;
          this_u_y = unitDirection.dy;
          this_r_x = boid.x - centerX;
          this_r_y = boid.y - centerY;
          //normalize r
          const r_len = Math.sqrt(this_r_x * this_r_x + this_r_y * this_r_y);
          if (r_len > 0) {
            this_r_x /= r_len;
            this_r_y /= r_len;
            this_u_x_r_x = this_u_x * this_r_x;
            this_u_y_r_y = this_u_y * this_r_y;
            this_u_r = this_u_x * this_r_x - this_r_y * this_u_y;
            sum_u_r += this_u_r; 
          } else { // r_len is 0, so we add nothing
            continue;
          }
        } else {
          // if the boid is not moving, we add nothing
          continue;
        }
      }
    O_r = Math.abs(sum_u_r) / n;
    return O_r;

  }


  function emitTelemetry({ includePositions }) {
    if (!postTelemetry) return;
    const nowMs = (typeof performance !== "undefined" && performance.now)
      ? performance.now()
      : Date.now();
    const tMs = Math.floor(nowMs - simStartMs);

    // calculate mean velocity
    const velocityVector = calculateMeanVelocity();
    const polarization = calculatePolarization();
    const rotationOrder = calculateRotationOrder();

    // Always send a minimal, JSON-friendly payload.
    const payload = {
      tMs,
      stepCount,
      n: boids.length,
      w: width,
      h: height,
      format: includePositions ? "u16xy" : "meta",
      params: {
        attractiveFactor: params.attractiveFactor,
        alignmentFactor: params.alignmentFactor,
        avoidFactor: params.avoidFactor,
        visualRange: params.visualRange,
        numBoids: params.numBoids,
        speedLimit: params.speedLimit,
        minDistance: params.minDistance,
        margin: params.margin,
        turnFactor: params.turnFactor,
        teleThrottle: params.teleThrottle,
      },
      velocity: velocityVector.velocity,
      vector: velocityVector.vector,
      polarization: polarization,
      rotationOrder: rotationOrder
    };

    if (includePositions) payload.data = positionsToBase64U16XY();

    postTelemetry(payload);
    return nowMs;
  }

  function maybeEmitTelemetry() {
    // Works with the incoming teleThrottle rate parameter to control how often we send telemetry back to the Python shell
    if (!postTelemetry) return;
    if (telemetryHz <= 0) return;

    const periodMs = 1000 / telemetryHz;
    const nowMs = (typeof performance !== "undefined" && performance.now)
      ? performance.now()
      : Date.now();
    if (nowMs - lastTelemetryMs < periodMs) return;

    // Keep payload lean: no JS boid objects, no trail history.
    const sentAtMs = emitTelemetry({ includePositions: true });
    if (typeof sentAtMs === "number") lastTelemetryMs = sentAtMs;
  }

  // -- END TELEMETRY FUNCTIONS --//

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
    ctx.setTransform(1, 0, 0, 1, 0, 0); // TODO verify

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
    stepCount += 1;
    // Fast-path: when telemetry is disabled (Hz <= 0), bypass all telemetry logic.
    if (telemetryHz > 0 && postTelemetry) maybeEmitTelemetry();
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
    // reset telemetry
    stepCount = 0;
    lastTelemetryMs = 0;
    simStartMs = (typeof performance !== "undefined" && performance.now)
      ? performance.now()
      : Date.now();
    boids = [];
    // reset state using current params
    resize();
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

  function init({ canvasId, sendTelemetry: sendFn }) {
    canvas = document.getElementById(canvasId);
    ctx = canvas.getContext("2d");
    postTelemetry = typeof sendFn === "function" ? sendFn : null;

    resize();
    initBoids();
    draw(); // show initial state without running
    stepCount = 0;
    lastTelemetryMs = 0;
    telemetryHz = Number(params.teleThrottle) || 0;
    simStartMs = (typeof performance !== "undefined" && performance.now)
      ? performance.now()
      : Date.now();

    // One-shot "hello" telemetry so the Streamlit UI isn't empty even when throttled off.
    // Metadata-only to keep it cheap (no base64 positions).
    const sentAtMs = emitTelemetry({ includePositions: false });
    if (typeof sentAtMs === "number") lastTelemetryMs = sentAtMs;
  }

  window.BOIDS = { init, setParams, start, stop, reload, resize };
})();