// Import necessary libraries from a CDN
import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const API_BASE_URL = ""; // Use a relative path for same-origin requests
const slider = document.getElementById("time-slider");
const details = document.getElementById("event-details");
const container = document.getElementById("chart-container");

async function renderTimeline(container, data) {
  // 1. Pre-process data
  const processedData = data.map((d) => ({
    ...d,
    ts: d3.isoParse(d.ts),
  }));

  // 2. Create our own D3 scale. This is the key fix.
  // By creating the scale ourselves, we are not dependent on the plot rendering successfully
  // to extract a scale from it.
  const [minTime, maxTime] = d3.extent(processedData, (d) => d.ts);
  const width = container.clientWidth;
  const margins = { top: 20, right: 20, bottom: 30, left: 40 };
  const xScale = d3
    .scaleUtc()
    .domain([minTime, maxTime])
    .range([margins.left, width - margins.right]);

  // 3. Define the plot options using our pre-built scale
  const plotOptions = {
    width,
    marginTop: margins.top,
    marginRight: margins.right,
    marginBottom: margins.bottom,
    marginLeft: margins.left,
    marks: [
      Plot.frame({ anchor: "bottom", facet: "include" }),
      Plot.frame({ anchor: "left", facet: "include" }),
      Plot.tickX(processedData, { x: "ts", facet: "include" }),
      // Placeholder for the ruleX mark, which we add dynamically
      null,
    ],
    facet: {
      data: processedData,
      y: "cohort",
    },
    // Provide our own scale to the x-axis
    x: { scale: xScale, label: "Timestamp" },
    height: 300,
  };

  // 4. Render the initial plot (without the cursor)
  container.replaceChildren(Plot.plot(plotOptions));

  // 5. Create the custom D3 slider using our reliable xScale
  const sliderContainer = d3.select("#slider-container");
  const [rangeStart, rangeEnd] = xScale.range();
  const sliderWidth = rangeEnd - rangeStart;

  sliderContainer.attr("width", width);

  const sliderG = sliderContainer
    .append("g")
    .attr("transform", `translate(${margins.left}, 15)`);

  sliderG
    .append("line")
    .attr("class", "track")
    .attr("x1", 0)
    .attr("x2", sliderWidth)
    .style("stroke", "#ccc")
    .style("stroke-width", "6px")
    .style("stroke-linecap", "round");

  const handle = sliderG
    .append("circle")
    .attr("class", "handle")
    .attr("r", 8)
    .style("fill", "steelblue")
    .style("cursor", "pointer");

  // 6. Add interaction via d3.drag
  const eventDetails = document.getElementById("event-details");

  const dragHandler = d3.drag().on("drag", (event) => {
    const x = Math.max(0, Math.min(sliderWidth, event.x));
    const sliderTime = xScale.invert(x + margins.left);

    const closestPoint = d3.least(processedData, (d) =>
      Math.abs(d.ts.getTime() - sliderTime.getTime())
    );

    if (closestPoint) {
      handle.attr("cx", xScale(closestPoint.ts) - margins.left);
      plotOptions.marks[3] = Plot.ruleX([closestPoint.ts], { stroke: "red" });
      container.replaceChildren(Plot.plot(plotOptions));
      eventDetails.textContent = JSON.stringify(closestPoint, null, 2);
    }
  });

  handle.call(dragHandler);

  // Initialize the view to the first data point
  const initialPoint = processedData[0];
  if (initialPoint) {
    handle.attr("cx", xScale(initialPoint.ts) - margins.left);
    plotOptions.marks[3] = Plot.ruleX([initialPoint.ts], { stroke: "red" });
    container.replaceChildren(Plot.plot(plotOptions));
    eventDetails.textContent = JSON.stringify(initialPoint, null, 2);
  }
}

async function main() {
  try {
    const response = await fetch(
      `${API_BASE_URL}/poisson-cohorts/list?limit=5000`
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log("Fetched data:", data);
    if (data.rows && data.rows.length > 0) {
      renderTimeline(container, data.rows);
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
