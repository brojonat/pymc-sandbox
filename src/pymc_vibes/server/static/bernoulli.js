// Import necessary libraries from a CDN
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const posteriorContainer = document.getElementById("chart-container");
const trialsContainer = document.getElementById("trials-container");
const useDummyData = true;

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

/**
 * Generates dummy posterior data for a Bernoulli trial.
 * In a real scenario, this would be samples from a Beta distribution.
 * Here, we simulate it with a clipped Normal distribution for simplicity.
 */
function generateDummyData() {
  const trueP = 0.65;
  const numTrials = 150;

  // 1. Generate raw trial data
  const trials = [];
  for (let i = 0; i < numTrials; i++) {
    trials.push(Math.random() < trueP ? 1 : 0);
  }

  // 2. Generate a plausible posterior from the raw data
  // For a Beta distribution, Posterior ~ Beta(alpha + successes, beta + failures)
  // We'll simulate this with a Normal approximation
  const successes = d3.sum(trials);
  const failures = numTrials - successes;
  const posteriorMean = (successes + 1) / (numTrials + 2); // Using Bayes estimator
  const posteriorStdDev = Math.sqrt(
    ((successes + 1) * (failures + 1)) /
      ((numTrials + 2) ** 2 * (numTrials + 3))
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

  // Filter to a plausible range [0, 1] for a probability
  const posterior = rates.filter((r) => r > 0 && r < 1);
  return { trials, posterior };
}

function renderTrials(container, trials) {
  // 1. Clear container and setup dimensions
  container.innerHTML = "";
  const margin = { top: 20, right: 30, bottom: 40, left: 30 };
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
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Raw Trial Data");

  // 6. Add a summary text
  const successes = d3.sum(trials);
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .attr("text-anchor", "middle")
    .style("font-size", "12px")
    .text(`${successes} successes in ${trials.length} trials`);
}

function renderPosterior(container, data) {
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
  const xScale = d3.scaleLinear().domain([0, 1]).range([0, width]);

  // 4. Compute KDE
  const stdDev = d3.deviation(data);
  const bandwidth = (1.06 * stdDev) / Math.pow(data.length, 0.2);
  const kde = kernelDensityEstimator(
    kernelEpanechnikov(bandwidth),
    xScale.ticks(100)
  );
  const density = kde(data);

  const yScale = d3
    .scaleLinear()
    .domain([0, d3.max(density, (d) => d[1]) * 1.1])
    .range([height, 0]);

  // 5. Draw the density line
  const line = d3
    .line()
    .x((d) => xScale(d[0]))
    .y((d) => yScale(d[1]))
    .curve(d3.curveBasis);

  svg
    .append("path")
    .datum(density)
    .attr("fill", "#69b3a2")
    .attr("fill-opacity", 0.4)
    .attr("stroke", "#000")
    .attr("stroke-width", 1.5)
    .attr("d", `M0,${height} ` + line(density) + ` L${width},${height}`);

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
    .text("Probability (p)");

  // 7. Draw Title
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Posterior Distribution for Bernoulli 'p'");
}

async function main() {
  if (useDummyData) {
    const data = generateDummyData();
    renderTrials(trialsContainer, data.trials);
    renderPosterior(posteriorContainer, data.posterior);
    return;
  }
  // TODO: Fetch data from the backend API
}

main();
