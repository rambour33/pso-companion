"""Outil pour lire et générer des boutons Bitfocus Companion (format .companionconfig, v12 / Companion 4.x).

Usage :
  python companion.py dump  <fichier.companionconfig>
  python companion.py apply <fichier.companionconfig> <spec.json> [--server <server.js>] [--dry-run]

Le fichier .companionconfig est du JSON compressé en gzip. `apply` fait une sauvegarde
<fichier>.bak avant d'écrire. Voir SKILL.md pour le format de spec.json.
"""
import gzip, json, os, re, secrets, shutil, string, sys

sys.stdout.reconfigure(encoding='utf-8')

ON_COLOR = 13056        # #003300 vert foncé  = overlay visible
OFF_COLOR = 11141120    # #AA0000 rouge       = overlay caché
WHITE = 16777215
SELF = '$(this:page)/$(this:row)/$(this:column)'
BASE_URL = 'http://localhost:3002'
_ALPHABET = string.ascii_letters + string.digits + '_-'


# ── Lecture / écriture ────────────────────────────────────────────────────────

def load(path):
    with open(path, 'rb') as f:
        return json.loads(gzip.decompress(f.read()).decode('utf-8', errors='surrogatepass'))


def save(path, data):
    shutil.copy(path, path + '.bak')
    out = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    with open(path, 'wb') as f:
        f.write(gzip.compress(out.encode('utf-8', errors='surrogatepass')))


def new_id():
    return ''.join(secrets.choice(_ALPHABET) for _ in range(21))


def color(v):
    """Accepte un entier Companion ou '#RRGGBB'."""
    if isinstance(v, str):
        return int(v.lstrip('#'), 16)
    return v


# ── Actions ───────────────────────────────────────────────────────────────────

def http_connection_id(data):
    for cid, inst in data['instances'].items():
        if inst.get('moduleId') == 'generic-http':
            return cid
    sys.exit('Aucune connexion generic-http trouvée dans la config (à créer dans Companion).')


def act_get(conn, url):
    if url.startswith('/'):
        url = BASE_URL + url
    return {
        'id': new_id(), 'definitionId': 'get', 'connectionId': conn,
        'options': {
            'url': {'value': url, 'isExpression': False},
            'header': {'isExpression': False, 'value': ''},
            'jsonResultDataVariable': {'isExpression': False},
            'result_stringify': {'isExpression': False, 'value': True},
            'statusCodeVariable': {'isExpression': False},
        },
        'upgradeIndex': 1, 'type': 'action',
    }


def act_internal(definition, **opts):
    return {
        'id': new_id(), 'definitionId': definition, 'connectionId': 'internal', 'type': 'action',
        'options': {k: {'isExpression': False, 'value': v} for k, v in opts.items()},
        'children': {},
    }


def act_bgcolor(location, c):
    return act_internal('bgcolor', location=location, color=color(c))


def act_set_step(location, step_index):
    # Remplace l'ancienne action `bank_current_step` (1-indexée, obsolète) : step_index est 0-indexé.
    return act_internal('button_set_current_step', location=location, step_index=step_index)


def act_page(definition):
    return act_internal(definition, surfaceId='self')


# ── Boutons ───────────────────────────────────────────────────────────────────

def button(text, bg, steps, size='auto', fg=WHITE):
    return {
        'type': 'button',
        'style': {
            'text': text, 'textExpression': False, 'size': str(size), 'png64': None,
            'alignment': 'center:center', 'pngalignment': 'center:center',
            'color': color(fg), 'bgcolor': color(bg), 'show_topbar': 'default',
        },
        'options': {'stepProgression': 'auto', 'stepExpression': '', 'rotaryActions': False},
        'feedbacks': [],
        'steps': {
            str(i): {'action_sets': {'down': down, 'up': up}, 'options': {'runWhileHeld': []}}
            for i, (down, up) in enumerate(steps)
        },
        'localVariables': [],
    }


def build(spec, conn, overlay_ids):
    """Construit un contrôle à partir d'une entrée de spec (hors 'master')."""
    kind = spec['kind']
    text = spec.get('text', '')
    size = spec.get('size', 'auto')
    on, off = spec.get('on_color', ON_COLOR), spec.get('off_color', OFF_COLOR)

    if kind == 'toggle':
        ov = spec['overlay']
        if overlay_ids and ov not in overlay_ids:
            print(f"  ⚠ overlay '{ov}' absent de TRANSITION_IDS dans server.js → le serveur renverra 404")
        show = spec.get('show_action', 'show')
        start_hidden = spec.get('start_hidden', False)
        return button(text, off if start_hidden else on, [
            ([act_get(conn, f'/api/deck/{ov}/{show}'), act_bgcolor(SELF, on)], []),
            ([act_get(conn, f'/api/deck/{ov}/hide'), act_bgcolor(SELF, off)], []),
        ], size)

    if kind == 'get':
        urls = spec['urls'] if 'urls' in spec else [spec['url']]
        return button(text, spec.get('bg', 0), [([act_get(conn, u) for u in urls], [])], size)

    if kind == 'page_up':
        return button(text or '⬆️', 0, [([act_page('dec_page')], [])])
    if kind == 'page_down':
        return button(text or '⬇️', 0, [([act_page('inc_page')], [])])
    if kind in ('pagenum', 'pageup', 'pagedown'):
        return {'type': kind}
    if kind == 'empty':
        return None
    sys.exit(f"Type de bouton inconnu : {kind}")


def step_urls(ctl, step):
    acts = ctl.get('steps', {}).get(str(step), {}).get('action_sets', {}).get('down', [])
    return [a['options']['url']['value'] for a in acts if a.get('definitionId') == 'get']


def build_master(spec, conn, pages):
    """Bouton maître : rejoue step 0 / step 1 de chaque cible, recolore et resynchronise leurs steps."""
    targets = spec['targets']
    on, off = spec.get('on_color', ON_COLOR), spec.get('off_color', OFF_COLOR)
    show_urls, hide_urls = [], []
    for loc in targets:
        p, r, c = loc.split('/')
        ctl = pages.get(p, {}).get('controls', {}).get(r, {}).get(c)
        if not ctl:
            sys.exit(f"Master : cible {loc} introuvable")
        show_urls += step_urls(ctl, 0)
        hide_urls += step_urls(ctl, 1)

    def step(urls, c, next_step):
        return ([act_get(conn, u) for u in urls]
                + [act_bgcolor(SELF, c)] + [act_bgcolor(t, c) for t in targets]
                + [act_set_step(t, next_step) for t in targets], [])

    # Après "tout afficher", chaque cible doit être prête à cacher (step 1), et inversement.
    return button(spec.get('text', 'ALL'), on, [step(show_urls, on, 1), step(hide_urls, off, 0)],
                  spec.get('size', 'auto'))


# ── Commandes ─────────────────────────────────────────────────────────────────

def read_overlay_ids(server_js):
    if not server_js or not os.path.exists(server_js):
        return None
    src = open(server_js, encoding='utf-8-sig').read()
    m = re.search(r'TRANSITION_IDS\s*=\s*\[(.*?)\]', src, re.S)
    return set(re.findall(r"'([^']+)'", m.group(1))) if m else None


def ensure_page(data, num, name=None):
    pages = data['pages']
    if num not in pages:
        pages[num] = {'id': new_id(), 'name': name or '', 'controls': {},
                      'gridSize': {'minColumn': 0, 'maxColumn': 7, 'minRow': 0, 'maxRow': 3}}
        print(f"+ page {num} créée")
    elif name is not None:
        pages[num]['name'] = name
    return pages[num]


def cmd_apply(cfg_path, spec_path, server_js, dry_run):
    data = load(cfg_path)
    spec = json.load(open(spec_path, encoding='utf-8-sig'))
    conn = http_connection_id(data)
    overlay_ids = read_overlay_ids(server_js)

    for num, p in spec.get('pages', {}).items():
        ensure_page(data, str(num), p.get('name'))

    # Les masters sont construits en dernier : ils lisent les URLs des boutons cibles.
    entries = spec['buttons']
    for b in sorted(entries, key=lambda b: b['kind'] == 'master'):
        p, r, c = b['loc'].split('/')
        page = ensure_page(data, p)
        ctl = build_master(b, conn, data['pages']) if b['kind'] == 'master' else build(b, conn, overlay_ids)
        row = page['controls'].setdefault(r, {})
        if ctl is None:
            row.pop(c, None)
        else:
            row[c] = ctl
        print(f"  {b['loc']:<8} {b['kind']:<9} {b.get('text', '')!r}")

    if dry_run:
        print('Dry-run : rien écrit.')
    else:
        save(cfg_path, data)
        print(f"OK — {cfg_path} mis à jour (sauvegarde : .bak)")


def cmd_dump(cfg_path):
    data = load(cfg_path)
    for cid, inst in data['instances'].items():
        print(f"connexion {cid} : {inst.get('moduleId')} « {inst.get('label')} » {inst.get('config', {}).get('prefix', '')}")
    for pn, page in sorted(data['pages'].items(), key=lambda kv: int(kv[0])):
        print(f"\n=== Page {pn} « {page.get('name', '')} »")
        for r, row in sorted(page['controls'].items(), key=lambda kv: int(kv[0])):
            for c, ctl in sorted(row.items(), key=lambda kv: int(kv[0])):
                if ctl.get('type') != 'button':
                    print(f"[{pn}/{r}/{c}] <{ctl.get('type')}>")
                    continue
                text = (ctl['style'].get('text') or '').replace('\n', ' ')
                print(f"[{pn}/{r}/{c}] {text!r} bg={ctl['style'].get('bgcolor')}")
                for sk, st in ctl.get('steps', {}).items():
                    for side, acts in st['action_sets'].items():
                        if not acts:
                            continue
                        summary = []
                        for a in acts:
                            o = a.get('options', {})
                            if a['definitionId'] == 'get':
                                summary.append('GET ' + o['url']['value'].replace(BASE_URL, ''))
                            elif 'location' in o:
                                summary.append(f"{a['definitionId']}→{o['location']['value'].replace(SELF, 'self')}")
                            else:
                                summary.append(a['definitionId'])
                        print(f"    step{sk}/{side}: " + ', '.join(summary))


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == 'dump':
        cmd_dump(args[1])
    elif len(args) >= 3 and args[0] == 'apply':
        server = None
        if '--server' in args:
            server = args[args.index('--server') + 1]
        cmd_apply(args[1], args[2], server, '--dry-run' in args)
    else:
        print(__doc__)
        sys.exit(1)
