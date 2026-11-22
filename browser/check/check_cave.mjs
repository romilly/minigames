// Plays the browser version of cave for a few moves, in Pyodide under Node,
// with node-canvas standing in for the page's <canvas id="screen">, and checks
// what's drawn. Run with scripts/browser_check.sh.
//   node check_cave.mjs REPO [MAZE_JSON] [SCREENSHOT_DIR]
// Without network access to Pyodide's CDN, PyYAML can't load; pass the maze
// as JSON and the game reads that, as it does on the board.
import { loadPyodide } from 'pyodide';
import canvasPkg from 'canvas';
import fs from 'fs';

const [REPO, MAZE_JSON, SHOTS] = process.argv.slice(2);
const { createCanvas } = canvasPkg;
const handlers = { doc: {}, canvas: {} };
const canvas = createCanvas(240, 240);
canvas.clientWidth = 480; canvas.clientHeight = 480;        // shown doubled
canvas.addEventListener = (name, f) => { handlers.canvas[name] = f; };
canvas.setPointerCapture = () => {};
globalThis.document = { getElementById: () => canvas,
                        addEventListener: (name, f) => { handlers.doc[name] = f; } };

// Keep in step with FILES in browser/index.html.
const FILES = {
  'minigame.py': 'minigame.py', 'tones.py': 'tones.py',
  'cave.py': 'cave.py', 'cave_core.py': 'cave_core.py', 'cave_mazes.py': 'cave_mazes.py',
  'cave_layout.py': 'cave_layout.py', 'cave_input.py': 'cave_input.py',
  'cave_screen.py': 'cave_screen.py',
  'minigame_web.py': 'browser/minigame_web.py', 'pygame.py': 'browser/pygame.py',
  'cave_web.py': 'browser/cave_web.py', 'mazes/mine.yaml': 'mazes/mine.yaml',
};
const html = fs.readFileSync(`${REPO}/browser/index.html`, 'utf8');
for (const path of Object.values(FILES)) {
  if (!html.includes(`'${path}'`)) fail(`index.html doesn't load ${path}`);
}

const pyodide = await loadPyodide();
try { await pyodide.loadPackage('pyyaml'); } catch (e) { /* reads the JSON instead */ }
pyodide.FS.mkdirTree('mazes');
for (const [name, path] of Object.entries(FILES)) {
  pyodide.FS.writeFile(name, fs.readFileSync(`${REPO}/${path}`, 'utf8'));
}
if (MAZE_JSON) pyodide.FS.writeFile('mine.json', fs.readFileSync(MAZE_JSON, 'utf8'));
pyodide.runPythonAsync('import cave_web\nawait cave_web.run()')
  .catch(e => fail(`Python: ${e.message}`));

const sleep = ms => new Promise(r => setTimeout(r, ms));
const pixel = (x, y) => Array.from(canvas.getContext('2d').getImageData(x, y, 1, 1).data.slice(0, 3));
const shot = name => SHOTS && fs.writeFileSync(`${SHOTS}/${name}.png`, canvas.toBuffer('image/png'));
const key = async k => { handlers.doc.keydown({ key: k, preventDefault() {} }); await sleep(60);
                         handlers.doc.keyup({ key: k }); await sleep(60); };
const tap = async (x, y) => { handlers.canvas.pointerdown({ offsetX: x, offsetY: y, pointerId: 1 });
                              handlers.canvas.pointerup({}); await sleep(120); };
function fail(message) { console.error(`FAIL: ${message}`); process.exit(1); }
function expect(what, actual, wanted) {
  if (JSON.stringify(actual) !== JSON.stringify(wanted)) fail(`${what}: ${actual} not ${wanted}`);
}

const TOOLBAR = [30, 40, 70], MENU_SELECTED = [60, 70, 120];
await sleep(800);
shot('web_start');
expect('the toolbar', pixel(230, 3), TOOLBAR);
for (const k of ['ArrowRight', 'ArrowUp', 'ArrowUp', 'ArrowUp', 'ArrowUp',
                 'ArrowLeft', 'ArrowUp', 'ArrowUp', 'ArrowUp']) await key(k);
await tap(10, 10);                                   // the menu button, in shown pixels
shot('web_menu');
expect('the menu, opened by a tap', pixel(230, 32), MENU_SELECTED);
await tap(240, 80);                                  // its first item
shot('web_taken');
if (JSON.stringify(pixel(230, 32)) === JSON.stringify(MENU_SELECTED)) fail('the menu stayed open');
console.log('browser check passed');
process.exit(0);
