---
name: companion
description: Crée ou modifie des boutons et macros Bitfocus Companion (Stream Deck) pour n'importe quel projet — boutons qui appellent une API HTTP, toggles ON/OFF colorés, boutons maîtres, enchaînements avec délais, pupitre vMix avec tally — en générant directement un fichier .companionconfig à importer. À utiliser quand l'utilisateur parle de Companion, Stream Deck, vMix, raccourcis, macros ou boutons deck.
---

# Companion — boutons Stream Deck pour n'importe quel projet

## Principe
- Un export Companion (`*.companionconfig`) est du **JSON compressé gzip** (format v12, Companion 4.3+). Ne jamais l'ouvrir avec Read/Edit : passer par le script `scripts/companion.py`.
- On ne modifie pas le fichier à la main : on écrit une **spec JSON** (la liste des touches voulues), puis le script la transforme en boutons Companion.
- Deux familles de connexions :
  - **HTTP** (module `generic-http`) : pour piloter l'API d'un projet. La connexion a une *Base URL* ; une URL de bouton qui ne commence pas par `http` lui est ajoutée (`/api/x` → `http://hôte:port/api/x`).
  - **vMix** (module `studiocoast-vmix` v5, label `vmix`, TCP 8099). Actions, options et feedbacks : voir **VMIX.md**.
- Le script crée une connexion si la spec en a besoin et qu'elle n'existe pas encore.
- Stream Deck XL : grille **8 colonnes × 4 lignes**. Adresse d'une touche = `page/ligne/colonne` (lignes 0–3, colonnes 0–7). Une touche hors de cette grille n'apparaît pas sur le deck (`dump` la signale).

## Méthode
1. **Comprendre le projet** : quelle API il expose (lire ses routes : fichier serveur, doc, README), son adresse (hôte + port), et ce que l'utilisateur veut déclencher. Ne jamais inventer une route : la trouver dans le code ou la demander.
2. **Partir d'un fichier** :
   - projet déjà configuré dans Companion : demander un export (Companion → Import / Export → Export) puis `python scripts/companion.py dump <fichier>` ;
   - nouveau projet : `python scripts/companion.py init <nouveau.companionconfig>`.
3. **Écrire la spec** dans le dossier de travail temporaire (format ci-dessous ; s'inspirer de `examples/`). Choisir des emplacements libres, ou confirmer avant d'écraser une touche existante.
4. **Générer** dans un nouveau fichier, sans toucher à l'original :
   `python scripts/companion.py apply <config> <spec.json> --out <résultat.companionconfig> --dry-run`, puis sans `--dry-run`.
5. **Vérifier** avec `dump`. Pour présenter le résultat à l'utilisateur (chaque page dessinée + la fonction de chaque touche, en français) : `python scripts/present.py <fichier> --out <page.html>` (option `--fps` pour convertir les images de replay en secondes). Puis expliquer l'import :
   Companion → Import / Export → importer le fichier, et **ne choisir que les pages et connexions concernées**.

> ⚠️ Ne jamais conseiller un import complet avec « tout remplacer » : Companion supprime et recrée l'intégration Stream Deck pendant que le deck est ouvert, et le deck peut rester noir (`Cannot write to hid device` dans les logs) jusqu'à ce qu'on quitte Companion et qu'on débranche/rebranche le deck.

Les chemins `scripts/…` et `examples/…` sont relatifs au dossier de ce skill.

## Format de spec.json
```json
{
  "http":  { "label": "mon-app", "base_url": "http://localhost:8080" },
  "vmix":  { "host": "127.0.0.1", "port": 8099 },
  "pages": { "1": { "name": "Mon projet" } },
  "buttons": [
    { "loc": "1/0/0", "kind": "page_up" },
    { "loc": "1/0/2", "kind": "get", "text": "Recharger", "url": "/api/reload", "bg": "#333333" },
    { "loc": "1/1/0", "kind": "toggle", "text": "▶ Bandeau", "on_url": "/api/banner/on", "off_url": "/api/banner/off" },
    { "loc": "1/1/2", "kind": "toggle", "text": "▶ Minuteur",
      "on":  [ { "post": "/api/timer", "body": { "action": "start", "seconds": 300 } } ],
      "off": [ { "post": "/api/timer", "body": { "action": "stop" } } ] },
    { "loc": "1/1/7", "kind": "master", "text": "▶ Tout", "targets": ["1/1/0", "1/1/2"] },
    { "loc": "1/2/0", "kind": "macro", "text": "▶ INTRO", "bg": "#006600",
      "actions": [ { "get": "/api/banner/off" }, { "get": "/api/intro/play" }, { "wait": 8000 }, { "get": "/api/banner/on" } ] }
  ]
}
```
`custom_variables` (optionnel) déclare des variables Companion réglables par l'utilisateur dans Companion (onglet Variables), utilisables partout avec `$(custom:nom)` :
```json
"custom_variables": { "vmix_video": { "description": "Vidéo à ajouter", "default": "C:\\Medias\\video.mp4" } }
```
Elles sont créées si absentes, jamais écrasées. Idéal pour un chemin de fichier, une URL ou un nom de source qui change d'un événement à l'autre : on ne régénère pas le fichier, on change la variable. À l'import, penser à cocher les variables personnalisées.

`http` et `vmix` sont optionnels : sans `http.base_url`, le script utilise la connexion `generic-http` déjà présente (celle dont le label vaut `http.label`, sinon la première).

### Types de touches (`kind`)
| kind | Champs | Résultat |
|---|---|---|
| `get` | `url` ou `urls`, `text`, `bg`, `size` | Un appui = une ou plusieurs requêtes GET |
| `toggle` | `on_url`/`off_url` **ou** `on`/`off` (listes d'items), `start_off`, `on_color`, `off_color` | 2 états : 1er appui = actions ON + vert foncé, 2e appui = actions OFF + rouge |
| `master` | `targets` (adresses de toggles) | Rejoue les actions ON/OFF de toutes les cibles, les recolore et synchronise leur état |
| `macro` | `actions` (items) ou `steps` (une liste d'items par appui), `feedbacks`, `sequential` (défaut true) | Touche libre : HTTP + vMix + délais |
| `page_up` / `page_down` | — | Page précédente / suivante sur ce deck |
| `pagenum` / `pageup` / `pagedown` | — | Contrôles de page natifs Companion |
| `empty` | — | Supprime la touche à cet emplacement |

Style commun : `text` (`\n` = retour à la ligne, variables `$(label:variable)` acceptées), `bg` / `fg` (`"#RRGGBB"` ou entier), `size` (`auto`, 14, 18…).

### Items (dans `actions`, `steps`, `on`, `off`)
- `{ "get": "/chemin" }` · `{ "post" | "put" | "patch" | "delete": "/chemin", "body": {…} }` : requête HTTP (corps envoyé en JSON). Ajouter `"connection": "<label>"` pour viser une autre connexion HTTP que celle par défaut.
- `{ "wait": 1000 }` : pause en ms.
- `{ "vmix": "<actionId>", …options }` : action vMix ; les options absentes prennent les défauts du module (VMIX.md).

Avec `sequential: true` (défaut) et plusieurs items, le script les place dans un `action_group` séquentiel : sans lui, Companion lance tout en même temps et les `wait` ne servent à rien.

### Feedbacks (vMix)
`{ "vmix": "inputLive", "input": "1", "bg": "#CC0000" }`. Pour un feedback booléen (`status`, `busMute`, `inputAudio`, `replayStatus`) : ajouter `"style": { "bgcolor": "#CC0000", "color": "#FFFFFF" }`.

## Conventions de mise en page
- Navigation : reprendre l'emplacement de `⬆️` / `⬇️` déjà utilisé dans le fichier de l'utilisateur (lire le `dump`). Par défaut : ligne 0, colonnes 0 et 1 ; certains préfèrent colonnes 6 et 7 (en haut à droite).
- Toggle : vert foncé `#003300` = actif, rouge `#AA0000` = inactif. Texte `▶ Nom`.
- vMix : tally preview vert `#009900`, program rouge `#CC0000` (feedbacks `inputPreview` / `inputLive`) ; texte d'une touche d'input `PVW 1\n$(vmix:input_1_name)`.
- Dans les automatisations vMix, désigner les inputs par leur **nom** plutôt que leur numéro, et dire à l'utilisateur de nommer ses inputs pareil.
- Actions à risque (arrêt du stream, FTB, suppression côté API) : les regrouper à part et le signaler.
- Changer le step d'une autre touche : `button_set_current_step` (`step_index` 0-indexé). L'ancienne `bank_current_step` est obsolète.

## Exemples
| Dossier | Contenu |
|---|---|
| `examples/generique/api-http.json` | Projet quelconque avec une API HTTP : GET, POST avec corps JSON, toggles, maître, macro avec délai |
| `examples/vmix/vmix-regie.json` | Pupitre vMix complet : transitions, preview/program avec tally, overlays, REC/stream, mute |
| `examples/vmix/vmix-audio.json` | Mutes (Master, bus, inputs 1–8), solo 1–8, volumes et fondus du Master |
| `examples/vmix/vmix-lecture.json` | Lecture de l'input en preview (play, pause, loop, mark, ±1 s/±5 s), playlist, compte à rebours d'un titre `TIMER` |
| `examples/vmix/vmix-transitions.json` | Auto T1–T4, stingers 3–4, overlays 1–4 in / out / off, T-bar, 8 transitions rapides |
| `examples/vmix/vmix-sorties.json` | External, Fullscreen, SRT, snapshot, stream par destination, REC, sources de Output 2 / Fullscreen / External 2 |
| `examples/vmix/vmix-sources.json` | Ajouter des sources (vidéo, image, photos, titre, playlist, audio, couleurs, PowerPoint) via variables personnalisées ; changer l'URL d'un input Browser et la source d'un input NDI ; annuler une fermeture |
| `examples/vmix/vmix-live.json` | Page 2 vMix seul : GO LIVE / FIN LIVE, replay (marquer 10 s, lire, enregistrer), mutes, sorties d'overlays, réglage de la transition 1 |
| `examples/pso/` | Un projet réel (overlay tournoi PSO) : page d'overlays + automatisations qui mélangent l'API du projet et vMix. Voir son README pour la démarche |

## Cas non couverts par la spec
Importer le script dans un petit programme Python et utiliser `load()`, les helpers (`act_http`, `act_vmix`, `fb_vmix`, `act_wait`, `act_group`, `act_internal`, `button`, `http_connection_id`, `vmix_connection_id`) puis `save()`.
