# PSO Companion

Skills Claude Code et serveur local pour la régie PSO : construction des boutons **Bitfocus Companion** (Stream Deck) qui pilotent l'overlay PSO (`http://localhost:3002/api/deck/...`) et **vMix** (module `studiocoast-vmix` v5), avec leur documentation.

## Contenu
| Chemin | Rôle |
|---|---|
| `skills/<nom>/` | Un dossier par skill (avec son `SKILL.md`) |
| `skills/companion/SKILL.md` | Instructions du skill companion |
| `skills/companion/VMIX.md` | Référence des actions / feedbacks vMix (relevée dans le code du module) |
| `skills/companion/scripts/companion.py` | Outil `dump` / `apply` pour lire et générer les boutons |
| `skills/companion/examples/` | `spec.json` (page PSO) et `vmix-spec.json` (pages « vMix Régie » et « vMix Auto ») |
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

`config.json` règle le port et le dossier des exports `.companionconfig` proposés au téléchargement. Le serveur est en lecture seule, sans authentification : à réserver au réseau local.

Ajouter un skill : créer `skills/<nom>/SKILL.md` avec un en-tête `name:` / `description:`. Il apparaît dans le catalogue sans redémarrer.

## Installer le skill companion
Depuis n'importe quel PC du réseau (remplacer l'IP) :
```powershell
Invoke-WebRequest http://192.168.1.105:3011/download/skills/companion.zip -OutFile "$env:TEMP\companion.zip"
Expand-Archive "$env:TEMP\companion.zip" -DestinationPath "P:\PSO 2\.claude\skills" -Force
```
Ou pour tous les projets : `-DestinationPath "$env:USERPROFILE\.claude\skills"`.

Ensuite, dans Claude Code : `/companion` ou « ajoute un bouton Stream Deck pour le bracket ».

## Utilisation directe du script
```powershell
$py = "skills\companion\scripts\companion.py"

# Voir les boutons existants
python $py dump "P:\PSO 2\PSO\companion\PSO-Companion (19).companionconfig"

# Générer les pages vMix dans un nouveau fichier (l'original n'est pas modifié)
python $py apply "P:\PSO 2\PSO\companion\PSO-Companion (19).companionconfig" skills\companion\examples\vmix-spec.json --server "P:\PSO 2\PSO\server.js" --out "P:\PSO 2\PSO\companion\PSO-Companion-vMix.companionconfig"
```
Après `apply`, réimporter le fichier dans Companion (Import/Export → Import). La connexion vMix (`127.0.0.1:8099`) est ajoutée si elle n'existe pas ; changer `vmix_host` dans la spec si vMix tourne sur un autre PC.

## Prérequis
- Node.js (serveur) et Python 3.8+ (script)
- Companion 4.3+ avec une connexion `generic-http` (préfixe `http://localhost:3002`)
