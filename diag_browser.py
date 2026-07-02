#!/usr/bin/env python3
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"

server = subprocess.Popen(
    [sys.executable, "server.py"],
    cwd=RUNTIME,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
time.sleep(1)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.add_init_script("""
            window._termLog = [];
            (function patch() {
                if (typeof Terminal !== 'undefined') {
                    const origWrite = Terminal.prototype.write;
                    Terminal.prototype.write = function(data) {
                        window._termLog.push(typeof data === 'string' ? data : new TextDecoder().decode(data));
                        return origWrite.apply(this, arguments);
                    };
                } else {
                    setTimeout(patch, 10);
                }
            })();
        """)

        page.goto("http://127.0.0.1:8000/?v=-1")

        # Wait up to 5 minutes for a shell prompt.
        for i in range(150):
            time.sleep(2)
            log = page.evaluate("() => window._termLog.join('')")
            if "$" in log[-500:]:
                print("Shell prompt appeared")
                break
            if i % 15 == 0:
                print(f"[{(i+1)*2}s] captured {len(log)} chars; last 120: {log[-120:]!r}")
        else:
            print("Timed out waiting for prompt")

        log = page.evaluate("() => window._termLog.join('')")
        print("Captured terminal log length:", len(log))
        print("Last 3000 chars:")
        print(log[-3000:])
        browser.close()
finally:
    server.terminate()
    server.wait(timeout=5)
