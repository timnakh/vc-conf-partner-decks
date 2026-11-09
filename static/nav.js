(function () {
  const path = location.pathname.replace(/\/$/, "") || "/";
  const mp = path === "/calendar" || path === "/import" || path.startsWith("/partners");
  const decks = path === "/decks";
  const mats = path === "/materials" || path === "/kits";
  const bar = document.createElement("header");
  bar.className = "site-bar" + (mp ? " mp" : "");
  bar.innerHTML =
    '<div class="inner">' +
      '<a class="brand" href="/">VC Conf 2027</a>' +
      '<a href="/decks"' + (decks ? ' class="on"' : "") + ">Презентации</a>" +
      '<a href="/materials"' + (mats ? ' class="on"' : "") + ">Постеры</a>" +
      '<a class="lock' + (mp ? " on" : "") + '" href="/calendar">Медиапартнёры <i>🔒</i></a>' +
      '<nav class="site-sub">' +
        '<a href="/calendar"' + (path === "/calendar" ? ' class="on"' : "") + ">Календарь</a>" +
        '<a href="/partners"' + (path.startsWith("/partners") ? ' class="on"' : "") + ">Партнёры</a>" +
        '<a href="/import"' + (path === "/import" ? ' class="on"' : "") + ">Импорт</a>" +
      "</nav>" +
    "</div>";
  document.body.prepend(bar);
})();

function ticksBar(ticks) {
  ticks = ticks || [];
  if (!ticks.length) return '<span class="hint">нет выходов</span>';
  const done = ticks.filter((s) => s === "published").length;
  const left = ticks.length - done;
  const cells = ticks.map((s) => {
    const cls = s === "published" ? "ok" : s === "missed" ? "miss" : "";
    return `<i class="${cls}" title="${s}"></i>`;
  }).join("");
  const label = left === 0
    ? `<span class="done">${done}/${ticks.length} · всё вышло</span>`
    : `${done}/${ticks.length} · <span class="left">осталось ${left}</span>`;
  return `<span class="prog-line"><span class="prog">${cells}</span><span class="prog-n">${label}</span></span>`;
}
