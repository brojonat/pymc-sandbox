// Import necessary libraries from a CDN
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const posteriorContainer = document.getElementById("chart-container");
const trialsContainer = document.getElementById("trials-container");
const useDummyData = true;

// --- KDE Helper Functions ---
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

/**
 * Generates dummy posterior data for multiple arms in a bandit problem.
 */
function generateDummyData() {
  const arms = [
    { name: "Arm 1", trueP: 0.3, numTrials: 150 },
    { name: "Arm 2", trueP: 0.38, numTrials: 250 },
    { name: "Arm 3 (Best)", trueP: 0.45, numTrials: 400 },
    { name: "Arm 4", trueP: 0.2, numTrials: 80 },
  ];
  const posteriors = {};
  const trials = {};

  arms.forEach((arm) => {
    // 1. Generate raw trial data
    const armTrials = [];
    for (let i = 0; i < arm.numTrials; i++) {
      armTrials.push(Math.random() < arm.trueP ? 1 : 0);
    }
    trials[arm.name] = armTrials;

    // 2. Generate a plausible posterior from the raw data
    const successes = d3.sum(armTrials);
    const failures = arm.numTrials - successes;
    const posteriorMean = (successes + 1) / (arm.numTrials + 2);
    const posteriorStdDev = Math.sqrt(
      ((successes + 1) * (failures + 1)) /
        ((arm.numTrials + 2) ** 2 * (arm.numTrials + 3))
    );

    const numSamples = 500;
    const rates = [];
    for (let k = 0; k < numSamples / 2; k++) {
      const u1 = Math.random();
      const u2 = Math.random();
      const z1 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
      const z2 = Math.sqrt(-2.0 * Math.log(u1)) * Math.sin(2.0 * Math.PI * u2);
      rates.push(z1 * posteriorStdDev + posteriorMean);
      rates.push(z2 * posteriorStdDev + posteriorMean);
    }
    posteriors[arm.name] = rates.filter((r) => r > 0 && r < 1);
  });

  return { trials, posteriors };
}

function renderSingleTrialStrip(container, armName, trials) {
  // 1. Setup dimensions
  const margin = { top: 30, right: 30, bottom: 40, left: 30 };
  const width = container.clientWidth - margin.left - margin.right;
  const height = 100 - margin.top - margin.bottom;

  // 2. Create SVG
  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // 3. Define scales and data
  const xScale = d3.scaleLinear().domain([0, trials.length]).range([0, width]);
  const color = d3.scaleOrdinal().domain([0, 1]).range(["#E67E22", "#2ECC71"]);

  // 4. Draw trial ticks
  svg
    .selectAll("rect")
    .data(trials)
    .enter()
    .append("rect")
    .attr("x", (d, i) => xScale(i))
    .attr("y", height * 0.25)
    .attr("width", Math.max(1, width / trials.length - 1))
    .attr("height", height * 0.5)
    .attr("fill", (d) => color(d));

  // 5. Draw Title
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2 + 10)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text(`Raw Data: ${armName}`);

  // 6. Add a summary text
  const successes = d3.sum(trials);
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 15)
    .attr("text-anchor", "middle")
    .style("font-size", "12px")
    .text(`${successes} successes in ${trials.length} trials`);
}

function renderAllTrials(container, trialsData) {
  container.innerHTML = "";
  // Sort arms by the number of trials to show exploration
  const sortedTrials = Object.entries(trialsData).sort(
    (a, b) => b[1].length - a[1].length
  );
  for (const [armName, trials] of sortedTrials) {
    const armContainer = document.createElement("div");
    container.appendChild(armContainer);
    renderSingleTrialStrip(armContainer, armName, trials);
  }
}

function renderPosteriors(container, data) {
  // 1. Clear container and setup dimensions
  container.innerHTML = "";
  const margin = { top: 40, right: 30, bottom: 50, left: 50 };
  const width = container.clientWidth - margin.left - margin.right;
  const height = 400 - margin.top - margin.bottom;

  // 2. Create SVG
  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // 3. Define scales
  const allSamples = Object.values(data).flat();
  const xDomain = d3.extent(allSamples);
  const xScale = d3.scaleLinear().domain(xDomain).range([0, width]);
  const color = d3.scaleOrdinal(d3.schemeCategory10);

  // 4. Compute KDE for each arm
  const allDensities = [];
  let maxDensity = 0;

  for (const [name, samples] of Object.entries(data)) {
    const stdDev = d3.deviation(samples);
    const bandwidth = (1.06 * stdDev) / Math.pow(samples.length, 0.2);
    const kde = kernelDensityEstimator(
      kernelEpanechnikov(bandwidth),
      xScale.ticks(100)
    );
    const density = kde(samples);
    allDensities.push({ name, density });
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

  allDensities.forEach(({ name, density }) => {
    svg
      .append("path")
      .datum(density)
      .attr("fill", "none")
      .attr("stroke", color(name))
      .attr("stroke-width", 2)
      .attr("stroke-linejoin", "round")
      .attr("d", line);
  });

  // 6. Draw X axis and label
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale));
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .text("Expected Reward (p)");

  // 7. Draw Title & Legend
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Posterior Distributions for Bandit Arms");

  const legend = svg
    .selectAll(".legend")
    .data(Object.keys(data))
    .enter()
    .append("g")
    .attr("class", "legend")
    .attr("transform", (d, i) => `translate(0,${i * 20})`);

  legend
    .append("rect")
    .attr("x", width - 18)
    .attr("width", 18)
    .attr("height", 18)
    .style("fill", color);

  legend
    .append("text")
    .attr("x", width - 24)
    .attr("y", 9)
    .attr("dy", ".35em")
    .style("text-anchor", "end")
    .text((d) => d);
}

async function main() {
  if (useDummyData) {
    const data = generateDummyData();
    renderPosteriors(posteriorContainer, data.posteriors);
    renderAllTrials(trialsContainer, data.trials);
    return;
  }
  // TODO: Fetch data from the backend API
}

main();
