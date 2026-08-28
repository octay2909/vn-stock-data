/**
 * SVG Text Wrap Helper
 * Wraps long text within SVG elements to fit specified width.
 */

function wrapText(textSelection, maxWidth) {
  textSelection.each(function() {
    const text = d3.select(this);
    const words = text.text().split(/\s+/).reverse();
    const lineHeight = 1.2;
    const x = text.attr('x') || 0;
    const y = text.attr('y') || 0;
    const dy = parseFloat(text.attr('dy') || 0);
    let word, line = [], lineNumber = 0;
    let tspan = text.text(null).append('tspan')
      .attr('x', x).attr('y', y).attr('dy', dy + 'em');
    while (word = words.pop()) {
      line.push(word);
      tspan.text(line.join(' '));
      if (tspan.node().getComputedTextLength() > maxWidth && line.length > 1) {
        line.pop();
        tspan.text(line.join(' '));
        line = [word];
        tspan = text.append('tspan')
          .attr('x', x).attr('y', y)
          .attr('dy', ++lineNumber * lineHeight + dy + 'em')
          .text(word);
      }
    }
  });
}

function truncateText(textSelection, maxWidth, suffix) {
  suffix = suffix || '...';
  textSelection.each(function() {
    const text = d3.select(this);
    const original = text.text();
    if (text.node().getComputedTextLength() <= maxWidth) return;
    let truncated = original;
    while (text.node().getComputedTextLength() > maxWidth && truncated.length > 0) {
      truncated = truncated.slice(0, -1);
      text.text(truncated + suffix);
    }
  });
}

function formatAxisLabel(value, type) {
  if (type === 'currency') {
    if (Math.abs(value) >= 1e6) return '$' + d3.format('.1f')(value / 1e6) + 'M';
    if (Math.abs(value) >= 1e3) return '$' + d3.format('.0f')(value / 1e3) + 'K';
    return '$' + d3.format(',.0f')(value);
  }
  if (type === 'percent') return d3.format('.0f')(value) + '%';
  if (type === 'count') {
    if (Math.abs(value) >= 1e6) return d3.format('.1f')(value / 1e6) + 'M';
    if (Math.abs(value) >= 1e3) return d3.format('.0f')(value / 1e3) + 'K';
    return d3.format(',')(value);
  }
  return String(value);
}
