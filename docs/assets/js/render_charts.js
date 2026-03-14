async function loadChart(container) {
  const src = container.dataset.chartSrc;
  if (!src || typeof echarts === "undefined") {
    return;
  }

  try {
    const response = await fetch(src);
    if (!response.ok) {
      throw new Error(`failed to load ${src}`);
    }
    const option = await response.json();
    const chart = echarts.init(container);
    chart.setOption(option);
    window.addEventListener("resize", () => chart.resize());
  } catch (error) {
    container.innerHTML = `<pre>${error.message}</pre>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-chart-src]").forEach((container) => {
    loadChart(container);
  });
});
