// Offline DOM and mocked HTTP tests. No browser, bridge, token, or device I/O.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const html = fs.readFileSync(path.join(__dirname, 'remote_store.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase();
    this.children = []; this.attributes = new Map(); this.dataset = {};
    this.textContent = ''; this.value = ''; this.hidden = false; this.files = [];
    const classes = new Set();
    this.classList = {
      add: name => classes.add(name),
      toggle: (name, active) => active ? classes.add(name) : classes.delete(name),
      contains: name => classes.has(name),
    };
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  removeAttribute(name) { this.attributes.delete(name); if (name === 'value') this.value = undefined; }
  get options() { return this.children.filter(child => child.tagName === 'OPTION'); }
  get selectedOptions() { return this.options.slice(0, 1); }
}

function page(fetchHandler) {
  const elements = new Map(), requests = [], stored = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, new Element(id === 'sectorProgress' ? 'progress' : 'div'));
    return elements.get(id);
  };
  element('jobProgress').hidden = true;
  for (const phase of ['preparing', 'write', 'readback', 'reset', 'boot']) {
    const step = new Element('li'); step.dataset.phase = phase;
    element('progressSteps').append(step);
  }
  const context = vm.createContext({
    document: {getElementById: element, createElement: tag => new Element(tag)},
    localStorage: {getItem: key => stored.get(key) || null, setItem: (key, value) => stored.set(key, value)},
    fetch: async (url, options) => {
      requests.push({url, method: options.method || 'GET'});
      const data = await fetchHandler?.(url, options);
      if (data === undefined) throw Error('Unexpected mocked request: ' + url);
      return {ok: true, json: async () => ({ok: true, data})};
    },
    setTimeout: callback => { callback(); return 1; },
  });
  vm.runInContext(script, context, {filename: 'remote_store.html'});
  return {
    element, requests, stored,
    show(job) { context.fixture = job; vm.runInContext('renderProgress(fixture)', context); },
    view(job) { context.fixture = job; return vm.runInContext('progressView(fixture)', context); },
    poll(id) { context.fixtureId = id; return vm.runInContext('poll(fixtureId)', context); },
    render(catalog, health) {
      context.fixtureCatalog = catalog; context.fixtureHealth = health;
      vm.runInContext('catalog=fixtureCatalog; health=fixtureHealth; render()', context);
    },
  };
}

const progress = (changes = {}) => ({phase: 'write', verified_sectors: 42, total_sectors: 139,
  message: 'Writing and verifying app sectors.', write_complete: false,
  full_readback_verified: false, boot_verified: false, failed: false, ...changes});
const job = (changes = {}, details = {}) => ({operation: 'switch_app', status: 'running',
  progress: progress(details), ...changes});
const health = {engine: {active: null, blocked_unknown: false}, device: {
  session_configured: true, serial_ports: [], uboot_disks: [], session: {blocked: true},
}};
const catalog = {apps: [], official_updater_configured: false};

test('MDX labels identify both songs and RayForce is the default without hiding the demo', () => {
  const demo = {id: 'mdx-demo', title: 'MDX Karaoke', variant: 'target-audio-lcd30-444',
    reason: 'Package matches this device', sha256: 'e29d'.repeat(16), ready: true};
  const rayforce = {id: 'mdx-rayforce-penetration', title: 'MDX RayForce - Penetration',
    variant: 'private-rayforce-20261008', reason: 'Package matches this device',
    sha256: 'c719'.repeat(16), ready: true};
  const variants = [demo, rayforce];
  const ui = page();
  ui.render({apps: [{profile: 'mdx', available: true, variants}]}, health);
  const card = ui.element('library').children[2];
  const select = card.children.find(child => child.tagName === 'SELECT');
  assert.deepEqual(select.options.map(option => option.value), [rayforce.id, demo.id]);
  assert.equal(select.value, rayforce.id);
  assert.equal(select.options[0].textContent, 'MDX RayForce - Penetration · private-rayforce-20261008');
  assert.equal(select.options[1].textContent, 'MDX Karaoke · target-audio-lcd30-444');
  assert.deepEqual(variants, [demo, rayforce], 'Rendering does not mutate catalog order');
  const detail = card.children.find(child => child.className === 'package');
  assert.match(detail.textContent, /^Package matches this device · c719/);
  select.value = demo.id; select.onchange();
  assert.match(detail.textContent, /^Package matches this device · e29d/);
});

test('native progress has an accessible label and descriptive verified count', () => {
  assert.match(html, /<progress id="sectorProgress"[^>]*aria-label="Verified app sectors"/);
  assert.match(html, /aria-describedby="progressCounts progressNote"/);
  const ui = page(); ui.show(job());
  assert.equal(ui.element('sectorProgress').value, 42);
  assert.equal(ui.element('sectorProgress').max, 139);
  assert.equal(ui.element('progressCounts').textContent, '42 / 139 app sectors verified');
  assert.match(ui.element('sectorProgress').attributes.get('aria-valuetext'), /42 \/ 139.*Running/);
});

test('all sectors verified does not complete a pending readback or startup check', () => {
  const ui = page();
  for (const phase of ['readback', 'reset', 'boot']) {
    ui.show(job({}, {phase, verified_sectors: 139, write_complete: true,
      full_readback_verified: phase !== 'readback', message: ''}));
    assert.equal(ui.element('sectorProgress').value, 139);
    assert.equal(ui.element('progressStatus').textContent, 'Running');
    assert.notEqual(ui.element('progressPhase').textContent, 'Completed');
    assert.match(ui.element('progressNote').textContent, /still running/);
  }
});

test('failed startup retains 139/139 verified sectors and failed job outcome', () => {
  const ui = page();
  ui.show(job({status: 'failed'}, {phase: 'failed', verified_sectors: 139, write_complete: true,
    full_readback_verified: true, failed: true, message: 'Startup check failed.'}));
  assert.equal(ui.element('progressPhase').textContent, 'Startup check failed');
  assert.equal(ui.element('progressStatus').textContent, 'Failed');
  assert.equal(ui.element('jobProgress').dataset.outcome, 'failed');
  assert.equal(ui.element('progressCounts').textContent, '139 / 139 app sectors verified');
  assert.match(ui.element('progressNote').textContent, /full image readback verified.*Startup check failed/);
  assert.equal(ui.element('progressSteps').children[4].attributes.get('aria-current'), 'step');
  assert.ok(ui.element('progressSteps').children[3].classList.contains('done'));
});

test('job status overrides an inconsistent completed phase', () => {
  const ui = page(); ui.show(job({status: 'failed'}, {phase: 'completed'}));
  assert.equal(ui.element('progressStatus').textContent, 'Failed');
  assert.equal(ui.element('progressPhase').textContent, 'Failed');
  ui.show(job({status: 'succeeded'}, {phase: 'boot', verified_sectors: 139}));
  assert.equal(ui.element('progressPhase').textContent, 'Completed');
});

test('unknown or invalid counts stay indeterminate without fabricated percentages', () => {
  const ui = page();
  for (const counts of [{verified_sectors: null, total_sectors: null},
    {verified_sectors: 140, total_sectors: 139}, {verified_sectors: -1, total_sectors: 139}]) {
    ui.show(job({}, counts));
    assert.equal(ui.element('sectorProgress').value, undefined);
    assert.match(ui.element('progressCounts').textContent, /not available/);
    assert.doesNotMatch(ui.element('progressCounts').textContent, /%/);
  }
});

test('legacy jobs without progress hide the progress panel', () => {
  const ui = page(); ui.show(job()); ui.show({operation: 'switch_app', status: 'failed'});
  assert.equal(ui.element('jobProgress').hidden, true);
});

test('poll displays live progress then failed startup using only GET requests', async () => {
  const id = 'a'.repeat(32), jobs = [job(), job({status: 'failed'}, {phase: 'failed',
    verified_sectors: 139, write_complete: true, full_readback_verified: true,
    message: 'Startup check failed.'})];
  const ui = page(url => url === '/v1/jobs/' + id ? jobs.shift() :
    url === '/v1/status' ? health : url === '/v1/catalog' ? catalog : undefined);
  await ui.poll(id);
  assert.equal(ui.element('progressStatus').textContent, 'Failed');
  assert.equal(ui.element('progressCounts').textContent, '139 / 139 app sectors verified');
  assert.equal(ui.requests.filter(request => request.url === '/v1/jobs/' + id).length, 2);
  assert.ok(ui.requests.every(request => request.method === 'GET'));
  assert.equal(ui.stored.size, 0, 'Polling does not persist authentication or other data');
});

test('network loss pauses polling without resubmission or invented progress', async () => {
  const id = 'b'.repeat(32); let reads = 0;
  const ui = page(url => { if (url === '/v1/jobs/' + id && reads++ === 0) return job();
    throw Error('Offline fixture: connection lost'); });
  await assert.rejects(ui.poll(id), /connection lost/);
  assert.equal(ui.element('progressStatus').textContent, 'Updates paused');
  assert.equal(ui.element('sectorProgress').value, 42);
  assert.equal(ui.requests.length, 2);
  assert.ok(ui.requests.every(request => request.method === 'GET'));
});

test('refresh failure after a terminal response preserves the failed outcome', async () => {
  const id = 'c'.repeat(32);
  const ui = page(url => { if (url === '/v1/jobs/' + id) return job({status: 'failed'},
    {phase: 'failed', verified_sectors: 139, full_readback_verified: true, message: 'Startup check failed.'});
    throw Error('Offline fixture: status unavailable'); });
  await assert.rejects(ui.poll(id), /status unavailable/);
  assert.equal(ui.element('progressStatus').textContent, 'Failed');
  assert.equal(ui.element('progressPhase').textContent, 'Startup check failed');
});
