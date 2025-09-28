import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

import { apiClient } from "/static/client.js";

const chartContainer = document.getElementById("chart-container");
const eventsContainer = document.getElementById("events-container");
const experimentName = chartContainer.dataset.experimentName;

function renderEvents(container, events) {
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
  const xScale = d3
    .scaleLinear()
    .domain([0, d3.max(events, (d) => d.duration)])
    .range([0, width]);
  const color = d3
    .scaleOrdinal()
    .domain([true, false])
    .range(["#2ECC71", "#E67E22"]);

  // 4. Draw event ticks
  svg
    .selectAll("rect")
    .data(events)
    .enter()
    .append("rect")
    .attr("x", (d) => xScale(d.duration))
    .attr("y", height * 0.25)
    .attr("width", 2)
    .attr("height", height * 0.5)
    .attr("fill", (d) => color(d.observed))
    .append("title")
    .text(
      (d) =>
        `Duration: ${d.duration.toFixed(2)}\nObserved: ${
          d.observed ? "Yes" : "No"
        }`
    );

  // 5. Draw Title
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2 + 10)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Raw Event Data (Green=Observed, Orange=Censored)");

  // 6. Draw X axis
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale));
}

function renderPosterior(container, data, title, color) {
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
  const height = 250 - margin.top - margin.bottom;

  // 2. Create SVG
  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // 3. Define scales
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
    .attr("fill", color)
    .attr("fill-opacity", 0.4)
    .attr("stroke", "#000")
    .attr("stroke-width", 1.5)
    .attr("d", area);

  // 5. Draw X axis and label
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale).ticks(5));
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .text(title.split(" ")[2]); // e.g., "α"

  // 6. Draw Title and Subtitle
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

  // 7. Add a vertical line for interactivity
  const indicatorLine = svg
    .append("line")
    .attr("stroke", "black")
    .attr("stroke-width", 1)
    .attr("stroke-dasharray", "4,4")
    .attr("y1", 0)
    .attr("y2", height)
    .style("opacity", 0);

  // 8. Return an update function
  return (value) => {
    if (value === null || value === undefined) {
      indicatorLine.style("opacity", 0);
    } else {
      indicatorLine
        .attr("x1", xScale(value))
        .attr("x2", xScale(value))
        .style("opacity", 1);
    }
  };
}

function sampleFromCurve(curve, n) {
  // Create a weighted sampler from the posterior curve
  const { x, y } = curve;
  const totalWeight = d3.sum(y);

  // Handle edge case where there are no positive weights
  if (totalWeight <= 0) {
    // Return samples from the uniform distribution of x as a fallback
    const xMin = d3.min(x);
    const xMax = d3.max(x);
    if (xMin === xMax) return d3.range(n).map(() => xMin);
    return d3.range(n).map(() => xMin + Math.random() * (xMax - xMin));
  }

  const weights = y.map((w) => w / totalWeight);

  const cumulativeWeights = [];
  let cumulative = 0;
  for (let i = 0; i < weights.length; i++) {
    cumulative += weights[i];
    cumulativeWeights.push(cumulative);
  }

  const samples = [];
  for (let i = 0; i < n; i++) {
    const r = Math.random();
    const index = cumulativeWeights.findIndex((cw) => cw >= r);
    // Fallback if findIndex returns -1 for some reason (e.g., rounding errors)
    samples.push(x[index !== -1 ? index : x.length - 1]);
  }
  return samples;
}

function renderSampledDistributions(
  container,
  posteriorData,
  updateAlphaIndicator,
  updateBetaIndicator
) {
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

  // 3. Weibull PDF function
  const weibullPDF = (x, alpha, beta) => {
    if (x < 0 || alpha <= 0 || beta <= 0) return 0;
    return (
      (alpha / beta) *
      Math.pow(x / beta, alpha - 1) *
      Math.exp(-Math.pow(x / beta, alpha))
    );
  };

  // 4. Sample from posterior curves
  const nSamples = 30;
  const alphaSamples = sampleFromCurve(posteriorData.alpha.curve, nSamples);
  const betaSamples = sampleFromCurve(posteriorData.beta.curve, nSamples);

  const sampledLines = [];
  for (let i = 0; i < nSamples; i++) {
    sampledLines.push({ alpha: alphaSamples[i], beta: betaSamples[i] });
  }

  // 5. Define scales
  const xMax =
    d3.quantile(
      sampledLines.map((d) => d.beta),
      0.95
    ) * 1.5 || 1; // Fallback for xMax
  const epsilon = xMax / 10000; // A small offset to avoid x=0
  const xDomain = d3.range(epsilon, xMax, xMax / 200);

  // Cap the y-range to twice the median of the max values of the traces
  const maxValues = sampledLines.map(({ alpha, beta }) =>
    d3.max(xDomain, (x) => weibullPDF(x, alpha, beta))
  );
  const medianMax = d3.median(maxValues);
  const yMax = medianMax * 2;

  const xScale = d3.scaleLinear().domain([0, xMax]).range([0, width]);
  const yScale = d3.scaleLinear().domain([0, yMax]).range([height, 0]);

  // 6. Draw lines
  const line = d3
    .line()
    .x((d) => xScale(d.x))
    .y((d) => yScale(d.y));

  const linePaths = svg
    .selectAll(".line")
    .data(sampledLines)
    .enter()
    .append("path")
    .attr("class", "line")
    .attr("fill", "none")
    .attr("stroke", "#555555")
    .attr("stroke-width", 1.5)
    .attr("stroke-opacity", 0.2)
    .attr("d", ({ alpha, beta }) =>
      line(xDomain.map((x) => ({ x, y: weibullPDF(x, alpha, beta) })))
    );

  // 6b. Draw the reference trace for constant failure rate (alpha=1)
  const medianBeta = d3.median(betaSamples);
  if (medianBeta) {
    svg
      .append("path")
      .attr("fill", "none")
      .attr("stroke", "red")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "6,4")
      .attr("d", () =>
        line(xDomain.map((x) => ({ x, y: weibullPDF(x, 1, medianBeta) })))
      );
  }

  // 7. Draw X axis and label
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale));
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .text("Duration");

  // 8. Draw Title
  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Sampled Weibull Distributions from Posterior");

  // 9. Add interactivity
  const overlay = svg
    .append("rect")
    .attr("width", width)
    .attr("height", height)
    .style("fill", "none")
    .style("pointer-events", "all");

  overlay
    .on("mousemove", (event) => {
      const [mouseX, mouseY] = d3.pointer(event);
      const xValue = xScale.invert(mouseX);
      const yValue = yScale.invert(mouseY);

      let minDistance = Infinity;
      let closestLine = null;

      sampledLines.forEach((d) => {
        const pdfValue = weibullPDF(xValue, d.alpha, d.beta);
        const distance = Math.abs(pdfValue - yValue);

        if (distance < minDistance) {
          minDistance = distance;
          closestLine = d;
        }
      });

      if (closestLine) {
        updateAlphaIndicator(closestLine.alpha);
        updateBetaIndicator(closestLine.beta);
        linePaths
          .attr("stroke", (d) => (d === closestLine ? "#000000" : "#555555"))
          .attr("stroke-opacity", (d) => (d === closestLine ? 1 : 0.2))
          .attr("stroke-width", (d) => (d === closestLine ? 2 : 1.5));
      }
    })
    .on("mouseleave", () => {
      updateAlphaIndicator(null);
      updateBetaIndicator(null);
      linePaths
        .attr("stroke", "#555555")
        .attr("stroke-opacity", 0.2)
        .attr("stroke-width", 1.5);
    });
}

function renderAllPosteriors(container, posteriorData) {
  // 1. Clear container and create layout
  container.innerHTML = "";
  const mainFlexContainer = document.createElement("div");
  mainFlexContainer.style.display = "flex";
  mainFlexContainer.style.alignItems = "flex-start";

  const leftColumnContainer = document.createElement("div");
  leftColumnContainer.style.flex = "1";
  leftColumnContainer.style.display = "flex";
  leftColumnContainer.style.flexDirection = "column";

  const alphaContainer = document.createElement("div");
  const betaContainer = document.createElement("div");
  leftColumnContainer.appendChild(alphaContainer);
  leftColumnContainer.appendChild(betaContainer);

  const rightColumnContainer = document.createElement("div");
  rightColumnContainer.style.flex = "2";
  rightColumnContainer.style.textAlign = "center";

  mainFlexContainer.appendChild(leftColumnContainer);
  mainFlexContainer.appendChild(rightColumnContainer);
  container.appendChild(mainFlexContainer);

  // 2. Render the plots and get their update functions
  const updateAlphaIndicator = renderPosterior(
    alphaContainer,
    posteriorData.alpha,
    "Posterior for α (Shape)",
    "#69b3a2"
  );
  const updateBetaIndicator = renderPosterior(
    betaContainer,
    posteriorData.beta,
    "Posterior for β (Scale)",
    "#E67E22"
  );
  renderSampledDistributions(
    rightColumnContainer,
    posteriorData,
    updateAlphaIndicator,
    updateBetaIndicator
  );

  // 3. Add explanatory text from template
  const explanationTemplate = document.getElementById("weibull-explanation");
  if (explanationTemplate) {
    const explanationContent = explanationTemplate.content.cloneNode(true);
    rightColumnContainer.appendChild(explanationContent);
  }
}

async function loadAndRenderPosterior(experimentName) {
  chartContainer.innerHTML = "<p>Fitting model...</p>";
  try {
    const posteriorData = await apiClient.getPosterior(
      "weibull",
      experimentName
    );
    renderAllPosteriors(chartContainer, posteriorData);
  } catch (e) {
    console.error(e);
    chartContainer.innerText = `Error loading posterior: ${e.message}`;
  }
}

async function main() {
  if (!experimentName) {
    eventsContainer.innerText = "Could not find experiment name.";
    return;
  }

  try {
    const data = await apiClient.getExperimentData(experimentName, {
      limit: 10000,
    });
    renderEvents(eventsContainer, data.rows);
    loadAndRenderPosterior(experimentName);
  } catch (e) {
    console.error(e);
    eventsContainer.innerText = `Error loading data: ${e.message}`;
  }
}

main();
