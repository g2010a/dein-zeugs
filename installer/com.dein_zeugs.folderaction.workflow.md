# Automator-Ordneraktion einrichten (optional)

> **Die meisten Nutzer benötigen dies nicht.** `dein-zeugs` lässt sich durch Doppelklick oder über das Terminal starten. Eine Automator-Ordneraktion ist nur sinnvoll, wenn `dein-zeugs` **automatisch** starten soll, sobald eine Datei in den inbox-Ordner abgelegt wird.

Diese Anleitung beschreibt, wie eine macOS-Automator-Ordneraktion konfiguriert wird, sodass das Ablegen einer MP3 in `inbox/` automatisch `dein-zeugs` auslöst.

## Schritte

1. **Automator öffnen**
   - `Cmd+Leertaste` drücken, `Automator` eingeben, Enter drücken.

2. **Neues Dokument erstellen**
   - **Ablage → Neu** auswählen
   - **Ordneraktion** wählen und auf **Auswählen** klicken

3. **Aktion mit dem inbox-Ordner verknüpfen**
   - Oben im Fenster: _„Ordneraktion empfängt Dateien und Ordner, die hinzugefügt werden zu:"_
   - Im Aufklappmenü **Andere...** auswählen
   - Zum `inbox`-Verzeichnis navigieren (Standard: `~/DeinZeugs/inbox`) und **Auswählen** klicken

4. **Aktion „Shell-Skript ausführen" hinzufügen**
   - In der Suchleiste links `Shell-Skript ausführen` eingeben
   - **Shell-Skript ausführen** in den Workflow-Bereich rechts ziehen

5. **Shell-Skript konfigurieren**
   - **Shell:** `/bin/zsh`
   - **Eingabe übergeben:** `als Argumente`
   - Den Standard-Skriptinhalt durch eine der folgenden Varianten ersetzen:

   Für den Standardordner (`~/DeinZeugs`):
   ```zsh
   /usr/local/bin/dein-zeugs >> "$HOME/Library/Logs/dein_zeugs/automator.log" 2>&1
   ```

   Für einen benutzerdefinierten Ordner:
   ```zsh
   /usr/local/bin/dein-zeugs "/absoluter/pfad/zum/projektordner" >> "$HOME/Library/Logs/dein_zeugs/automator.log" 2>&1
   ```

6. **Workflow speichern**
   - `Cmd+S` drücken
   - Namen eingeben: `dein-zeugs inbox-Beobachter`
   - Auf **Sichern** klicken

## Hinweise

- Die `$@`-Argumente (die abgelegten Dateipfade) werden bewusst ignoriert. `dein-zeugs` durchsucht bei jedem Aufruf das gesamte `inbox/`-Verzeichnis und verarbeitet so auch Dateien, die bereits vor dem Auslösen der Aktion vorhanden waren.

- Protokollmeldungen aus Automator-gesteuerten Starts werden in
  `~/Library/Logs/dein_zeugs/automator.log` geschrieben. Das vollständige Protokoll liegt unter
  `~/Library/Logs/dein_zeugs/dein_zeugs.log`.

- Schlägt `dein-zeugs` fehl, wird eine Fehlerseite unter
  `{root}/reports/report.html` erstellt und automatisch im Browser geöffnet.

- Zum Testen: eine einzelne MP3 in den inbox-Ordner ziehen und die Protokolldatei beobachten (`tail -f ~/Library/Logs/dein_zeugs/dein_zeugs.log`).

- Die Sperrdatei unter `{root}/.dein_zeugs.lock` verhindert gleichzeitige Starts, falls `dein-zeugs` manuell und über die Ordneraktion gleichzeitig ausgelöst wird.
