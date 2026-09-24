# pso-companion

Skills Claude Code et serveur local pour les distribuer. Le skill **companion** fabrique des touches **Bitfocus Companion** (Stream Deck) pour n'importe quel projet : appels à une API HTTP, toggles, boutons maîtres, enchaînements avec délais, pupitre **vMix** avec tally.

## Contenu
| Chemin | Rôle |
|---|---|
| `skills/<nom>/` | Un dossier par skill (avec son `SKILL.md`) |
| `skills/companion/SKILL.md` | Instructions du skill : méthode, format des specs, conventions |
| `skills/companion/VMIX.md` | Référence des actions / feedbacks vMix (relevée dans le code du module) |
| `skills/companion/scripts/companion.py` | Outil `init` / `dump` / `apply` |
| `skills/companion/examples/generique/` | Projet quelconque avec une API HTTP |
| `skills/companion/examples/vmix/` | Pupitre vMix réutilisable |
| `skills/companion/examples/pso/` | Exemple réel complet : régie de tournoi PSO (API maison + vMix) |
| `server.js` · `start.bat` · `config.json` | Serveur local de skills et de documentation (port 3011) |
| `public/` | Catalogue des skills (`/`) et documentation (`/docs`) |

## Serveur de skills
```powershell
start.bat          # ou : npm install ; npm start
```
Le serveur écoute sur toutes les interfaces et affiche ses adresses au démarrage :

| URL | Contenu |
|---|---|
| `http://<IP>:3011/` | Catalogue : téléchargement .zip, commande d'installation, lecture des fichiers, exports Companion |
| `http://<IP>:3011/docs` | Documentation et tutoriel de mise en place |
| `/download/skills/<nom>.zip` | Le skill, prêt à décompresser dans `.claude\skills` |
| `/api/skills` · `/api/exports` · `/api/info` | Données JSON |

`config.json` :
```json
{ "port": 3011, "exportsDirs": [] }
```
`exportsDirs` liste les dossiers de tes projets dont les fichiers `.companionconfig` sont proposés au téléchargement, par exemple `["D:/MonProjet/companion"]`.

Les réglages propres à un PC vont dans `config.local.json` (non versionné, prioritaire sur `config.json`), par exemple :
```json
{ "exportsDirs": ["P:/PSO 2/PSO/companion"] }
```

Le serveur est en lecture seule, sans authentification : à réserver au réseau local. Ajouter un skill : créer `skills/<nom>/SKILL.md` avec un en-tête `name:` / `description:` ; il apparaît dans le catalogue sans redémarrer.

## Installer le skill companion
Depuis n'importe quel PC du réseau (remplacer l'IP), pour tous tes projets :
```powershell
Invoke-WebRequest http://192.168.1.105:3011/download/skills/companion.zip -OutFile "$env:TEMP\companion.zip"
Expand-Archive "$env:TEMP\companion.zip" -DestinationPath "$env:USERPROFILE\.claude\skills" -Force
```
Pour un seul projet : `-DestinationPath "<projet>\.claude\skills"`.

Ensuite, dans Claude Code ouvert sur ton projet : `/companion` ou « crée une page Stream Deck pour piloter l'API de ce projet ».

## Utilisation directe du script
```powershell
$py = "$env:USERPROFILE\.claude\skills\companion\scripts\companion.py"

python $py init  D:\MonProjet\companion.companionconfig                 # fichier neuf
python $py dump  D:\MonProjet\export.companionconfig                    # voir les touches
python $py apply D:\MonProjet\companion.companionconfig ma-spec.json --out D:\MonProjet\resultat.companionconfig
```
Puis importer le résultat dans Companion (Import / Export) en ne choisissant **que** les pages et connexions concernées : un import complet en « tout remplacer » peut laisser le Stream Deck noir.

## Prérequis
- Python 3.8+ (script) et Node.js (serveur de skills)
- Companion 4.3+ ; les modules `generic-http` et `studiocoast-vmix` s'installent à l'import si besoin
