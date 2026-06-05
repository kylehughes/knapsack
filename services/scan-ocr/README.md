# Scan OCR Service

Watches `/Users/Shared/Scans` for scanned PDFs, OCRs them with `ocrmypdf`, then moves searchable PDFs to iCloud Drive:

`~/Library/Mobile Documents/com~apple~CloudDocs/New Documents/Scans`

The source of truth lives here:

`/Users/kyle/knapsack/services/scan-ocr`

## Install

```sh
/Users/kyle/knapsack/services/scan-ocr/install.sh
```

## Uninstall

```sh
/Users/kyle/knapsack/services/scan-ocr/uninstall.sh
```

## Status

```sh
launchctl print gui/$(id -u)/com.kyle.scan-ocr
tail -f ~/Library/Logs/scan-ocr.log
```

The service is expected to show `state = not running` when idle. `WatchPaths` wakes it when files are added, and `StartInterval` runs it every 5 minutes as a backstop.

## Restart

```sh
launchctl kickstart gui/$(id -u)/com.kyle.scan-ocr
```

## Dependencies

```sh
brew install ocrmypdf
```

The script also sets a Homebrew-friendly PATH because `launchd` does not read the normal interactive shell startup files.

## Failure Behavior

- Files are ignored until their size and modified time stop changing.
- Only one OCR run is allowed at a time; stale locks are cleaned up automatically.
- Reinstall waits for active OCR to finish instead of killing it mid-file.
- Finished PDFs are copied to a hidden temporary file in the iCloud destination, then renamed into place.
- Startup temp cleanup is limited to the local cache to avoid macOS privacy failures from scanning iCloud Drive under `launchd`.
- Existing destination names are not overwritten; duplicates receive a numbered suffix.
- Originals are removed only after OCR output has been moved successfully.
- Logs rotate to `~/Library/Logs/scan-ocr.log.1` after they exceed 5 MB.

## Live Files

```text
~/bin/scan-ocr
~/Library/LaunchAgents/com.kyle.scan-ocr.plist
~/Library/Logs/scan-ocr.log
/Users/Shared/Scans
```

The executable and LaunchAgent are symlinks back to this directory, so future edits should be made here.
