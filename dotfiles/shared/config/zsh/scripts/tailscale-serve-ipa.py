#!/usr/bin/env python3
"""Serve a signed iOS build over Tailscale. Run with --help for usage.

Requires Python 3.9+, Tailscale with HTTPS enabled, and Xcode 15.3+ for exports.
Exit codes: 1 invalid IPA, 2 usage or dependency, 3 build/export, 4 serving,
130 interrupted, 143 terminated. Temporary files and serving stop on exit.
"""

import argparse
from functools import partial
import html
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
from socketserver import TCPServer
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlencode
from xml.parsers.expat import ExpatError
import zipfile


class Failure(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="tailscale-serve-ipa", allow_abbrev=False,
        description="Serve a signed iOS build for installation from Safari over Tailscale.",
        epilog="The iPhone must reach this Mac through Tailscale. The build must be "
               "signed for that device. Archive exports use development signing. "
               "Keep this command running until installation finishes; Ctrl-C stops serving.",
    )
    parser.add_argument("input", nargs="?", type=Path, help="an .ipa or .xcarchive")
    parser.add_argument("--scheme", help="archive and export this scheme")
    container = parser.add_mutually_exclusive_group()
    container.add_argument("--workspace", type=Path)
    container.add_argument("--project", type=Path)
    parser.add_argument("--configuration", help="build configuration (default: Debug)")
    parser.add_argument("--port", type=int, default=8443, help="Tailscale HTTPS port (default: 8443)")
    args = parser.parse_args(argv)
    if bool(args.input) == bool(args.scheme):
        parser.error("provide an IPA/archive or --scheme")
    if not args.scheme and any((args.workspace, args.project, args.configuration is not None)):
        parser.error("--workspace, --project, and --configuration require --scheme")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.input:
        args.input = args.input.resolve()
        valid = (args.input.suffix == ".ipa" and args.input.is_file()
                 or args.input.suffix == ".xcarchive" and args.input.is_dir())
        if not valid:
            parser.error("input must be an existing .ipa file or .xcarchive directory")
    return args


def run_command(argv, code, capture=False):
    # A separate process group lets cancellation stop Xcode's descendants too.
    process = subprocess.Popen(argv, start_new_session=True,
                               stdout=subprocess.PIPE if capture else None, text=True)
    completed = False
    try:
        output, _ = process.communicate()
        completed = True
        if process.returncode:
            raise Failure(f"{argv[0]} failed (exit {process.returncode})", code)
        return output
    finally:
        if not completed:
            # Closing the foreground Serve session removes only its own listener.
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(process.pid, sig)
                except ProcessLookupError:
                    break
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    process.poll()
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(0.05)
                else:
                    continue
                break
            process.wait()


def tailscale_host():
    try:
        status = json.loads(run_command(["tailscale", "status", "--json"], 2, capture=True))
        host = status["Self"]["DNSName"].rstrip(".")
        if status.get("BackendState") != "Running" or not re.fullmatch(r"[a-zA-Z0-9.-]+", host):
            raise ValueError("Tailscale is not connected")
        return host
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise Failure("Could not read this Mac's MagicDNS name; connect Tailscale first", 2) from error


def export_ipa(args, work_dir):
    if args.input and args.input.suffix == ".ipa":
        return args.input
    archive = args.input or work_dir / "app.xcarchive"
    if args.scheme:
        command = ["xcodebuild", "archive"]
        if args.workspace:
            command += ["-workspace", str(args.workspace)]
        elif args.project:
            command += ["-project", str(args.project)]
        command += ["-scheme", args.scheme, "-configuration", args.configuration or "Debug",
                    "-destination", "generic/platform=iOS", "-archivePath", str(archive),
                    "-allowProvisioningUpdates", "-quiet"]
        print(f"Archiving {args.scheme} ({args.configuration or 'Debug'})...", flush=True)
        run_command(command, 3)
    options = work_dir / "ExportOptions.plist"
    options.write_bytes(plistlib.dumps({"method": "debugging"}))
    export_dir = work_dir / "export"
    print("Exporting IPA...", flush=True)
    run_command(["xcodebuild", "-exportArchive", "-archivePath", str(archive),
                 "-exportPath", str(export_dir), "-exportOptionsPlist", str(options),
                 "-allowProvisioningUpdates", "-quiet"], 3)
    ipas = list(export_dir.glob("*.ipa"))
    if len(ipas) != 1:
        raise Failure("Export must produce exactly one IPA; check the iOS archive", 3)
    return ipas[0]


def read_metadata(ipa):
    try:
        with zipfile.ZipFile(ipa) as archive:
            # A watch app can have another Info.plist deeper inside the main app.
            candidates = [entry for entry in archive.infolist()
                          if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", entry.filename)]
            if len(candidates) != 1:
                raise ValueError("expected one top-level app Info.plist")
            info = plistlib.loads(archive.read(candidates[0]))
        for key in ("CFBundleIdentifier", "CFBundleVersion"):
            if not isinstance(info.get(key), str) or not info[key].strip():
                raise ValueError(f"missing {key}")
        title = info.get("CFBundleDisplayName") or info.get("CFBundleName") or info["CFBundleIdentifier"]
        version = info.get("CFBundleShortVersionString") or info["CFBundleVersion"]
        if not isinstance(title, str) or not isinstance(version, str):
            raise ValueError("app title and version must be strings")
        return info["CFBundleIdentifier"], info["CFBundleVersion"], title, version
    except (OSError, ValueError, TypeError, AttributeError, ExpatError, zipfile.BadZipFile,
            plistlib.InvalidFileException, RuntimeError) as error:
        raise Failure(f"Could not read IPA metadata: {error}", 1) from error


def prepare_site(ipa, site, base_url):
    bundle_id, build, title, version = read_metadata(ipa)
    site.mkdir()
    shutil.copyfile(ipa, site / "app.ipa")
    stamp = time.time_ns()
    manifest = {"items": [{
        "assets": [{"kind": "software-package", "url": f"{base_url}/app.ipa?v={stamp}"}],
        "metadata": {"bundle-identifier": bundle_id, "bundle-version": build,
                     "kind": "software", "title": title},
    }]}
    (site / "manifest.plist").write_bytes(plistlib.dumps(manifest))
    install_url = "itms-services://?" + urlencode({
        "action": "download-manifest", "url": f"{base_url}/manifest.plist?v={stamp}",
    })
    (site / "index.html").write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Install {html.escape(title)}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 17px -apple-system, sans-serif; margin: 48px 24px; text-align: center; }}
  a {{ display: inline-block; margin-top: 24px; padding: 14px 32px; border-radius: 12px;
       background: #007aff; color: #fff; text-decoration: none; font-weight: 600; }}
  p {{ color: gray; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>{html.escape(bundle_id)}<br>{html.escape(version)} ({html.escape(build)})</p>
<a href="{html.escape(install_url)}">Install</a>
</body>
</html>
""", encoding="utf-8")
    return f"{title} {version} ({build})"


class InstallHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".ipa": "application/octet-stream", ".plist": "text/xml"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        pass


class InstallServer(ThreadingHTTPServer):
    def server_bind(self):
        # The proxy uses a numeric loopback address; reverse DNS can stall startup.
        TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]


def serve(site, port, base_url, label):
    handler = partial(InstallHandler, directory=str(site))
    # Bind once and keep the socket; there is no free-port selection race.
    with InstallServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            print(f"\nServing {label}\nOpen on the iPhone: {base_url}/\n"
                  "Press Ctrl-C to stop.\n", flush=True)
            run_command(["tailscale", "serve", f"--https={port}",
                         f"http://127.0.0.1:{server.server_port}"], 4)
        finally:
            server.shutdown()
            thread.join()


def main(argv=None):
    args = parse_args(argv)
    try:
        dependencies = ["tailscale"]
        if args.scheme or args.input.suffix == ".xcarchive":
            dependencies.append("xcodebuild")
        for tool in dependencies:
            if shutil.which(tool) is None:
                raise Failure(f"'{tool}' not found", 2)
        host = tailscale_host()
        base_url = f"https://{host}" + (f":{args.port}" if args.port != 443 else "")
        with tempfile.TemporaryDirectory(prefix="tailscale-serve-ipa-") as temporary:
            work_dir = Path(temporary)
            ipa = export_ipa(args, work_dir)
            site = work_dir / "site"
            label = prepare_site(ipa, site, base_url)
            serve(site, args.port, base_url, label)
        return 0
    except Failure as error:
        print(f"Error: {error}", file=sys.stderr)
        return error.code
    except OSError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 4


def stop(signum, frame):
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
