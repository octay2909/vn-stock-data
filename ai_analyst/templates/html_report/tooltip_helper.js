/**
 * D3.js Tooltip Helper
 * Consistent tooltip positioning and formatting across all charts.
 */

function setupTooltip(container) {
  let tooltip = d3.select(container).select('.chart-tooltip');
  if (tooltip.empty()) {
    tooltip = d3.select(container)
      .append('div')
      .attr('class', 'chart-tooltip')
      .style('position', 'absolute')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('background', '#1A202C')
      .style('color', '#FFFFFF')
      .style('padding', '8px 12px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('font-family', "'IBM Plex Sans', system-ui, sans-serif")
      .style('box-shadow', '0 4px 6px rgba(0,0,0,0.15)')
      .style('z-index', '1000')
      .style('max-width', '250px')
      .style('line-height', '1.4');
  }
  return tooltip;
}

function showTooltip(tooltip, event, content) {
  tooltip.html(content).style('opacity', 1);
  const tooltipNode = tooltip.node();
  const containerRect = tooltipNode.parentNode.getBoundingClientRect();
  const tooltipRect = tooltipNode.getBoundingClientRect();
  let left = event.clientX - containerRect.left + 15;
  let top = event.clientY - containerRect.top - 10;
  if (left + tooltipRect.width > containerRect.width)
    left = event.clientX - containerRect.left - tooltipRect.width - 15;
  if (top + tooltipRect.height > containerRect.height)
    top = event.clientY - containerRect.top - tooltipRect.height - 10;
  tooltip.style('left', left + 'px').style('top', top + 'px');
}

function hideTooltip(tooltip) {
  tooltip.style('opacity', 0);
}

function formatTooltipValue(value, type) {
  if (type === 'currency') return '$' + d3.format(',.0f')(value);
  if (type === 'percent') return d3.format('.1f')(value) + '%';
  if (type === 'count') return d3.format(',')(value);
  if (type === 'decimal') return d3.format(',.2f')(value);
  return String(value);
}

function buildTooltipContent(label, value, delta, type) {
  let html = '<strong>' + label + '</strong><br/>';
  html += '<span style="font-size:14px;font-weight:600">' + formatTooltipValue(value, type) + '</span>';
  if (delta !== undefined && delta !== null) {
    const color = delta >= 0 ? '#10B981' : '#EF4444';
    const prefix = delta >= 0 ? '+' : '';
    html += '<br/><span style="color:' + color + '">' + prefix + formatTooltipValue(delta, type) + '</span>';
  }
  return html;
}
