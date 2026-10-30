// Shrinks long company names so they fit the available width.
// Keeps the text baseline in place, so the layout below does not move.
document.querySelectorAll('.fit').forEach(function (el) {
  var max = parseFloat(el.dataset.max), min = parseFloat(el.dataset.min);
  var width = parseFloat(el.dataset.width);
  var top0 = parseFloat(el.style.top);
  var size = max;
  el.style.fontSize = size + 'px';
  while (el.scrollWidth > width && size > min) {
    size -= 1;
    el.style.fontSize = size + 'px';
  }
  el.style.top = (top0 + 0.864 * (max - size)) + 'px';
  if (el.scrollWidth > width) { el.style.whiteSpace = 'normal'; el.style.width = width + 'px'; }
});
