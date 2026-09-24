# PSO Companion

Skill Claude Code pour construire des boutons **Bitfocus Companion** (Stream Deck) qui pilotent l'overlay PSO (`http://localhost:3002/api/deck/...`) et **vMix** (module `studiocoast-vmix` v5).

Le skill lit et modifie directement un export `.companionconfig` (JSON gzip, Companion 4.x) : boutons toggle d'overlay, boutons score, boutons maîtres « tout afficher / tout cacher », navigation de pages.

## Contenu
| Fichier | Rôle |
|---|---|
| `SKILL.md` | Instructions du skill (conventions des boutons PSO, endpoints, méthode) |
| `scripts/companion.py` | Outil `dump` / `apply` pour lire et générer les boutons |
| `VMIX.md` | Référence des actions / feedbacks vMix (relevée dans le code du module) |
| `examples/spec.json` | Exemple de spec de boutons PSO |
| `examples/vmix-spec.json` | Pages « vMix Régie » (pupitre avec tally) et « vMix Auto » (automatisations vMix + PSO) |

## Installation
Copier le dossier dans les skills Claude Code du projet PSO :

```powershell
New-Item -ItemType Directory -Force "P:\PSO 2\.claude\skills\companion\scripts"
Copy-Item SKILL.md "P:\PSO 2\.claude\skills\companion\"
Copy-Item scripts\companion.py "P:\PSO 2\.claude\skills\companion\scripts\"
```

Ou pour tous les projets : `%USERPROFILE%\.claude\skills\companion\`.

Ensuite, dans Claude Code : `/companion` ou « ajoute un bouton Stream Deck pour le bracket ».

## Utilisation directe du script
```powershell
# Voir les boutons existants
python scripts/companion.py dump "PSO/companion/PSO-Companion (19).companionconfig"

# Tester une spec sans écrire
python scripts/companion.py apply "<config>" examples/spec.json --server PSO/server.js --dry-run

# Appliquer (crée <config>.bak avant d'écrire)
python scripts/companion.py apply "<config>" examples/spec.json --server PSO/server.js
```

Après `apply`, réimporter le fichier dans Companion (Import/Export → Import).

### Générer les pages vMix dans un nouveau fichier
```powershell
python scripts/companion.py apply "PSO/companion/PSO-Companion (19).companionconfig" examples/vmix-spec.json --server PSO/server.js --out "PSO/companion/PSO-Companion-vMix.companionconfig"
```
La connexion vMix (`127.0.0.1:8099`) est ajoutée si elle n'existe pas ; changer `vmix_host` dans la spec si vMix tourne sur un autre PC.

## Prérequis
- Python 3.8+
- Une connexion `generic-http` dans la config Companion (préfixe `http://localhost:3002`)
