/**
 * Responsive Resize Handler
 * Re-renders charts on window resize with debouncing.
 */

const chartRegistry = {};

function registerChart(chartId, renderFn) {
  chartRegistry[chartId] = renderFn;
}

function resizeChart(chartId) {
  const container = document.getElementById('chart-' + chartId);
  if (!container) return;
  const svgContainer = container.querySelector('.chart-svg');
  if (!svgContainer) return;
  svgContainer.innerHTML = '';
  if (chartRegistry[chartId]) chartRegistry[chartId]();
}

function resizeAllCharts() {
  Object.keys(chartRegistry).forEach(function(id) { resizeChart(id); });
}

let resizeTimeout;
window.addEventListener('resize', function() {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(resizeAllCharts, 250);
});

document.addEventListener('DOMContentLoaded', function() {
  Object.keys(chartRegistry).forEach(function(id) { chartRegistry[id](); });
});
