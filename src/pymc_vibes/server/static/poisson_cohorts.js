// Import necessary libraries from a CDN
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

import { apiClient } from "/static/client.js";

// --- Create a global tooltip ---
const tooltip = d3
  .select("body")
  .append("div")
  .style("opacity", 0)
  .style("position", "absolute")
  .style("background-color", "rgba(0, 0, 0, 0.8)")
  .style("color", "white")
  .style("padding", "5px 10px")
  .style("border-radius", "4px")
  .style("font-size", "12px")
  .style("pointer-events", "none")
  .style("z-index", "10");

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
  const [start, end] = timeDomain;
  const xScale = d3.scaleUtc().domain([start, end]).range([0, width]);

  // 4. Draw event ticks
  svg
    .selectAll("event-line")
    .data(cohortData)
    .join("line")
    .attr("class", "event-line")
    .attr("x1", (d) => xScale(d.timestamp))
    .attr("x2", (d) => xScale(d.timestamp))
    .attr("y1", 0)
    .attr("y2", height)
    .attr("stroke", "black")
    .attr("stroke-width", 1)
    .attr("stroke-opacity", 0.5);

  // Add wider, transparent lines for easier hovering
  svg
    .selectAll("hover-line")
    .data(cohortData)
    .join("line")
    .attr("class", "hover-line")
    .attr("x1", (d) => xScale(d.timestamp))
    .attr("x2", (d) => xScale(d.timestamp))
    .attr("y1", 0)
    .attr("y2", height)
    .attr("stroke", "transparent")
    .attr("stroke-width", 8) // Wider hover area
    .style("cursor", "pointer")
    .on("mouseover", () => {
      tooltip.style("opacity", 1);
    })
    .on("mousemove", (event, d) => {
      tooltip
        .html(d.timestamp.toLocaleString())
        .style("left", `${event.pageX + 15}px`)
        .style("top", `${event.pageY - 15}px`);
    })
    .on("mouseout", () => {
      tooltip.style("opacity", 0);
    });

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
  const margin = { top: 30, right: 30, bottom: 40, left: 30 };
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
  const [start, end] = timeDomain;
  const xScale = d3.scaleUtc().domain([start, end]).range([0, width]);
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
    .text("Event Distribution");

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

function renderSinglePosterior(
  container,
  title,
  summaryData,
  xDomain,
  yDomain,
  chartHeight,
  color = "#69b3a2",
  timeUnit = "day"
) {
  const { stats, curve } = summaryData;
  const statsData = stats.data[0];
  const mean = statsData[stats.columns.indexOf("mean")];
  const median = statsData[stats.columns.indexOf("median")];
  const hdi_lower = statsData[stats.columns.indexOf("hdi_3%")];
  const hdi_upper = statsData[stats.columns.indexOf("hdi_97%")];

  const margin = { top: 60, right: 10, bottom: 50, left: 10 };
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

  const area = d3
    .area()
    .x((d, i) => xScale(curve.x[i]))
    .y0(height)
    .y1((d) => yScale(d))
    .curve(d3.curveBasis);

  svg
    .append("path")
    .datum(curve.y)
    .attr("fill", color)
    .attr("fill-opacity", 0.4)
    .attr("stroke", "#000")
    .attr("stroke-width", 1.5)
    .attr("d", area);

  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale).ticks(5));
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .text(`Rate [events/${timeUnit}/unit]`);

  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text(title);

  const statsLabel = svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 15 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "12px");

  statsLabel
    .append("tspan")
    .text(`Mean: ${mean.toFixed(3)} | Median: ${median.toFixed(3)}`);

  statsLabel
    .append("tspan")
    .attr("x", width / 2)
    .attr("dy", "1.2em")
    .text(`94% HDI: [${hdi_lower.toFixed(3)}, ${hdi_upper.toFixed(3)}]`);
}

export function renderPosteriors(
  container,
  data,
  groupNames,
  timeUnit = "day"
) {
  // data is a dictionary of { groupName: PosteriorSummary }
  container.innerHTML = "";

  // --- 1. Calculate Global Domains & Sort Groups ---
  if (!groupNames) {
    groupNames = Object.keys(data).sort((a, b) => {
      const summaryA = data[a];
      const summaryB = data[b];
      const meanA =
        summaryA.stats.data[0][summaryA.stats.columns.indexOf("mean")];
      const meanB =
        summaryB.stats.data[0][summaryB.stats.columns.indexOf("mean")];
      return meanA - meanB;
    });
  }

  if (groupNames.length === 0) {
    container.innerHTML = "<p>No posterior data to display.</p>";
    return;
  }
  const allGroups = groupNames.map((name) => data[name]);
  const allX = allGroups.flatMap((v) => v.curve.x);
  const allY = allGroups.flatMap((v) => v.curve.y);
  const globalXDomain = d3.extent(allX);
  const globalYDomain = [0, d3.max(allY) * 1.1];
  const color = d3.scaleOrdinal(d3.schemeCategory10);

  // --- 2. Create Layout Containers ---
  const mainFlexContainer = document.createElement("div");
  mainFlexContainer.style.display = "flex";
  mainFlexContainer.style.width = "100%";
  mainFlexContainer.style.alignItems = "flex-start";
  mainFlexContainer.style.gap = "20px";

  const leftColumnContainer = document.createElement("div");
  leftColumnContainer.style.flex = "4";
  leftColumnContainer.style.display = "flex";
  leftColumnContainer.style.flexDirection = "column";
  leftColumnContainer.style.gap = "10px";

  const rightColumnContainer = document.createElement("div");
  rightColumnContainer.style.flex = "6";

  mainFlexContainer.appendChild(leftColumnContainer);
  mainFlexContainer.appendChild(rightColumnContainer);
  container.appendChild(mainFlexContainer);

  // --- 3. Render Combined Plot (Right Column) ---
  const combinedPlotHeight = 500;
  const margin = { top: 60, right: 5, bottom: 50, left: 55 };
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

  // Draw lines for each group
  for (const name of groupNames) {
    const summary = data[name];
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
    .call(d3.axisBottom(xScale).ticks(5));
  combinedSvg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", combinedWidth / 2)
    .attr("y", combinedHeight + margin.bottom - 10)
    .text(`Rate [events/${timeUnit}/unit]`);
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
    .data(groupNames)
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
  const individualPlotHeight = combinedPlotHeight / groupNames.length;

  for (const name of groupNames) {
    const summary = data[name];
    const groupContainer = document.createElement("div");
    leftColumnContainer.appendChild(groupContainer);

    const localXDomain = d3.extent(summary.curve.x);

    renderSinglePosterior(
      groupContainer,
      `Posterior for ${name}`,
      summary,
      localXDomain,
      globalYDomain,
      individualPlotHeight,
      color(name),
      timeUnit
    );
  }
}

export function scalePosteriorData(posteriorData, exposures, timeUnit = "day") {
  if (!posteriorData) return null;

  const timeFactors = {
    day: 1,
    hour: 24,
    minute: 24 * 60,
    second: 24 * 60 * 60,
  };
  const timeFactor = timeFactors[timeUnit] || 1;

  const scaledPosteriorData = {};
  for (const groupName in posteriorData) {
    const summary = posteriorData[groupName];
    const exposure = exposures[groupName] || 1.0;

    const scalingDivisor = exposure * timeFactor;

    // Scale statistical summary
    const scaledStats = JSON.parse(JSON.stringify(summary.stats)); // Deep copy
    const rateMetrics = ["mean", "median", "hdi_3%", "hdi_97%", "sd"];
    const colIndices = scaledStats.columns.reduce((acc, col, i) => {
      if (rateMetrics.includes(col)) acc[col] = i;
      return acc;
    }, {});

    scaledStats.data.forEach((row) => {
      for (const metric of rateMetrics) {
        if (colIndices[metric] !== undefined) {
          row[colIndices[metric]] /= scalingDivisor;
        }
      }
    });

    // Scale KDE curve
    const scaledCurve = {
      x: summary.curve.x.map((val) => val / scalingDivisor),
      y: summary.curve.y.map((val) => val * scalingDivisor),
    };

    scaledPosteriorData[groupName] = {
      stats: scaledStats,
      curve: scaledCurve,
    };
  }
  return scaledPosteriorData;
}

export async function fetchAndRenderAll(groupBy) {
  const posteriorContainer = document.getElementById("chart-container");
  const timelinesContainer = document.getElementById("timelines-container");
  const globalTimelineContainer = document.getElementById(
    "global-timeline-container"
  );
  const experimentName = posteriorContainer.dataset.experimentName;

  if (!groupBy || groupBy.length === 0) {
    // Prevent fetching/rendering if nothing is selected
    posteriorContainer.innerHTML =
      "<p>Please select at least one dimension to group by.</p>";
    globalTimelineContainer.innerHTML = "";
    timelinesContainer.innerHTML = "";
    return { posteriorData: null, cohortNames: [] };
  }

  if (!experimentName) {
    timelinesContainer.innerText = "Could not find experiment name.";
    posteriorContainer.innerText = "";
    return { posteriorData: null, cohortNames: [] };
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
      return { posteriorData: null, cohortNames: [] };
    }

    const processedData = data.rows.map((d) => ({
      ...d,
      timestamp: d3.isoParse(d.timestamp),
    }));
    // Create a single composite key for grouping instead of nesting
    const groupAccessor = (d) => groupBy.map((key) => d[key]).join(" | ");
    groupedEvents = d3.group(processedData, groupAccessor);
    timeDomain = d3.extent(processedData, (d) => d.timestamp);

    if (!timeDomain[0] || !timeDomain[1]) {
      timelinesContainer.innerText = "No valid timestamps found in event data.";
      posteriorContainer.innerHTML = "";
      return { posteriorData: null, cohortNames: [] };
    }

    renderGlobalTimeline(globalTimelineContainer, groupedEvents, timeDomain);
    renderAllTimelines(timelinesContainer, groupedEvents, timeDomain);
  } catch (e) {
    console.error(e);
    timelinesContainer.innerText = `Error loading data: ${e.message}`;
    posteriorContainer.innerHTML = ""; // Clear fitting model message
    return { posteriorData: null, cohortNames: [] };
  }

  // Then fetch posterior data asynchronously
  try {
    const [start, end] = timeDomain;
    const posteriorData = await apiClient.getPosterior(
      "poisson-cohorts",
      experimentName,
      {
        start: start.toISOString(),
        end: end.toISOString(),
        group_by: groupBy,
      }
    );

    return { posteriorData, cohortNames: Array.from(groupedEvents.keys()) };
  } catch (e) {
    console.error(e);
    posteriorContainer.innerText = `Error loading posterior: ${e.message}`;
    return {
      posteriorData: null,
      cohortNames: Array.from(groupedEvents.keys()),
    };
  }
}
