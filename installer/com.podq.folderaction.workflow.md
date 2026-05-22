# Automator Folder Action Setup (optional)

> **Most users do not need this.** The release installer puts a `Run podq.command` launcher on your Desktop — double-clicking it processes your `inbox/` and opens the report. Set up an Automator folder action only if you want podq to run **automatically** the moment a file is dropped into the inbox.

This guide walks you through configuring a macOS Automator Folder Action so that
dropping an MP3 into `inbox/` automatically triggers `podq`.

## Steps

1. **Open Automator**
   - Press `Cmd+Space`, type `Automator`, press Enter.

2. **Create a new Folder Action**
   - Go to **File → New**
   - Select **Folder Action** and click **Choose**

3. **Attach the action to your inbox folder**
   - At the top of the window, find: _"Folder Action receives files and folders added to:"_
   - Click the dropdown and select **Other...**
   - Browse to your `inbox` directory (default: `~/Podq/inbox`) and click **Choose**

4. **Add a "Run Shell Script" action**
   - In the search bar on the left, type `Run Shell Script`
   - Drag **Run Shell Script** into the workflow area on the right

5. **Configure the shell script**
   - **Shell:** `/bin/zsh`
   - **Pass input:** `as arguments`
   - Replace the default script body with one of the following:

   For the default root (`~/Podq`):
   ```zsh
   /usr/local/bin/podq >> "$HOME/Library/Logs/podq/automator.log" 2>&1
   ```

   For a custom root:
   ```zsh
   /usr/local/bin/podq "/absolute/path/to/your/root" >> "$HOME/Library/Logs/podq/automator.log" 2>&1
   ```

6. **Save the workflow**
   - Press `Cmd+S`
   - Name it: `podq inbox watcher`
   - Click **Save**

## Notes

- The `$@` arguments (the dropped file paths) are intentionally ignored. `podq` always
  scans the entire `inbox/` directory on each invocation, so it handles batch drops and
  files that were already present before the action fired.

- Logs from Automator-triggered runs are written to
  `~/Library/Logs/podq/automator.log`. The full podq log is at
  `~/Library/Logs/podq/podq.log`.

- If `podq` fails, it writes an error page to
  `{root}/reports/report.html` and opens it in the browser automatically.

- To test the setup: drag a single MP3 into your inbox folder and watch
  `~/Library/Logs/podq/podq.log` for activity (`tail -f ~/Library/Logs/podq/podq.log`).

- The Desktop launcher (`Run podq.command`) and the Automator action are
  not mutually exclusive — both can be installed. The lockfile in
  `{root}/.podq.lock` prevents concurrent runs from colliding.
