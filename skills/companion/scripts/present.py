"""Présentation HTML d'un export Companion : chaque page dessinée, puis la fonction de chaque touche.

Usage :
  python present.py <fichier.companionconfig> [--out page.html] [--fps 60] [--back /]

Sans --out, la page est écrite sur la sortie standard (utilisé par le serveur de skills).
--fps sert à convertir en secondes les déplacements de replay exprimés en images.
--back ajoute un lien de retour vers cette adresse.
"""
import html, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
from companion import load

args = sys.argv[1:]
if not args:
    print(__doc__)
    sys.exit(1)
_arg = lambda flag, dflt=None: args[args.index(flag) + 1] if flag in args else dflt
SRC = args[0]
OUT = _arg('--out')
FPS = float(_arg('--fps', 60))
BACK = _arg('--back')
data = load(SRC)
labels = {cid: i.get('label') for cid, i in data['instances'].items()}

# Présentation des pages connues des exemples du skill, reconnues par leur nom.
PAGE_INTRO = {
    'clipping xl': "Fabrication des clips replay : marquer un moment, ajuster ses points d'entrée et de sortie, choisir sa vitesse et ses caméras, se déplacer dans l'enregistrement.",
    'playback reg': "Diffusion des clips : lancer le clip sélectionné ou toute la liste, régler la vitesse, avancer ou reculer, écouter le programme ou le replay en solo.",
    'clip/play reg': "Version compacte qui réunit l'essentiel du clipping et du playout sur une seule page.",
    'vmix live': "Automatisations du direct : lancement et fin du live, replay rapide, mutes, sorties d'overlays et réglage de la transition 1.",
    'vmix régie': "Le pupitre : preview et programme des inputs 1 à 8 avec tally, transitions, stingers, overlays, enregistrement et stream.",
    'vmix audio': "Tout le son : mutes du Master, des bus et des inputs 1 à 8, solos, volume et fondus.",
    'vmix lecture': "Lecture des médias sur l'input en preview, playlist et compte à rebours du titre TIMER.",
    'vmix transitions': "Transitions automatiques, stingers 3 et 4, overlays 1 à 4, T-bar et transitions rapides.",
    'vmix sorties': "Toutes les sorties : External, Fullscreen, SRT, snapshot, stream par destination, enregistrement et source de chaque sortie.",
    'vmix sources': "Ajout de nouvelles sources et changement de la source des inputs Browser (WEB) et NDI (NDI).",
    'vmix auto': "Automatisations qui enchaînent l'API du projet et vMix, avec des pauses.",
}

def opt(a, k, default=None):
    v = a.get('options', {}).get(k, {})
    return v.get('value', default) if isinstance(v, dict) else default

def secs(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{f:g}".replace('.', ',')

REPLAY_CMD = {
    'ReplayPlayBackward': "lit le replay en arrière",
    'ReplayPlayForward': "lit le replay en avant",
    'ReplayPlay': "lance la lecture du replay",
    'ReplayPause': "met le replay en pause",
    'ReplayPlayPause': "lecture / pause du replay",
    'ReplaySetDirectionForward': "remet le sens de lecture vers l'avant",
    'ReplaySelectPreviousEvent': "sélectionne le clip précédent de la liste",
    'ReplaySelectNextEvent': "sélectionne le clip suivant de la liste",
    'ReplayMarkIn': "marque le début d'un clip",
    'ReplayMarkOut': "marque la fin du clip",
    'ReplayMarkCancel': "annule le marquage en cours",
    'ReplayJumpToSelectedInPoint': "saute au début du clip sélectionné",
    'ReplayJumpToSelectedOutPoint': "saute à la fin du clip sélectionné",
    'ReplayUpdateSelectedInPoint': "remplace le début du clip sélectionné par la position actuelle",
    'ReplayUpdateSelectedOutPoint': "remplace la fin du clip sélectionné par la position actuelle",
    'ReplaySelectAllEvents': "sélectionne tous les clips de la liste",
    'ReplayPlayNext': "enchaîne sur le clip suivant",
    'ReplayPlaySelectedEvent': "diffuse le clip sélectionné",
    'ReplayPlayAllEvents': "diffuse tous les clips de la liste à la suite",
    'ReplayStopEvents': "arrête la diffusion des clips",
    'ReplayRecorded': "passe le replay en mode « enregistré » (hors direct)",
}

def describe_command(cmd):
    parts = cmd.split(' ', 1)
    fn, params = parts[0], (parts[1] if len(parts) > 1 else '')
    val = re.search(r'value=([-\d.,]+)', params, re.I)
    v = val.group(1) if val else None
    if fn == 'ReplayUpdateSelectedSpeedFromValue':
        return f"règle la vitesse du clip sélectionné à {round(float(v) * 100)} %"
    if fn == 'ReplaySetSpeed':
        return f"règle la vitesse de lecture à {round(float(v) * 100)} %"
    if fn in ('ReplayMoveSelectedInPoint', 'ReplayMoveSelectedOutPoint'):
        which = "le début" if 'In' in fn else "la fin"
        n = int(float(v))
        sens = "recule" if n < 0 else "avance"
        return f"{sens} {which} du clip sélectionné de {abs(n)} images (≈ {secs(round(abs(n) / FPS, 2))} s à {secs(FPS)} i/s)"
    if fn == 'ReplaySelectedEventSingleCameraOn':
        return f"le clip sélectionné n'utilise plus que la caméra {v}"
    m = re.match(r'ReplayCamera(\d)', fn)
    if m:
        return f"affiche la caméra {m.group(1)} sur la sortie replay"
    return REPLAY_CMD.get(fn, f"fonction vMix « {cmd} »")

TRANS_NAMES = {'Cut': 'cut', 'Fade': 'fondu', 'Zoom': 'zoom', 'Wipe': 'volet', 'Slide': 'glissement', 'Fly': 'fly',
               'Cube': 'cube', 'Merge': 'merge', 'CrossZoom': 'cross zoom', 'VerticalWipe': 'volet vertical'}
SOURCE_NAMES = {'Output': 'le programme', 'Preview': 'la preview', 'MultiView': 'le multiview', 'Replay': 'le replay'}
OUTPUT_NAMES = {'SetOutput2': "l'Output 2", 'SetOutputFullscreen': 'le Fullscreen 1', 'SetOutputFullscreen2': 'le Fullscreen 2',
                'SetOutputExternal2': "l'External 2", 'SetOutput3': "l'Output 3", 'SetOutput4': "l'Output 4"}
ADD_TYPES = {'Video': 'une vidéo', 'Image': 'une image', 'Photos': 'un diaporama du dossier', 'Title': 'un titre',
             'VideoList': 'une playlist', 'Colour': 'un fond de couleur', 'AudioFile': 'un fichier audio',
             'PowerPoint': 'une présentation PowerPoint', 'Flash': 'une animation Flash'}

def inp(v):
    return f"l'input {v}" if str(v).isdigit() else f"l'input « {v} »"

def var(v):
    return re.sub(r'\$\(custom:([\w-]+)\)', r'la variable \1', str(v))

def describe(a):
    d = a['definitionId']
    conn = labels.get(a.get('connectionId'), a.get('connectionId'))
    f = lambda k, dflt=None: opt(a, k, dflt)
    if d == 'wait':
        ms = int(float(f('time', 0) or 0))
        return None if ms < 50 else f"attend {secs(ms / 1000)} s"
    if d == 'action_group':
        kids = (a.get('children') or {}).get('default', [])
        return [x for k in kids for x in flat(describe(k))]
    if d == 'inc_page': return "page suivante"
    if d == 'dec_page': return "page précédente"
    if d in ('bgcolor', 'button_set_current_step', 'bank_current_step'): return None
    if d == 'command': return describe_command(f('command', ''))
    if d in ('get', 'post'): return f"requête {d.upper()} {f('url')}"
    fid = f('functionID')
    if d == 'replayMark':
        n = f('value')
        return {'ReplayMarkInOutLive': f"crée un clip des {n} dernières secondes du direct",
                'ReplayMarkInRecorded': "marque le début d'un clip à la position de lecture",
                'ReplayMarkIn': "marque le début d'un clip", 'ReplayMarkOut': "marque la fin du clip"}.get(fid, f"marquage replay ({fid})")
    if d == 'replayFastForwardBackward':
        return f"{'avance' if 'Forward' in fid else 'retour'} rapide ×{f('value')}"
    if d == 'replayPause': return "met le replay en pause"
    if d == 'replayJumpToNow': return "revient au direct dans l'enregistrement replay"
    if d == 'replayChangeDirection': return "inverse le sens de lecture du replay"
    if d == 'replayPlayLastEventToOutput': return "diffuse le dernier clip sur la sortie"
    if d == 'replayStopEvents': return "arrête la diffusion des clips"
    if d == 'replayRecording': return "démarre / arrête l'enregistrement du replay"
    if d == 'transitionMix':
        name = TRANS_NAMES.get(fid, fid)
        dur = f"en {secs(int(f('duration', 0)) / 1000)} s" if fid != 'Cut' else "sans transition"
        return f"passe la preview à l'antenne : {name} {dur}"
    if d == 'transition':
        return f"lance le stinger {fid[-1]}" if fid.startswith('Stinger') else f"lance la transition automatique {fid[-1]} réglée dans vMix"
    if d == 'setTransitionEffect': return f"la transition 1 devient : {TRANS_NAMES.get(f('value'), f('value'))}"
    if d == 'setTransitionDuration': return f"la transition 1 dure désormais {secs(int(f('value')) / 1000)} s"
    if d == 'previewInput': return f"met {inp(f('input'))} en preview"
    if d == 'programCut': return f"envoie {inp(f('input'))} directement à l'antenne"
    if d == 'previewInputNext': return "met l'input suivant en preview"
    if d == 'previewInputPrevious': return "met l'input précédent en preview"
    if d == 'overlayFunctions':
        t, n = f('type'), f('overlay')
        return {'OverlayInput': f"met l'input en preview dans l'overlay {n} (ou l'enlève s'il y est)",
                'In': f"fait entrer l'input en preview dans l'overlay {n}",
                'Out': f"fait sortir l'overlay {n} avec sa transition",
                'Off': f"coupe l'overlay {n} immédiatement",
                'OverlayInputAllOff': "retire tous les overlays"}.get(t, f"overlay {n} ({t})")
    if d == 'fadeToBlack': return "fondu au noir (appuyer à nouveau pour revenir)"
    if d in ('recordingFunctions', 'streamingFunctions', 'multicorderFunctions', 'externalFunctions', 'srtFunctions', 'fullscreenFunctions'):
        what = {'recordingFunctions': "l'enregistrement", 'streamingFunctions': "le stream", 'multicorderFunctions': "le MultiCorder",
                'externalFunctions': "la sortie External", 'srtFunctions': "la sortie SRT", 'fullscreenFunctions': "le plein écran"}[d]
        if d == 'streamingFunctions' and f('value') not in ('', None):
            what = f"le stream {f('value')}"
        verb = "démarre" if fid.startswith('Start') and not fid.startswith('StartStop') else \
               "arrête" if fid.startswith('Stop') else "démarre / arrête"
        if d == 'fullscreenFunctions': verb = "active / désactive"
        return f"{verb} {what}"
    if d == 'busXAudio':
        return "coupe / rétablit le son du Master" if f('value') == 'Master' else f"coupe / rétablit le son du bus {f('value')}"
    if d == 'audio': return f"coupe / rétablit le son de {inp(f('input'))}"
    if d == 'solo': return f"met {inp(f('input'))} en solo (écoute seule) ou l'enlève"
    if d == 'soloAllOff': return "coupe tous les solos"
    if d == 'audioMixerShowHide': return "affiche / cache la fenêtre du mixer audio"
    if d == 'setBusVolumeFade':
        bus = 'du Master' if f('value') == 'Master' else f"du bus {f('value')}"
        return f"fondu du volume {bus} jusqu'à {f('fadeVol')} % en {secs(int(f('fadeTime')) / 1000)} s (vMix 28+)"
    if d == 'setBusVolume':
        bus = 'du Master' if f('value') == 'Master' else f"du bus {f('value')}"
        adj = {'Set': f"règle le volume {bus} à {f('amount')} %", 'Increase': f"monte le volume {bus} de {f('amount')}",
               'Decrease': f"baisse le volume {bus} de {f('amount')}"}
        return adj[f('adjustment')]
    if d == 'videoActions':
        return {'Play': "lance la lecture", 'Pause': "met en pause", 'PlayPause': "lecture / pause", 'Restart': "revient au début",
                'Loop': "active / désactive la boucle"}.get(fid, fid) + " de l'input en preview"
    if d == 'videoPlayhead':
        ms = int(f('value') or 0)
        return {'Set': "remet la tête de lecture au début", 'Increase': f"avance de {secs(ms / 1000)} s",
                'Decrease': f"recule de {secs(ms / 1000)} s"}[f('adjustment')] + " (input en preview)"
    if d == 'videoMark':
        return {'MarkIn': "place le point d'entrée", 'MarkOut': "place le point de sortie",
                'MarkReset': "efface les points d'entrée et de sortie"}.get(fid, fid) + " de la vidéo en preview"
    if d == 'playListFunctions':
        return {'StartPlayList': "démarre la playlist", 'StopPlayList': "arrête la playlist",
                'NextPlayListEntry': "passe à l'élément suivant de la playlist",
                'PreviousPlayListEntry': "revient à l'élément précédent de la playlist"}[fid]
    if d == 'controlCountdown':
        return {'StartCountdown': "démarre", 'PauseCountdown': "met en pause", 'StopCountdown': "arrête"}[fid] + \
               f" le compte à rebours du titre « {f('input')} »"
    if d == 'tbar':
        return f"place le T-bar à {round(int(f('value')) / 255 * 100)} %"
    if d == 'outputSet':
        return f"{OUTPUT_NAMES.get(fid, fid)} affiche {SOURCE_NAMES.get(f('value'), f('value'))}"
    if d == 'snapshot': return "enregistre une image fixe de la sortie (nom horodaté)"
    if d == 'writeDurationToRecordingLog': return "note la durée d'enregistrement actuelle dans le journal (repère)"
    if d == 'addInput':
        t, _, path = str(f('value')).partition('|')
        if t == 'Colour':
            return f"ajoute un fond de couleur {var(path)}"
        return f"ajoute {ADD_TYPES.get(t, t)} : fichier indiqué par {var(path)}"
    if d == 'browserNavigate': return f"l'input Browser « {f('input')} » ouvre la page de {var(f('value'))}"
    if d == 'browser': return f"recharge la page de l'input Browser « {f('input')} »"
    if d == 'ndiSelectSource': return f"l'input NDI « {f('input')} » prend la source de {var(f('value'))}"
    if d == 'undo': return "rouvre le dernier input fermé"
    if d == 'createVirtualInput': return f"crée une copie virtuelle de {inp(f('input'))}"
    return f"{conn} : {d}"

def flat(x):
    if x is None: return []
    return x if isinstance(x, list) else [x]

FB = {
    'inputPreview': lambda f: f"vert quand {inp(f('input'))} est en preview",
    'inputLive': lambda f: f"rouge quand {inp(f('input'))} est à l'antenne",
    'overlayStatus': lambda f: f"vert si l'overlay {f('overlay')} est en preview, rouge s'il est à l'antenne",
    'busMute': lambda f: f"rouge quand {'le Master' if f('value') == 'Master' else 'le bus ' + str(f('value'))} est muté",
    'inputAudio': lambda f: f"rouge quand {inp(f('input'))} est muté",
    'inputSolo': lambda f: f"allumé quand {inp(f('input'))} est en solo",
    'replayStatus': lambda f: "rouge pendant " + ("l'enregistrement du replay" if f('status') == 'recording' else "la diffusion d'un replay"),
    'status': lambda f: {'connection': "vert quand Companion est connecté à vMix", 'fadeToBlack': "rouge pendant le fondu au noir",
                         'recording': "rouge pendant l'enregistrement", 'streaming': "rouge pendant le stream" + (f" {int(f('value')) + 1}" if f('value') not in ('', None) else ''),
                         'multiCorder': "rouge pendant le MultiCorder", 'external': "rouge quand External est actif",
                         'fullscreen': "rouge quand le plein écran est actif", 'playList': "rouge quand la playlist tourne"}.get(f('status'), f('status')),
}

def key_text(t):
    return (t or '').replace('\\n', '\n')

def hexcol(n):
    """Couleur Companion : entier, chaîne numérique, « #rrggbb » ou « rgb(r,g,b) »."""
    if isinstance(n, str):
        s = n.strip()
        if s.startswith('#'):
            return s
        m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', s)
        if m:
            return '#%02x%02x%02x' % tuple(int(x) for x in m.groups())
        n = int(s) if s.isdigit() else 0
    return '#%06x' % (n or 0)

pages_html, nav = [], []
for pn in sorted(data['pages'], key=int):
    page = data['pages'][pn]
    ctrls = page['controls']
    cells, rows_desc = [], []
    for r in range(4):
        items = []
        for c in range(8):
            ctl = ctrls.get(str(r), {}).get(str(c))
            if not ctl or ctl.get('type') != 'button':
                cells.append('<div class="key empty"></div>')
                continue
            st = ctl['style']
            txt = key_text(st.get('text'))
            fbs = [FB[fb['definitionId']](lambda k, dflt=None, fb=fb: opt(fb, k, dflt)) for fb in ctl.get('feedbacks', []) if fb['definitionId'] in FB]
            step0 = ctl.get('steps', {}).get('0', {}).get('action_sets', {})
            down = [x for a in step0.get('down', []) for x in flat(describe(a))]
            up = [x for a in step0.get('up', []) for x in flat(describe(a))]
            nav_key = down in (["page suivante"], ["page précédente"])
            cls = 'key nav' if nav_key else 'key'
            dot = '<span class="fb"></span>' if fbs else ''
            cells.append(f'<div class="{cls}" style="background:{hexcol(st.get("bgcolor"))};color:{hexcol(st.get("color", 0xffffff))}">'
                         f'{html.escape(txt)}{dot}</div>')
            if nav_key:
                continue
            desc = '<ol>' + ''.join(f'<li>{html.escape(x)}</li>' for x in down) + '</ol>' if len(down) > 1 else \
                   f'<p>{html.escape(down[0][:1].upper() + down[0][1:])}</p>' if down else '<p class="muted">Aucune action : témoin</p>'
            if up:
                desc += '<p class="up"><b>Au relâchement :</b> ' + html.escape(', '.join(up)) + '</p>'
            if fbs:
                desc += '<p class="fbline"><b>Couleur :</b> ' + html.escape(' · '.join(fbs)) + '</p>'
            label = html.escape(txt.replace('\n', ' '))
            items.append(f'<li><div class="chip" style="background:{hexcol(st.get("bgcolor"))};color:{hexcol(st.get("color", 0xffffff))}">{label}</div>'
                         f'<div class="d"><span class="pos">{pn}/{r}/{c}</span>{desc}</div></li>')
        if items:
            rows_desc.append(f'<h4>Ligne {r + 1}</h4><ul class="keys">{"".join(items)}</ul>')
    name = html.escape(page.get('name') or f'Page {pn}')
    nav.append(f'<a href="#p{pn}"><b>{pn}</b> {name}</a>')
    pages_html.append(f'''
<section id="p{pn}" class="page">
  <div class="page-head"><span class="num">Page {pn}</span><h2>{name}</h2></div>
  <p class="lead">{html.escape(PAGE_INTRO.get((page.get('name') or '').strip().lower(), ''))}</p>
  <div class="deck-wrap"><div class="deck" aria-label="Touches de la page {pn}">{''.join(cells)}</div></div>
  {''.join(rows_desc)}
</section>''')

conns = ' · '.join(f"<code>{html.escape(i['label'])}</code> ({html.escape(i['moduleId'])} {html.escape(str(i.get('moduleVersionId')))})"
                   for i in data['instances'].values())
cvars = data.get('custom_variables', {})
vars_rows = ''.join(f'<tr><td><code>$(custom:{html.escape(k)})</code></td><td>{html.escape(v.get("description", ""))}</td></tr>'
                    for k, v in sorted(cvars.items(), key=lambda kv: kv[1].get('sortOrder', 0)))

FILE = os.path.basename(SRC)
TITLE = os.path.splitext(FILE)[0]
BACK_LINK = f'<a class="back" href="{html.escape(BACK)}">← Catalogue</a>' if BACK else ''
VARS_SECTION = f'''<section class="page">
  <h2>Variables à régler</h2>
  <p class="lead">Utilisées par la page Sources. Elles se modifient dans Companion, onglet Variables → Custom variables, sans regénérer le fichier.</p>
  <div class="tw"><table>{vars_rows}</table></div>
</section>''' if vars_rows else ''
HTML = f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(TITLE)} · Stream Deck</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#f3f5f7;--surface:#fff;--surface-2:#e9edf1;--ink:#14191f;--ink-2:#4a5561;--line:#d3dae1;--accent:#0b6f78;--accent-ink:#fff;--code-bg:#e8ecf0;--deck:#15181c;
--display:"Barlow Condensed","Arial Narrow",sans-serif;--body:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;--mono:"IBM Plex Mono",Consolas,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#0f1316;--surface:#161b20;--surface-2:#1d242a;--ink:#e6ebef;--ink-2:#a3afba;--line:#2b343c;--accent:#4fc1c9;--accent-ink:#06282b;--code-bg:#1f272e;--deck:#0a0c0e}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#0f1316;--surface:#161b20;--surface-2:#1d242a;--ink:#e6ebef;--ink-2:#a3afba;--line:#2b343c;--accent:#4fc1c9;--accent-ink:#06282b;--code-bg:#1f272e;--deck:#0a0c0e}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--ink);font:16px/1.55 var(--body);padding-inline:20px;padding-block:0 64px}}
code{{font-family:var(--mono);font-size:.86em;background:var(--code-bg);padding:.1em .35em;border-radius:4px}}
h1,h2,h4{{font-family:var(--display);text-transform:uppercase;letter-spacing:.02em;line-height:1.05;text-wrap:balance}}
.wrap{{max-width:1100px;margin:0 auto}}
header{{padding-block:36px 20px;border-bottom:1px solid var(--line);margin-bottom:20px}}
.eyebrow{{font-family:var(--display);font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}}
h1{{font-size:clamp(2.4rem,6vw,3.8rem);margin:.1em 0 .2em}}
header p{{color:var(--ink-2);max-width:70ch;margin:.3em 0}}
nav{{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);padding-block:10px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:6px}}
nav a{{text-decoration:none;color:var(--ink-2);border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:3px 12px;font-size:.88rem;white-space:nowrap}}
nav a b{{color:var(--accent);margin-right:2px}}
nav a:hover{{color:var(--ink);border-color:var(--accent)}}
.page{{padding-block:34px 10px;border-bottom:1px solid var(--line);scroll-margin-top:60px}}
.page-head{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}}
.num{{font-family:var(--mono);font-size:.85rem;color:var(--accent)}}
h2{{font-size:2.2rem;margin:0}}
.lead{{color:var(--ink-2);max-width:72ch;margin:.4em 0 18px}}
.deck-wrap{{overflow-x:auto;padding-bottom:6px}}
.deck{{background:var(--deck);border-radius:16px;padding:14px;display:grid;grid-template-columns:repeat(8,74px);gap:8px;width:max-content;box-shadow:0 8px 24px rgba(0,0,0,.18)}}
.key{{width:74px;height:74px;border-radius:9px;border:1px solid #000;display:flex;align-items:center;justify-content:center;text-align:center;white-space:pre-line;font:600 10.5px/1.15 var(--body);padding:4px;position:relative;overflow:hidden;word-break:break-word}}
.key.empty{{background:#1b1f24;border-color:#111}}
.key.nav{{font-size:22px}}
.key .fb{{position:absolute;top:4px;right:4px;width:7px;height:7px;border-radius:50%;background:#fff;opacity:.85;box-shadow:0 0 0 1px rgba(0,0,0,.4)}}
h4{{font-size:1.1rem;color:var(--ink-2);margin:22px 0 8px;letter-spacing:.08em}}
ul.keys{{list-style:none;padding:0;margin:0;display:grid;gap:6px}}
ul.keys li{{display:grid;grid-template-columns:150px minmax(0,1fr);gap:14px;align-items:start;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 14px}}
@media (max-width:560px){{ul.keys li{{grid-template-columns:minmax(0,1fr)}}}}
.chip{{border-radius:7px;padding:6px 8px;font:600 .8rem/1.2 var(--body);text-align:center;border:1px solid rgba(0,0,0,.35)}}
.d{{min-width:0;font-size:.93rem}}
.d p{{margin:0}}
.d ol{{margin:0;padding-left:1.2em}}
.pos{{float:right;font-family:var(--mono);font-size:.72rem;color:var(--ink-2);margin-left:10px}}
.up,.fbline{{margin-top:4px!important;color:var(--ink-2);font-size:.88rem}}
.muted{{color:var(--ink-2);font-style:italic}}
table{{border-collapse:collapse;width:100%;font-size:.9rem;background:var(--surface);border:1px solid var(--line)}}
td{{border-bottom:1px solid var(--line);padding:7px 12px;vertical-align:top}}
.tw{{overflow-x:auto;margin-top:10px}}
footer{{color:var(--ink-2);font-size:.85rem;padding-top:20px}}
.back{{display:inline-block;margin-bottom:14px;color:var(--accent);text-decoration:none;font-weight:500}}
</style>
</head>
<body>
<div class="wrap">
<header>
  {BACK_LINK}
  <div class="eyebrow">Companion · Stream Deck XL · vMix</div>
  <h1>{html.escape(TITLE)}</h1>
  <p>Les {len(data['pages'])} pages du fichier <code>{html.escape(FILE)}</code>, présentées une par une avec la fonction de chaque touche. Un point blanc sur une touche signale qu'elle change de couleur selon l'état de vMix.</p>
  <p>Connexions : {conns}</p>
</header>
<nav aria-label="Pages">{''.join(nav)}</nav>
{''.join(pages_html)}
{VARS_SECTION}
<footer>Généré depuis le fichier Companion : les descriptions reflètent exactement les actions programmées.</footer>
</div>
'''
HTML += '</body>\n</html>\n'
if OUT:
    open(OUT, 'w', encoding='utf-8').write(HTML)
    print(f'OK — {OUT} écrit ({len(data["pages"])} pages)')
else:
    sys.stdout.write(HTML)
