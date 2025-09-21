// Import necessary libraries from a CDN
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const API_BASE_URL = ""; // Use a relative path for same-origin requests
const container = document.getElementById("chart-container");

// --- Global State ---
const posteriorCache = {};
const color = d3.scaleOrdinal(d3.schemeCategory10);
const cohortVisibility = {};

function renderPosterior(container, posteriorData, plotHeight) {
  // 1. Clear container and setup dimensions
  container.innerHTML = "";
  const margin = { top: 20, right: 30, bottom: 30, left: 40 };
  const width = container.clientWidth - margin.left - margin.right;
  const height = plotHeight - margin.top - margin.bottom;

  // 2. Create SVG
  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // 3. Get data
  const cohortName = Object.keys(posteriorData)[0];
  const rates = posteriorData[cohortName].posterior_rate;

  // 4. Define scales
  const xScale = d3.scaleLinear().domain(d3.extent(rates)).range([0, width]);
  const bins = d3.bin().domain(xScale.domain()).thresholds(xScale.ticks(25))(
    rates
  );
  const yScale = d3
    .scaleLinear()
    .domain([0, d3.max(bins, (d) => d.length) * 1.1])
    .range([height, 0]);

  // 5. Draw histogram bars
  svg
    .selectAll("rect")
    .data(bins)
    .join("rect")
    .attr("x", (d) => xScale(d.x0) + 1)
    .attr("width", (d) => Math.max(0, xScale(d.x1) - xScale(d.x0) - 1))
    .attr("y", (d) => yScale(d.length))
    .attr("height", (d) => height - yScale(d.length))
    .style("fill", color(cohortName));

  // 6. Draw mean line
  const mean = d3.mean(rates);
  svg
    .append("line")
    .attr("x1", xScale(mean))
    .attr("x2", xScale(mean))
    .attr("y1", 0)
    .attr("y2", height)
    .attr("stroke", "red")
    .attr("stroke-width", 3);

  // 7. Draw X axis and label
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale).ticks(5).tickFormat(d3.format(".3r")))
    .attr("font-size", "10px");
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom)
    .attr("font-size", "12px")
    .text("λ [events/day]");

  // 8. Draw Title
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text("Posterior distribution");
}

// --- KDE Helper Functions ---
// (Based on https://d3-graph-gallery.com/graph/density_basic.html)
function kernelDensityEstimator(kernel, X) {
  return function (V) {
    return X.map(function (x) {
      return [
        x,
        d3.mean(V, function (v) {
          return kernel(x - v);
        }),
      ];
    });
  };
}

function kernelEpanechnikov(k) {
  return function (v) {
    return Math.abs((v /= k)) <= 1 ? (0.75 * (1 - v * v)) / k : 0;
  };
}

function renderGlobalPosterior(container, posteriorCache, visibility) {
  // 1. Clear container and setup dimensions
  container.innerHTML = "";
  const margin = { top: 40, right: 30, bottom: 30, left: 40 };
  const width = container.clientWidth - margin.left - margin.right;
  const height = 300 - margin.top - margin.bottom; // A fixed larger height

  // 2. Create SVG
  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // 3. Filter visible cohorts, get all their rates, and define global scales
  const visibleCohorts = Object.entries(posteriorCache).filter(
    ([cohortName]) => visibility[cohortName]
  );

  let allRates = [];
  for (const [, posteriorData] of visibleCohorts) {
    const name = Object.keys(posteriorData)[0];
    allRates.push(...posteriorData[name].posterior_rate);
  }
  if (allRates.length === 0) return;

  const xDomain = d3.extent(allRates);
  const xScale = d3.scaleLinear().domain(xDomain).range([0, width]);

  // 4. Compute KDE for each cohort to get smooth density curves
  const allDensities = [];
  let maxDensity = 0;

  for (const [cohortName, posteriorData] of visibleCohorts) {
    const cohortKey = Object.keys(posteriorData)[0];
    const rates = posteriorData[cohortKey].posterior_rate;

    // Use Silverman's rule of thumb for bandwidth selection
    const stdDev = d3.deviation(rates);
    // Add a small epsilon to stdDev to prevent bandwidth from being zero in low-variance cases
    const bandwidth = (1.06 * (stdDev || 1e-9)) / Math.pow(rates.length, 0.2);

    const kde = kernelDensityEstimator(
      kernelEpanechnikov(bandwidth),
      xScale.ticks(100) // Evaluate density at 100 points for a smooth curve
    );
    const density = kde(rates);
    allDensities.push({ cohortName, density });

    const currentMax = d3.max(density, (d) => d[1]);
    if (currentMax > maxDensity) {
      maxDensity = currentMax;
    }
  }

  const yScale = d3
    .scaleLinear()
    .domain([0, maxDensity * 1.1])
    .range([height, 0]);

  // 5. Draw the density lines
  const line = d3
    .line()
    .x((d) => xScale(d[0]))
    .y((d) => yScale(d[1]))
    .curve(d3.curveBasis);

  allDensities.forEach(({ cohortName, density }) => {
    svg
      .append("path")
      .datum(density)
      .attr("fill", "none")
      .attr("stroke", color(cohortName))
      .attr("stroke-width", 2.5)
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("d", line);
  });

  // 6. Draw X axis and label
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale))
    .attr("font-size", "10px");
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom)
    .attr("font-size", "12px")
    .text("λ [events/day]");

  // 7. Draw Title
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Global Posterior Distributions");
}

function renderToggle(container, cohortName) {
  container.innerHTML = ""; // Clear previous content

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `toggle-${cohortName}`;
  checkbox.checked = cohortVisibility[cohortName];

  checkbox.addEventListener("change", () => {
    cohortVisibility[cohortName] = checkbox.checked;
    const globalContainer = document.getElementById(
      "global-posterior-container"
    );
    renderGlobalPosterior(globalContainer, posteriorCache, cohortVisibility);
  });

  const label = document.createElement("label");
  label.htmlFor = `toggle-${cohortName}`;
  label.textContent = " Global";
  label.style.marginLeft = "4px";
  label.style.cursor = "pointer";
  label.style.fontSize = "12px";

  container.appendChild(checkbox);
  container.appendChild(label);
}

async function updateCohortActionPanel(cohortName, minTime, maxTime) {
  const actionContainer = document.getElementById(
    `action-container-${cohortName}`
  );
  const toggleContainer = document.getElementById(
    `toggle-container-${cohortName}`
  );
  const plotHeight = 75;

  if (posteriorCache[cohortName]) {
    // Data exists: render posterior and toggle
    renderPosterior(actionContainer, posteriorCache[cohortName], plotHeight);
    renderToggle(toggleContainer, cohortName);
  } else {
    // No data: render fit button
    actionContainer.innerHTML = "Fitting model...";
    toggleContainer.innerHTML = ""; // Clear toggle

    try {
      const experimentName = container.dataset.experimentName;
      const response = await fetch(
        `${API_BASE_URL}/poisson-cohorts/posterior?experiment_name=${experimentName}&start=${minTime.toISOString()}&end=${maxTime.toISOString()}&cohort=${cohortName}`
      );
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);

      const responseData = await response.json();
      posteriorCache[cohortName] = responseData.results;

      // Update this specific cohort's panel
      renderPosterior(actionContainer, posteriorCache[cohortName], plotHeight);
      renderToggle(toggleContainer, cohortName);

      // Redraw global plot
      const globalContainer = document.getElementById(
        "global-posterior-container"
      );
      renderGlobalPosterior(globalContainer, posteriorCache, cohortVisibility);
    } catch (error) {
      console.error("Failed to fetch or render posterior data:", error);
      actionContainer.innerText = "Failed to load posterior data.";
    }
  }
}

function renderTimeline(container, cohortData, plotHeight, timeDomain) {
  // 1. Clear container and setup dimensions
  container.innerHTML = "";
  const margin = { top: 20, right: 30, bottom: 30, left: 40 };
  const width = container.clientWidth - margin.left - margin.right;
  const height = plotHeight - margin.top - margin.bottom;

  // 2. Create SVG
  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // 3. Define scales
  const xScale = d3.scaleUtc().domain(timeDomain).range([0, width]);

  // 4. Draw event ticks
  svg
    .selectAll("line")
    .data(cohortData)
    .join("line")
    .attr("x1", (d) => xScale(d.ts))
    .attr("x2", (d) => xScale(d.ts))
    .attr("y1", height * 0.25)
    .attr("y2", height * 0.75)
    .attr("stroke", "black")
    .attr("stroke-width", 1);

  // 5. Draw X axis and label
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale).tickFormat(d3.timeFormat("%b")))
    .attr("font-size", "10px");
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom)
    .attr("font-size", "12px")
    .text("Timestamp");

  // 6. Draw Title
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text(cohortData[0].cohort);
}

function updateAndRedrawAll() {
  // 1. Recalculate global x-domain from the entire cache
  if (Object.keys(posteriorCache).length === 0) return; // Nothing to draw

  // Render the global plot at the top
  const globalContainer = document.getElementById("global-posterior-container");
  renderGlobalPosterior(globalContainer, posteriorCache, cohortVisibility);

  // 2. Rerender all cached plots with the new domains
  for (const [name, posteriorData] of Object.entries(posteriorCache)) {
    const target = document.getElementById(`action-container-${name}`);
    const plotHeight = 75; // This should be consistent
    renderPosterior(target, posteriorData, plotHeight);
  }
}

async function renderCohorts(container, data) {
  // 1. Pre-process data
  const processedData = data.map((d) => ({ ...d, ts: d3.isoParse(d.ts) }));
  const cohorts = d3.group(processedData, (d) => d.cohort);

  // Initialize visibility state for all cohorts
  for (const cohortName of cohorts.keys()) {
    if (cohortVisibility[cohortName] === undefined) {
      cohortVisibility[cohortName] = true;
    }
  }

  const sortedCohorts = new Map(
    [...cohorts.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  );
  const [minTime, maxTime] = d3.extent(processedData, (d) => d.ts);
  const plotHeight = 75;

  // 2. Build the DOM structure first (Pass 1)
  container.innerHTML = ""; // Clear previous content
  for (const [cohortName] of sortedCohorts) {
    const cohortWrapper = document.createElement("div");
    cohortWrapper.style.display = "flex";
    cohortWrapper.style.alignItems = "center";
    cohortWrapper.style.marginBottom = "20px";

    const timelineContainer = document.createElement("div");
    timelineContainer.id = `timeline-container-${cohortName}`;
    timelineContainer.style.width = "600px";
    cohortWrapper.appendChild(timelineContainer);

    const actionWrapper = document.createElement("div");
    actionWrapper.style.display = "flex";
    actionWrapper.style.alignItems = "center";
    actionWrapper.style.marginLeft = "20px";

    const actionContainer = document.createElement("div");
    actionContainer.id = `action-container-${cohortName}`;
    actionContainer.style.width = "600px";

    const toggleContainer = document.createElement("div");
    toggleContainer.id = `toggle-container-${cohortName}`;
    toggleContainer.style.marginLeft = "10px";

    actionWrapper.appendChild(actionContainer);
    actionWrapper.appendChild(toggleContainer);
    cohortWrapper.appendChild(actionWrapper);

    container.appendChild(cohortWrapper);
  }

  // 4. Now render content into the existing DOM structure (Pass 2)
  for (const [cohortName, cohortData] of sortedCohorts) {
    const timelineContainer = document.getElementById(
      `timeline-container-${cohortName}`
    );
    renderTimeline(timelineContainer, cohortData, plotHeight, [
      minTime,
      maxTime,
    ]);
    updateCohortActionPanel(cohortName, minTime, maxTime);
  }

  // Initial render of the global plot
  const globalContainer = document.getElementById("global-posterior-container");
  renderGlobalPosterior(globalContainer, posteriorCache, cohortVisibility);
}

const useDummyData = true;

/**
 * Generates dummy data for frontend development and testing.
 * To disable, set `useDummyData` to `false`.
 */
function generateDummyData(dataGenParams) {
  const rows = [];
  const posteriors = {};
  const endDate = new Date();
  const startDate = new Date();
  startDate.setFullYear(endDate.getFullYear() - 1);

  dataGenParams.forEach((params) => {
    const { cohortName, mean, stdDev, numSamples, numEvents } = params;

    // 1. Generate event timeline data
    for (let j = 0; j < numEvents; j++) {
      const ts = new Date(
        startDate.getTime() +
          Math.random() * (endDate.getTime() - startDate.getTime())
      );
      rows.push({ cohort: cohortName, ts: ts.toISOString() });
    }

    // 2. Generate posterior distribution data
    const rates = [];

    // Use Box-Muller transform for a normal distribution
    for (let k = 0; k < numSamples / 2; k++) {
      const u1 = Math.random();
      const u2 = Math.random();
      const z1 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
      const z2 = Math.sqrt(-2.0 * Math.log(u1)) * Math.sin(2.0 * Math.PI * u2);
      rates.push(z1 * stdDev + mean);
      rates.push(z2 * stdDev + mean);
    }

    // Structure the data as the API would
    posteriors[cohortName] = {
      [cohortName]: {
        // Filter out negative rates, as they are not physically meaningful
        posterior_rate: rates.filter((r) => r > 0),
      },
    };
  });

  return { rows, posteriors };
}

async function main() {
  if (useDummyData) {
    console.log("Using dummy data. To disable, set useDummyData to false.");
    const dataGenParams = [
      {
        cohortName: "alpha",
        mean: 0.1,
        stdDev: 0.001,
        numSamples: 500,
        numEvents: 75,
      },
      {
        cohortName: "beta",
        mean: 0.2,
        stdDev: 0.03,
        numSamples: 500,
        numEvents: 120,
      },
      {
        cohortName: "gamma",
        mean: 0.15,
        stdDev: 0.025,
        numSamples: 500,
        numEvents: 90,
      },
      {
        cohortName: "delta",
        mean: 0.3,
        stdDev: 0.05,
        numSamples: 500,
        numEvents: 150,
      },
    ];
    const dummyData = generateDummyData(dataGenParams);
    // Pre-populate the cache with dummy posterior data
    Object.assign(posteriorCache, dummyData.posteriors);
    // Render the cohorts with dummy event data
    renderCohorts(container, dummyData.rows);
    return;
  }
  try {
    const experimentName = container.dataset.experimentName;
    const response = await fetch(
      `${API_BASE_URL}/poisson-cohorts/list?experiment_name=${experimentName}&limit=5000`
    );
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const data = await response.json();
    if (data.rows && data.rows.length > 0) {
      renderCohorts(container, data.rows);
    } else {
      container.innerText = "No data to display.";
    }
  } catch (error) {
    console.error("Failed to fetch or render data:", error);
    container.innerText = "Failed to load data.";
  }
}

// Run the main function when the script loads
main();
