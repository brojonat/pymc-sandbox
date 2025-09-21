// Import necessary libraries from a CDN
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

import { apiClient } from "/static/client.js";

const posteriorContainer = document.getElementById("chart-container");
const timelinesContainer = document.getElementById("timelines-container");
const globalTimelineContainer = document.getElementById(
  "global-timeline-container"
);
const groupByCheckboxes = document.querySelectorAll(".group-by-checkbox");

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

function renderSingleTimeline(container, cohortName, cohortData, timeDomain) {
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

  // 3. Define scales
  const xScale = d3.scaleUtc().domain(timeDomain).range([0, width]);

  // 4. Draw event ticks
  svg
    .selectAll("line")
    .data(cohortData)
    .join("line")
    .attr("x1", (d) => xScale(d.timestamp))
    .attr("x2", (d) => xScale(d.timestamp))
    .attr("y1", 0)
    .attr("y2", height)
    .attr("stroke", "black")
    .attr("stroke-width", 1)
    .attr("stroke-opacity", 0.5);

  // 5. Draw X axis
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale));

  // 6. Draw Title
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2 + 10)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text(`Raw Data: ${cohortName}`);

  // 7. Add a summary text
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 15)
    .attr("text-anchor", "middle")
    .style("font-size", "12px")
    .text(`${cohortData.length} events`);
}

function renderGlobalTimeline(container, cohortEvents, timeDomain) {
  // 1. Setup dimensions
  container.innerHTML = "";
  const margin = { top: 30, right: 30, bottom: 40, left: 50 };
  const width = container.clientWidth - margin.left - margin.right;
  const height = 150 - margin.top - margin.bottom;

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
  const color = d3.scaleOrdinal(d3.schemeCategory10);

  // 4. Compute KDE for each cohort
  const allDensities = [];
  let maxDensity = 0;
  const numericTicks = xScale.ticks(200).map((d) => d.getTime());

  for (const [cohortName, events] of cohortEvents) {
    const timestamps = events.map((d) => d.timestamp);
    const numericTimestamps = timestamps.map((d) => d.getTime());
    const stdDev = d3.deviation(numericTimestamps);
    const bandwidth =
      (1.06 * (stdDev || 1e-9)) / Math.pow(timestamps.length, 0.2);
    const kde = kernelDensityEstimator(
      kernelEpanechnikov(bandwidth),
      numericTicks
    );
    const density = kde(numericTimestamps);
    allDensities.push({ name: cohortName, density: density });
    const currentMax = d3.max(density, (d) => d[1]);
    if (currentMax > maxDensity) {
      maxDensity = currentMax;
    }
  }

  const xDensityScale = d3
    .scaleLinear()
    .domain(d3.extent(numericTicks))
    .range([0, width]);
  const yScale = d3
    .scaleLinear()
    .domain([0, maxDensity * 1.1])
    .range([height, 0]);

  // 5. Draw the density lines
  const line = d3
    .line()
    .x((d) => xDensityScale(d[0]))
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

  // 6. Draw X axis
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale));

  // 7. Draw Title & Legend
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2 + 10)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text("Global Event Distribution");

  const legend = svg
    .selectAll(".legend")
    .data(cohortEvents.keys())
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

function renderAllTimelines(container, cohortEvents, timeDomain) {
  container.innerHTML = "";
  const sortedCohorts = new Map(
    [...cohortEvents.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  );
  for (const [cohortName, cohortData] of sortedCohorts) {
    const cohortContainer = document.createElement("div");
    container.appendChild(cohortContainer);
    renderSingleTimeline(cohortContainer, cohortName, cohortData, timeDomain);
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
  const allSamples = Object.values(data)
    .map((d) => d.posterior_rate)
    .flat();
  const xDomain = d3.extent(allSamples);
  const xScale = d3.scaleLinear().domain(xDomain).range([0, width]);
  const color = d3.scaleOrdinal(d3.schemeCategory10);

  // 4. Compute KDE for each variant
  const allDensities = [];
  let maxDensity = 0;

  for (const [name, samples] of Object.entries(data)) {
    const rates = samples.posterior_rate;
    const stdDev = d3.deviation(rates);
    const bandwidth = (1.06 * (stdDev || 1e-9)) / Math.pow(rates.length, 0.2);
    const kde = kernelDensityEstimator(
      kernelEpanechnikov(bandwidth),
      xScale.ticks(100)
    );
    const density = kde(rates);
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
    .text("λ [events/day]");

  // 7. Draw Title & Legend
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Posterior Distributions for Cohort Event Rates");

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

async function fetchAndRender() {
  const experimentName = posteriorContainer.dataset.experimentName;
  const groupBy = Array.from(groupByCheckboxes)
    .filter((cb) => cb.checked)
    .map((cb) => cb.value);

  if (groupBy.length === 0) {
    // Prevent fetching/rendering if nothing is selected
    posteriorContainer.innerHTML =
      "<p>Please select at least one dimension to group by.</p>";
    globalTimelineContainer.innerHTML = "";
    timelinesContainer.innerHTML = "";
    return;
  }

  if (!experimentName) {
    timelinesContainer.innerText = "Could not find experiment name.";
    posteriorContainer.innerText = "";
    return;
  }

  // Show loading messages
  timelinesContainer.innerHTML = "<p>Loading event data...</p>";
  globalTimelineContainer.innerHTML = "";
  posteriorContainer.innerHTML = "<p>Fitting model...</p>";

  // Fetch event data first
  let groupedEvents, timeDomain;
  try {
    const data = await apiClient.getExperimentData(experimentName, {
      limit: 10000,
    });

    if (!data.rows || data.rows.length === 0) {
      timelinesContainer.innerText = "No event data to display.";
      posteriorContainer.innerHTML = "";
      return;
    }

    const processedData = data.rows.map((d) => ({
      ...d,
      timestamp: d3.isoParse(d.timestamp),
    }));
    // The d3.group function can take an array of accessors to group by multiple dimensions
    groupedEvents = d3.group(processedData, ...groupBy.map((g) => (d) => d[g]));
    timeDomain = d3.extent(processedData, (d) => d.timestamp);

    if (!timeDomain[0] || !timeDomain[1]) {
      timelinesContainer.innerText = "No valid timestamps found in event data.";
      posteriorContainer.innerHTML = "";
      return;
    }

    renderGlobalTimeline(globalTimelineContainer, groupedEvents, timeDomain);
    renderAllTimelines(timelinesContainer, groupedEvents, timeDomain);
  } catch (e) {
    console.error(e);
    timelinesContainer.innerText = `Error loading data: ${e.message}`;
    posteriorContainer.innerHTML = ""; // Clear fitting model message
    return;
  }

  // Then fetch posterior data asynchronously
  try {
    const [start, end] = timeDomain;
    const posteriorData = await apiClient.getPoissonCohortsPosterior(
      experimentName,
      {
        start: start.toISOString(),
        end: end.toISOString(),
        group_by: groupBy,
      }
    );
    renderPosteriors(posteriorContainer, posteriorData.results);
  } catch (e) {
    console.error(e);
    posteriorContainer.innerText = `Error loading posterior: ${e.message}`;
  }
}

async function main() {
  groupByCheckboxes.forEach((cb) =>
    cb.addEventListener("change", fetchAndRender)
  );
  await fetchAndRender();
}

main();
