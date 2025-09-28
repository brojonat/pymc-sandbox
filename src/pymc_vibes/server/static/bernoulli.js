// Import necessary libraries from a CDN
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

import { apiClient } from "/static/client.js";

const posteriorContainer = document.getElementById("chart-container");
const trialsContainer = document.getElementById("trials-container");

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
  // The data object now contains `stats` and `curve` properties.
  const { stats, curve } = data;
  const statsData = stats.data[0];
  const mean = statsData[stats.columns.indexOf("mean")];
  const median = statsData[stats.columns.indexOf("median")];
  const hdi_lower = statsData[stats.columns.indexOf("hdi_3%")];
  const hdi_upper = statsData[stats.columns.indexOf("hdi_97%")];

  // 1. Clear container and setup dimensions
  container.innerHTML = "";
  const margin = { top: 60, right: 30, bottom: 50, left: 50 };
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

  // 3. Define scales using the pre-computed curve data
  const xScale = d3.scaleLinear().domain(d3.extent(curve.x)).range([0, width]);
  const yScale = d3
    .scaleLinear()
    .domain([0, d3.max(curve.y) * 1.1])
    .range([height, 0]);

  const area = d3
    .area()
    .x((d, i) => xScale(curve.x[i]))
    .y0(height)
    .y1((d) => yScale(d))
    .curve(d3.curveBasis);

  svg
    .append("path")
    .datum(curve.y)
    .attr("fill", "#69b3a2")
    .attr("fill-opacity", 0.4)
    .attr("stroke", "#000")
    .attr("stroke-width", 1.5)
    .attr("d", area);

  // 5. Draw X axis and label
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

  // 6. Draw Title and Subtitle with Summary Stats
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Posterior Distribution for Bernoulli 'p'");

  const statsText =
    `Mean: ${mean.toFixed(3)} | ` +
    `Median: ${median.toFixed(3)} | ` +
    `94% HDI: [${hdi_lower.toFixed(3)}, ${hdi_upper.toFixed(3)}]`;

  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 20 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "12px")
    .text(statsText);
}

async function loadAndRenderPosterior(experimentName) {
  posteriorContainer.innerHTML = "<p>Fitting model...</p>";
  try {
    const posteriorData = await apiClient.getPosterior(
      "bernoulli",
      experimentName
    );
    renderPosterior(posteriorContainer, posteriorData);
  } catch (e) {
    console.error(e);
    posteriorContainer.innerText = `Error loading posterior: ${e.message}`;
  }
}

async function main() {
  const experimentName = posteriorContainer.dataset.experimentName;
  if (!experimentName) {
    trialsContainer.innerText = "Could not find experiment name.";
    return;
  }

  try {
    const data = await apiClient.getExperimentData(experimentName, {
      limit: 10000,
    });
    const trials = data.rows.map((d) => d.outcome);
    renderTrials(trialsContainer, trials);
    loadAndRenderPosterior(experimentName);
  } catch (e) {
    console.error(e);
    trialsContainer.innerText = `Error loading data: ${e.message}`;
  }
}

main();
