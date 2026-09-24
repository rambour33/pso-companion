// Serveur local pso-companion : catalogue des skills Claude Code, téléchargement en .zip,
// exports Companion et documentation. Lecture seule, accessible sur le réseau local.

const express = require('express');
const fs      = require('fs');
const os      = require('os');
const path    = require('path');
const zlib    = require('zlib');
const { marked } = require('marked');

const ROOT       = __dirname;
const SKILLS_DIR = path.join(ROOT, 'skills');
const CONFIG     = JSON.parse(fs.readFileSync(path.join(ROOT, 'config.json'), 'utf8'));
const PORT       = process.env.PORT || CONFIG.port || 3010;
const EXPORTS_DIR = CONFIG.exportsDir ? path.resolve(CONFIG.exportsDir) : null;

const app = express();
app.use(express.static(path.join(ROOT, 'public')));

// ─── Utilitaires ─────────────────────────────────────────────────────────────

function getLocalIPs() {
  const result = [];
  for (const iface of Object.values(os.networkInterfaces())) {
    for (const addr of iface) {
      if (addr.family === 'IPv4' && !addr.internal) result.push(addr.address);
    }
  }
  return result;
}

/** Résout `rel` dans `base` et refuse toute sortie du dossier (../). */
function safeJoin(base, rel) {
  const full = path.resolve(base, rel || '');
  if (full !== base && !full.startsWith(base + path.sep)) return null;
  return full;
}

function walk(dir, prefix = '') {
  const out = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    if (ent.name.startsWith('.') || ent.name === '__pycache__') continue;
    const rel = prefix ? `${prefix}/${ent.name}` : ent.name;
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...walk(full, rel));
    else {
      const st = fs.statSync(full);
      out.push({ path: rel, size: st.size, mtime: st.mtimeMs });
    }
  }
  return out.sort((a, b) => a.path.localeCompare(b.path));
}

/** Lit le frontmatter YAML simple (clé: valeur) en tête d'un SKILL.md. */
function readFrontmatter(md) {
  const m = md.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  const meta = {};
  if (m) {
    for (const line of m[1].split(/\r?\n/)) {
      const kv = line.match(/^([\w-]+):\s*(.*)$/);
      if (kv) meta[kv[1]] = kv[2].trim();
    }
  }
  return { meta, body: m ? md.slice(m[0].length) : md };
}

function listSkills() {
  if (!fs.existsSync(SKILLS_DIR)) return [];
  return fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory() && fs.existsSync(path.join(SKILLS_DIR, d.name, 'SKILL.md')))
    .map(d => {
      const dir = path.join(SKILLS_DIR, d.name);
      const { meta } = readFrontmatter(fs.readFileSync(path.join(dir, 'SKILL.md'), 'utf8'));
      const files = walk(dir);
      return {
        id: d.name,
        name: meta.name || d.name,
        description: meta.description || '',
        files,
        size: files.reduce((s, f) => s + f.size, 0),
        updated: Math.max(...files.map(f => f.mtime)),
      };
    });
}

function skillDir(id) {
  const dir = safeJoin(SKILLS_DIR, id);
  return dir && fs.existsSync(path.join(dir, 'SKILL.md')) ? dir : null;
}

// ─── Zip (sans dépendance) ───────────────────────────────────────────────────

function dosDateTime(d) {
  const time = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
  const date = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  return { time, date };
}

/** entries : [{ name: 'dossier/fichier.ext', data: Buffer, mtime: Date }] */
function buildZip(entries) {
  const locals = [], centrals = [];
  let offset = 0;
  for (const e of entries) {
    const name = Buffer.from(e.name, 'utf8');
    const deflated = zlib.deflateRawSync(e.data);
    const crc = zlib.crc32(e.data);
    const { time, date } = dosDateTime(e.mtime);
    const FLAGS = 0x0800; // noms en UTF-8 (accents)

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(FLAGS, 6);
    local.writeUInt16LE(8, 8);             // deflate
    local.writeUInt16LE(time, 10);
    local.writeUInt16LE(date, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(deflated.length, 18);
    local.writeUInt32LE(e.data.length, 22);
    local.writeUInt16LE(name.length, 26);
    local.writeUInt16LE(0, 28);
    locals.push(local, name, deflated);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(FLAGS, 8);
    central.writeUInt16LE(8, 10);
    central.writeUInt16LE(time, 12);
    central.writeUInt16LE(date, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(deflated.length, 20);
    central.writeUInt32LE(e.data.length, 24);
    central.writeUInt16LE(name.length, 28);
    central.writeUInt32LE(offset, 42);
    centrals.push(central, name);

    offset += local.length + name.length + deflated.length;
  }
  const centralSize = centrals.reduce((s, b) => s + b.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(centralSize, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, ...centrals, end]);
}

function zipSkill(id) {
  const dir = skillDir(id);
  return buildZip(walk(dir).map(f => ({
    name: `${id}/${f.path}`,
    data: fs.readFileSync(path.join(dir, f.path)),
    mtime: new Date(f.mtime),
  })));
}

// ─── API ─────────────────────────────────────────────────────────────────────

app.get('/api/info', (req, res) => {
  res.json({ port: PORT, ips: getLocalIPs(), hostname: os.hostname(), exportsDir: EXPORTS_DIR });
});

app.get('/api/skills', (req, res) => res.json(listSkills()));

// Contenu d'un fichier de skill : Markdown rendu en HTML, le reste en texte brut.
app.get('/api/skills/:id/file', (req, res) => {
  const dir = skillDir(req.params.id);
  if (!dir) return res.status(404).json({ error: `Skill inconnu : ${req.params.id}` });
  const file = safeJoin(dir, req.query.path);
  if (!file || !fs.existsSync(file) || fs.statSync(file).isDirectory())
    return res.status(404).json({ error: `Fichier introuvable : ${req.query.path}` });
  const text = fs.readFileSync(file, 'utf8');
  if (file.endsWith('.md')) {
    const { meta, body } = readFrontmatter(text);
    return res.json({ type: 'markdown', meta, html: marked.parse(body) });
  }
  res.json({ type: 'text', text });
});

app.get('/api/exports', (req, res) => {
  if (!EXPORTS_DIR || !fs.existsSync(EXPORTS_DIR)) return res.json([]);
  const files = fs.readdirSync(EXPORTS_DIR)
    .filter(f => f.endsWith('.companionconfig'))
    .map(f => {
      const st = fs.statSync(path.join(EXPORTS_DIR, f));
      return { name: f, size: st.size, mtime: st.mtimeMs };
    })
    .sort((a, b) => b.mtime - a.mtime);
  res.json(files);
});

// ─── Téléchargements ─────────────────────────────────────────────────────────

app.get('/download/skills/:id.zip', (req, res) => {
  if (!skillDir(req.params.id)) return res.status(404).send(`Skill inconnu : ${req.params.id}`);
  const zip = zipSkill(req.params.id);
  res.set({
    'Content-Type': 'application/zip',
    'Content-Disposition': `attachment; filename="${req.params.id}.zip"`,
    'Content-Length': zip.length,
  });
  res.end(zip);
});

app.get('/download/skills/:id/file', (req, res) => {
  const dir = skillDir(req.params.id);
  const file = dir && safeJoin(dir, req.query.path);
  if (!file || !fs.existsSync(file)) return res.status(404).send('Fichier introuvable');
  res.download(file);
});

app.get('/download/exports/:name', (req, res) => {
  const file = EXPORTS_DIR && safeJoin(EXPORTS_DIR, req.params.name);
  if (!file || !file.endsWith('.companionconfig') || !fs.existsSync(file))
    return res.status(404).send('Export introuvable');
  res.download(file);
});

app.get('/docs', (req, res) => res.sendFile(path.join(ROOT, 'public', 'docs.html')));

// ─── Démarrage ───────────────────────────────────────────────────────────────

app.listen(PORT, '0.0.0.0', () => {
  const ips = getLocalIPs();
  console.log('');
  console.log('📦 pso-companion démarré !');
  console.log('');
  console.log('  ── Ce PC (localhost) ──────────────────────────────────────');
  console.log('   Skills     → http://localhost:' + PORT + '/');
  console.log('   Doc        → http://localhost:' + PORT + '/docs');
  if (ips.length > 0) {
    console.log('');
    console.log('  ── Autre PC (réseau local) ────────────────────────────────');
    ips.forEach(ip => {
      console.log('   Skills     → http://' + ip + ':' + PORT + '/');
      console.log('   Doc        → http://' + ip + ':' + PORT + '/docs');
    });
  }
  console.log('');
  console.log(`  ${listSkills().length} skill(s) dans ${SKILLS_DIR}`);
  if (EXPORTS_DIR) console.log(`  Exports Companion : ${EXPORTS_DIR}`);
  console.log('');
});
