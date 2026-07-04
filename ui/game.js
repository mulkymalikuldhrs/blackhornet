/* BlackHornet Living World — interactive game engine */
const TILE = 32;
const COLS = 60, ROWS = 40;
const MAP_W = COLS * TILE, MAP_H = ROWS * TILE;

let canvas, ctx, minimapCtx;
let cam = { x: 0, y: 0 };
let selected = null;
let resources = { wood: 100, food: 100, gold: 50 };
let entities = [];
let buildings = [];
let particles = [];
let ws = null;
let chatLog = [];
let mouse = { x: 0, y: 0, worldX: 0, worldY: 0 };

const TERRAIN = { GRASS:0, WATER:1, TREE:2, MOUNTAIN:3, SAND:4, DARK_GRASS:5 };
const COLORS = {
  [TERRAIN.GRASS]:'#3a6b35', [TERRAIN.WATER]:'#1a3a5a', [TERRAIN.TREE]:'#2a5a20',
  [TERRAIN.MOUNTAIN]:'#5a4a3a', [TERRAIN.SAND]:'#8a7a5a', [TERRAIN.DARK_GRASS]:'#2a5a2a'
};

let map = [];

function generateMap() {
  map = [];
  for (let y = 0; y < ROWS; y++) {
    map[y] = [];
    for (let x = 0; x < COLS; x++) {
      let n = noise(x*0.08, y*0.08);
      if (n < -0.2) map[y][x] = TERRAIN.WATER;
      else if (n < 0) map[y][x] = TERRAIN.SAND;
      else if (n < 0.3) map[y][x] = TERRAIN.GRASS;
      else if (n < 0.5) map[y][x] = TERRAIN.DARK_GRASS;
      else map[y][x] = TERRAIN.FOREST;
    }
  }
  // place resources
  for (let i = 0; i < 40; i++) {
    let rx = 2 + Math.floor(Math.random() * (COLS-4));
    let ry = 2 + Math.floor(Math.random() * (ROWS-4));
    if (map[ry][rx] === TERRAIN.GRASS || map[ry][rx] === TERRAIN.DARK_GRASS) {
      map[ry][rx] = TERRAIN.TREE;
    }
  }
  for (let i = 0; i < 20; i++) {
    let rx = 2 + Math.floor(Math.random() * (COLS-4));
    let ry = 2 + Math.floor(Math.random() * (ROWS-4));
    if (map[ry][rx] === TERRAIN.GRASS) map[ry][rx] = TERRAIN.MOUNTAIN;
  }
}

function noise(x, y) {
  let ix = Math.floor(x), iy = Math.floor(y);
  let fx = x - ix, fy = y - iy;
  let v00 = hash(ix, iy), v10 = hash(ix+1, iy);
  let v01 = hash(ix, iy+1), v11 = hash(ix+1, iy+1);
  let ux = fx*fx*(3-2*fx), uy = fy*fy*(3-2*fy);
  return lerp(lerp(v00, v10, ux), lerp(v01, v11, ux), uy);
}
function hash(x, y) { return ((x*374761393 + y*668265263) & 0x7fffffff) / 0x7fffffff * 2 - 1; }
function lerp(a, b, t) { return a + (b-a) * t; }

class Unit {
  constructor(x, y, type, hp=50) {
    this.x = x; this.y = y; this.type = type;
    this.hp = hp; this.maxHp = hp;
    this.targetX = x; this.targetY = y;
    this.speed = 1.5; this.size = 10;
    this.color = type === 'worker' ? '#ff8844' : '#ff4444';
    this.orders = [];
    this.building = null;
  }
  update() {
    let dx = this.targetX - this.x, dy = this.targetY - this.y;
    let dist = Math.sqrt(dx*dx + dy*dy);
    if (dist > 2) {
      this.x += (dx/dist) * this.speed;
      this.y += (dy/dist) * this.speed;
    }
    // resource gathering
    if (this.type === 'worker' && this.building) {
      let bx = this.building.x * TILE + TILE/2;
      let by = this.building.y * TILE + TILE/2;
      let bd = Math.hypot(this.x-bx, this.y-by);
      if (bd < 30 && this.building.progress < 100) {
        this.building.progress += 0.5;
      }
    }
  }
  draw(ctx) {
    ctx.save();
    ctx.translate(this.x - cam.x, this.y - cam.y);
    // body
    ctx.fillStyle = this.color;
    ctx.beginPath();
    ctx.arc(0, 0, this.size, 0, Math.PI*2);
    ctx.fill();
    // border
    ctx.strokeStyle = selected === this ? '#ffcc00' : '#333';
    ctx.lineWidth = selected === this ? 2 : 1;
    ctx.stroke();
    // hp bar
    let bw = 16, bh = 3;
    ctx.fillStyle = '#333';
    ctx.fillRect(-bw/2, -this.size-6, bw, bh);
    ctx.fillStyle = this.hp/this.maxHp > 0.5 ? '#4a4' : '#a44';
    ctx.fillRect(-bw/2, -this.size-6, bw * (this.hp/this.maxHp), bh);
    ctx.restore();
  }
}

class Building {
  constructor(tx, ty, type, name) {
    this.tx = tx; this.ty = ty;
    this.type = type; this.name = name;
    this.hp = 200; this.maxHp = 200;
    this.progress = type === 'base' ? 100 : 0;
    this.size = type === 'base' ? 2 : 1.5;
  }
  get x() { return this.tx * TILE; }
  get y() { return this.ty * TILE; }
  get cx() { return this.x + TILE*this.size/2; }
  get cy() { return this.y + TILE*this.size/2; }
  draw(ctx) {
    let px = this.x - cam.x, py = this.y - cam.y;
    let s = TILE * this.size;
    // shadow
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.fillRect(px+2, py+2, s, s);
    // body
    let grad = ctx.createLinearGradient(px, py, px+s, py+s);
    if (this.type === 'base') {
      grad.addColorStop(0, '#4a2a6a'); grad.addColorStop(1, '#2a1a4a');
    } else if (this.type === 'barracks') {
      grad.addColorStop(0, '#6a3a2a'); grad.addColorStop(1, '#4a2a1a');
    } else {
      grad.addColorStop(0, '#2a5a3a'); grad.addColorStop(1, '#1a3a2a');
    }
    ctx.fillStyle = grad;
    ctx.fillRect(px, py, s, s);
    ctx.strokeStyle = '#3a3a5a';
    ctx.lineWidth = 1;
    ctx.strokeRect(px, py, s, s);
    // name
    ctx.fillStyle = '#aab';
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(this.name, px + s/2, py - 4);
    // progress bar
    if (this.progress < 100) {
      let bw = s, bh = 3;
      ctx.fillStyle = '#333';
      ctx.fillRect(px, py + s + 2, bw, bh);
      ctx.fillStyle = '#4a4';
      ctx.fillRect(px, py + s + 2, bw * (this.progress/100), bh);
    }
    if (selected === this) {
      ctx.strokeStyle = '#ffcc00'; ctx.lineWidth = 2;
      ctx.strokeRect(px-2, py-2, s+4, s+4);
    }
  }
}

function init() {
  canvas = document.getElementById('game-canvas');
  ctx = canvas.getContext('2d');
  minimapCtx = document.getElementById('minimap').getContext('2d');
  resize();
  generateMap();
  // starting base
  buildings.push(new Building(10, 10, 'base', 'Hive'));
  buildings.push(new Building(8, 13, 'barracks', 'Nest'));
  buildings.push(new Building(12, 13, 'workshop', 'Forge'));
  // starting units
  for (let i = 0; i < 4; i++) {
    entities.push(new Unit(12*TILE + i*20, 14*TILE + 20, 'worker'));
  }
  entities.push(new Unit(14*TILE, 12*TILE, 'guard'));
  entities.push(new Unit(15*TILE, 12*TILE, 'guard'));
  connect();
  gameLoop();
  setupInput();
}

function resize() {
  canvas.width = window.innerWidth - 280;
  canvas.height = window.innerHeight;
}

function connect() {
  let proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  let host = location.host || 'localhost:8080';
  try {
    ws = new WebSocket(`${proto}//${host}/ws`);
    ws.onmessage = (e) => {
      try {
        let msg = JSON.parse(e.data);
        if (msg.type === 'response') addChat(`> ${msg.result}`);
      } catch(_) {}
    };
    ws.onopen = () => addChat('Connected to BH Ω');
    ws.onclose = () => addChat('Disconnected');
  } catch(_) {}
}

function addChat(msg) {
  chatLog.push(msg);
  if (chatLog.length > 50) chatLog.shift();
  let el = document.getElementById('chat-log');
  el.innerHTML = chatLog.map(m => `<div>${m}</div>`).join('');
  el.scrollTop = el.scrollHeight;
}

function gameLoop() {
  update();
  draw();
  updateMinimap();
  updateUI();
  requestAnimationFrame(gameLoop);
}

function update() {
  entities.forEach(u => u.update());
  // auto-gather resources
  entities.filter(u => u.type === 'worker').forEach(w => {
    let tileX = Math.floor(w.x / TILE), tileY = Math.floor(w.y / TILE);
    if (tileX >= 0 && tileX < COLS && tileY >= 0 && tileY < ROWS) {
      if (map[tileY][tileX] === TERRAIN.TREE && Math.random() < 0.02) {
        resources.wood += 0.5;
      }
    }
  });
}

function draw() {
  ctx.fillStyle = '#1a1a22';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // draw tiles
  let sx = Math.max(0, Math.floor(cam.x / TILE));
  let sy = Math.max(0, Math.floor(cam.y / TILE));
  let ex = Math.min(COLS, Math.ceil((cam.x + canvas.width) / TILE));
  let ey = Math.min(ROWS, Math.ceil((cam.y + canvas.height) / TILE));
  for (let y = sy; y < ey; y++) {
    for (let x = sx; x < ex; x++) {
      let t = map[y][x];
      let px = x * TILE - cam.x, py = y * TILE - cam.y;
      ctx.fillStyle = COLORS[t] || '#3a6b35';
      ctx.fillRect(px, py, TILE, TILE);
      if (t === TERRAIN.TREE) {
        ctx.fillStyle = '#3a7a28';
        ctx.fillRect(px+6, py+4, 20, 20);
        ctx.fillStyle = '#2a5a18';
        ctx.fillRect(px+10, py+20, 12, 8);
      } else if (t === TERRAIN.MOUNTAIN) {
        ctx.fillStyle = '#6a5a4a';
        ctx.beginPath();
        ctx.moveTo(px+4, py+28); ctx.lineTo(px+16, py+4);
        ctx.lineTo(px+28, py+28); ctx.fill();
      }
    }
  }
  // grid
  ctx.strokeStyle = 'rgba(255,255,255,0.03)';
  ctx.lineWidth = 0.5;
  for (let x = sx; x <= ex; x++) {
    ctx.beginPath(); ctx.moveTo(x*TILE-cam.x, 0); ctx.lineTo(x*TILE-cam.x, canvas.height); ctx.stroke();
  }
  for (let y = sy; y <= ey; y++) {
    ctx.beginPath(); ctx.moveTo(0, y*TILE-cam.y); ctx.lineTo(canvas.width, y*TILE-cam.y); ctx.stroke();
  }
  // buildings
  buildings.forEach(b => b.draw(ctx));
  // units
  entities.forEach(u => u.draw(ctx));
  // selection box
  if (mouse.dragging) {
    ctx.strokeStyle = '#ffcc00'; ctx.lineWidth = 1;
    ctx.setLineDash([4,4]);
    let lx = Math.min(mouse.downX, mouse.x), ly = Math.min(mouse.downY, mouse.y);
    let lw = Math.abs(mouse.downX - mouse.x), lh = Math.abs(mouse.downY - mouse.y);
    ctx.strokeRect(lx, ly, lw, lh);
    ctx.setLineDash([]);
  }
}

function updateMinimap() {
  let ms = 160, tw = ms/COLS, th = ms/ROWS;
  minimapCtx.fillStyle = '#0a0a12';
  minimapCtx.fillRect(0, 0, ms, ms);
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      let t = map[y][x];
      minimapCtx.fillStyle = t === TERRAIN.WATER ? '#1a3a5a' :
        t === TERRAIN.TREE ? '#2a5a20' :
        t === TERRAIN.MOUNTAIN ? '#5a4a3a' : '#3a6b35';
      minimapCtx.fillRect(x*tw, y*th, tw+0.5, th+0.5);
    }
  }
  // units
  entities.forEach(u => {
    minimapCtx.fillStyle = u.type === 'worker' ? '#ff8844' : '#ff4444';
    minimapCtx.fillRect((u.x/TILE)*tw, (u.y/TILE)*th, 2, 2);
  });
  // buildings
  buildings.forEach(b => {
    minimapCtx.fillStyle = '#aa66ff';
    minimapCtx.fillRect(b.tx*tw, b.ty*th, tw*b.size, th*b.size);
  });
  // viewport
  minimapCtx.strokeStyle = '#ffcc00';
  minimapCtx.lineWidth = 1;
  minimapCtx.strokeRect((cam.x/MAP_W)*ms, (cam.y/MAP_H)*ms, (canvas.width/MAP_W)*ms, (canvas.height/MAP_H)*ms);
}

function updateUI() {
  document.getElementById('wood').textContent = Math.floor(resources.wood);
  document.getElementById('food').textContent = Math.floor(resources.food);
  document.getElementById('gold').textContent = Math.floor(resources.gold);
  if (selected) {
    let info = document.getElementById('selection-info');
    if (selected.type) {
      info.textContent = `${selected.type} | HP: ${Math.floor(selected.hp)}/${selected.maxHp}`;
    } else {
      info.textContent = `${selected.name} | HP: ${Math.floor(selected.hp)}/${selected.maxHp} | ${selected.progress < 100 ? 'Building...' : 'Active'}`;
    }
    let actions = document.getElementById('actions');
    if (selected.type === 'worker') {
      actions.innerHTML = `
        <button onclick="buildBuilding('barracks')">Nest</button>
        <button onclick="buildBuilding('workshop')">Forge</button>
        <button onclick="buildBuilding('tower')">Spire</button>
      `;
    } else { actions.innerHTML = ''; }
  }
}

function buildBuilding(type) {
  if (!selected || selected.type !== 'worker') return;
  let names = { barracks: 'Nest', workshop: 'Forge', tower: 'Spire' };
  let costs = { barracks: {wood:50,food:30}, workshop: {wood:30,food:50}, tower: {wood:80,food:40,gold:20} };
  let cost = costs[type];
  if (!cost) return;
  for (let k in cost) { if ((resources[k]||0) < cost[k]) { addChat(`Need more ${k}`); return; } }
  for (let k in cost) resources[k] -= cost[k];
  let tx = Math.floor(selected.x/TILE) + 3;
  let ty = Math.floor(selected.y/TILE) + 3;
  if (tx < COLS-2 && ty < ROWS-2) {
    let b = new Building(tx, ty, type, names[type]);
    buildings.push(b);
    selected.building = b;
    addChat(`Building ${names[type]}...`);
  }
}

function setupInput() {
  let dragging = false, downX, downY;
  canvas.addEventListener('mousedown', (e) => {
    let rect = canvas.getBoundingClientRect();
    let mx = e.clientX - rect.left, my = e.clientY - rect.top;
    mouse.downX = mx; mouse.downY = my;
    mouse.dragging = true;
  });
  canvas.addEventListener('mousemove', (e) => {
    let rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
    mouse.worldX = mouse.x + cam.x;
    mouse.worldY = mouse.y + cam.y;
  });
  canvas.addEventListener('mouseup', (e) => {
    let rect = canvas.getBoundingClientRect();
    let mx = e.clientX - rect.left, my = e.clientY - rect.top;
    let dx = Math.abs(mx - (mouse.downX||mx)), dy = Math.abs(my - (mouse.downY||my));
    mouse.dragging = false;
    if (dx < 5 && dy < 5) {
      // click select
      let wx = mx + cam.x, wy = my + cam.y;
      selected = null;
      for (let b of buildings) {
        if (wx >= b.x && wx <= b.x + TILE*b.size && wy >= b.y && wy <= b.y + TILE*b.size) {
          selected = b; break;
        }
      }
      if (!selected) {
        for (let u of entities) {
          if (Math.hypot(wx-u.x, wy-u.y) < u.size+5) { selected = u; break; }
        }
      }
      if (!selected) {
        // move units
        let tx = Math.floor(wx/TILE), ty = Math.floor(wy/TILE);
        if (tx >= 0 && tx < COLS && ty >= 0 && ty < ROWS && map[ty][tx] !== TERRAIN.WATER) {
          entities.forEach(u => {
            if (u.type === 'worker') { u.targetX = wx; u.targetY = wy; }
          });
        }
      }
    } else {
      // drag select
      let lx = Math.min(mouse.downX, mx) + cam.x, ly = Math.min(mouse.downY, my) + cam.y;
      let rx = Math.max(mouse.downX, mx) + cam.x, ry = Math.max(mouse.downY, my) + cam.y;
      selected = null;
      for (let u of entities) {
        if (u.x >= lx && u.x <= rx && u.y >= ly && u.y <= ry) { selected = u; break; }
      }
    }
  });
  canvas.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    let rect = canvas.getBoundingClientRect();
    let wx = (e.clientX - rect.left) + cam.x, wy = (e.clientY - rect.top) + cam.y;
    let tx = Math.floor(wx/TILE), ty = Math.floor(wy/TILE);
    if (tx >= 0 && tx < COLS && ty >= 0 && ty < ROWS && map[ty][tx] !== TERRAIN.WATER) {
      entities.forEach(u => {
        u.targetX = wx; u.targetY = wy;
      });
    }
  });
  // scroll
  canvas.addEventListener('wheel', (e) => {
    cam.x += e.deltaX; cam.y += e.deltaY;
    cam.x = Math.max(0, Math.min(MAP_W - canvas.width, cam.x));
    cam.y = Math.max(0, Math.min(MAP_H - canvas.height, cam.y));
  });

  // keyboard
  window.addEventListener('keydown', (e) => {
    let step = 40;
    if (e.key === 'ArrowLeft') cam.x -= step;
    else if (e.key === 'ArrowRight') cam.x += step;
    else if (e.key === 'ArrowUp') cam.y -= step;
    else if (e.key === 'ArrowDown') cam.y += step;
    cam.x = Math.max(0, Math.min(MAP_W - canvas.width, cam.x));
    cam.y = Math.max(0, Math.min(MAP_H - canvas.height, cam.y));
  });
  // chat
  document.getElementById('chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      let input = e.target;
      let cmd = input.value.trim();
      if (cmd) {
        addChat(`> ${cmd}`);
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({type:'command', command: cmd}));
        }
        // Local commands
        if (cmd === 'status') {
          addChat(`BH: ${document.getElementById('bh-score').textContent} | SCS: ${document.getElementById('scs').textContent} | Projects: ${document.getElementById('project-count').textContent}`);
        } else if (cmd.startsWith('spawn ')) {
          let count = parseInt(cmd.split(' ')[1]) || 1;
          for (let i = 0; i < count; i++) {
            entities.push(new Unit(12*TILE + i*16, 15*TILE, 'worker'));
          }
          addChat(`Spawned ${count} workers`);
        }
        input.value = '';
      }
    }
  });
  // minimap click
  document.getElementById('minimap').addEventListener('click', (e) => {
    let rect = e.target.getBoundingClientRect();
    let mx = (e.clientX - rect.left) / 160;
    let my = (e.clientY - rect.top) / 160;
    cam.x = mx * MAP_W - canvas.width/2;
    cam.y = my * MAP_H - canvas.height/2;
    cam.x = Math.max(0, Math.min(MAP_W - canvas.width, cam.x));
    cam.y = Math.max(0, Math.min(MAP_H - canvas.height, cam.y));
  });

  window.addEventListener('resize', resize);
}

window.onload = init;
