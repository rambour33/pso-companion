# Référence vMix pour Companion

Relevé dans le code source du module officiel **`studiocoast-vmix` v5.0.5** (github.com/bitfocus/companion-module-studiocoast-vmix), qui cible **Companion 4.3+**.

## Connexion
- Module `studiocoast-vmix`, label **`vmix`** (les variables s'écrivent `$(vmix:...)`).
- Protocole **TCP, port 8099** (pas le port du Web Controller de vMix, qui ne doit pas être 8099).
- `lastUpgradeIndex` et `upgradeIndex` des actions/feedbacks = **17** (18 scripts de mise à jour dans la v5.0.5). Une valeur plus basse ferait rejouer d'anciennes migrations sur des options déjà au format v5.
- `mix` est **1-indexé** depuis la v5 (`mix: 1` = mix principal).
- Un `input` accepte un **numéro**, un **nom** (titre court de l'input dans vMix) ou un GUID.

## Actions utiles (`definitionId` → options)
| Action | Options (défauts) | Rôle |
|---|---|---|
| `transitionMix` | `mix: 1`, `functionID: 'Cut'` (Fade, Zoom, Wipe, Slide, Fly, CrossZoom, FlyRotate, Cube, CubeZoom, VerticalWipe, VerticalSlide, Merge, …Reverse), `duration: '1000'`, `input: ''` | Transition Preview→Program (ou d'un input précis si `input` rempli) |
| `transition` | `functionID: 'Transition1'`…`'Transition4'`, `'Stinger1'`…`'Stinger8'`, `mix: 1` | Lance une transition auto / un stinger configuré dans vMix |
| `setTransitionEffect` | `functionID: 'SetTransitionEffect1'`, `value: 'Cut'` | Change l'effet d'un bouton de transition |
| `setTransitionDuration` | `functionID: 'SetTransitionDuration1'`, `value: 1000` | Change sa durée |
| `previewInput` | `input: '1'`, `mix: 1` | Envoie un input en Preview |
| `programCut` | `input: '1'`, `mix: 1` | Cut direct à l'antenne |
| `quickPlay` | `input: '1'` | Quick Play |
| `overlayFunctions` | `type: 'OverlayInput'` (PreviewOverlayInput, In, Out, Last, Off, Zoom, OverlayInputAllOff), `input: ''`, `overlay: '1'`, `mix: [1]` | Overlays 1–8. `input` vide = l'input en Preview |
| `fadeToBlack` | — | FTB (bascule) |
| `recordingFunctions` | `functionID: 'StartRecording'` / `StopRecording` / `StartStopRecording` | Enregistrement |
| `streamingFunctions` | `functionID: 'StartStreaming'` / `StopStreaming` / `StartStopStreaming`, `value: ''` (tous) ou 1–5 | Stream |
| `multicorderFunctions` | `functionID: 'StartStopMultiCorder'` / `StartMultiCorder` / `StopMultiCorder` | MultiCorder |
| `externalFunctions` | `functionID: 'StartExternal'` / `StopExternal` / `StartStopExternal` | Sortie External |
| `audio` | `input: '1'`, `functionID: 'Audio'` / `AudioOn` / `AudioOff` | Mute d'un input |
| `busXAudio` | `value: 'Master'` (ou A–G), `functionID: 'BusXAudio'` / `BusXAudioOn` / `BusXAudioOff` | Mute d'un bus |
| `setText` | `input`, `selectedIndex: '0'` (index ou nom de calque), `adjustment: 'Set'`/`Increase`/`Decrease`, `value`, `encode: false` | Texte d'un titre GT |
| `replayMark` | `functionID: 'ReplayMarkIn'` (…`ReplayMarkInOutLive`, `ReplayMarkOut`…), `value: '10'` (secondes), `value2: '10'` | Marquer un replay |
| `replayPlayLastEventToOutput` | `channel: 'Current'` / `A` / `B` | Rejouer le dernier event |
| `replayStopEvents` | — | Stopper le replay |
| `replayRecording` | `functionID: 'ReplayStartStopRecording'` / `ReplayStartRecording` / `ReplayStopRecording` | Enregistrement du replay |
| `scriptStart` | `value: 'NomDuScript'` | Lancer un script vMix |
| `solo` | `input`, `functionID: 'Solo'` / `SoloOn` / `SoloOff` | Solo d'un input |
| `soloAllOff` · `audioMixerShowHide` | — | Coupe tous les solos · affiche / cache le mixer audio |
| `setBusVolume` | `value: 'Master'` (A–G, Headphones), `adjustment: 'Set'`/`Increase`/`Decrease`, `amount: '100'` | Volume d'un bus (0–100) |
| `setBusVolumeFade` | `value: 'Master'`, `fadeVol: '0'`, `fadeTime: '2000'` | Fondu de volume d'un bus (vMix 28+) |
| `setInputVolume` · `setVolumeFade` | `input`, `adjustment`, `amount` · `input`, `fadeMin`, `fadeTime` | Volume / fondu d'un input |
| `videoActions` | `input`, `inputType` (true = l'input en preview), `functionID: 'Play'` / `Pause` / `PlayPause` / `Restart` / `Loop`… | Lecture d'une vidéo |
| `videoPlayhead` | `input`, `inputType`, `adjustment`, `value` (ms) | Déplacer la tête de lecture |
| `videoMark` | `input`, `inputType`, `functionID: 'MarkIn'` / `MarkOut` / `MarkReset`… | Points d'entrée / sortie d'une vidéo |
| `playListFunctions` | `functionID: 'StartPlayList'` / `StopPlayList` / `NextPlayListEntry` / `PreviousPlayListEntry` | Playlist |
| `controlCountdown` | `functionID: 'StartCountdown'` / `PauseCountdown` / `StopCountdown`, `input`, `selectedIndex: '0'` | Compte à rebours d'un titre |
| `tbar` | `value: '0'`…`'255'` | Position du T-bar |
| `outputSet` | `functionID: 'SetOutput2'`/`3`/`4`/`SetOutputExternal2`/`SetOutputFullscreen`/`2`, `value: 'Output'`/`Preview`/`MultiView`/`Replay`/`Mix`/`Input` | Source d'une sortie |
| `fullscreenFunctions` · `srtFunctions` | `functionID` : `Fullscreen` / `FullscreenOn` / `FullscreenOff` · `StartStopSRTOutput`… | Sorties Fullscreen, SRT |
| `snapshot` | `input: ''` (vide = la sortie), `value` : nom de fichier, ex. `Snapshot {0:yyyy-MM-dd HH-mm-ss}.jpg` | Capture d'image |
| `command` | `command: 'Fonction Param=…'`, `encode: false` | N'importe quelle fonction de l'API vMix |

## Feedbacks utiles
| Feedback | Type | Options | Effet |
|---|---|---|---|
| `inputPreview` | advanced | `input`, `mix: 1`, `fg`, `bg` (vert), `tally: ''` | Couleur quand l'input est en Preview |
| `inputLive` | advanced | `input`, `mix: 1`, `fg`, `bg` (rouge), `tally: ''` | Couleur quand l'input est à l'antenne |
| `overlayStatus` | advanced | `input: ''` (n'importe lequel), `overlay: '1'`, `fg`, `bgPreview`, `bgProgram` | État d'un overlay |
| `status` | boolean + `style` | `status`: connection, fadeToBlack, recording, external, streaming, multiCorder, fullscreen, playList | État global de vMix |
| `busMute` | boolean + `style` | `value: 'Master'` | Bus muté |
| `inputAudio` | boolean + `style` | `input` | Input muté |
| `replayStatus` | boolean + `style` | `status: 'recording'` / `'live'` | État du replay |
| `inputSolo` | boolean + `style` | `input` | Input en solo |
| `inputState` | boolean + `style` | `input`, `type: 'playing'` / `'loop'` | Vidéo en lecture / en boucle |

Les feedbacks *advanced* portent leurs couleurs dans leurs options, les *boolean* dans `style` (`bgcolor`, `color`).

## Enchaîner des actions
Les actions d'un bouton partent **en même temps** par défaut. Pour une vraie séquence (stinger vMix, puis attendre, puis appel à l'API de ton projet), le script les place dans une action interne **`action_group`** avec `execution_mode: 'sequential'` et des actions **`wait`** (`time` en ms). C'est le comportement de `"kind": "macro"` avec `"sequential": true` (défaut).

## Variables pratiques
- `$(vmix:input_1_name)` : nom de l'input 1 (à mettre dans le texte d'une touche)
- Liste complète : `docs/variables.md` du module.
