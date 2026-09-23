(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('graph-data').textContent);
  const byId = new Map(data.nodes.map(node => [node.id, node]));
  const adjacency = new Map(data.nodes.map(node => [node.id, []]));
  data.edges.forEach(edge => {
    adjacency.get(edge.from).push({ other: edge.to, edge });
    adjacency.get(edge.to).push({ other: edge.from, edge });
  });
  const $ = id => document.getElementById(id);
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const relationColors = { friend: '#38e66f', rival: '#ff4b4b', related: '#8b9d9b', mixed: '#d9b278' };
  const state = { mode: 'focus', selected: byId.has('Garen') ? 'Garen' : data.nodes[0].id, region: '', relation: 'all', prompt: '', hidden: new Set(), ready: false, visible: [], regionLayout: null };

  $('champion-list').replaceChildren(...data.nodes.map(node => {
    const option = document.createElement('option'); option.value = node.id; return option;
  }));
  const regions = [...new Set(data.nodes.map(node => node.faction).filter(Boolean))].sort();
  $('region-select').append(...regions.map(region => {
    const option = document.createElement('option'); option.value = region; option.textContent = region; return option;
  }));

  if (!window.vis || !window.vis.Network) {
    $('graph-loading').textContent = 'The graph library could not load. The connection list is still available.';
    renderDetails();
    return;
  }
  const nodes = new vis.DataSet(data.nodes.map(node => ({
    id: node.id, label: node.id, title: `${node.id} · ${node.faction || 'Region unknown'} · Double-click for League Universe`,
    image: node.image ? data.imagePrefix + node.image : undefined,
    shape: node.image ? 'circularImage' : 'dot', size: Math.min(31, 22 + Math.sqrt(adjacency.get(node.id).length) * 2),
    borderWidth: 2, color: { border: '#bba272', background: '#bba272', highlight: { border: '#f5d58c', background: '#bba272' }, hover: { border: '#f5d58c' } },
    font: { color: '#f4f0e8', size: 14, face: 'Arial', strokeWidth: 4, strokeColor: '#172326' }
  })));
  const edges = new vis.DataSet(data.edges.map((edge, index) => ({
    id: index, from: edge.from, to: edge.to, relation: edge.relation,
    color: { color: relationColors[edge.relation], highlight: relationColors[edge.relation], hover: relationColors[edge.relation], opacity: edge.relation === 'related' ? 0.45 : 1 },
    width: edge.relation === 'related' ? 1 : 2.5,
    dashes: edge.relation === 'rival' ? [6, 5] : edge.relation === 'mixed' ? [2, 5] : false,
    title: edge.relation === 'mixed' ? 'Friend + rival: both labels appear in the source' : edge.relation
  })));
  const network = new vis.Network($('network'), { nodes, edges }, {
    layout: { randomSeed: 42, improvedLayout: true },
    interaction: { hover: true, hoverConnectedEdges: false, selectConnectedEdges: false, hideEdgesOnDrag: true, hideEdgesOnZoom: true, tooltipDelay: 160, keyboard: { enabled: true, bindToWindow: false } },
    physics: { stabilization: { enabled: true, iterations: 220, updateInterval: 50 }, barnesHut: { gravitationalConstant: -3200, springLength: 130, springConstant: 0.012, damping: 0.15 } },
    edges: { smooth: { type: 'continuous', roundness: 0.12 }, selectionWidth: 2 },
    nodes: { shadow: false }
  });
  network.on('beforeDrawing', context => {
    if (state.mode !== 'region' || !state.regionLayout) return;
    context.save();
    state.regionLayout.groups.forEach((group, index) => {
      context.beginPath();
      context.arc(group.x, group.y, group.radius, 0, 2 * Math.PI);
      context.fillStyle = index === 0 ? 'rgba(233, 188, 116, 0.045)' : 'rgba(152, 170, 169, 0.035)';
      context.fill();
      context.setLineDash([5, 9]);
      context.lineWidth = index === 0 ? 2 : 1.5;
      context.strokeStyle = index === 0 ? 'rgba(233, 188, 116, 0.62)' : 'rgba(174, 191, 186, 0.44)';
      context.stroke();
      context.setLineDash([]);
      context.fillStyle = index === 0 ? '#e9bc74' : '#bdc9c2';
      context.font = '600 20px Georgia, serif';
      context.textAlign = 'center';
      context.fillText(group.region.toUpperCase(), group.x, group.y - group.radius - 17);
    });
    context.restore();
  });

  let settled = false;
  let layoutKey = '';
  let lastSelected = '';
  const layoutCache = new Map();
  let activeMotion = null;
  function finishLayout() {
    if (settled) return;
    settled = true;
    network.stopSimulation();
    network.setOptions({ physics: false });
    state.ready = true;
    $('graph-loading').classList.add('is-hidden');
    render();
  }
  network.once('stabilizationIterationsDone', finishLayout);
  network.stabilize(220);
  window.setTimeout(finishLayout, 6000);

  function matching(edge) { return state.relation === 'all' || edge.relation === state.relation; }
  function buildRegionLayout() {
    const primary = data.nodes.filter(node => node.faction === state.region && !state.hidden.has(node.id)).map(node => node.id);
    const primarySet = new Set(primary);
    const candidates = new Map();
    data.edges.forEach(edge => {
      if (!matching(edge) || state.hidden.has(edge.from) || state.hidden.has(edge.to)) return;
      const target = primarySet.has(edge.from) ? edge.to : primarySet.has(edge.to) ? edge.from : '';
      if (!target || primarySet.has(target)) return;
      const region = byId.get(target).faction;
      if (!region) return;
      const entry = candidates.get(region) || { score: 0, targets: new Map() };
      const weight = edge.evidence.includes('related') ? 3 : edge.relation === 'friend' ? 2 : 1;
      entry.score += weight;
      entry.targets.set(target, (entry.targets.get(target) || 0) + weight);
      candidates.set(region, entry);
    });
    const neighborLimit = window.matchMedia('(max-width: 760px)').matches ? 1 : 2;
    const neighbors = [...candidates].sort((a, b) => b[1].score - a[1].score || a[0].localeCompare(b[0])).slice(0, neighborLimit);
    const groups = [{ region: state.region, ids: primary }, ...neighbors.map(([region, entry]) => ({
      region, ids: [...entry.targets].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 8).map(([id]) => id)
    }))];
    groups.forEach((group, index) => {
      group.radius = 115 + 31 * Math.sqrt(group.ids.length);
      if (index === 0) { group.x = 0; group.y = 0; }
      else {
        group.x = groups[0].radius + group.radius + 115;
        group.y = index === 1 ? -group.radius - 75 : group.radius + 75;
      }
    });
    const positions = [];
    groups.forEach(group => {
      const ordered = [...group.ids].sort((a, b) => adjacency.get(b).length - adjacency.get(a).length || a.localeCompare(b));
      if (group.region === state.region && ordered.includes(state.selected)) ordered.splice(ordered.indexOf(state.selected), 1), ordered.unshift(state.selected);
      if (ordered.length) positions.push({ id: ordered[0], x: group.x, y: group.y });
      let start = 1;
      const rings = ordered.length <= 16 ? [[15, group.radius - 45]] : [[8, 96], [24, group.radius - 45]];
      for (const [capacity, radius] of rings) {
        const count = Math.min(capacity, ordered.length - start);
        if (count <= 0) break;
        for (let index = 0; index < count; index++) {
          const angle = -Math.PI / 2 + 2 * Math.PI * index / count;
          positions.push({ id: ordered[start + index], x: group.x + radius * Math.cos(angle), y: group.y + radius * Math.sin(angle) });
        }
        start += count;
      }
    });
    return { groups, positions, visible: new Set(groups.flatMap(group => group.ids)) };
  }
  function visibleIds() {
    const result = state.mode === 'all' ? new Set(byId.keys()) :
      state.mode === 'region' ? (state.regionLayout = buildRegionLayout()).visible :
      new Set([state.selected]);
    if (state.mode !== 'region') state.regionLayout = null;
    if (state.mode === 'focus') adjacency.get(state.selected).forEach(({ other, edge }) => { if (matching(edge)) result.add(other); });
    state.hidden.forEach(id => result.delete(id));
    return result;
  }
  function placeSolos(connected, solo, fullView) {
    if (!solo.length) return;
    const positions = connected.length ? network.getPositions(connected) : {};
    const center = connected.length ? connected.reduce((point, id) => ({ x: point.x + positions[id].x / connected.length, y: point.y + positions[id].y / connected.length }), { x: 0, y: 0 }) : { x: 0, y: 0 };
    const extent = connected.length ? Math.max(...connected.map(id => Math.hypot(positions[id].x - center.x, positions[id].y - center.y))) : 0;
    const baseRadius = Math.min(fullView ? 650 : 480, Math.max(200, extent + 105));
    const soloPositions = [];
    let placed = 0;
    let ring = 0;
    while (placed < solo.length) {
      const radius = connected.length ? baseRadius + ring * 130 : ring * 140;
      const capacity = ring === 0 && !connected.length ? 1 : Math.max(1, Math.floor(2 * Math.PI * radius / 115));
      const count = Math.min(capacity, solo.length - placed);
      for (let index = 0; index < count; index++) {
        const angle = 2 * Math.PI * index / count - Math.PI / 2;
        soloPositions.push({ id: solo[placed++], x: center.x + radius * Math.cos(angle), y: center.y + radius * Math.sin(angle) });
      }
      ring++;
    }
    nodes.update(soloPositions);
  }
  function finishMotion(motion, refit = true) {
    if (activeMotion !== motion) return;
    window.clearTimeout(motion.timer);
    activeMotion = null;
    network.stopSimulation();
    network.setOptions({ physics: false });
    placeSolos(motion.connected, motion.solo, motion.fullView);
    layoutCache.set(motion.key, network.getPositions(motion.visible));
    if (layoutCache.size > 24) layoutCache.delete(layoutCache.keys().next().value);
    if (refit && layoutKey === motion.key) network.fit({ nodes: motion.visible, animation: { duration: 220, easingFunction: 'easeInOutQuad' } });
  }
  function renderGraph() {
    const visible = visibleIds();
    if (state.mode === 'region' && !visible.has(state.selected) && visible.size) state.selected = state.regionLayout.groups[0].ids[0] || visible.values().next().value;
    state.visible = [...visible];
    const nodeAppearance = node => ({ id: node.id, label: state.mode === 'all' && adjacency.get(node.id).length < 12 && node.id !== state.selected ? '' : node.id,
      borderWidth: node.id === state.selected ? 5 : 2, color: { border: node.id === state.selected ? '#f5d58c' : '#bba272' } });
    const showEdge = edge => visible.has(edge.from) && visible.has(edge.to) && matching(edge) &&
      (state.mode !== 'focus' || edge.from === state.selected || edge.to === state.selected);
    const fullView = state.mode === 'all';
    $('explorer-grid').classList.toggle('is-full', fullView || state.mode === 'region');
    const nextLayoutKey = [state.mode, state.mode === 'focus' ? state.selected : state.region, state.relation, state.visible.join('|')].join(':');
    const layoutChanged = nextLayoutKey !== layoutKey;
    const selectionChanged = state.selected !== lastSelected;
    if (layoutChanged) {
      if (activeMotion) finishMotion(activeMotion, false);
      layoutKey = nextLayoutKey;
      network.stopSimulation();
      network.setOptions({ physics: false });
      nodes.update(data.nodes.map(node => ({ ...nodeAppearance(node), hidden: !visible.has(node.id) })));
      edges.update(data.edges.map((edge, id) => ({ id, hidden: !showEdge(edge),
        title: fullView ? '' : edge.relation === 'mixed' ? 'Friend + rival: both labels appear in the source' : edge.relation })));
      network.setOptions({ interaction: { hover: !fullView, dragNodes: state.mode !== 'region' }, edges: { smooth: state.mode === 'focus' } });
      const cachedPositions = layoutCache.get(nextLayoutKey);
      if (state.mode === 'region') {
        nodes.update(state.regionLayout.positions.map(position => ({ ...position, physics: false, fixed: true })));
      } else if (cachedPositions) {
        nodes.update(state.visible.map(id => ({ id, ...cachedPositions[id], physics: false, fixed: false })));
      } else {
        const degree = new Map(state.visible.map(id => [id, 0]));
        data.edges.filter(showEdge).forEach(edge => {
          degree.set(edge.from, degree.get(edge.from) + 1);
          degree.set(edge.to, degree.get(edge.to) + 1);
        });
        const connected = state.visible.filter(id => degree.get(id) > 0);
        const solo = state.visible.filter(id => degree.get(id) === 0).sort((a, b) => a === state.selected ? -1 : b === state.selected ? 1 : a.localeCompare(b));
        nodes.update(data.nodes.map(node => ({ id: node.id, physics: visible.has(node.id) && degree.get(node.id) > 0,
          fixed: solo.includes(node.id) })));
        const animateFull = fullView && !reducedMotion && connected.length > 20;
        if (animateFull) {
          const positions = network.getPositions(connected);
          const center = connected.reduce((point, id) => ({ x: point.x + positions[id].x / connected.length, y: point.y + positions[id].y / connected.length }), { x: 0, y: 0 });
          nodes.update(connected.map(id => ({ id, x: center.x + (positions[id].x - center.x) * 0.62,
            y: center.y + (positions[id].y - center.y) * 0.62 })));
          placeSolos(connected, solo, fullView);
        }
        network.setOptions({ physics: {
          enabled: true,
          stabilization: { enabled: !animateFull, iterations: fullView ? 180 : 140 },
          barnesHut: { gravitationalConstant: fullView ? -7000 : state.mode === 'region' ? -6500 : -5000, centralGravity: fullView ? 0.08 : state.mode === 'region' ? 0.08 : 0.11,
            springLength: fullView ? 190 : state.mode === 'region' ? 180 : 160, springConstant: 0.012,
            damping: fullView ? 0.17 : 0.2, avoidOverlap: 0.65 },
          maxVelocity: 18, minVelocity: 0.4
        } });
        if (animateFull) {
          const motion = { key: nextLayoutKey, visible: [...state.visible], connected, solo, fullView, timer: 0 };
          activeMotion = motion;
          motion.timer = window.setTimeout(() => finishMotion(motion), 1100);
          network.startSimulation();
        } else {
          network.stabilize(fullView ? 180 : 140);
          placeSolos(connected, solo, fullView);
          network.stopSimulation();
          network.setOptions({ physics: false });
          layoutCache.set(nextLayoutKey, network.getPositions(state.visible));
          if (layoutCache.size > 24) layoutCache.delete(layoutCache.keys().next().value);
        }
      }
    } else if (selectionChanged) {
      nodes.update([lastSelected, state.selected].filter(id => byId.has(id)).map(id => nodeAppearance(byId.get(id))));
    }
    const edgeCount = data.edges.filter(showEdge).length;
    $('graph-title').textContent = state.mode === 'all' ? 'The full network' : state.mode === 'region' ? `${state.region} · region map` : `${state.selected}’s connections`;
    const bridgeGroups = state.prompt === 'bridge' && !fullView ? new Set([byId.get(state.selected).community, ...adjacency.get(state.selected).map(({ other }) => byId.get(other).community)]).size : 0;
    $('graph-summary').textContent = state.mode === 'region' ? `${state.regionLayout.groups[0].ids.length} in ${state.region} · connected champions from ${state.regionLayout.groups.slice(1).map(group => group.region).join(' & ') || 'no other region'} · ${edgeCount} links` :
      `${visible.size} champion${visible.size === 1 ? '' : 's'} · ${edgeCount} visible connection${edgeCount === 1 ? '' : 's'}` + (state.hidden.size ? ` · ${state.hidden.size} hidden` : '') + (state.mode === 'focus' ? bridgeGroups ? ` · Spans ${bridgeGroups} detected groups` : '' : ` · Selected: ${state.selected}`);
    $('focus-selected').hidden = state.mode === 'focus';
    $('focus-selected').textContent = `${state.selected}’s connections →`;
    $('view-neighbors').classList.toggle('is-active', state.mode === 'focus');
    $('view-region').classList.toggle('is-active', state.mode === 'region');
    $('view-all').classList.toggle('is-active', state.mode === 'all');
    if (layoutChanged || selectionChanged) network.selectNodes(visible.has(state.selected) ? [state.selected] : []);
    lastSelected = state.selected;
    if (layoutChanged) window.requestAnimationFrame(() => { network.redraw(); fitVisible(); });
  }
  function fitVisible() {
    if (!state.ready || !state.visible.length) return;
    if (state.mode === 'region' && state.regionLayout) {
      const groups = state.regionLayout.groups;
      const minX = Math.min(...groups.map(group => group.x - group.radius - 45));
      const maxX = Math.max(...groups.map(group => group.x + group.radius + 45));
      const minY = Math.min(...groups.map(group => group.y - group.radius - 70));
      const maxY = Math.max(...groups.map(group => group.y + group.radius + 45));
      const stage = $('network');
      const scale = Math.min(stage.clientWidth / (maxX - minX), stage.clientHeight / (maxY - minY));
      network.moveTo({ position: { x: (minX + maxX) / 2, y: (minY + maxY) / 2 }, scale,
        animation: reducedMotion ? false : { duration: 250, easingFunction: 'easeInOutQuad' } });
      return;
    }
    network.fit({ nodes: state.visible, animation: reducedMotion || state.mode === 'all' ? false : { duration: 250, easingFunction: 'easeInOutQuad' } });
  }
  function renderDetails() {
    const node = byId.get(state.selected);
    $('detail-title').textContent = node.id;
    $('detail-meta').textContent = [node.faction || 'Region unknown', node.role || 'Role unknown'].join(' · ');
    const source = $('detail-source'); source.href = node.url; source.hidden = !node.url;
    const image = $('detail-image'); image.hidden = !node.image; if (node.image) image.src = data.imagePrefix + node.image;
    const links = adjacency.get(node.id).filter(({ other, edge }) => !state.hidden.has(other) && matching(edge)).sort((a, b) => a.other.localeCompare(b.other));
    $('detail-count').textContent = `(${links.length})`;
    const list = $('connection-list'); list.replaceChildren();
    if (!links.length) { const empty = document.createElement('p'); empty.className = 'empty-note'; empty.textContent = 'No connections match this relationship filter.'; list.append(empty); }
    links.forEach(({ other, edge }) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'connection-item';
      const name = document.createElement('span'); name.textContent = other;
      const relation = document.createElement('span'); relation.textContent = edge.relation === 'mixed' ? 'Friend + rival' : edge.relation; relation.className = `relation-${edge.relation}`;
      button.append(name, relation); button.addEventListener('click', () => focus(other)); list.append(button);
    });
  }
  function renderHidden() {
    const names = [...state.hidden].sort((a, b) => a.localeCompare(b));
    $('hidden-list').replaceChildren(...names.map(name => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'hidden-chip'; button.textContent = `${name} ×`;
      button.setAttribute('aria-label', `Show ${name}`);
      button.addEventListener('click', () => { state.hidden.delete(name); $('hide-message').textContent = ''; render(); });
      return button;
    }));
    $('clear-hidden').hidden = names.length === 0;
  }
  function render() { renderHidden(); if (state.ready) renderGraph(); renderDetails(); }
  function focus(id, prompt = '') {
    if (!byId.has(id)) return;
    state.hidden.delete(id);
    state.selected = id; state.mode = 'focus'; state.prompt = prompt; $('champion-search').value = id;
    $('search-message').textContent = ''; $('hide-message').textContent = ''; render();
  }
  function findMatches(query) {
    const normalized = query.trim().toLocaleLowerCase();
    const exact = data.nodes.find(node => node.id.toLocaleLowerCase() === normalized);
    return !normalized ? [] : exact ? [exact] : data.nodes.filter(node => node.id.toLocaleLowerCase().includes(normalized));
  }
  $('champion-form').addEventListener('submit', event => {
    event.preventDefault();
    const matches = findMatches($('champion-search').value);
    if (!matches.length) { $('search-message').textContent = 'No champion found. Try another name.'; return; }
    if (matches.length > 1) { $('search-message').textContent = `${matches.length} names match. Choose a complete name from the suggestions.`; return; }
    focus(matches[0].id);
  });
  $('hide-form').addEventListener('submit', event => {
    event.preventDefault();
    const matches = findMatches($('hide-search').value);
    if (!matches.length) { $('hide-message').textContent = 'No champion found.'; return; }
    if (matches.length > 1) { $('hide-message').textContent = 'Choose a complete name.'; return; }
    const id = matches[0].id;
    if (state.hidden.has(id)) { $('hide-message').textContent = `${id} is already hidden.`; return; }
    if (state.hidden.size === data.nodes.length - 1) { $('hide-message').textContent = 'Keep at least one champion visible.'; return; }
    state.hidden.add(id);
    if (state.selected === id) {
      const next = adjacency.get(id).find(({ other }) => !state.hidden.has(other))?.other || data.nodes.find(node => !state.hidden.has(node.id)).id;
      state.selected = next; state.prompt = ''; $('champion-search').value = next;
      if (state.mode === 'region' && byId.get(next).faction !== state.region) state.mode = 'all';
    }
    $('hide-search').value = ''; $('hide-message').textContent = ''; render();
  });
  $('clear-hidden').addEventListener('click', () => { state.hidden.clear(); $('hide-message').textContent = ''; render(); });
  $('prompt-garen').addEventListener('click', () => focus(byId.has('Garen') ? 'Garen' : data.nodes[0].id));
  $('prompt-bridge').addEventListener('click', () => focus(data.bridge, 'bridge'));
  $('prompt-region').addEventListener('click', () => $('region-select').focus());
  function chooseRegion(event) {
    if (!event.target.value) return;
    const regionNodes = data.nodes.filter(node => node.faction === event.target.value && !state.hidden.has(node.id));
    if (!regionNodes.length) { $('hide-message').textContent = 'All champions in that region are hidden.'; return; }
    state.region = event.target.value;
    state.prompt = '';
    state.selected = regionNodes.sort((a, b) => adjacency.get(b.id).length - adjacency.get(a.id).length)[0].id;
    $('champion-search').value = '';
    $('search-message').textContent = '';
    state.mode = 'region'; render();
  }
  $('region-select').addEventListener('change', chooseRegion);
  $('region-select').addEventListener('input', chooseRegion);
  $('view-neighbors').addEventListener('click', () => { state.mode = 'focus'; render(); });
  $('view-region').addEventListener('click', () => { state.region = byId.get(state.selected).faction; $('region-select').value = state.region; state.mode = 'region'; render(); });
  $('view-all').addEventListener('click', () => { state.mode = 'all'; $('search-message').textContent = ''; render(); });
  function chooseRelation(event) { state.relation = event.target.value; render(); }
  $('relationship-filter').addEventListener('change', chooseRelation);
  $('relationship-filter').addEventListener('input', chooseRelation);
  $('fit-graph').addEventListener('click', () => { if (activeMotion) finishMotion(activeMotion, false); fitVisible(); });
  function zoom(factor) {
    if (activeMotion) finishMotion(activeMotion, false);
    network.moveTo({ position: network.getViewPosition(), scale: Math.max(0.08, Math.min(3, network.getScale() * factor)), animation: false });
  }
  $('zoom-out').addEventListener('click', () => zoom(1 / 1.35));
  $('zoom-in').addEventListener('click', () => zoom(1.35));
  $('focus-selected').addEventListener('click', () => focus(state.selected));
  network.on('click', params => { if (params.nodes.length) {
    if (activeMotion) finishMotion(activeMotion, false);
    const id = params.nodes[0];
    if (state.mode === 'focus') focus(id);
    else { state.selected = id; state.prompt = ''; renderDetails(); renderGraph(); }
  } });
  network.on('dragStart', () => { if (activeMotion) finishMotion(activeMotion, false); });
  network.on('doubleClick', params => { if (params.nodes.length) {
    const url = byId.get(params.nodes[0]).url;
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
  } });
  network.on('dragEnd', params => { if (params.nodes.length && layoutKey) layoutCache.set(layoutKey, network.getPositions(state.visible)); });
  renderHidden(); renderDetails();
})();
