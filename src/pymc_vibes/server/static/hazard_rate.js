import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

import { apiClient } from "/static/client.js";

const chartContainer = document.getElementById("chart-container");
const experimentName = chartContainer.dataset.experimentName;

function renderCombinedPlot(container, eventData, posteriorData) {
  // 1. Clear container and setup dimensions
  container.innerHTML = "";
  const margin = { top: 40, right: 30, bottom: 50, left: 60 };
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

  // 3. Determine shared x-domain
  const maxEventDuration = d3.max(eventData.rows, (d) => d.duration);
  const maxBoundary = d3.max(posteriorData.boundaries);
  const xMax = Math.max(maxEventDuration, maxBoundary) || 1.0;
  const xDomain = [0, xMax];

  // 4. Process posterior data
  const { lambdas, boundaries } = posteriorData;
  const lambdaData = lambdas.data;
  const lambdaColumns = lambdas.columns;
  const medianIdx = lambdaColumns.indexOf("median");
  const hdiLowerIdx = lambdaColumns.indexOf("hdi_3%");
  const hdiUpperIdx = lambdaColumns.indexOf("hdi_97%");

  const plotData = lambdaData.map((row, i) => ({
    median: row[medianIdx],
    hdiLower: row[hdiLowerIdx],
    hdiUpper: row[hdiUpperIdx],
  }));

  const fullBoundaries = [0, ...boundaries, xMax];
  const yMax = d3.max(plotData, (d) => d.hdiUpper) * 1.1;

  // 5. Define scales
  const xScale = d3.scaleLinear().domain(xDomain).range([0, width]);
  const yScale = d3.scaleLinear().domain([0, yMax]).range([height, 0]);

  // Generate midpoints for smoothing
  const midpoints = fullBoundaries
    .slice(0, -1)
    .map((d, i) => (d + fullBoundaries[i + 1]) / 2);

  // 6. Draw the HDI bands (area)
  const area = d3
    .area()
    .x((d, i) => xScale(midpoints[i]))
    .y0((d) => yScale(d.hdiLower))
    .y1((d) => yScale(d.hdiUpper))
    .curve(d3.curveBasis);

  svg
    .append("path")
    .datum(plotData)
    .attr("fill", "#69b3a2")
    .attr("fill-opacity", 0.3)
    .attr("d", area(plotData.map((d, i) => ({ ...d, x: fullBoundaries[i] }))));

  // 7. Draw the median hazard rate (step line)
  const line = d3
    .line()
    .x((d, i) => xScale(midpoints[i]))
    .y((d) => yScale(d.median))
    .curve(d3.curveBasis);

  svg
    .append("path")
    .datum(plotData)
    .attr("fill", "none")
    .attr("stroke", "#69b3a2")
    .attr("stroke-width", 2.5)
    .attr("d", line);

  // 8. Draw event data as a rug plot
  const color = d3
    .scaleOrdinal()
    .domain([true, false])
    .range(["#2ECC71", "#E67E22"]);

  svg
    .selectAll(".event-tick")
    .data(eventData.rows)
    .enter()
    .append("rect")
    .attr("class", "event-tick")
    .attr("x", (d) => xScale(d.duration))
    .attr("y", height - 10) // Position at the bottom of the plot area
    .attr("width", 2)
    .attr("height", 10)
    .attr("fill", (d) => color(d.observed))
    .append("title")
    .text(
      (d) =>
        `Duration: ${d.duration.toFixed(2)}\nObserved: ${
          d.observed ? "Yes" : "No"
        }`
    );

  // 9. Draw Axes
  svg
    .append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale));

  svg.append("g").call(d3.axisLeft(yScale));

  // 10. Draw Titles and Labels
  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .text("Duration");

  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("transform", "rotate(-90)")
    .attr("y", -margin.left + 20) // Adjusted for more space
    .attr("x", -height / 2)
    .text("Hazard Rate (λ)");

  svg
    .append("text")
    .attr("x", width / 2)
    .attr("y", 0 - margin.top / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Posterior Estimated Hazard Rate");

  // Add a legend for the rug plot
  const legend = svg
    .append("g")
    .attr("class", "legend")
    .attr("transform", `translate(${width - 150}, ${-margin.top / 2 - 10})`);

  legend
    .append("rect")
    .attr("x", 0)
    .attr("width", 10)
    .attr("height", 10)
    .attr("fill", "#2ECC71");
  legend.append("text").attr("x", 15).attr("y", 10).text("Observed");

  legend
    .append("rect")
    .attr("x", 80)
    .attr("width", 10)
    .attr("height", 10)
    .attr("fill", "#E67E22");
  legend.append("text").attr("x", 95).attr("y", 10).text("Censored");
}

async function main() {
  if (!experimentName) {
    chartContainer.innerHTML = "<p>Could not find experiment name.</p>";
    return;
  }

  chartContainer.innerHTML =
    "<p>Loading data and fitting model (this may take a minute)...</p>";

  try {
    // 1. Fetch both datasets in parallel
    const [eventData, posteriorData] = await Promise.all([
      apiClient.getExperimentData(experimentName, { limit: 10000 }),
      apiClient.getPosterior("hazard-rate", experimentName),
    ]);

    // 2. Render the combined plot
    renderCombinedPlot(chartContainer, eventData, posteriorData);
  } catch (e) {
    console.error(e);
    chartContainer.innerText = `Error loading data: ${e.message}`;
  }
}

main();
