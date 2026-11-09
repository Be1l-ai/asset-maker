'use strict';

const $ = (selector) => document.querySelector(selector);
const labels = { all: 'All assets', '3d': '3D model', '2d': '2D graphic', vfx: 'Visual effect', sfx: 'Sound effect' };
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const state = { assets: [], category: 'all', collection: 'all', search: '', motionPaused: reducedMotion.matches, activeAudio: null, selected: null };
const views = new Map();
const jsonCache = new Map();
const imageCache = new Map();
const audio = $('#audio-player');
const dialog = $('#asset-dialog');
let toastTimer;
let playbackRequest = 0;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function icon(name) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  node.setAttribute('class', 'icon');
  node.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', `#i-${name}`);
  node.append(use);
  return node;
}
function button(text, className, callback, iconName) {
  const node = element('button', className);
  node.type = 'button';
  if (iconName) node.append(icon(iconName));
  if (text) node.append(element('span', '', text));
  if (callback) node.addEventListener('click', callback);
  return node;
}
function localPath(path) {
  if (typeof path !== 'string' || !/^[a-zA-Z0-9_.\/-]+$/.test(path) || path.startsWith('/') || path.split('/').includes('..')) {
    throw new Error('Asset paths must be local to this project.');
  }
  return path;
}
function notify(message) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message;
  $('#toast').classList.add('visible');
  toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 4000);
}
function fetchJSON(path) {
  path = localPath(path);
  if (!jsonCache.has(path)) {
    const promise = fetch(path).then(response => {
      if (!response.ok) throw new Error(`Could not load ${path} (${response.status})`);
      return response.json();
    }).catch(error => { jsonCache.delete(path); throw error; });
    jsonCache.set(path, promise);
  }
  return jsonCache.get(path);
}
function fetchImage(path) {
  path = localPath(path);
  if (!imageCache.has(path)) {
    imageCache.set(path, new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => { imageCache.delete(path); reject(new Error('Image preview unavailable')); };
      image.src = path;
    }));
  }
  return imageCache.get(path);
}
function fitCanvas(canvas) {
  const box = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.round(box.width * ratio));
  const height = Math.max(1, Math.round(box.height * ratio));
  if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
  return [width, height];
}
function normalizeMesh(mesh) {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  mesh.vertices.forEach(vertex => vertex.forEach((value, axis) => {
    min[axis] = Math.min(min[axis], value);
    max[axis] = Math.max(max[axis], value);
  }));
  const extent = Math.max(...max.map((value, axis) => value - min[axis]));
  return { ...mesh, vertices: mesh.vertices.map(vertex => vertex.map((value, axis) => (value - (max[axis] + min[axis]) / 2) / extent)) };
}
function attachPreview(canvas, asset, options = {}) {
  const previous = views.get(canvas);
  if (previous?.buffer) modelRenderer.gl.deleteBuffer(previous.buffer);
  const view = { canvas, asset, kind: asset.category, data: null, yaw: asset.yaw ?? .65, pitch: .3, zoom: 1,
    time: asset.posterFrame !== undefined ? asset.posterFrame / asset.fps : asset.loop === false ? .35 : 0,
    paused: false, auto: false, hover: false, dragging: false, ...options };
  views.set(canvas, view);
  if (view.kind === '3d') {
    fetchJSON(asset.model).then(mesh => { view.data = normalizeMesh(mesh); }).catch(() => { view.error = true; });
  } else if (view.kind === 'vfx') {
    fetchImage(asset.atlas).then(image => { view.data = image; }).catch(() => { view.error = true; });
  } else if (view.kind === 'sfx') { view.data = asset.waveform; }
  if (options.interactive) enableOrbit(view);
  canvas.parentElement.addEventListener('pointerenter', () => { view.hover = true; });
  canvas.parentElement.addEventListener('pointerleave', () => { view.hover = false; });
  return view;
}
function enableOrbit(view) {
  const { canvas } = view;
  canvas.tabIndex = 0;
  canvas.style.cursor = 'grab';
  canvas.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    view.dragging = true;
    view.lastX = event.clientX;
    view.lastY = event.clientY;
    view.auto = false;
    canvas.setPointerCapture(event.pointerId);
    canvas.style.cursor = 'grabbing';
  });
  canvas.addEventListener('pointermove', event => {
    if (!view.dragging) return;
    view.yaw += (event.clientX - view.lastX) * .012;
    view.pitch = Math.max(-.35, Math.min(1.15, view.pitch + (event.clientY - view.lastY) * .009));
    view.lastX = event.clientX;
    view.lastY = event.clientY;
  });
  const stop = () => { view.dragging = false; canvas.style.cursor = 'grab'; };
  canvas.addEventListener('pointerup', stop);
  canvas.addEventListener('pointercancel', stop);
  canvas.addEventListener('lostpointercapture', stop);
  canvas.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    view.auto = false;
    if (event.key === 'ArrowLeft') view.yaw -= .15;
    if (event.key === 'ArrowRight') view.yaw += .15;
    if (event.key === 'ArrowUp') view.pitch = Math.min(1.15, view.pitch + .1);
    if (event.key === 'ArrowDown') view.pitch = Math.max(-.35, view.pitch - .1);
  });
}
function createModelRenderer() {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl', { alpha: true, antialias: true, premultipliedAlpha: false, preserveDrawingBuffer: true });
  if (!gl) return null;
  const program = gl.createProgram();
  const shaders = [
    [gl.VERTEX_SHADER, `
      attribute vec3 position;
      attribute vec3 normal;
      attribute vec3 color;
      uniform vec4 rotation;
      uniform vec3 projection;
      varying vec3 tint;
      vec3 turn(vec3 p) {
        float x = rotation.x * p.x - rotation.y * p.y;
        float y = rotation.y * p.x + rotation.x * p.y;
        return vec3(x, rotation.z * p.z - rotation.w * y, rotation.w * p.z + rotation.z * y);
      }
      void main() {
        vec3 p = turn(position);
        gl_Position = vec4(p.x * projection.x, p.y * projection.y + projection.z, -p.z * .9, 1.);
        float shade = .48 + .52 * max(0., dot(turn(normal), vec3(-.35, .65, .65)));
        tint = color * shade;
      }`],
    [gl.FRAGMENT_SHADER, 'precision mediump float; varying vec3 tint; void main() { gl_FragColor = vec4(tint, 1.); }']
  ];
  for (const [type, source] of shaders) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
    gl.attachShader(program, shader);
    gl.deleteShader(shader);
  }
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  gl.enable(gl.DEPTH_TEST);
  gl.clearColor(0, 0, 0, 0);
  return { canvas, gl, attributes: ['position', 'normal', 'color'].map(name => gl.getAttribLocation(program, name)),
    rotation: gl.getUniformLocation(program, 'rotation'), projection: gl.getUniformLocation(program, 'projection') };
}
const modelRenderer = createModelRenderer();
function drawModel(view, context, width, height) {
  if (!modelRenderer) {
    context.fillStyle = '#718264';
    context.font = '12px sans-serif';
    context.textAlign = 'center';
    context.fillText('3D preview requires WebGL. Download the GLB to inspect.', width / 2, height / 2, width * .9);
    return;
  }
  const { gl, canvas, attributes, rotation, projection } = modelRenderer;
  const key = [width, height, view.yaw, view.pitch, view.zoom].join('/');
  if (view.renderKey !== key) {
    if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
    gl.viewport(0, 0, width, height);
    if (!view.buffer) {
      const mesh = view.data;
      const vertices = new Float32Array(mesh.faces.length * 27);
      let offset = 0;
      mesh.faces.forEach((face, index) => face.forEach(vertex => {
        vertices.set(mesh.vertices[vertex], offset);
        vertices.set(mesh.normals[index], offset + 3);
        vertices.set(mesh.colors[index].slice(0, 3).map(channel => channel / 255), offset + 6);
        offset += 9;
      }));
      view.buffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, view.buffer);
      gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    } else gl.bindBuffer(gl.ARRAY_BUFFER, view.buffer);
    attributes.forEach((location, index) => {
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location, 3, gl.FLOAT, false, 36, index * 12);
    });
    const scale = Math.min(width, height) * (view.hero ? .78 : .76) * view.zoom;
    gl.uniform4f(rotation, Math.cos(view.yaw), Math.sin(view.yaw), Math.cos(view.pitch), Math.sin(view.pitch));
    gl.uniform3f(projection, 2 * scale / width, 2 * scale / height, 1 - 2 * (view.hero ? .47 : .51));
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLES, 0, view.data.faces.length * 3);
    view.rendered ||= document.createElement('canvas');
    view.rendered.width = width; view.rendered.height = height;
    const cached = view.rendered.getContext('2d');
    cached.fillStyle = view.hero ? '#091e1445' : '#334b2220';
    cached.beginPath();
    cached.ellipse(width / 2, height * .85, scale * .34, scale * .045, 0, 0, 2 * Math.PI);
    cached.fill();
    cached.drawImage(canvas, 0, 0);
    view.renderKey = key;
  }
  context.drawImage(view.rendered, 0, 0);
}
function drawVFX(view, context, width, height) {
  const asset = view.asset;
  const index = Math.floor(view.time * asset.fps) % asset.frames;
  const size = Math.min(width, height) * .9;
  context.drawImage(view.data, (index % asset.columns) * asset.frameSize, Math.floor(index / asset.columns) * asset.frameSize,
    asset.frameSize, asset.frameSize, (width - size) / 2, (height - size) / 2, size, size);
  if (view.counter) view.counter.textContent = `${String(index + 1).padStart(2, '0')} / ${asset.frames} FRAMES`;
  if (view.scrubber) view.scrubber.value = String(index);
}
function drawWave(view, context, width, height) {
  const bins = view.data;
  const progress = state.activeAudio === view.asset.id && Number.isFinite(audio.duration) ? audio.currentTime / audio.duration : 0;
  const left = width * .09, span = width * .82, gap = span / bins.length;
  bins.forEach((value, index) => {
    const bar = Math.max(3, value * height * .35);
    context.fillStyle = index / bins.length < progress ? '#557545' : '#b2ba8c';
    context.fillRect(left + index * gap, (height - bar) / 2, Math.max(1, gap * .57), bar);
  });
  if (progress > 0) { context.fillStyle = '#8ca966'; context.fillRect(0, height - 3, width * progress, 3); }
}
let previousFrame = 0;
let lastDraw = 0;
function animate(time) {
  requestAnimationFrame(animate);
  const delta = previousFrame ? Math.min((time - previousFrame) / 1000, .06) : 0;
  previousFrame = time;
  if (time - lastDraw < 1000 / 30) return;
  const step = lastDraw ? Math.min((time - lastDraw) / 1000, .1) : delta;
  lastDraw = time;
  for (const [canvas, view] of views) {
    if (!canvas.isConnected) {
      if (view.buffer) modelRenderer.gl.deleteBuffer(view.buffer);
      views.delete(canvas); continue;
    }
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || (view.drawn && (rect.bottom < 0 || rect.top > innerHeight))) continue;
    const [width, height] = fitCanvas(canvas);
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, width, height);
    if (!view.data) {
      context.font = `${Math.max(11, width / 40)}px monospace`;
      context.fillStyle = view.hero ? '#abc597' : '#869577';
      context.textAlign = 'center';
      context.fillText(view.error ? 'Preview unavailable' : 'Preparing preview…', width / 2, height / 2);
      continue;
    }
    if (!state.motionPaused && !view.paused) {
      view.time += step;
      if (view.kind === '3d' && (view.auto || (!view.interactive && view.hover)) && !view.dragging) view.yaw += step * .2;
    }
    if (view.kind === '3d') drawModel(view, context, width, height);
    if (view.kind === 'vfx') drawVFX(view, context, width, height);
    if (view.kind === 'sfx') drawWave(view, context, width, height);
    view.drawn = true;
  }
}
requestAnimationFrame(animate);

function createAudioVisual(asset, stage) {
  const canvas = element('canvas');
  canvas.setAttribute('aria-label', `${asset.name} waveform`);
  stage.append(canvas);
  attachPreview(canvas, asset);
  const play = button('', 'audio-play', () => toggleAudio(asset), 'play');
  play.dataset.play = asset.id;
  play.setAttribute('aria-label', `Play ${asset.name}`);
  stage.append(play, element('span', 'audio-duration', `${asset.duration.toFixed(2)} SEC / 48 KHZ`));
  updateAudioButtons();
}
async function toggleAudio(asset) {
  const request = ++playbackRequest;
  if (state.activeAudio === asset.id && !audio.paused) { audio.pause(); return; }
  if (state.activeAudio !== asset.id) {
    audio.pause();
    state.activeAudio = asset.id;
    audio.src = localPath(asset.file);
  }
  try { await audio.play(); }
  catch (error) { if (request === playbackRequest && error.name !== 'AbortError') notify('Audio could not play. Try downloading the WAV file.'); }
  updateAudioButtons();
}
function updateAudioButtons() {
  document.querySelectorAll('[data-play]').forEach(node => {
    const asset = state.assets.find(item => item.id === node.dataset.play);
    const playing = state.activeAudio === node.dataset.play && !audio.paused;
    node.replaceChildren(icon(playing ? 'pause' : 'play'));
    node.setAttribute('aria-label', `${playing ? 'Pause' : 'Play'} ${asset?.name || 'audio'}`);
    node.setAttribute('aria-pressed', String(playing));
  });
}
['play', 'pause', 'ended', 'error'].forEach(event => audio.addEventListener(event, updateAudioButtons));
audio.volume = .65;

function renderGrid() {
  const grid = $('#asset-grid');
  grid.replaceChildren();
  const collection = state.assets.filter(asset => state.collection === 'all' || state.collection === asset.collection);
  document.querySelectorAll('[data-count]').forEach(node => {
    node.textContent = node.dataset.count === 'all' ? collection.length : collection.filter(asset => asset.category === node.dataset.count).length;
  });
  const selected = collection.filter(asset => (state.category === 'all' || state.category === asset.category)
    && `${asset.name} ${asset.description} ${asset.tags.join(' ')} ${labels[asset.category]}`.toLowerCase().includes(state.search));
  $('#empty-state').hidden = selected.length > 0;
  $('#result-count').textContent = `${selected.length} ${selected.length === 1 ? 'asset' : 'assets'}${state.search ? ' found' : ' to explore'}`;
  for (const asset of selected) {
    const card = element('article', 'asset-card');
    card.dataset.asset = asset.id;
    const visual = asset.category === 'sfx' ? element('div', `asset-visual category-${asset.category}`)
      : button('', `asset-visual category-${asset.category}`, () => openInspector(asset));
    if (asset.category !== 'sfx') visual.setAttribute('aria-label', `Inspect ${asset.name}`);
    const label = asset.category === '3d' ? 'DRAG IN INSPECTOR' : asset.category === '2d' ? (asset.nineSlice ? '9-SLICE UI / PNG' : asset.stats.Tiling === 'XY periodic' ? 'SEAMLESS TILE / PNG' : 'TRANSPARENT / PNG') : asset.category === 'vfx' ? `${asset.frames} FRAMES / ${asset.loop ? 'LOOP' : 'ONE-SHOT'}` : 'PROCEDURAL AUDIO';
    visual.append(element('span', 'visual-label', label));
    if (asset.category === '2d') {
      const image = element('img');
      image.src = localPath(asset.preview || asset.file);
      image.alt = asset.name;
      image.loading = 'lazy';
      visual.append(image);
    } else if (asset.category === 'sfx') { createAudioVisual(asset, visual); }
    else {
      const canvas = element('canvas');
      canvas.setAttribute('aria-hidden', 'true');
      visual.append(canvas);
      attachPreview(canvas, asset);
    }
    if (asset.category !== 'sfx') visual.append(element('span', 'inspect-hint', 'Inspect asset ↗'));
    const body = element('div', 'asset-body');
    const category = element('div', 'card-category', labels[asset.category].toUpperCase());
    category.dataset.kind = asset.category;
    const title = button(asset.name, 'title-button', () => openInspector(asset));
    const footer = element('div', 'asset-card-footer');
    const download = element('a', 'asset-download');
    download.href = localPath(asset.file);
    download.download = '';
    download.setAttribute('aria-label', `Download ${asset.name}`);
    download.append(icon('down'));
    footer.append(element('span', 'asset-meta', asset.meta), download);
    body.append(category, title, element('p', 'asset-description', asset.description), footer);
    card.append(visual, body);
    grid.append(card);
  }
  updateAudioButtons();
}
function setCategory(category) {
  state.category = category;
  document.querySelectorAll('[data-category]').forEach(node => {
    const active = node.dataset.category === category;
    node.classList.toggle('active', active);
    node.setAttribute('aria-pressed', String(active));
  });
  renderGrid();
}
document.querySelectorAll('[data-category]').forEach(node => node.addEventListener('click', () => {
  setCategory(node.dataset.category);
  if (node.closest('.side-nav')) $('#collection').scrollIntoView({ behavior: reducedMotion.matches ? 'instant' : 'smooth' });
}));
$('#search').addEventListener('input', event => { state.search = event.target.value.trim().toLowerCase(); renderGrid(); });
$('#collection-select').addEventListener('change', event => { state.collection = event.target.value; renderGrid(); });
$('#clear-filters').addEventListener('click', () => {
  state.search = ''; state.collection = 'all'; $('#search').value = ''; $('#collection-select').value = 'all'; setCategory('all');
});
function updateMotionButton() {
  $('#motion-toggle').setAttribute('aria-pressed', String(state.motionPaused));
  $('#motion-toggle').replaceChildren(icon(state.motionPaused ? 'play' : 'pause'), element('span', '', state.motionPaused ? 'Resume motion' : 'Pause motion'));
}
$('#motion-toggle').addEventListener('click', () => { state.motionPaused = !state.motionPaused; updateMotionButton(); });
updateMotionButton();

function openInspector(asset) {
  state.selected = asset;
  $('#dialog-title').textContent = asset.name;
  $('#dialog-category').textContent = `${labels[asset.category].toUpperCase()} / SEED ${String(asset.seed).padStart(3, '0')}`;
  $('#dialog-description').textContent = asset.description;
  $('#dialog-tags').replaceChildren(...asset.tags.map(tag => element('span', '', tag)));
  $('#dialog-stats').replaceChildren();
  Object.entries(asset.stats).forEach(([key, value]) => $('#dialog-stats').append(element('dt', '', key), element('dd', '', String(value))));
  $('#asset-download').href = localPath(asset.file);
  $('#recipe-link').href = localPath(asset.recipe);
  $('#manifest-link').href = localPath(asset.manifest);
  $('#inspector-note').textContent = asset.category === '3d' ? 'Depth-buffered, flat-shaded preview of exported geometry. No UVs, rigging, or engine certification.'
    : asset.category === 'vfx' ? `${asset.loop ? 'Seamless loop' : 'One-shot, replayed here for inspection'}. The downloadable PNG contains all ${asset.frames} frames.`
    : asset.category === 'sfx' ? 'Synthesized locally, not sampled. Preview at a comfortable volume; no audio starts automatically.'
    : 'Original RGBA export. Backgrounds in this inspector are for preview only.';
  $('#asset-review').hidden = !asset.review;
  $('#asset-review').textContent = asset.review ? `Review target: ${asset.review}` : '';
  const stage = $('#inspector-stage');
  const controls = $('#preview-controls');
  stage.replaceChildren();
  controls.replaceChildren();
  $('.inspector-view').classList.toggle('dark', asset.category === 'vfx');
  if (asset.category === '2d') {
    const image = element('img');
    image.src = localPath(asset.file);
    image.alt = asset.name;
    stage.append(image);
    const background = button('Dark background', '', () => {
      const dark = $('.inspector-view').classList.toggle('dark');
      background.lastElementChild.textContent = dark ? 'Light background' : 'Dark background';
    }, 'image');
    controls.append(background);
    if (asset.panelPreview) {
      let wide = false;
      const panel = button('Test wide 9-slice', '', () => {
        wide = !wide;
        image.src = localPath(wide ? asset.panelPreview : asset.file);
        panel.lastElementChild.textContent = wide ? 'Show source panel' : 'Test wide 9-slice';
      }, 'sliders');
      controls.append(panel);
    }
  } else if (asset.category === 'sfx') {
    createAudioVisual(asset, stage);
    const volume = element('label', '', 'Volume');
    const slider = element('input');
    slider.type = 'range'; slider.min = '0'; slider.max = '1'; slider.step = '.05'; slider.value = String(audio.volume);
    slider.setAttribute('aria-label', 'Audio volume');
    slider.addEventListener('input', () => { audio.volume = Number(slider.value); });
    volume.append(slider);
    controls.append(volume);
  } else {
    const canvas = element('canvas');
    canvas.setAttribute('aria-label', asset.category === '3d' ? `${asset.name}. Drag or use arrow keys to rotate.` : `${asset.name} animated preview`);
    stage.append(canvas);
    const view = attachPreview(canvas, asset, { interactive: asset.category === '3d', auto: asset.category === '3d', modal: true });
    if (asset.category === '3d') {
      controls.append(button('Reset view', '', () => { view.yaw = asset.yaw ?? .65; view.pitch = .3; view.zoom = 1; slider.value = '1'; }, 'refresh'));
      const zoom = element('label', '', 'Zoom');
      const slider = element('input');
      slider.type = 'range'; slider.min = '.65'; slider.max = '1.4'; slider.step = '.05'; slider.value = '1';
      slider.setAttribute('aria-label', 'Model zoom');
      slider.addEventListener('input', () => { view.zoom = Number(slider.value); });
      zoom.append(slider);
      controls.append(zoom);
    } else {
      const play = button(state.motionPaused ? 'Play' : 'Pause', '', () => {
        if (state.motionPaused) { state.motionPaused = false; updateMotionButton(); view.paused = false; }
        else view.paused = !view.paused;
        play.replaceChildren(icon(view.paused ? 'play' : 'pause'), element('span', '', view.paused ? 'Play' : 'Pause'));
      }, state.motionPaused ? 'play' : 'pause');
      view.counter = element('span', 'frame-counter');
      const frame = element('input');
      frame.type = 'range'; frame.min = '0'; frame.max = String(asset.frames - 1); frame.value = '0';
      frame.setAttribute('aria-label', 'Animation frame');
      view.scrubber = frame;
      frame.addEventListener('input', () => {
        view.time = Number(frame.value) / asset.fps;
        view.paused = true;
        play.replaceChildren(icon('play'), element('span', '', 'Play'));
      });
      const background = button('Light background', 'background-toggle', () => {
        const dark = $('.inspector-view').classList.toggle('dark');
        background.lastElementChild.textContent = dark ? 'Light background' : 'Dark background';
      }, 'image');
      controls.append(play, frame, view.counter, background);
    }
  }
  if (!dialog.open) dialog.showModal();
  $('#close-dialog').focus();
}
document.querySelectorAll('[data-review-asset]').forEach(node => node.addEventListener('click', () => {
  const asset = state.assets.find(item => item.id === node.dataset.reviewAsset);
  if (asset) openInspector(asset);
}));
$('#close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => {
  const bounds = dialog.getBoundingClientRect();
  if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
});
dialog.addEventListener('close', () => {
  if (state.selected?.category === 'sfx') audio.pause();
  $('#inspector-stage').replaceChildren();
  state.selected = null;
});
$('#copy-command').addEventListener('click', async () => {
  const asset = state.selected;
  if (!asset) return;
  const expansion = asset.collection === 'expansion';
  const command = `.venv-code-assets/bin/python ${localPath(asset.recipe)} --out ${expansion ? 'gallery-expansion-next' : 'gallery-next'}${expansion ? ` --seed ${asset.seed}` : ''}`;
  try { await navigator.clipboard.writeText(command); notify('Generation command copied. It creates a new collection.'); }
  catch { notify(`Run: ${command}`); }
});
document.addEventListener('keydown', event => {
  if (event.key === '/' && !dialog.open && !event.ctrlKey && !event.metaKey && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
    event.preventDefault(); $('#search').focus();
  }
});

async function loadCollection() {
  $('#load-error').hidden = true;
  $('#result-count').textContent = 'Loading the collection…';
  try {
    const [original, expansion] = await Promise.all([fetchJSON('gallery/catalog.json'), fetchJSON('gallery/expansion/catalog.json')]);
    const assets = [];
    for (const [catalog, collection] of [[expansion, 'expansion'], [original, 'original']]) {
      if (!Array.isArray(catalog.assets) || !catalog.assets.length) throw new Error('No assets in catalog');
      catalog.assets.forEach(asset => {
        if (!['3d', '2d', 'vfx', 'sfx'].includes(asset.category) || !Array.isArray(asset.tags)) throw new Error('Invalid asset metadata');
        ['file', 'recipe', 'manifest', 'preview', 'model', 'atlas', 'panelPreview'].forEach(key => { if (asset[key]) localPath(asset[key]); });
        assets.push({ ...asset, collection });
      });
    }
    if (new Set(assets.map(asset => asset.id)).size !== assets.length) throw new Error('Duplicate asset identifiers');
    state.assets = assets;
    $('#total-stat').textContent = String(assets.length).padStart(2, '0');
    $('#demonstrated-count').textContent = assets.length;
    for (const option of $('#collection-select').options) {
      const count = option.value === 'all' ? assets.length : assets.filter(asset => asset.collection === option.value).length;
      const name = option.value === 'all' ? 'All studies' : option.value === 'expansion' ? 'New gameplay studies' : 'Original collection';
      option.textContent = `${name} · ${count}`;
    }
    const hero = state.assets.find(asset => asset.id === 'crystal-cluster');
    if (hero) attachPreview($('#hero-model'), hero, { auto: true, interactive: true, hero: true, pitch: .28 });
    renderGrid();
  } catch (error) {
    $('#asset-grid').replaceChildren();
    $('#empty-state').hidden = true;
    $('#load-error').hidden = false;
    $('#result-count').textContent = 'Collection unavailable';
    console.error('Gallery load failed:', error.message);
  }
}
$('#retry-load').addEventListener('click', loadCollection);
loadCollection();
