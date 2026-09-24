"""Outil pour lire et générer des boutons Bitfocus Companion (format .companionconfig, v12 / Companion 4.x).

Usage :
  python companion.py dump  <fichier.companionconfig>
  python companion.py apply <fichier.companionconfig> <spec.json> [--server <server.js>] [--out <sortie>] [--dry-run]

Le fichier .companionconfig est du JSON compressé en gzip. `apply` fait une sauvegarde
<fichier>.bak avant d'écrire (sauf avec --out, qui écrit dans un nouveau fichier).
Voir SKILL.md pour le format de spec.json et VMIX.md pour les actions vMix.
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


def save(path, data, backup=True):
    if backup and os.path.exists(path):
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


def act_wait(ms):
    return act_internal('wait', time=str(ms))


def act_group(children, mode='sequential'):
    """Action Group interne : 'sequential' attend chaque action (et chaque wait) avant la suivante."""
    group = act_internal('action_group', execution_mode=mode)
    group['children'] = {'default': children}
    return group


# ── vMix (module studiocoast-vmix v5, Companion 4.3+) ──────────────────────────
# Options par défaut relevées dans le code source du module (src/actions, src/feedbacks).
# Toutes les options sont écrites dans le fichier, sinon Companion les laisse vides.

VMIX_MODULE = 'studiocoast-vmix'
VMIX_VERSION = '5.0.5'
VMIX_UPGRADE_INDEX = 17     # 18 scripts de mise à jour dans le module v5.0.5 → index du dernier

VMIX_ACTIONS = {
    'transitionMix':           {'mix': 1, 'functionID': 'Cut', 'duration': '1000', 'input': ''},
    'transition':              {'functionID': 'Transition1', 'mix': 1},
    'setTransitionEffect':     {'functionID': 'SetTransitionEffect1', 'value': 'Cut'},
    'setTransitionDuration':   {'functionID': 'SetTransitionDuration1', 'value': 1000},
    'previewInput':            {'input': '1', 'mix': 1},
    'programCut':              {'input': '1', 'mix': 1},
    'quickPlay':               {'input': '1'},
    'overlayFunctions':        {'type': 'OverlayInput', 'input': '', 'overlay': '1', 'mix': [1]},
    'fadeToBlack':             {},
    'recordingFunctions':      {'functionID': 'StartRecording'},
    'streamingFunctions':      {'functionID': 'StartStreaming', 'value': ''},
    'multicorderFunctions':    {'functionID': 'StartStopMultiCorder'},
    'externalFunctions':       {'functionID': 'StartExternal'},
    'fullscreenFunctions':     {'functionID': 'FullscreenOn'},
    'audio':                   {'input': '1', 'functionID': 'Audio'},
    'busXAudio':               {'value': 'Master', 'functionID': 'BusXAudio'},
    'setText':                 {'input': '1', 'selectedIndex': '0', 'adjustment': 'Set', 'value': '', 'encode': False},
    'replayMark':              {'functionID': 'ReplayMarkIn', 'value': '10', 'value2': '10'},
    'replayPlayLastEvent':     {'channel': 'Current'},
    'replayPlayLastEventToOutput': {'channel': 'Current'},
    'replayStopEvents':        {},
    'scriptStart':             {'value': ''},
    'command':                 {'command': '', 'encode': False},
}

# type : 'boolean' (couleur via style) ou 'advanced' (couleurs dans les options fg/bg)
VMIX_FEEDBACKS = {
    'inputPreview':  ('advanced', {'input': '1', 'mix': 1, 'fg': WHITE, 'bg': 0x00ff00, 'tally': ''}),
    'inputLive':     ('advanced', {'input': '1', 'mix': 1, 'fg': WHITE, 'bg': 0xff0000, 'tally': ''}),
    'overlayStatus': ('advanced', {'input': '', 'overlay': '1', 'fg': WHITE, 'bgPreview': 0x00ff00, 'bgProgram': 0xff0000}),
    'status':        ('boolean',  {'status': 'connection', 'value': ''}),
    'busMute':       ('boolean',  {'value': 'Master'}),
    'inputAudio':    ('boolean',  {'input': '1'}),
    'replayStatus':  ('boolean',  {'status': 'recording'}),
}


def vmix_connection_id(data, host='127.0.0.1', port=8099):
    """Renvoie la connexion vMix, en la créant (label 'vmix') si elle n'existe pas."""
    for cid, inst in data['instances'].items():
        if inst.get('moduleId') == VMIX_MODULE:
            return cid
    cid = new_id()
    order = max([i.get('sortOrder', 0) for i in data['instances'].values()] or [0]) + 1
    data['instances'][cid] = {
        'moduleInstanceType': 'connection', 'moduleId': VMIX_MODULE, 'moduleVersionId': VMIX_VERSION,
        'updatePolicy': 'stable', 'sortOrder': order, 'label': 'vmix', 'isFirstInit': False,
        'config': {
            'label': 'vmix', 'host': host, 'tcpPort': port, 'connectionErrorLog': True, 'apiPollInterval': 250,
            'volumeLinear': False, 'variablesShowInputs': True, 'variablesShowInputsLowercase': True,
            'variablesShowInputNumbers': True, 'variablesShowInputGUID': False, 'variablesShowInputPosition': False,
            'variablesShowInputCC': False, 'variablesShowInputLayers': False, 'variablesShowInputLayerPosition': False,
            'variablesShowInputList': False, 'variablesShowInputTitleIndex': False, 'variablesShowInputTitleName': False,
            'variablesShowInputVolume': False, 'variablesShowInputJSON': False, 'variablesShowAudio': False,
            'variablesShowDynamicInputs': False, 'variablesShowDynamicValues': False, 'variablesShowMix': False,
            'variablesShowOutputs': False, 'variablesShowOverlays': False, 'variablesShowReplay': True,
            'variablesShowTransitions': False, 'debugSettings': False, 'debugVariableDefinitionDelay': 2000,
            'debugVersionUpdateNotifications': True, 'audioPresets': {},
        },
        'secrets': {}, 'lastUpgradeIndex': VMIX_UPGRADE_INDEX, 'enabled': True,
    }
    print(f"+ connexion vMix créée ({host}:{port}, label 'vmix')")
    return cid


def _wrap(opts):
    return {k: {'isExpression': False, 'value': v} for k, v in opts.items()}


def act_vmix(conn, action_id, **opts):
    if action_id not in VMIX_ACTIONS:
        print(f"  ⚠ action vMix '{action_id}' sans valeurs par défaut connues : vérifier ses options dans Companion")
    merged = {**VMIX_ACTIONS.get(action_id, {}), **opts}
    return {'id': new_id(), 'definitionId': action_id, 'connectionId': conn, 'type': 'action',
            'options': _wrap(merged), 'upgradeIndex': VMIX_UPGRADE_INDEX}


def fb_vmix(conn, feedback_id, style=None, **opts):
    kind, defaults = VMIX_FEEDBACKS.get(feedback_id, ('boolean', {}))
    fb = {'id': new_id(), 'definitionId': feedback_id, 'connectionId': conn, 'type': 'feedback',
          'options': _wrap({**defaults, **{k: color(v) if k in ('fg', 'bg', 'bgPreview', 'bgProgram') else v
                                          for k, v in opts.items()}}),
          'upgradeIndex': VMIX_UPGRADE_INDEX}
    if kind == 'boolean':
        fb['isInverted'] = {'isExpression': False, 'value': False}
        fb['style'] = {k: color(v) if k in ('bgcolor', 'color') else v
                       for k, v in (style or {'bgcolor': 0xcc0000, 'color': WHITE}).items()}
    return fb


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


def macro_actions(items, conns, overlay_ids):
    """Traduit une liste d'items {get|wait|vmix} de la spec en actions Companion."""
    out = []
    for it in items:
        if 'get' in it:
            m = re.match(r'/api/deck/([^/]+)/', it['get'])
            if m and overlay_ids and m.group(1) not in overlay_ids and m.group(1) != 'score':
                print(f"  ⚠ overlay '{m.group(1)}' absent de TRANSITION_IDS dans server.js → le serveur renverra 404")
            out.append(act_get(conns['http'](), it['get']))
        elif 'wait' in it:
            out.append(act_wait(it['wait']))
        elif 'vmix' in it:
            opts = {k: v for k, v in it.items() if k != 'vmix'}
            out.append(act_vmix(conns['vmix'](), it['vmix'], **opts))
        else:
            sys.exit(f"Item de macro inconnu : {it}")
    return out


def build_macro(spec, conns, overlay_ids):
    """Bouton libre : actions HTTP PSO + vMix + waits, feedbacks vMix, 1 ou plusieurs steps."""
    sequential = spec.get('sequential', True)

    def one_step(items):
        acts = macro_actions(items, conns, overlay_ids)
        if sequential and len(acts) > 1:
            acts = [act_group(acts, 'sequential')]
        return (acts, [])

    steps_spec = spec['steps'] if 'steps' in spec else [spec.get('actions', [])]
    ctl = button(spec.get('text', ''), spec.get('bg', 0), [one_step(s) for s in steps_spec],
                 spec.get('size', 'auto'), spec.get('fg', WHITE))
    for f in spec.get('feedbacks', []):
        opts = {k: v for k, v in f.items() if k not in ('vmix', 'style')}
        ctl['feedbacks'].append(fb_vmix(conns['vmix'](), f['vmix'], f.get('style'), **opts))
    return ctl


def build(spec, conns, overlay_ids):
    """Construit un contrôle à partir d'une entrée de spec (hors 'master')."""
    kind = spec['kind']
    if kind == 'macro':
        return build_macro(spec, conns, overlay_ids)
    conn = conns['http']() if kind in ('toggle', 'get') else None
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


def cmd_apply(cfg_path, spec_path, server_js, dry_run, out_path=None, vmix_host='127.0.0.1'):
    data = load(cfg_path)
    spec = json.load(open(spec_path, encoding='utf-8-sig'))
    overlay_ids = read_overlay_ids(server_js)

    # Connexions résolues à la demande : la connexion vMix n'est créée que si la spec l'utilise.
    cache = {}
    conns = {
        'http': lambda: cache.setdefault('http', http_connection_id(data)),
        'vmix': lambda: cache.setdefault('vmix', vmix_connection_id(data, spec.get('vmix_host', vmix_host),
                                                                    spec.get('vmix_port', 8099))),
    }

    for num, p in spec.get('pages', {}).items():
        ensure_page(data, str(num), p.get('name'))

    # Les masters sont construits en dernier : ils lisent les URLs des boutons cibles.
    entries = spec['buttons']
    for b in sorted(entries, key=lambda b: b['kind'] == 'master'):
        p, r, c = b['loc'].split('/')
        page = ensure_page(data, p)
        if b['kind'] == 'master':
            ctl = build_master(b, conns['http'](), data['pages'])
        else:
            ctl = build(b, conns, overlay_ids)
        row = page['controls'].setdefault(r, {})
        if ctl is None:
            row.pop(c, None)
        else:
            row[c] = ctl
        print(f"  {b['loc']:<8} {b['kind']:<9} {b.get('text', '')!r}")

    if dry_run:
        print('Dry-run : rien écrit.')
    elif out_path:
        save(out_path, data, backup=False)
        print(f"OK — {out_path} écrit ({cfg_path} inchangé)")
    else:
        save(cfg_path, data)
        print(f"OK — {cfg_path} mis à jour (sauvegarde : .bak)")


def _summ(a, labels):
    o = a.get('options', {})
    val = lambda k: o.get(k, {}).get('value')
    d = a['definitionId']
    if d == 'get':
        return 'GET ' + val('url').replace(BASE_URL, '')
    if d == 'wait':
        return f"wait {val('time')}ms"
    if d == 'action_group':
        kids = (a.get('children') or {}).get('default', [])
        return f"[{val('execution_mode')}: " + ', '.join(_summ(k, labels) for k in kids) + ']'
    if 'location' in o:
        return f"{d}→{val('location').replace(SELF, 'self')}"
    conn = labels.get(a.get('connectionId'), a.get('connectionId'))
    if conn != 'internal':
        shown = {k: v['value'] for k, v in o.items() if v.get('value') not in ('', None, False, [])}
        return f"{conn}:{d} {json.dumps(shown, ensure_ascii=False)}"
    return d


def cmd_dump(cfg_path):
    data = load(cfg_path)
    labels = {cid: inst.get('label') for cid, inst in data['instances'].items()}
    for cid, inst in data['instances'].items():
        cfg = inst.get('config', {})
        where = cfg.get('prefix') or (f"{cfg.get('host')}:{cfg.get('tcpPort')}" if 'host' in cfg else '')
        print(f"connexion {cid} : {inst.get('moduleId')} {inst.get('moduleVersionId')} « {inst.get('label')} » {where}")
    for pn, page in sorted(data['pages'].items(), key=lambda kv: int(kv[0])):
        print(f"\n=== Page {pn} « {page.get('name', '')} »")
        for r, row in sorted(page['controls'].items(), key=lambda kv: int(kv[0])):
            for c, ctl in sorted(row.items(), key=lambda kv: int(kv[0])):
                if ctl.get('type') != 'button':
                    print(f"[{pn}/{r}/{c}] <{ctl.get('type')}>")
                    continue
                text = (ctl['style'].get('text') or '').replace('\n', ' ')
                print(f"[{pn}/{r}/{c}] {text!r} bg={ctl['style'].get('bgcolor')}")
                for fb in ctl.get('feedbacks', []):
                    print(f"    feedback: {_summ(fb, labels)}")
                for sk, st in ctl.get('steps', {}).items():
                    for side, acts in st['action_sets'].items():
                        if acts:
                            print(f"    step{sk}/{side}: " + ', '.join(_summ(a, labels) for a in acts))


def _arg(args, flag):
    return args[args.index(flag) + 1] if flag in args else None


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == 'dump':
        cmd_dump(args[1])
    elif len(args) >= 3 and args[0] == 'apply':
        cmd_apply(args[1], args[2], _arg(args, '--server'), '--dry-run' in args,
                  _arg(args, '--out'), _arg(args, '--vmix-host') or '127.0.0.1')
    else:
        print(__doc__)
        sys.exit(1)
