# Entwicklungsprotokoll — comfyui-opencode

Dieses Dokument hält fest, wie die Node entstanden ist, welche Sackgassen es gab und warum
die Lösung so aussieht, wie sie aussieht. Ziel: beim nächsten opencode-Upgrade nicht wieder
bei null anfangen.

## Ausgangslage

ComfyUI soll lokale opencode-Modelle (inkl. Ollama) nutzen, um Prompts zu verarbeiten.
Anforderung: Modellauswahl in der ComfyUI-Oberfläche, System-Prompt injizierbar,
Ausgabe als String weiterverarbeitbar.

Verifiziert auf: opencode v2.2.7, ComfyUI v0.45.4, Python 3.14.8, Fedora/Nobara.

## Verlauf

### Phase 1 — CLI-Schnittstelle erkunden

`opencode run --help` zeigte die relevanten Flags: `--agent`, `--model`, `--format json`,
`--standalone`. `--format json` liefert einen Event-Stream (NDJSON) mit `step_start`,
`text`, `step_finish`. Der Text steht in `part.text`.

Ein reiner `generate/text`-Endpunkt existiert (`/api/experimental/generate/text`), nimmt
aber nur `prompt` und `model` — **kein System-Prompt**. Damit war klar: der Weg muss über
einen Agent gehen.

### Phase 2 — Irrweg: Agent als Markdown-Datei

Erster Ansatz: `.opencode/agent/<name>.md` mit YAML-Frontmatter. Schlägt fehl mit
`Agent not found`. Auch ein `api GET /api/agent` blieb leer.

Erkenntnis: In v2 gehören Agents in die `opencode.json`. Der SChema-Dump über
`/openapi.json` (erreichbar nur mit `OPENCODE_PASSWORD` aus `~/.config/opencode/service.json`
bzw. der Port-Ausgabe im Server-Log) zeigte `Config.AgentEncoded` und — entscheidend —
den Top-Level-Schlüssel `agents` (Plural).

### Phase 3 — Irrweg: Unterstrich im Namen

Mit `agents` in der Config lief es reproduzierbar **nicht** mit `comfyui_runner`, aber
sofort mit `comfy-test`. Keine Fehlermeldung deutet darauf hin. Regel: nur Bindestriche.

### Phase 4 — Irrweg: Git-Repo ohne Commit

Mit `git init` allein blieb es bei `Agent not found`. `api GET /api/location` zeigte
`project.id = "global"` — opencode erkannte das Verzeichnis nicht als Projekt und wandte
die lokale Config nie an.

Der Initial-Commit war die Lösung: danach lieferte `/api/location` eine echte Projekt-ID
(`36ce76…` statt `global`). `ensure_workspace()` prüft `git rev-parse --verify HEAD` und
committet bei Bedarf.

### Phase 5 — Die eigentliche Falle: Aufrufkontext

Nach Phase 4 funktionierte der Aufruf aus der Bash, aber **nicht** aus Python — bei
identischen Argumenten, identischem `cwd`, identischer Umgebung.

Reproduzierbar über je 10 Läufe:

```
subprocess.run(['opencode', '--standalone', 'run', ...])              -> 0/10
subprocess.run(['/bin/bash', '-lc', 'opencode --standalone run ...']) -> 10/10
```

Systematisch ausgeschlossen:

| Hypothese | Test | Ergebnis |
|---|---|---|
| Fehlendes TTY | `pty.openpty()` | scheitert weiter |
| Prozessgruppe | `start_new_session=True` | scheitert weiter |
| stdin | `/dev/null`, Pipe, inherit | scheitert weiter |
| Umgebungsvariablen | einzelne Var (`SHELL`, `TERM`, `USER`, `LOGNAME`, `SHLVL`, `_`) | scheitert weiter |
| Komplette Shell-Env | `env -0` aus `bash -lc` übernommen | scheitert weiter |
| `OPENCODE_PASSWORD` | entfernt | scheitert weiter |
| Andere Binary | absoluter Pfad `/home/deniz/.opencode/bin/opencode` | scheitert weiter |
| Aufrufer-CWD | aus `/tmp`, `/home/deniz`, ComfyUI | scheitert weiter |
| Verzeichnis-Permissions | `chmod 755` statt `700` | scheitert weiter |
| Timing/Race | 4× Retry mit 1,5 s Pause | scheitert weiter |
| mkdtemp vs mkdir | beide Varianten | kein Unterschied |

**Ursache nicht isoliert.** `_run()` geht deshalb über `/bin/bash -lc`. Das ist der einzige
reproduzierbar zuverlässige Aufrufweg und im Code als solcher kommentiert.

Nebenbefund aus Phase 5: `time`/`DEFAULT_TIMEOUT` werden in `_run` nicht gebraucht, ein
Retry-Loop auf `Agent not found` war eine falsche Fährte (kein Race) und wurde wieder
entfernt.

### Phase 6 — Abschlussverifikation

Frischer Workspace (`rm -rf ~/.cache/comfyui-opencode`), 10 Läufe ohne manuellen Warm-up:
**10/10 erfolgreich**, System-Prompt nachweislich angewandt (Marker `ZEBRA`, Antwort durch-
gehend Großbuchstaben).

Node-Load über `define_schema()`: 108 Modelle in der Combo, 4 Inputs, 1 Output.
`execute()` liefert einen brauchbaren englischen Bildprompt aus einem deutschen Input.

### Phase 7 — Die Node erschien nicht in ComfyUI

Beim Nutzer war die Node in der Oberfläche nicht auffindbar. Das Log zeigte:

```
Cannot import .../custom_nodes/comfyui-opencode module for custom nodes:
No module named '/home/deniz/ComfyUI/custom_nodes/comfyui-opencode.nodes'
IMPORT FAILED: /home/deniz/ComfyUI/custom_nodes/comfyui-opencode
```

Alle Tests bis hierher liefen mit einem selbstgebauten Import (`submodule_search_locations`
gesetzt, teils mit gestubbtem `comfy_aimdo`) — also **nicht** mit ComfyUIs echtem Loader. Das
war der Fehler in der Verifikation: ich habe den Node-Load simuliert statt ihn auszulösen.

Drei echte Fehler, nacheinander sichtbar:

**7.1 — Relative Imports scheitern.** ComfyUI lädt ein Node-Verzeichnis mit
`spec_from_file_location(<path>, "<dir>/__init__.py")`, wobei der Modulname der Pfad mit
escapten Punkten ist (`custom_nodes/comfyui-opencode`). Dieser Name enthält einen
Schrägstrich, daher kann `from .nodes import …` nicht auflösen.
Lösung: flaches Layout, kein Unterpaket.

**7.2 — `nodes.py` kollidiert mit ComfyUIs eigenem Modul.** Nach dem Flachlegen hieß die
Node-Datei `nodes.py`; `import nodes` traf ComfyUIs eigenes `nodes`-Modul
(`module 'nodes' has no attribute 'OpenCodePromptNode'`).
Lösung: Datei heißt `opencode_nodes.py`.

**7.3 — Falsche Basisklasse.** Nach dem Import meldete ComfyUI
`type object 'OpenCodePromptNode' has no attribute 'GET_SCHEMA'` — die Klasse erbte nicht von
`io.ComfyNode`.
Lösung: `class OpenCodePromptNode(io.ComfyNode)`.

Verifikation danach **mit ComfyUIs echtem Loader** (`init_extra_nodes()` in der venv
`comfy714`):

```
ERFOLG: registriert -> custom_nodes.comfyui-opencode
Display: OpenCode Prompt
EXECUTE OK: 'A cozy domestic photograph of a fluffy gray tabby cat ...'
```

**Lehre für künftige Nodes:** Immer `init_extra_nodes()` in der ComfyUI-venv aufrufen und
`NODE_CLASS_MAPPINGS` prüfen. Ein Import-Test mit eigener `spec`-Konstruktion beweist nichts.

## Architekturentscheidungen

**Fester Workspace statt Temp-Verzeichnis.** Jeder Lauf ein `mkdtemp` hätte pro ComfyUI-
Ausführung eine neue Projekt-Registrierung in opencodes SQLite-DB erzeugt. Der feste Pfad
`~/.cache/comfyui-opencode/workspace` bleibt warm, wird nur bei Bedarf initialisiert und
ist über `OPENCODE_WORKSPACE` umbiegbar.

**Agent-Config wird pro Lauf neu geschrieben.** Der System-Prompt ist ein Node-Input und
ändert sich zwischen Ausführungen. Die `opencode.json` im Workspace wird deshalb bei
jedem `ensure_workspace()` neu geschrieben — das ist billig und hält den Prompt korrekt,
ohne Neustart von opencode.

**Aufruf über Login-Shell.** Siehe Phase 5. Unschön, aber empirisch der einzige stabile
Weg; der Kommentar im Code benennt den Grund.

**Keine Abhängigkeit von `comfy_api` in `client.py`.** Der Client ist reines Python und
damit ohne ComfyUI testbar (`tests/smoke.py`). Die `comfy_api`-Imports stehen in
`nodes.py`/`__init__.py`.

## Offene Punkte

- **Wurzelursache Phase 5 unklar.** Sollte opencode eine Version liefern, in der der
  direkte `subprocess`-Aufruf funktioniert, kann der `bash -lc`-Umweg entfernt werden.
  Verifikation: `tests/smoke.py` mit direkter Invocation.
- **Kein Streaming.** `execute()` blockiert bis zur vollständigen Antwort. Bei langen
  Prompts und langsamen Modellen läuft das in den `timeout`. Ein Fortschritts-Report an
  die ComfyUI-Konsole wäre wünschenswert (Rückkanal via `io.NodeOutput` nicht vorgesehen).
- **Modellliste wird beim Node-Load gezogen.** `opencode models` läuft einmalig beim
  Schema-Aufbau (~1,3 s). Neue Modelle erscheinen erst nach ComfyUI-Neustart.
- **`comfy_aimdo.storage` fehlt** in der lokalen Installation, wodurch `comfy_api.latest`
  in einem nackten `python3`-Prozess nicht importierbar ist. Betrifft ComfyUI global, nicht
  diese Node. Node-Tests stubben das Modul.
