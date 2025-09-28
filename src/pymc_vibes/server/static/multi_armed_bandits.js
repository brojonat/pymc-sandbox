import { json, format } from "https://cdn.jsdelivr.net/npm/d3@7/+esm";
import {
  boxX,
  plot,
} from "https://cdn.jsdelivr.net/npm/@observablehq/plot/+esm";

// Function to fetch data and render the plot and table
async function render() {
  const chartContainer = document.getElementById("chart-container");
  const rewardContainer = document.getElementById("expected-reward-container");
  const experimentName = chartContainer.dataset.experimentName;
  const url = `/multi-armed-bandits/posterior?experiment_name=${experimentName}`;

  try {
    const data = await json(url);
    const armsData = data.arms;

    // 1. Render Est. Success Prob. Plot
    const probPlot = plot({
      title: "Est. Success Prob. Distribution",
      marks: [
        boxX(
          armsData.flatMap((d) =>
            d.posterior_samples.est_prob.map((p) => ({ ...d, p }))
          ),
          {
            x: "p",
            y: "arm",
            fill: "arm",
            tip: true,
          }
        ),
      ],
      y: { grid: true, label: "Arm" },
      x: { label: "Success Probability" },
      color: { legend: true },
    });
    chartContainer.innerHTML = ""; // Clear previous chart
    chartContainer.appendChild(probPlot);

    // 2. Render Est. Expected Reward Plot
    const rewardPlot = plot({
      title: "Est. Expected Reward Distribution",
      marks: [
        boxX(
          armsData.flatMap((d) =>
            d.posterior_samples.expected_reward.map((r) => ({ ...d, r }))
          ),
          {
            x: "r",
            y: "arm",
            fill: "arm",
            tip: true,
          }
        ),
      ],
      y: { grid: true, label: "Arm" },
      x: { label: "Expected Reward" },
      color: { legend: true },
    });
    rewardContainer.innerHTML = "";
    rewardContainer.appendChild(rewardPlot);

    // 3. Render the data table
    renderTable(armsData);
  } catch (error) {
    chartContainer.innerHTML = `<div class="error">Failed to load data: ${error.message}</div>`;
  }
}

// Function to render the data table
function renderTable(data) {
  const trialsContainer = document.getElementById("trials-container");
  let table = `
    <h3 class="text-xl font-semibold mb-4">Arm Details</h3>
    <table class="min-w-full bg-white border border-gray-300">
        <thead>
            <tr>
                <th class="py-2 px-4 border-b">Arm</th>
                <th class="py-2 px-4 border-b">Magnitude</th>
                <th class="py-2 px-4 border-b">Est. Success Prob.</th>
                <th class="py-2 px-4 border-b">Expected Reward</th>
                <th class="py-2 px-4 border-b">Prob. to be Best</th>
            </tr>
        </thead>
        <tbody>
`;
  data.forEach((arm) => {
    table += `
        <tr>
            <td class="py-2 px-4 border-b">${arm.arm}</td>
            <td class="py-2 px-4 border-b">${format(".2f")(arm.magnitude)}</td>
            <td class="py-2 px-4 border-b">${format(".4f")(arm.est_prob)}</td>
            <td class="py-2 px-4 border-b">${format(".4f")(
              arm.expected_reward
            )}</td>
            <td class="py-2 px-4 border-b">${format(".2%")(arm.prob_best)}</td>
        </tr>
`;
  });
  table += `
        </tbody>
    </table>`;
  trialsContainer.innerHTML = table;
}

// Initial render after the DOM is fully loaded
document.addEventListener("DOMContentLoaded", render);
