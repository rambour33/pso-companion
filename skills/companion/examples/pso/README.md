# Exemple : overlay de tournoi PSO

Un projet réel qui montre la démarche complète : un serveur Node (`server.js`, port 3002) pilote des overlays OBS/vMix pour un tournoi Smash Bros, et le Stream Deck le contrôle via Companion, en même temps que vMix.

## 1. Trouver l'API du projet
Dans `server.js`, la section « Stream Deck » expose des routes GET sans authentification :

| URL | Effet |
|---|---|
| `/api/deck/<overlay>/show` · `/hide` · `/toggle` · `/reveal` | Affiche / cache un overlay avec sa transition |
| `/api/deck/score/p1/inc` · `p1/dec` · `p2/inc` · `p2/dec` | Score ±1 |
| `/api/deck/score/reset` | Score 0-0 |
| `/api/deck` | Liste JSON des overlays et de leurs URLs |

Les `<overlay>` valides sont ceux de la constante `TRANSITION_IDS` du serveur (scoreboard, casters, cam, victory, vs-screen, top8…). Un autre id renvoie 404 : c'est pourquoi on relit toujours les routes avant d'écrire une spec.

## 2. Les specs
| Fichier | Page | Contenu |
|---|---|---|
| `pso-overlays.json` | 1 « PSO » | Barre de score, 21 toggles d'overlay (`on_url` = `/show`, `off_url` = `/hide`), bouton maître « ▶ Overlays » qui les commande tous |
| `pso-vmix-auto.json` | 4 « vMix Auto » | Automatisations : DÉBUT MATCH (écran VS 5 s → stinger vMix vers l'input JEU → scoreboard), FIN MATCH, PAUSE, RETOUR JEU, CAM CASTERS, REPLAY 10 s, TOP 8, GO LIVE / FIN LIVE, mutes |

Les deux déclarent la même connexion : `"http": { "label": "http", "base_url": "http://localhost:3002" }`, d'où des URLs courtes (`/api/deck/cam/show`).

## 3. Générer
```powershell
$py = "<dossier du skill>\scripts\companion.py"
python $py apply "PSO-Companion (19).companionconfig" examples\pso\pso-overlays.json --out etape1.companionconfig
python $py apply etape1.companionconfig examples\pso\pso-vmix-auto.json --out PSO-Companion-vMix.companionconfig
```
Puis importer seulement les pages 1 et 4 et les connexions `http` et `vmix`.

## Ce que l'exemple montre
- **Une API maison** pilotée par des `get` et des `toggle`.
- **Un bouton maître** qui réutilise les actions de 21 toggles.
- **Des enchaînements multi-logiciels** : actions HTTP du projet + actions vMix + `wait`, exécutées dans l'ordre.
- **Des conventions propres au projet** : inputs vMix nommés `JEU`, `CASTERS`, `PAUSE`, `MUSIQUE`, `MICROS` ; stinger 1 configuré dans vMix.
- **Nettoyage** : les entrées `empty` retirent d'anciennes touches placées en ligne 4, hors de la grille 8 × 4 du Stream Deck XL.
