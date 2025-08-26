// Import necessary libraries from a CDN
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const API_BASE_URL = ""; // Use a relative path for same-origin requests
const container = document.getElementById("chart-container");

// --- Global State ---
const posteriorCache = {};
let globalXDomain = [null, null];

function renderPosterior(container, posteriorData, plotHeight, xDomain) {
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
  const xScale = d3.scaleLinear().domain(xDomain).range([0, width]);
  const bins = d3.bin().domain(xScale.domain()).thresholds(xScale.ticks(40))(
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
    .style("fill", "steelblue");

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
    .call(d3.axisBottom(xScale))
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

  let allRates = [];
  for (const cachedData of Object.values(posteriorCache)) {
    const name = Object.keys(cachedData)[0];
    allRates.push(...cachedData[name].posterior_rate);
  }
  globalXDomain = d3.extent(allRates);

  // 2. Rerender all cached plots with the new domains
  for (const [name, posteriorData] of Object.entries(posteriorCache)) {
    const target = document.getElementById(`action-container-${name}`);
    const plotHeight = 75; // This should be consistent
    renderPosterior(target, posteriorData, plotHeight, globalXDomain);
  }
}

async function renderCohorts(container, data) {
  // 1. Pre-process data
  const processedData = data.map((d) => ({ ...d, ts: d3.isoParse(d.ts) }));
  const cohorts = d3.group(processedData, (d) => d.cohort);
  const sortedCohorts = new Map(
    [...cohorts.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  );
  const [minTime, maxTime] = d3.extent(processedData, (d) => d.ts);
  const plotHeight = 75;

  // 2. Pre-populate dummy data
  const cohortEntries = [...sortedCohorts.entries()];
  for (let i = 0; i < 3 && i < cohortEntries.length; i++) {
    const [cohortName] = cohortEntries[i];
    const mean = 5 + i * 2;
    const stddev = 1 + i * 0.5;
    const dummyRates = Array.from({ length: 1000 }, () =>
      d3.randomNormal(mean, stddev)()
    );
    posteriorCache[cohortName] = {
      [cohortName]: { posterior_rate: dummyRates },
    };
  }

  // 3. Build the DOM structure first (Pass 1)
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

    const actionContainer = document.createElement("div");
    actionContainer.id = `action-container-${cohortName}`;
    actionContainer.style.width = "600px";
    actionContainer.style.marginLeft = "20px";
    cohortWrapper.appendChild(actionContainer);

    container.appendChild(cohortWrapper);
  }

  // 4. Initial calculation of global domain and drawing of cached posteriors
  if (Object.keys(posteriorCache).length > 0) {
    updateAndRedrawAll();
  }

  // 5. Now render content into the existing DOM structure (Pass 2)
  for (const [cohortName, cohortData] of sortedCohorts) {
    const timelineContainer = document.getElementById(
      `timeline-container-${cohortName}`
    );
    const actionContainer = document.getElementById(
      `action-container-${cohortName}`
    );

    renderTimeline(timelineContainer, cohortData, plotHeight, [
      minTime,
      maxTime,
    ]);

    if (posteriorCache[cohortName]) {
      renderPosterior(
        actionContainer,
        posteriorCache[cohortName],
        plotHeight,
        globalXDomain
      );
    } else {
      const fitButton = document.createElement("button");
      fitButton.innerText = `Fit ${cohortName}`;
      actionContainer.appendChild(fitButton);

      fitButton.addEventListener("click", async () => {
        actionContainer.innerHTML = "Fitting model...";
        try {
          const response = await fetch(
            `${API_BASE_URL}/poisson-cohorts/fit?start=${minTime.toISOString()}&end=${maxTime.toISOString()}&cohort=${cohortName}`
          );
          if (!response.ok)
            throw new Error(`HTTP error! status: ${response.status}`);

          const responseData = await response.json();
          posteriorCache[cohortName] = responseData.results;
          updateAndRedrawAll();
        } catch (error) {
          console.error("Failed to fetch or render posterior data:", error);
          actionContainer.innerText = "Failed to load posterior data.";
        }
      });
    }
  }
}

async function main() {
  try {
    const response = await fetch(
      `${API_BASE_URL}/poisson-cohorts/list?limit=5000`
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
