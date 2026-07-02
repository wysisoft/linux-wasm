#!/usr/bin/env python3
"""End-to-end test for the JavaScript node process in linux-wasm."""

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"


def main():
    # Start the local dev server.
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

            # Capture console messages from the page for debugging.
            messages = []
            page.on("console", lambda msg: messages.append(f"[{msg.type}] {msg.text}"))

            # Capture page errors.
            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            page.goto("http://127.0.0.1:8000/?v=-1")

            # Wait for the terminal to appear and Linux to boot to a shell.
            terminal = page.locator("#terminal")
            terminal.wait_for(state="visible", timeout=60000)

            # Poll the terminal text for a while and print progress.
            for i in range(60):
                time.sleep(2)
                text = terminal.text_content()
                if "$" in text:
                    break
                # Print progress every ~10s.
                if i % 5 == 0:
                    snippet = text.replace("\n", " ")[:200]
                    print(f"[{(i+1)*2}s] terminal snippet: {snippet!r}")
            else:
                print("FAILURE: shell prompt did not appear after 120s.")
                print("Final terminal text:", terminal.text_content())
                print("Console messages:")
                for m in messages:
                    print(" ", m)
                print("Page errors:")
                for e in page_errors:
                    print(" ", e)
                browser.close()
                return 1

            print("Shell prompt appeared; typing /hello.js")

            # Type the JS program path and press Enter.
            terminal.click()
            page.keyboard.type("/hello.js")
            page.keyboard.press("Enter")

            # Wait for the expected output.
            expected = "Hello from JavaScript process!"
            try:
                page.wait_for_function(
                    f"() => {{ const t = document.querySelector('#terminal'); return t && t.textContent.includes({expected!r}); }}",
                    timeout=30000,
                )
                print("SUCCESS: node process produced expected output.")
                result = 0
            except PlaywrightTimeout:
                print("FAILURE: did not see expected JS output in time.")
                print("Terminal text:", terminal.text_content())
                print("Console messages:")
                for m in messages:
                    print(" ", m)
                print("Page errors:")
                for e in page_errors:
                    print(" ", e)
                result = 1

            browser.close()
            return result
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    sys.exit(main())
