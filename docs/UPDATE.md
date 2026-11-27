# Update the Pi

## One-time setup

1. The PC and the Pi must be on the home network; SSH must be enabled on the Pi.
2. Run `windows/Set up SSH once.cmd`. If needed, the setup asks for Windows administrator
   approval for the OpenSSH key service.
3. Enter your own key passphrase; then, if needed, enter the Pi password once in the visible
   OpenSSH dialog. Never paste either into the chat.
4. The setup then explicitly verifies a login without a password dialog.

If a connection attempt is aborted, run the same starter again.
A complete existing key pair is reused; use the same passphrase. The earlier bash
syntax error with `base64.b64decode` has been fixed: the registration script is now
transferred via SSH stdin, without nested quotation marks. Other Pi keys are kept;
repeated runs do not add a duplicate entry for the same key.

The dedicated Ed25519 key is stored under `%USERPROFILE%/.ssh/`, outside OneDrive.
The private key stays passphrase-protected and restricted to the Windows user.
The Windows key service stores the ability to log in for this Windows account.
Only the public key is appended on the Pi; other keys are kept.
The `restrict` option blocks forwarding and interactive terminals for this key,
but allows the commands and file transfers in the user account that the update needs.

A known SSH device identity is a prerequisite. If the identity has changed, the setup
aborts; it does not automatically accept and replace a host key.
The password is not stored. Target settings are in `private/pi-update.json`.
On the first run, enter the hostname or IPv4 address of the Raspberry Pi.
The updater expects the Pi account `pi` and the program folder
`~/wetterstation/Wetterstation`. If the address changes, adjust the `host` field
and verify the known device identity again. The historical CLI transfer tools
use the local SSH host alias `wetterstation-pi`.

For the first update, the older Pi application must be closed by hand once.
It does not yet support the new orderly remote shutdown. The update does not start an
application that was closed beforehand; afterwards, use the existing Pi desktop icon once.

## Future updates

Double-click `windows/Update Pi.cmd`. The window shows the progress.
While it works, the window explicitly says "Update läuft" (update in progress). On success,
"Update abgeschlossen" (update completed), a fully filled green bar and
"Fertig. Du kannst dieses Fenster jetzt schließen" (done, you can close this window now)
appear. On errors, instead, "Update mit Fehler beendet" (update finished with an error)
appears in red with the specific hint and without a green bar.
"Fenster schließen" (close window) is enabled after every final state. The backup path and
the program run state are shown below the completion notice.
A second update of the same working folder is blocked. The updater has
neither autostart nor a schedule; only the separately set-up key service starts with Windows.

A separate copy of the current program and test files is created, without
private data. Changes during copying cause an abort. Changes after
copying belong to the next update. The offline tests check this copy;
the same state is packaged and transferred. The report is at
`build/reports/last-update-tests.txt`, the checked package under `build/pi/`.

Before the display is closed, the target, libraries, memory and program identity
are checked and all required files are transferred. Only the clearly identified
weather station is shut down in an orderly way. No forced termination on timeout.
Backup, installation, checksum comparison and offline check on the Pi follow.
Location, country, API key, certificates, caches, device ID, counters and the Pi widget layout
are not imported from the PC or reset.

A previously running application restarts in its previous mode and in the same
desktop session. The new process must confirm that it is ready.
This confirms the program start, not the success of external weather services.
A live start can trigger real weather requests; a previously closed application stays closed.
Phone sessions end with the program restart; browsers sign in again with a new display code.

## Errors and recovery

If installation or offline check fails, the installer restores the previous
program files. After a failed update, nothing is started automatically. If the
restart fails, the new, checked version stays installed; the
window explicitly reports that the start could not be confirmed.

If the connection drops during installation, the state is initially unknown.
Check on the Pi before starting another attempt. Never simply delete the start lock
`.pi-update-in-progress.json`. It names the backup.

Backups are stored outside the program folder under
`~/wetterstation/Wetterstation-Backups/<timestamp>/installation/`.
They contain confidential Pi data and do not belong on GitHub.

On the Pi, with the specific backup path:

```sh
python3 pi_update.py restore --target "$HOME/wetterstation/Wetterstation" --backup "KONKRETER_SICHERUNGSPFAD"
```

If the program tool is damaged, use the standalone `update.py` from the matching
subfolder in `~/wetterstation/.Wetterstation-update-staging/`.
The restore does not reset counters, certificates or newer private changes.
When returning to a state from before the reorganization, the backed-up old
program files are restored as well. Old backups from earlier updater versions
are restored with the version of the tool that belonged to them at the time.

On 28 Oct 2026, key login, secured takeover, orderly shutdown
and restart were verified in the actual Pi desktop session with the widget demo.
The display and phone arrangement were then confirmed by the user as smooth and
working. A missing optional ImageTk was handled without
package installation by native Tk PNG image transfer; details and
measurements in [OPTIMIZATION.md](OPTIMIZATION.md). Still not confirmed by this
demo acceptance: login after a Windows restart and restart in live operation.
