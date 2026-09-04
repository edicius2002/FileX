// N37 — qué FORMA de `file://` emite el runtime del CLIENTE.
//
// Claude Code es TypeScript sobre Node, así que `url.pathToFileURL` es el
// productor que un cliente MCP escrito en ese runtime usa para declarar un
// root. La pregunta de `CLAUDE.md` §5 —*sondear en ejecución, no deducir*—
// aplicada a la decisión de N37: si los productores reales emiten la forma con
// *authority* para UNC, rechazarla rompe clientes legítimos.
//
// Va en fichero y no en `node -e` por la TRAMPA 19: el shell de este entorno se
// come los backslashes, y con `-e` la primera pasada midió rutas corruptas
// (`\\servidor\recurso` llegó como `\servidor\recurso`).

const { pathToFileURL, fileURLToPath } = require('url');

const CASOS = [
  ['local',       'D:\\Work\\research\\FileX'],
  ['unc',         '\\\\servidor\\recurso'],
  ['unc_sub',     '\\\\servidor\\recurso\\sub'],
  ['unc_admin',   '\\\\localhost\\D$\\Work'],
  ['raiz_unidad', 'D:\\'],
];

const filas = [];
for (const [nombre, ruta] of CASOS) {
  let uri = null, err = null, vuelta = null, vuelta_err = null;
  try { uri = pathToFileURL(ruta).href; } catch (e) { err = String(e.message); }
  if (uri !== null) {
    try { vuelta = fileURLToPath(uri); } catch (e) { vuelta_err = String(e.message); }
  }
  let host = null;
  if (uri !== null) { try { host = new URL(uri).host; } catch (e) { host = '<URL falla>'; } }
  filas.push({
    caso: nombre,
    ruta_de_entrada: ruta,
    uri_emitido: uri,
    error: err,
    authority_emitida: host,
    ida_y_vuelta: vuelta,
    ida_y_vuelta_error: vuelta_err,
    ida_y_vuelta_fiel: vuelta === ruta,
  });
}

// El otro lado: ¿qué acepta el consumidor de Node ante las formas que la
// decisión de N37 tiene que clasificar?
const CONSUMO = [
  'file://servidor/recurso',
  'file:///recurso',
  'file://localhost/D:/Work',
  'file:///D:/Work',
  'file://',
  'file:///',
];
const consumo = [];
for (const u of CONSUMO) {
  let p = null, err = null, host = null;
  try { host = new URL(u).host; } catch (e) { host = '<URL falla>'; }
  try { p = fileURLToPath(u); } catch (e) { err = String(e.message); }
  consumo.push({ uri: u, authority: host, fileURLToPath: p, error: err });
}

console.log(JSON.stringify({
  runtime: 'node ' + process.version,
  produccion: filas,
  consumo: consumo,
}, null, 2));
