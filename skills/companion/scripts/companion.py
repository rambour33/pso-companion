"""Outil pour lire et générer des boutons Bitfocus Companion (format .companionconfig, v12 / Companion 4.3+).
Générique : fonctionne pour n'importe quel projet qui expose une API HTTP, et/ou pour vMix.

Usage :
  python companion.py init  <nouveau.companionconfig>
  python companion.py dump  <fichier.companionconfig>
  python companion.py apply <fichier.companionconfig> <spec.json> [--out <sortie>] [--dry-run]

Le fichier .companionconfig est du JSON compressé en gzip. `apply` fait une sauvegarde
<fichier>.bak avant d'écrire (sauf avec --out, qui écrit dans un nouveau fichier).
Voir SKILL.md pour le format de spec.json, VMIX.md pour vMix, examples/ pour des projets complets.
"""
import copy, gzip, json, os, secrets, shutil, string, sys

sys.stdout.reconfigure(encoding='utf-8')

ON_COLOR = 0x003300     # vert foncé : état actif
OFF_COLOR = 0xAA0000    # rouge      : état inactif
WHITE = 0xFFFFFF
SELF = '$(this:page)/$(this:row)/$(this:column)'
COMPANION_BUILD = '4.3.1+9209-stable-bf5535c82b'
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


def _wrap(opts):
    return {k: {'isExpression': False, 'value': v} for k, v in opts.items()}


def _next_sort_order(data):
    return max([i.get('sortOrder', 0) for i in data['instances'].values()] or [0]) + 1


def empty_config():
    """Squelette d'export complet Companion 4.3 (format v12), sans page ni connexion."""
    def surface(module):
        return {'moduleInstanceType': 'surface', 'moduleId': module, 'moduleVersionId': 'builtin',
                'updatePolicy': 'stable', 'sortOrder': 1, 'label': module, 'isFirstInit': True,
                'config': {}, 'secrets': {}, 'lastUpgradeIndex': -1, 'enabled': True}
    return {
        'version': 12, 'type': 'full', 'companionBuild': COMPANION_BUILD,
        'pages': {}, 'triggers': {}, 'triggerCollections': [],
        'custom_variables': {}, 'customVariablesCollections': [],
        'expressionVariables': {}, 'expressionVariablesCollections': [],
        'instances': {}, 'connectionCollections': [],
        'surfaces': {}, 'surfaceGroups': {}, 'surfacesRemote': {},
        'surfaceInstances': {new_id(): surface('elgato-stream-deck')},
        'surfaceInstanceCollections': [],
    }


# ── Actions internes Companion ────────────────────────────────────────────────

def act_internal(definition, **opts):
    return {'id': new_id(), 'definitionId': definition, 'connectionId': 'internal', 'type': 'action',
            'options': _wrap(opts), 'children': {}}


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


# ── HTTP (module generic-http) ────────────────────────────────────────────────
# Une URL qui ne commence pas par « http » est préfixée par la « Base URL » de la connexion.

HTTP_MODULE = 'generic-http'
HTTP_VERSION = '3.1.1'
HTTP_ACTION_UPGRADE_INDEX = 1   # format des actions « get » depuis la v3.0 du module


def http_connection_id(data, base_url=None, label='http'):
    """Renvoie la connexion HTTP (la première, ou celle portant `label`), en la créant si besoin."""
    candidates = [(cid, i) for cid, i in data['instances'].items() if i.get('moduleId') == HTTP_MODULE]
    for cid, inst in candidates:
        if inst.get('label') == label:
            return cid
    if candidates and not base_url:
        return candidates[0][0]
    if not base_url:
        sys.exit("Aucune connexion generic-http dans la config : ajouter \"http\": {\"base_url\": \"http://…\"} "
                 "dans la spec pour la créer.")
    cid = new_id()
    data['instances'][cid] = {
        'moduleInstanceType': 'connection', 'moduleId': HTTP_MODULE, 'moduleVersionId': HTTP_VERSION,
        'updatePolicy': 'stable', 'sortOrder': _next_sort_order(data), 'label': label, 'isFirstInit': False,
        'config': {'prefix': base_url, 'proxyAddress': '', 'rejectUnauthorized': True},
        'secrets': {}, 'lastUpgradeIndex': HTTP_ACTION_UPGRADE_INDEX, 'enabled': True,
    }
    print(f"+ connexion HTTP créée (label '{label}', Base URL {base_url})")
    return cid


def act_http(conn, url, method='get', body=None):
    opts = {
        'url': url, 'header': '',
        'jsonResultDataVariable': None, 'result_stringify': True, 'statusCodeVariable': None,
    }
    if method != 'get':
        # Mêmes options et défauts que le module (src/fields.js) : corps JSON « {} » par défaut.
        opts['body'] = '{}' if body is None else body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        if method != 'delete':
            opts['contenttype'] = 'application/json'
        else:
            del opts['statusCodeVariable']
    options = _wrap(opts)
    for k in ('jsonResultDataVariable', 'statusCodeVariable'):
        if k in options:
            options[k] = {'isExpression': False}
    return {'id': new_id(), 'definitionId': method, 'connectionId': conn, 'type': 'action',
            'options': options, 'upgradeIndex': HTTP_ACTION_UPGRADE_INDEX}


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
    data['instances'][cid] = {
        'moduleInstanceType': 'connection', 'moduleId': VMIX_MODULE, 'moduleVersionId': VMIX_VERSION,
        'updatePolicy': 'stable', 'sortOrder': _next_sort_order(data), 'label': 'vmix', 'isFirstInit': False,
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


def items_to_actions(items, conns):
    """Traduit une liste d'items de spec en actions Companion.

    Items : {"get": url} · {"post"|"put"|"patch"|"delete": url, "body": …} · {"wait": ms} · {"vmix": id, …options}
    """
    out = []
    for it in items:
        method = next((m for m in ('get', 'post', 'put', 'patch', 'delete') if m in it), None)
        if method:
            out.append(act_http(conns['http'](it.get('connection')), it[method], method, it.get('body')))
        elif 'wait' in it:
            out.append(act_wait(it['wait']))
        elif 'vmix' in it:
            opts = {k: v for k, v in it.items() if k != 'vmix'}
            out.append(act_vmix(conns['vmix'](), it['vmix'], **opts))
        else:
            sys.exit(f"Item inconnu : {it}")
    return out


def _step_actions(items, conns, sequential):
    acts = items_to_actions(items, conns)
    if sequential and len(acts) > 1:
        acts = [act_group(acts, 'sequential')]
    return acts


def build_macro(spec, conns):
    """Bouton libre : HTTP + vMix + waits, feedbacks vMix, 1 ou plusieurs steps."""
    sequential = spec.get('sequential', True)
    steps_spec = spec['steps'] if 'steps' in spec else [spec.get('actions', [])]
    ctl = button(spec.get('text', ''), spec.get('bg', 0),
                 [(_step_actions(s, conns, sequential), []) for s in steps_spec],
                 spec.get('size', 'auto'), spec.get('fg', WHITE))
    for f in spec.get('feedbacks', []):
        opts = {k: v for k, v in f.items() if k not in ('vmix', 'style')}
        ctl['feedbacks'].append(fb_vmix(conns['vmix'](), f['vmix'], f.get('style'), **opts))
    return ctl


def build_toggle(spec, conns):
    """Bouton à 2 états : 1er appui = actions `on` + couleur on, 2e appui = actions `off` + couleur off."""
    on, off = spec.get('on_color', ON_COLOR), spec.get('off_color', OFF_COLOR)
    on_items = spec.get('on') or [{'get': spec['on_url']}]
    off_items = spec.get('off') or [{'get': spec['off_url']}]
    sequential = spec.get('sequential', True)
    ctl = button(spec.get('text', ''), off if spec.get('start_off') else on, [
        (_step_actions(on_items, conns, sequential) + [act_bgcolor(SELF, on)], []),
        (_step_actions(off_items, conns, sequential) + [act_bgcolor(SELF, off)], []),
    ], spec.get('size', 'auto'), spec.get('fg', WHITE))
    for f in spec.get('feedbacks', []):
        opts = {k: v for k, v in f.items() if k not in ('vmix', 'style')}
        ctl['feedbacks'].append(fb_vmix(conns['vmix'](), f['vmix'], f.get('style'), **opts))
    return ctl


def build(spec, conns):
    """Construit un contrôle à partir d'une entrée de spec (hors 'master')."""
    kind = spec['kind']
    text = spec.get('text', '')
    if kind == 'macro':
        return build_macro(spec, conns)
    if kind == 'toggle':
        return build_toggle(spec, conns)
    if kind == 'get':
        urls = spec['urls'] if 'urls' in spec else [spec['url']]
        conn = conns['http'](spec.get('connection'))
        return button(text, spec.get('bg', 0), [([act_http(conn, u) for u in urls], [])], spec.get('size', 'auto'))
    if kind == 'page_up':
        return button(text or '⬆️', 0, [([act_page('dec_page')], [])])
    if kind == 'page_down':
        return button(text or '⬇️', 0, [([act_page('inc_page')], [])])
    if kind in ('pagenum', 'pageup', 'pagedown'):
        return {'type': kind}
    if kind == 'empty':
        return None
    sys.exit(f"Type de bouton inconnu : {kind}")


def _refresh_ids(action):
    action['id'] = new_id()
    for kids in (action.get('children') or {}).values():
        for k in kids or []:
            _refresh_ids(k)
    return action


def step_payload(ctl, step):
    """Actions « métier » d'un step (sans recoloration ni synchro de steps), copiées avec de nouveaux ids."""
    acts = ctl.get('steps', {}).get(str(step), {}).get('action_sets', {}).get('down', [])
    skip = ('bgcolor', 'button_set_current_step', 'bank_current_step')
    return [_refresh_ids(copy.deepcopy(a)) for a in acts
            if not (a.get('connectionId') == 'internal' and a.get('definitionId') in skip)]


def build_master(spec, pages):
    """Bouton maître : rejoue step 0 / step 1 de chaque cible, recolore et resynchronise leurs steps."""
    targets = spec['targets']
    on, off = spec.get('on_color', ON_COLOR), spec.get('off_color', OFF_COLOR)
    on_acts, off_acts = [], []
    for loc in targets:
        p, r, c = loc.split('/')
        ctl = pages.get(p, {}).get('controls', {}).get(r, {}).get(c)
        if not ctl:
            sys.exit(f"Master : cible {loc} introuvable")
        on_acts += step_payload(ctl, 0)
        off_acts += step_payload(ctl, 1)

    def step(acts, c, next_step):
        return (acts + [act_bgcolor(SELF, c)] + [act_bgcolor(t, c) for t in targets]
                + [act_set_step(t, next_step) for t in targets], [])

    # Après « tout activer », chaque cible doit être prête à désactiver (step 1), et inversement.
    return button(spec.get('text', 'ALL'), on, [step(on_acts, on, 1), step(off_acts, off, 0)],
                  spec.get('size', 'auto'))


# ── Commandes ─────────────────────────────────────────────────────────────────

def ensure_page(data, num, name=None):
    pages = data['pages']
    if num not in pages:
        pages[num] = {'id': new_id(), 'name': name or '', 'controls': {},
                      'gridSize': {'minColumn': 0, 'maxColumn': 7, 'minRow': 0, 'maxRow': 3}}
        print(f"+ page {num} créée")
    elif name is not None:
        pages[num]['name'] = name
    return pages[num]


def cmd_init(out_path):
    if os.path.exists(out_path):
        sys.exit(f"{out_path} existe déjà : choisir un autre nom (init ne remplace jamais un fichier).")
    save(out_path, empty_config(), backup=False)
    print(f"OK — {out_path} créé (vide). Ajouter des boutons avec : apply {out_path} <spec.json>")


def cmd_apply(cfg_path, spec_path, dry_run, out_path=None):
    data = load(cfg_path)
    spec = json.load(open(spec_path, encoding='utf-8-sig'))
    http_cfg = spec.get('http', {})
    vmix_cfg = spec.get('vmix', {})

    # Connexions résolues à la demande : une connexion n'est créée que si la spec l'utilise.
    cache = {}

    def http(label=None):
        key = 'http:' + (label or http_cfg.get('label', 'http'))
        if key not in cache:
            cache[key] = http_connection_id(data, http_cfg.get('base_url') if not label else None,
                                            label or http_cfg.get('label', 'http'))
        return cache[key]

    def vmix():
        if 'vmix' not in cache:
            cache['vmix'] = vmix_connection_id(data, vmix_cfg.get('host', spec.get('vmix_host', '127.0.0.1')),
                                               vmix_cfg.get('port', spec.get('vmix_port', 8099)))
        return cache['vmix']

    conns = {'http': http, 'vmix': vmix}

    for num, p in spec.get('pages', {}).items():
        ensure_page(data, str(num), p.get('name'))

    # Les masters sont construits en dernier : ils lisent les actions des boutons cibles.
    for b in sorted(spec['buttons'], key=lambda b: b['kind'] == 'master'):
        p, r, c = b['loc'].split('/')
        page = ensure_page(data, p)
        ctl = build_master(b, data['pages']) if b['kind'] == 'master' else build(b, conns)
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


def _summ(a, labels, prefixes):
    o = a.get('options', {})
    val = lambda k: o.get(k, {}).get('value')
    d = a['definitionId']
    conn = a.get('connectionId')
    if d in ('get', 'post', 'put', 'patch', 'delete') and 'url' in o:
        url = val('url') or ''
        pre = prefixes.get(conn)
        if pre and url.startswith(pre):
            url = url[len(pre):]
        return f"{d.upper()} {url}"
    if d == 'wait':
        return f"wait {val('time')}ms"
    if d == 'action_group':
        kids = (a.get('children') or {}).get('default', [])
        return f"[{val('execution_mode')}: " + ', '.join(_summ(k, labels, prefixes) for k in kids) + ']'
    if 'location' in o:
        return f"{d}→{(val('location') or '').replace(SELF, 'self')}"
    label = labels.get(conn, conn)
    if label != 'internal':
        shown = {k: v.get('value') for k, v in o.items() if v.get('value') not in ('', None, False, [])}
        return f"{label}:{d} {json.dumps(shown, ensure_ascii=False)}"
    return d


def cmd_dump(cfg_path):
    data = load(cfg_path)
    labels = {cid: inst.get('label') for cid, inst in data['instances'].items()}
    prefixes = {cid: inst.get('config', {}).get('prefix') for cid, inst in data['instances'].items()}
    for cid, inst in data['instances'].items():
        cfg = inst.get('config', {})
        where = cfg.get('prefix') or (f"{cfg.get('host')}:{cfg.get('tcpPort')}" if 'host' in cfg else '')
        print(f"connexion {cid} : {inst.get('moduleId')} {inst.get('moduleVersionId')} « {inst.get('label')} » {where}")
    for pn, page in sorted(data['pages'].items(), key=lambda kv: int(kv[0])):
        print(f"\n=== Page {pn} « {page.get('name', '')} »")
        grid = page.get('gridSize', {})
        for r, row in sorted(page['controls'].items(), key=lambda kv: int(kv[0])):
            for c, ctl in sorted(row.items(), key=lambda kv: int(kv[0])):
                outside = grid and (int(r) > grid.get('maxRow', 99) or int(c) > grid.get('maxColumn', 99))
                flag = '  ⚠ hors de la grille (invisible sur le deck)' if outside else ''
                if ctl.get('type') != 'button':
                    print(f"[{pn}/{r}/{c}] <{ctl.get('type')}>{flag}")
                    continue
                text = (ctl['style'].get('text') or '').replace('\n', ' ')
                print(f"[{pn}/{r}/{c}] {text!r} bg={ctl['style'].get('bgcolor')}{flag}")
                for fb in ctl.get('feedbacks', []):
                    print(f"    feedback: {_summ(fb, labels, prefixes)}")
                for sk, st in ctl.get('steps', {}).items():
                    for side, acts in st['action_sets'].items():
                        if acts:
                            print(f"    step{sk}/{side}: " + ', '.join(_summ(a, labels, prefixes) for a in acts))


def _arg(args, flag):
    return args[args.index(flag) + 1] if flag in args else None


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == 'init':
        cmd_init(args[1])
    elif len(args) >= 2 and args[0] == 'dump':
        cmd_dump(args[1])
    elif len(args) >= 3 and args[0] == 'apply':
        cmd_apply(args[1], args[2], '--dry-run' in args, _arg(args, '--out'))
    else:
        print(__doc__)
        sys.exit(1)
