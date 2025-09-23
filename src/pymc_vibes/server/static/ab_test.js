// Import necessary libraries from a CDN
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

import { apiClient } from "/static/client.js";

const posteriorContainer = document.getElementById("chart-container");
const trialsContainer = document.getElementById("trials-container");

function renderSingleTrialStrip(container, variantName, trials) {
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
    .text(`Raw Data: ${variantName}`);

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
  // Sort the variants alphabetically by name before rendering
  const sortedTrials = new Map(
    [...trialsData.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  );

  for (const [variantName, variantRows] of sortedTrials.entries()) {
    const variantContainer = document.createElement("div");
    container.appendChild(variantContainer);
    const outcomes = variantRows.map((d) => d.outcome);
    renderSingleTrialStrip(variantContainer, variantName, outcomes);
  }
}

function renderSinglePosterior(
  container,
  title,
  summaryData,
  xDomain,
  yDomain,
  chartHeight,
  color = "#69b3a2"
) {
  const { stats, curve } = summaryData;
  const statsData = stats.data[0];
  const mean = statsData[stats.columns.indexOf("mean")];
  const median = statsData[stats.columns.indexOf("median")];
  const hdi_lower = statsData[stats.columns.indexOf("hdi_3%")];
  const hdi_upper = statsData[stats.columns.indexOf("hdi_97%")];

  const margin = { top: 60, right: 30, bottom: 50, left: 50 };
  const width = container.clientWidth - margin.left - margin.right;
  const height = chartHeight - margin.top - margin.bottom;

  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  const xScale = d3.scaleLinear().domain(xDomain).range([0, width]);
  const yScale = d3.scaleLinear().domain(yDomain).range([height, 0]);

  const line = d3
    .line()
    .x((d, i) => xScale(curve.x[i]))
    .y((d) => yScale(d))
    .curve(d3.curveBasis);

  svg
    .append("path")
    .datum(curve.y)
    .attr("fill", color)
    .attr("fill-opacity", 0.4)
    .attr("stroke", "#000")
    .attr("stroke-width", 1.5)
    .attr("d", `M0,${height} ` + line(curve.y) + ` L${width},${height}`);

  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale).ticks(5));
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .text("Value");

  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text(title);

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

function renderPosteriors(container, data) {
  // data contains `variants`
  container.innerHTML = "";

  // --- 1. Calculate Global Domains & Sort Variants ---
  const variantNames = Object.keys(data.variants).sort();
  const allVariants = variantNames.map((name) => data.variants[name]);
  const allX = allVariants.flatMap((v) => v.curve.x);
  const allY = allVariants.flatMap((v) => v.curve.y);
  const globalXDomain = d3.extent(allX);
  const globalYDomain = [0, d3.max(allY) * 1.1];
  const color = d3.scaleOrdinal(d3.schemeCategory10);

  // --- 2. Create Layout Containers ---
  const mainFlexContainer = document.createElement("div");
  mainFlexContainer.style.display = "flex";
  mainFlexContainer.style.alignItems = "flex-start";
  mainFlexContainer.style.gap = "20px";

  const leftColumnContainer = document.createElement("div");
  leftColumnContainer.style.flex = "1";
  leftColumnContainer.style.display = "flex";
  leftColumnContainer.style.flexDirection = "column";
  leftColumnContainer.style.gap = "10px";

  const rightColumnContainer = document.createElement("div");
  rightColumnContainer.style.flex = "2";

  mainFlexContainer.appendChild(leftColumnContainer);
  mainFlexContainer.appendChild(rightColumnContainer);
  container.appendChild(mainFlexContainer);

  // --- 3. Render Combined Plot (Right Column) ---
  const combinedPlotHeight = 500;
  const margin = { top: 60, right: 30, bottom: 50, left: 50 };
  const combinedWidth =
    rightColumnContainer.clientWidth - margin.left - margin.right;
  const combinedHeight = combinedPlotHeight - margin.top - margin.bottom;

  const combinedSvg = d3
    .select(rightColumnContainer)
    .append("svg")
    .attr("width", combinedWidth + margin.left + margin.right)
    .attr("height", combinedPlotHeight)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  const xScale = d3
    .scaleLinear()
    .domain(globalXDomain)
    .range([0, combinedWidth]);
  const yScale = d3
    .scaleLinear()
    .domain(globalYDomain)
    .range([combinedHeight, 0]);

  const line = d3
    .line()
    .x((d, i) => xScale(d.x[i]))
    .y((d) => yScale(d.y));

  // Draw lines for each variant
  for (const name of variantNames) {
    const summary = data.variants[name];
    const lineData = summary.curve.y.map((y, i) => ({
      x: summary.curve.x,
      y: y,
    }));
    combinedSvg
      .append("path")
      .datum(lineData)
      .attr("fill", "none")
      .attr("stroke", color(name))
      .attr("stroke-width", 2.5)
      .attr("d", line);
  }

  // Add Axes and Title for combined plot
  combinedSvg
    .append("g")
    .attr("transform", `translate(0,${combinedHeight})`)
    .call(d3.axisBottom(xScale));
  combinedSvg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", combinedWidth / 2)
    .attr("y", combinedHeight + margin.bottom - 10)
    .text("Value");
  combinedSvg
    .append("text")
    .attr("x", combinedWidth / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Combined Posterior Distributions");

  // Add Legend for combined plot
  const legend = combinedSvg
    .selectAll(".legend")
    .data(variantNames)
    .enter()
    .append("g")
    .attr("class", "legend")
    .attr("transform", (d, i) => `translate(0,${i * 20})`);

  legend
    .append("rect")
    .attr("x", combinedWidth - 18)
    .attr("width", 18)
    .attr("height", 18)
    .style("fill", color);

  legend
    .append("text")
    .attr("x", combinedWidth - 24)
    .attr("y", 9)
    .attr("dy", ".35em")
    .style("text-anchor", "end")
    .text((d) => d);

  // --- 4. Render Individual Plots (Left Column) ---
  const numVariants = variantNames.length;
  const individualPlotHeight = combinedPlotHeight / numVariants;

  for (const name of variantNames) {
    const summary = data.variants[name];
    const variantContainer = document.createElement("div");
    leftColumnContainer.appendChild(variantContainer);

    renderSinglePosterior(
      variantContainer,
      `Posterior for ${name}`,
      summary,
      globalXDomain,
      globalYDomain,
      individualPlotHeight,
      color(name)
    );
  }
}

async function main() {
  const experimentName = posteriorContainer.dataset.experimentName;
  if (!experimentName) {
    trialsContainer.innerText = "Could not find experiment name.";
    posteriorContainer.innerText = "";
    return;
  }

  // Show loading messages
  trialsContainer.innerHTML = "<p>Loading trial data...</p>";
  posteriorContainer.innerHTML = "<p>Fitting model...</p>";

  // Fetch trial data first
  try {
    const data = await apiClient.getExperimentData(experimentName, {
      limit: 10000,
    });
    const trials = d3.group(data.rows, (d) => d.variant);
    renderAllTrials(trialsContainer, trials);
  } catch (e) {
    console.error(e);
    trialsContainer.innerText = `Error loading data: ${e.message}`;
  }

  // Then fetch posterior data asynchronously
  try {
    const posteriorData = await apiClient.getABTestPosterior(experimentName);
    renderPosteriors(posteriorContainer, posteriorData);
  } catch (e) {
    console.error(e);
    posteriorContainer.innerText = `Error loading posterior: ${e.message}`;
  }
}

main();
