"""PC program entry point: runs the Streamlit app in-process and opens it as a Chrome app window.

Used by the PyInstaller build (MarketingAI.exe). `streamlit run app.py` keeps working as before.
Closing the app window (or this console) quits the program.
"""

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

import config


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(url: str, timeout: float = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url + "/_stcore/health", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def _open_window(url: str):
    """Open the UI; when the Chrome app window closes, end the program."""
    if not _wait_until_up(url):
        print("서버가 시작되지 않았습니다. data/error.log 를 확인하세요.")
        return
    from browser_automation import _find_chrome

    chrome = _find_chrome()
    if not chrome:
        webbrowser.open(url)
        print(f"Chrome을 찾지 못해 기본 브라우저로 열었습니다: {url}")
        print("종료하려면 이 창을 닫으세요.")
        return
    profile = config.user_path("data", "app_window")
    os.makedirs(profile, exist_ok=True)
    started = time.time()
    process = subprocess.Popen([
        chrome,
        f"--app={url}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1400,900",
    ])
    print(f"프로그램 창을 열었습니다: {url}")
    print("프로그램 창을 닫으면 자동으로 종료됩니다. (이 창을 닫아도 종료)")
    process.wait()
    if time.time() - started < 5:
        # Chrome handed the window to an already-open instance of this profile; we cannot track it.
        print("창이 이미 열려 있는 프로그램 창으로 넘어갔습니다. 종료하려면 이 창을 닫으세요.")
        return
    os._exit(0)


def _check_browser() -> int:
    """`MarketingAI.exe --check-browser`: confirms the bundled Playwright driver can drive Chrome."""
    import tempfile

    import browser_automation

    async def probe(profile):
        async with browser_automation.async_playwright() as p:
            context = await p.chromium.launch_persistent_context(profile, headless=True, channel="chrome")
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("data:text/html,ok", wait_until="domcontentloaded")
            text = await page.evaluate("document.body.innerText")
            await context.close()
            return text

    with tempfile.TemporaryDirectory(dir=config.user_path("data")) as profile:
        text = browser_automation._run(probe(profile))
    print("browser check:", text)
    return 0 if text == "ok" else 1


def main():
    if "--check-browser" in sys.argv:
        os.makedirs(config.user_path("data"), exist_ok=True)
        sys.exit(_check_browser())
    port = _free_port()
    url = f"http://localhost:{port}"
    # Same as `streamlit run` flags (bootstrap turns "server_port" into "server.port").
    flag_options = {
        "server_headless": True,
        "server_port": port,
        "server_address": "localhost",
        "browser_gatherUsageStats": False,
        "global_developmentMode": False,  # frozen builds otherwise look like a Streamlit dev checkout
        "server_fileWatcherType": "none",
        "server_runOnSave": False,
    }
    from streamlit.web import bootstrap

    print("운명원 마케팅 AI에이전트를 시작하는 중...")
    threading.Thread(target=_open_window, args=(url,), daemon=True).start()
    # args=[]: the script's sys.argv is just app.py, so --ui-dev is never on in the program.
    bootstrap.load_config_options(flag_options)  # what `streamlit run` does before bootstrap.run
    bootstrap.run(config.resource_path("app.py"), False, [], flag_options)


if __name__ == "__main__":
    main()
