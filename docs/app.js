let D, timer;
const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x !== undefined) e.textContent = x; return e; };
async function init() {
  D = await (await fetch("data/latest.json", {cache: "no-store"})).json();
  const box = document.getElementById("panels");
  D.agents.forEach(a => {
    const p = el("div", "panel"), h = el("div", "head");
    h.append(el("div", "avatar " + a.id, a.name.split(" ").pop()[0]));
    const m = el("div"); m.append(el("strong", "", a.name), el("div", "meta", a.provider + " / " + a.model)); h.append(m);
    p.append(h, el("div", "", "")); p.lastChild.id = "log-" + a.id; box.append(p);
  });
  const rows = D.candidates.map(c => `<tr><td>${c.name}</td><td>${c.gp}</td><td>${c.pts}</td><td>${c.reb}</td><td>${c.ast}</td><td>${c.stl}</td><td>${c.blk}</td><td>${c.score}</td></tr>`).join("");
  document.getElementById("boardtable").innerHTML = "<table><tr><th>Player</th><th>GP</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>Score</th></tr>" + rows + "</table>";
  document.getElementById("foot").textContent = "Debate for " + D.date + (D.mock ? " (mock data)" : "");
  document.getElementById("play").onclick = play;
  const now = new Date(new Date().toLocaleString("en-US", {timeZone: "America/Los_Angeles"}));
  if (now.getHours() === 15 && now.getMinutes() < 5) play();
}
function play() {
  clearInterval(timer);
  D.agents.forEach(a => document.getElementById("log-" + a.id).innerHTML = "");
  let i = 0;
  const step = () => {
    if (i >= D.lines.length) return clearInterval(timer);
    const l = D.lines[i++];
    document.getElementById("log-" + l.agent).append(el("div", "line", l.text));
  };
  step(); timer = setInterval(step, Math.round(180000 / D.lines.length)); // ~3 min total
}
init();
