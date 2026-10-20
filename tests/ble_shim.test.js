// Drives the live-19 Bluetooth bridge with a fake native plugin. Exit 0 and "ok N" lines on success.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'web', 'index.html'), 'utf8');
const i = html.indexOf('/*live-p19*/'), j = html.indexOf('SX.boot();\n})();', i);
if (i < 0 || j < 0) { console.error('layer 19 not in page'); process.exit(1); }
const src = html.slice(i, j);

const calls = [];
const listeners = {};
const FakeBLE = {
  initialize: async o => { calls.push(['initialize', o]); },
  isEnabled: async () => ({ value: true }),
  requestEnable: async () => {},
  requestDevice: async o => { calls.push(['requestDevice', o]); return o.namePrefix ? { deviceId: 'CC:DD', name: 'Polar H10 1234' } : { deviceId: 'AA:BB', name: 'Omron HEM' }; },
  connect: async o => { calls.push(['connect', o]); },
  disconnect: async o => { calls.push(['disconnect', o]); },
  getServices: async o => ({ services: o.deviceId === 'AA:BB' ? [{ uuid: '00001810-0000-1000-8000-00805f9b34fb' }] : [] }),   // a device that reports nothing is taken on trust
  addListener: async (k, f) => { listeners[k] = f; return { remove() { delete listeners[k]; } }; },
  startNotifications: async o => { calls.push(['startNotifications', o]); },
  stopNotifications: async o => { calls.push(['stopNotifications', o]); },
  read: async o => { calls.push(['read', o]); return { value: '64' }; },
  write: async o => { calls.push(['write', o]); },
  writeWithoutResponse: async o => { calls.push(['writeWithoutResponse', o]); },
};

// the minimum of the app the layer touches at load time
const noop = () => {};
global.window = global;
global.navigator = { bluetooth: undefined, userAgent: 'node' };
global.location = { hash: '', pathname: '/app', search: '' };
global.history = { replaceState: noop };
global.document = { body: {}, getElementById: () => null, addEventListener: noop };
global.fetch = async () => ({ ok: true, json: async () => ({ providers: [], links: [] }) });
global.Capacitor = { isNativePlatform: () => true, Plugins: { BluetoothLe: FakeBLE } };
global.page = 'dash'; global.render = noop; global.go = noop; global.toast = noop; global.confirm = () => false;
const SX = { p: s => s, S: { key: 'k', hc: {}, vitals: {} }, extend: noop, act: {}, me: () => ({ id: 'd1', name: 'A' }), hcMerge: () => 0, save: noop, ledger: noop };
const E = s => s;
new Function('SX', 'S', 'E', 'P', src)(SX, SX.S, E, SX.p);

let n = 0;
const ok = (c, m) => { if (!c) { console.error('not ok -', m); process.exit(1); } console.log('ok', ++n, '-', m); };

(async () => {
  ok(navigator.bluetooth && navigator.bluetooth._native && SX.nativeBle === true, 'navigator.bluetooth installed from the native plugin');
  // 1. the standard-profile reader: filters by service name → full UUIDs, scan by service
  const dev = await navigator.bluetooth.requestDevice({ filters: [{ services: ['heart_rate'] }, { services: ['blood_pressure'] }], optionalServices: ['heart_rate', 'blood_pressure', 'battery_service'] });
  const rq = calls.find(c => c[0] === 'requestDevice')[1];
  ok(rq.services.join(',') === '0000180d-0000-1000-8000-00805f9b34fb,00001810-0000-1000-8000-00805f9b34fb' && !rq.namePrefix && rq.optionalServices.length === 3, 'service names become 128-bit UUIDs');
  ok(dev.name === 'Omron HEM' && dev.gatt && dev.gatt.connected === false, 'device object looks like Web Bluetooth');
  const srv = await dev.gatt.connect();
  ok(dev.gatt.connected === true && calls.some(c => c[0] === 'connect' && c[1].deviceId === 'AA:BB'), 'connect goes to the plugin');
  const s = await srv.getPrimaryService('blood_pressure');
  let missing = false; try { await srv.getPrimaryService('glucose'); } catch (e) { missing = true; }
  ok(missing, 'a service the device lacks throws, so the reader tries the next profile');
  const ch = await s.getCharacteristic('blood_pressure_measurement');
  let got = null; ch.addEventListener('characteristicvaluechanged', ev => { got = ev.target.value; });
  await ch.startNotifications();
  const key = 'notification|AA:BB|00001810-0000-1000-8000-00805f9b34fb|00002a35-0000-1000-8000-00805f9b34fb';
  const shortKey = 'notification|AA:BB|1810|2a35';
  ok(listeners[key] && listeners[shortKey], 'listens on the full and the short (iOS) UUID spelling');
  // an Omron reading: flags 0x00 (mmHg), sys 128, dia 82, MAP 97 as SFLOATs
  listeners[shortKey]({ value: '00 80 00 52 00 61 00' });
  ok(got instanceof DataView && got.byteLength === 7 && got.getUint8(1) === 0x80, 'hex payload arrives as a DataView');
  await ch.stopNotifications();
  ok(!listeners[key] && !listeners[shortKey] && calls.some(c => c[0] === 'stopNotifications'), 'stopNotifications removes both listeners');
  // 2. the Polar strap: name prefixes → one common prefix, no service filter; write goes out as hex
  calls.length = 0;
  const polar = await navigator.bluetooth.requestDevice({ filters: [{ namePrefix: 'Polar H10' }, { namePrefix: 'Polar H9' }, { services: ['fb005c80-02e7-f387-1cad-8acd2d8df0c8'] }], optionalServices: ['fb005c80-02e7-f387-1cad-8acd2d8df0c8', 'heart_rate'] });
  const rq2 = calls.find(c => c[0] === 'requestDevice')[1];
  ok(rq2.namePrefix === 'Polar H' && !rq2.services, 'name-prefix filters become the common prefix');
  await polar.gatt.connect();
  const cp = await (await polar.gatt.getPrimaryService('fb005c80-02e7-f387-1cad-8acd2d8df0c8')).getCharacteristic('fb005c81-02e7-f387-1cad-8acd2d8df0c8');
  await cp.writeValue(new Uint8Array([0x02, 0x00, 0x0e]));
  const w = calls.find(c => c[0] === 'write')[1];
  ok(w.value === '02 00 0e' && w.characteristic === 'fb005c81-02e7-f387-1cad-8acd2d8df0c8', 'writeValue sends space-separated hex');
  const bl = await (await polar.gatt.getPrimaryService('battery_service')).getCharacteristic('battery_level');
  const v = await bl.readValue();
  ok(v.getUint8(0) === 100, 'readValue returns a DataView');
  polar.gatt.disconnect();
  ok(polar.gatt.connected === false, 'disconnect');
  process.exit(0);
})().catch(e => { console.error('not ok -', e && e.stack || e); process.exit(1); });
