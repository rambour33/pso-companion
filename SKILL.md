---
name: companion
description: Crée ou modifie des boutons/macros Bitfocus Companion (Stream Deck) pour l'overlay PSO et pour vMix — boutons toggle d'overlay, score, boutons maîtres, pupitre vMix (preview/program/transitions/overlays/REC/stream avec tally), automatisations qui enchaînent vMix et PSO — en éditant directement le fichier .companionconfig. À utiliser quand l'utilisateur parle de Companion, Stream Deck, vMix, raccourcis, macros ou boutons deck.
---

# Companion — macros Stream Deck pour PSO

## Contexte
- Export Companion : `PSO/companion/*.companionconfig` (le plus récent, ex. `PSO-Companion (19).companionconfig`).
  C'est du **JSON compressé gzip** (format v12, Companion 4.3). Ne jamais l'ouvrir avec Read/Edit : passer par le script.
- Stream Deck XL : grille **8 colonnes × 4 lignes**. Adresse d'un bouton = `page/ligne/colonne` (0-indexé pour ligne et colonne, ex. `1/0/7` = page 1, ligne du haut, dernière colonne).
- Connexion HTTP : module `generic-http`, préfixe `http://localhost:3002`. Les commandes PSO sont des **GET** vers ce serveur.
- Connexion vMix : module `studiocoast-vmix` v5, label `vmix`, TCP 8099. Créée automatiquement par le script si une spec l'utilise. Actions, options et feedbacks : voir **VMIX.md** (à lire avant toute macro vMix).
- Companion ne relit pas le fichier tout seul : après modification, l'utilisateur doit le **réimporter** (Companion → Import/Export → Import → remplacer ou choisir les pages).

## Endpoints PSO (server.js, section « Stream Deck »)
| URL | Effet |
|---|---|
| `/api/deck/<overlay>/show` · `/hide` · `/toggle` · `/reveal` | Affiche / cache un overlay avec sa transition |
| `/api/deck/score/p1/inc` · `p1/dec` · `p2/inc` · `p2/dec` | Score ±1 |
| `/api/deck/score/reset` | Score 0-0 |
| `/api/deck` | Liste JSON des overlays et de leurs URLs |

Les `<overlay>` valides sont ceux de `TRANSITION_IDS` dans `PSO/server.js` (à relire avant de créer un bouton, la liste évolue). Tout autre id renvoie **404**.

## Conventions des boutons existants (à reproduire)
- **Toggle overlay** : 2 steps, progression auto.
  - step 0 : `GET /api/deck/<id>/show` + `bgcolor` self → vert `13056` (#003300)
  - step 1 : `GET /api/deck/<id>/hide` + `bgcolor` self → rouge `11141120` (#AA0000)
  - Texte `▶ Nom` (retour à la ligne `\n` si long), taille `auto`, texte blanc.
- **Bouton score** : 1 step, un GET. Couleurs : J1 +1 `#AA0000`, J1 −1 `#660000`, J2 +1 `#0000AA`, J2 −1 `#000066`, reset `#806200`, taille 18 (14 pour RESET).
- **Bouton maître** (« ▶ Overlays », « All Scènes ») : step 0 envoie tous les `show` des cibles, recolore toutes les cibles en vert et met chaque cible sur **step 1** ; step 1 fait l'inverse (tous les `hide`, rouge, cibles sur step 0). Ainsi le prochain appui sur une cible fait l'action logique.
- Ligne 0 de chaque page : `⬆️` (dec_page) en `x/0/0`, `⬇️` (inc_page) en `x/0/1`, puis la barre score en colonnes 2→6, le maître en colonne 7.
- Pour changer le step d'un autre bouton, utiliser `button_set_current_step` (`step_index` 0-indexé). L'ancienne action `bank_current_step` (1-indexée) est obsolète — ne pas en ajouter.

## Méthode
1. Lire l'état actuel :
   `python .claude/skills/companion/scripts/companion.py dump "PSO/companion/<fichier>.companionconfig"`
2. Vérifier les ids d'overlay dans `TRANSITION_IDS` de `PSO/server.js`. Si l'utilisateur veut piloter quelque chose qui n'a pas d'endpoint, proposer d'ajouter la route dans server.js (section Stream Deck, **avant** le handler générique `/api/deck/:overlay/:action` si c'est une route spécifique).
3. Choisir des emplacements libres (ou confirmer avec l'utilisateur avant d'écraser un bouton existant).
4. Écrire un fichier spec JSON dans le scratchpad, puis :
   `python .claude/skills/companion/scripts/companion.py apply "<config>" <spec.json> --server PSO/server.js --dry-run`
   puis sans `--dry-run`. Le script crée `<config>.bak` avant d'écrire. Avec `--out <nouveau fichier>`, il écrit ailleurs et laisse l'original intact (à privilégier pour un gros ajout).
5. Refaire un `dump` pour vérifier, et rappeler à l'utilisateur de réimporter le fichier dans Companion.

## Format de spec.json
```json
{
  "pages": { "3": { "name": "Casters" } },
  "buttons": [
    { "loc": "3/0/0", "kind": "page_up" },
    { "loc": "3/0/1", "kind": "page_down" },
    { "loc": "3/1/0", "kind": "toggle", "text": "▶ Cam", "overlay": "cam" },
    { "loc": "3/1/1", "kind": "toggle", "text": "▶ Victoire", "overlay": "victory", "start_hidden": true },
    { "loc": "3/0/2", "kind": "get", "text": "+1\nJ1", "url": "/api/deck/score/p1/inc", "bg": "#AA0000", "size": 18 },
    { "loc": "3/2/0", "kind": "get", "text": "Pause", "urls": ["/api/deck/scoreboard/hide", "/api/deck/cam/show"], "bg": "#333333" },
    { "loc": "3/0/7", "kind": "master", "text": "▶ Tout", "targets": ["3/1/0", "3/1/1"] },
    { "loc": "3/3/7", "kind": "empty" }
  ]
}
```
| kind | Champs | Résultat |
|---|---|---|
| `toggle` | `overlay`, `text`, option `show_action` (`show`/`reveal`), `start_hidden`, `on_color`, `off_color` | Bouton 2 steps show/hide coloré |
| `get` | `url` ou `urls`, `text`, `bg`, `size` | Un appui = un ou plusieurs GET (URL relative → préfixée `http://localhost:3002`) |
| `master` | `targets` (adresses), `text` | Rejoue les URLs step 0/step 1 des cibles + couleurs + synchro des steps. Construit après les autres boutons, donc les cibles peuvent être dans la même spec |
| `page_up` / `page_down` | — | Navigation de page (surface courante) |
| `pagenum` / `pageup` / `pagedown` | — | Contrôles de page natifs Companion |
| `macro` | `actions` (liste d'items), ou `steps` (liste de listes, un step par appui), `feedbacks`, `sequential` (défaut true), `text`, `bg`, `fg`, `size` | Bouton libre : mélange PSO + vMix + délais |
| `empty` | — | Supprime le bouton à cet emplacement |

### Items d'une macro
- `{ "get": "/api/deck/scoreboard/show" }` : requête PSO
- `{ "wait": 1000 }` : pause en ms (utile seulement en séquentiel)
- `{ "vmix": "<actionId>", ...options }` : action vMix ; les options absentes prennent les défauts du module (VMIX.md)

Avec `sequential: true` et plusieurs items, le script les place dans un `action_group` séquentiel, sinon Companion les lance tous en même temps et les `wait` ne servent à rien.

### Feedbacks (vMix)
`{ "vmix": "inputLive", "input": "1", "bg": "#CC0000" }`. Pour un feedback booléen (`status`, `busMute`, `inputAudio`, `replayStatus`), ajouter `"style": { "bgcolor": "#CC0000", "color": "#FFFFFF" }`.

```json
{ "loc": "4/1/0", "kind": "macro", "text": "▶ DÉBUT\nMATCH", "bg": "#006600",
  "actions": [
    { "get": "/api/deck/vs-screen/show" }, { "wait": 5000 }, { "get": "/api/deck/vs-screen/hide" },
    { "vmix": "previewInput", "input": "JEU" }, { "vmix": "transition", "functionID": "Stinger1" },
    { "wait": 1000 }, { "get": "/api/deck/scoreboard/show" } ] }
```
Exemple complet : `examples/vmix-spec.json` (page « vMix Régie » + page « vMix Auto »).

### Conventions vMix
- Tally : Preview vert `#009900`, Program rouge `#CC0000`, via les feedbacks `inputPreview` / `inputLive`.
- Texte d'un bouton d'input : `PVW 1\n$(vmix:input_1_name)` pour afficher le vrai nom de l'input.
- Dans les automatisations, désigner les inputs vMix par leur **nom** (`JEU`, `CASTERS`, `PAUSE`…) plutôt que par leur numéro, et rappeler à l'utilisateur de nommer ses inputs pareil dans vMix.
- Actions à risque (arrêt du stream, FTB) : les regrouper à part et le signaler à l'utilisateur.

Couleurs : entier Companion ou `"#RRGGBB"`. Pour un cas que la spec ne couvre pas, importer `companion.py` dans un petit script Python et utiliser `load()`, les helpers (`act_get`, `act_vmix`, `fb_vmix`, `act_wait`, `act_group`, `act_internal`, `button`) puis `save()`.
