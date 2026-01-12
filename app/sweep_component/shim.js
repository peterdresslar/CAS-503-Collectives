(function() {
  function sendMessageToStreamlitClient(type, data) {
    var outData = Object.assign({ isStreamlitMessage: true, type: type }, data);
    window.parent.postMessage(outData, "*");
  }

  function setFrameHeight(height) {
    sendMessageToStreamlitClient("streamlit:setFrameHeight", { height: height });
  }

  function sendToStreamlit(value) {
    sendMessageToStreamlitClient("streamlit:setComponentValue", { value: value });
  }

  let hasSeenRender = false;

  function handleRender(event) {
    if (event.data.type !== "streamlit:render") return;
    hasSeenRender = true;

    const configs = event.data.args?.configs;
    if (!configs || !Array.isArray(configs)) return;

    // Run all simulations, collect results
    const results = configs.map((config, i) => {
      if (config.verbose) {
        console.log(`Running config ${i + 1} of ${configs.length}`);
      }
      return run(config);  // from boids-headless.js
    });

    sendToStreamlit(results);
  }

  window.addEventListener("message", handleRender);

  // Signal ready (invisible component)
  sendMessageToStreamlitClient("streamlit:componentReady", { apiVersion: 1 });
  setFrameHeight(0);
})();