# ComfyUI OpenCode

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-custom%20node-blue)](https://github.com/comfyanonymous/ComfyUI)

Eine ComfyUI-Custom-Node, die deinen Prompt durch die lokale
[opencode](https://opencode.ai)-CLI schickt. Damit werden alle Modelle, die dort eingerichtet
sind — Cloud-Modelle, lokale Ollama-Modelle oder eine eigene Agent-Konfiguration — innerhalb
eines ComfyUI-Workflows nutzbar.

Modell in der Node auswählen, System-Prompt schreiben, Antworttext als String zurückbekommen und
in jeden Prompt-Eingang weiterleiten.

```
prompt ─────────┐
system_prompt ──┤──> OpenCode Prompt ──> text ──> CLIP Text Encode / nächste Node
model ──────────┘
```

## Wozu

Prompt-Eingänge in ComfyUI sind statischer Text. Diese Node macht sie dynamisch: eine grobe Idee
in einen ausführlichen Bildprompt umschreiben, unterwegs übersetzen, ein Konzept zu Varianten
ausbauen, Bildunterschriften erzeugen — oder Stilvorgaben an einer Stelle pflegen und im ganzen
Workflow wiederverwenden.

Weil der Weg über opencode läuft, bist du nicht an einen Anbieter gebunden. Auswählbar ist, was
`opencode models` auflistet.

## Funktionen

- **Modellauswahl in der Oberfläche** — die Combo-Box wird aus `opencode models` gefüllt und passt
  damit immer zur tatsächlich eingerichteten Umgebung (108 Modelle im Referenz-Setup).
- **System-Prompt als Node-Eingang** — die Rolle des Modells gehört zum Workflow, nicht in eine
  Konfigurationsdatei.
- **Beliebiger Anbieter** — Cloud, lokales Ollama, gemischte Setups. Keine zusätzlichen API-Keys
  in ComfyUI.
- **String rein, String raus** — passt in jede bestehende Prompt-Kette, ohne Konvertierungs-Nodes.
- **Wiederverwendeter Agent-Workspace** — die vorbereitete opencode-Umgebung bleibt zwischen
  Ausführungen bestehen.
- **Kein Hintergrunddienst nötig** — jeder Aufruf startet die CLI eigenständig.

## Node-Referenz

`OpenCode Prompt` (Kategorie `opencode`)

| Eingang | Typ | Standard | Beschreibung |
|---|---|---|---|
| `model` | Combo | erstes verfügbares | Gefüllt aus `opencode models`, z. B. `deepseek/deepseek-flash`, `ollama/qwen3.5:9b` |
| `prompt` | String (mehrzeilig) | leer | Der Nutzer-Prompt |
| `system_prompt` | String (mehrzeilig) | leer | System-Prompt / Rollenvorgabe |
| `timeout` | Int | 300 | Sekunden bis Abbruch (1–3600) |

| Ausgang | Typ | Beschreibung |
|---|---|---|
| `text` | String | Antwort des Modells |

## Voraussetzungen

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) (getestet mit v0.45.4)
- [opencode CLI](https://opencode.ai) — installiert und angemeldet (`opencode auth login`)
- Python 3.10+ (die ComfyUI-Umgebung genügt, keine zusätzlichen Pakete)

Vor der Installation prüfen:

```bash
opencode --version
opencode models | head
```

## Installation

```bash
cd /pfad/zu/ComfyUI/custom_nodes
git clone https://github.com/Agantila/comfyui-opencode.git
```

ComfyUI neu starten. Die Node erscheint unter der Kategorie **`opencode`** als
**`OpenCode Prompt`**.

Aus einem lokalen Checkout heraus legt `./install.sh /pfad/zu/ComfyUI` den Symlink an.

## Benutzung

1. `OpenCode Prompt` hinzufügen (Rechtsklick → Add Node → opencode → OpenCode Prompt).
2. `model` auswählen.
3. `prompt` schreiben.
4. `system_prompt` schreiben, zum Beispiel:

   ```
   Du bist Prompt-Engineer für Bildgenerierung. Schreibe die Idee des Nutzers als einen
   ausführlichen, kommagetrennten englischen Prompt um. Gib nur den Prompt aus, keine Erklärung.
   ```

5. Den `text`-Ausgang mit einem `CLIP Text Encode` verbinden.

`timeout` steht standardmäßig auf 300 Sekunden. Aufrufe blockieren — bei langsamen Modellen oder
langen Prompts erhöhen.

### Beispiel

| | |
|---|---|
| `prompt` | `Ein roter Apfel auf einem Holztisch` |
| `system_prompt` | `Antworte mit einem kommagetrennten englischen Bildprompt, keine Erklärung.` |
| `text` | `A single glossy red apple with a fresh green leaf resting on a rustic wooden table, rich crimson skin with soft highlights, visible wood grain, warm natural light` |

Die Ausgabe ist ein echtes Ergebnis dieser Node.

## Konfiguration

| Variable | Standard | Zweck |
|---|---|---|
| `OPENCODE_BIN` | automatisch erkannt | Absoluter Pfad zur opencode-Binary |
| `OPENCODE_WORKSPACE` | `~/.cache/comfyui-opencode/workspace` | Verzeichnis für den wiederverwendeten Agent-Workspace |

## Fehlersuche

**Node erscheint nicht in der Oberfläche.** In der ComfyUI-Konsole nach `comfyui-opencode` suchen.
Lässt sich das Schema nicht bauen, wird die ganze Node ausgeblendet statt einen Fehler in der
Oberfläche zu zeigen. Häufigste Ursache: Die opencode-CLI fehlt im `PATH` des ComfyUI-Prozesses —
ComfyUI wird oft aus einer Umgebung gestartet, die die Shell-rc-Dateien nie geladen hat. Die Node
sucht die üblichen Installationsorte selbst (`~/.opencode/bin`, `~/.local/bin`, `~/.bun/bin`,
`/usr/local/bin`, `/usr/bin`). Schlägt das fehl, `OPENCODE_BIN` setzen.

**`Agent not found`.** opencode v2 hat undokumentiertes Verhalten bei projektlokalen Agents. Die
Node fängt es ab; wer den Code anpasst, sollte es kennen — siehe
[docs/entwicklung.md](docs/entwicklung.md).

**Aufrufe sind langsam.** Jeder Aufruf startet die CLI neu; die Modell-Latenz dominiert. Für
interaktives Arbeiten ein schnelleres Modell wählen.

**Ollama-Modelle fehlen im Dropdown.** Die Liste wird einmal beim Registrieren der Node gelesen.
Nach dem Ziehen eines neuen Modells ComfyUI neu starten.

## Wie es funktioniert

Jeder Aufruf schreibt eine Agent-Definition in einen wiederverwendeten Workspace und führt
`opencode run --agent comfyui-runner --format json` aus. Der JSON-Event-Stream wird geparst, die
`text`-Teile werden verkettet; Reasoning-Blöcke und Tool-Events bleiben unberücksichtigt.

Der Workspace ist ein kleines Git-Repository mit genau einem Commit, weil opencode v2
projektlokale Agent-Konfiguration nur aus einem Verzeichnis liest, das es als Projekt registriert.

### opencode-v2-Fallstricke, die diese Node umgeht

Undokumentiert, und jeder einzelne kostet Stunden. Nach einem Upgrade in dieser Reihenfolge prüfen.

1. **Agents stehen unter `agents`, nicht `agent`.** Der Singular-Schlüssel wird ohne Fehler
   akzeptiert und still ignoriert.
2. **Der Agent-Name darf keinen Unterstrich enthalten.** `comfyui_runner` scheitert,
   `comfyui-runner` funktioniert.
3. **Der Workspace muss ein Git-Repository mit mindestens einem Commit sein.** Ohne Commit fällt
   opencode auf das Projekt `global` zurück und wendet die lokale Konfiguration nie an.
4. **Aufruf über eine Login-Shell.** Derselbe Befehl über `subprocess` scheitert 10/10 mit
   `Agent not found`, über `/bin/bash -lc` gelingt er 10/10. Ursache nicht isoliert.
5. **`--standalone` ist Pflicht**, sonst hängt sich der Aufruf an den Hintergrunddienst, der `cwd`
   ignoriert.

Ausführlich in [docs/entwicklung.md](docs/entwicklung.md).

### Hinweis zum Dateilayout

Die Dateien liegen bewusst flach im Wurzelverzeichnis. ComfyUI lädt ein Node-Verzeichnis unter
einem Modulnamen, der Pfadtrenner enthält — relative Importe in ein Unterpaket lassen sich damit
nicht auflösen. Aus demselben Grund heißt die Node-Datei `opencode_nodes.py` und nicht `nodes.py`,
was mit ComfyUIs eigenem Modul kollidieren würde.

## Entwicklung

```
__init__.py          ComfyUI-Entrypoint (comfy_entrypoint)
opencode_nodes.py    Node-Definition (V3-Schema)
client.py            opencode-CLI-Wrapper, Workspace-Verwaltung
tests/smoke.py       Stabilitätstest über 10 Läufe
docs/entwicklung.md  Debug-Verlauf und Architekturentscheidungen
```

Smoke-Test nach Änderungen:

```bash
python3 tests/smoke.py                    # Standardmodell
python3 tests/smoke.py ollama/qwen3.5:9b  # bestimmtes Modell
```

Erwartet wird `result: 10/10`. Der Test prüft, ob der System-Prompt tatsächlich angewandt wurde —
ein stillschweigend ignorierter Prompt fällt durch.

## Kompatibilität

- ComfyUI v0.45.4 (V3-Schema, `comfy_api.latest`)
- opencode v2.2.7
- Linux (entwickelt und getestet auf Fedora/Nobara mit AMD ROCm)

## Lizenz

[MIT](LICENSE)

---

English: [README.md](README.md)
