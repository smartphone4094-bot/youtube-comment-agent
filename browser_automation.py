import asyncio
import json
import os
import shutil
import subprocess
import sys
from playwright.async_api import async_playwright
import config
import time

_GOOGLE_LOGIN_URL = "https://accounts.google.com/ServiceLogin?continue=https%3A%2F%2Fwww.youtube.com%2F"
_GOOGLE_ACCOUNTS_URL = "https://accounts.google.com/ListAccounts?gpsia=1&source=ChromiumBrowser&json=standard"

_active_login = None


def _run(coro):
    """Run a Playwright coroutine.

    Streamlit (via Tornado) switches Windows to the selector event loop, which cannot start
    subprocesses, so Playwright fails with NotImplementedError under plain asyncio.run().
    """
    if sys.platform == "win32":
        with asyncio.Runner(loop_factory=asyncio.ProactorEventLoop) as runner:
            return runner.run(coro)
    return asyncio.run(coro)


def get_available_profiles() -> list[dict]:
    profiles = config.load_profiles()
    return [
        {"index": i, "name": p.get("name", f"유튜브{i + 1}"), "path": p["path"]}
        for i, p in enumerate(profiles)
    ]


def _find_chrome() -> str | None:
    bases = [os.getenv("PROGRAMFILES"), os.getenv("PROGRAMFILES(X86)"), os.getenv("LOCALAPPDATA")]
    for base in filter(None, bases):
        path = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
        if os.path.isfile(path):
            return path
    return shutil.which("chrome")


def start_google_login():
    """Open Google's sign-in page in a new app-owned Chrome profile.

    Chrome runs with no automation attached because Google refuses sign-in from automated browsers.
    """
    global _active_login
    if _active_login:
        return
    chrome = _find_chrome()
    if not chrome:
        raise FileNotFoundError("chrome.exe not found")
    path = config.new_managed_profile_dir()
    process = subprocess.Popen([
        chrome,
        f"--user-data-dir={path}",
        "--no-first-run",
        "--no-default-browser-check",
        _GOOGLE_LOGIN_URL,
    ])
    _active_login = {"path": path, "process": process}


def google_login_status() -> str | None:
    """None when no login is running, "open" while its window is open, "closed" once it was closed."""
    if not _active_login:
        return None
    return "open" if _active_login["process"].poll() is None else "closed"


def cancel_google_login():
    global _active_login
    if not _active_login:
        return
    login, _active_login = _active_login, None
    login["process"].terminate()
    try:
        login["process"].wait(timeout=5)
    except subprocess.TimeoutExpired:
        login["process"].kill()
    config.remove_managed_profile(login["path"])


def _parse_google_accounts(body: str) -> dict | None:
    accounts = json.loads(body)[1]
    if not accounts:
        return None
    account = accounts[0]
    picture = account[4] or ""
    return {
        "name": account[2] or "",
        "email": account[3] or "",
        "picture": f"https:{picture}" if picture.startswith("//") else picture,
    }


async def _read_google_account_async(profile_path: str) -> dict | None:
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(profile_path, headless=True, channel="chrome")
        try:
            # Fetched from inside the page: context.request bypasses Chrome's network stack and certificates.
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("https://accounts.google.com/robots.txt", wait_until="domcontentloaded")
            body = await page.evaluate(
                "url => fetch(url, {method: 'POST', credentials: 'include'}).then(r => r.text())",
                _GOOGLE_ACCOUNTS_URL,
            )
            return _parse_google_accounts(body)
        finally:
            await context.close()


def finish_google_login() -> dict | None:
    """Read the account from a closed login window. Returns a profile, or None if nobody signed in."""
    global _active_login
    login, _active_login = _active_login, None
    account = None
    try:
        account = _run(_read_google_account_async(login["path"]))
    finally:
        if not account:
            config.remove_managed_profile(login["path"])
    if not account:
        return None
    # ListAccounts only gives a legacy photo URL that shows Google's grey placeholder;
    # the profile Chrome just closed records the account's real photo.
    picture = config.read_chrome_profile_info(login["path"])["picture"] or account["picture"]
    return {**account, "picture": picture, "path": login["path"]}


async def _post_comment_async(video_id: str, comment: str, profile_index: int, status_callback=None):
    profiles = config.load_profiles()
    if profile_index >= len(profiles):
        return {"success": False, "error": f"프로필 {profile_index + 1} 경로가 설정되지 않았습니다."}

    profile_path = profiles[profile_index]["path"]

    async with async_playwright() as p:
        if status_callback:
            status_callback("프로필 여는 중")

        context = await p.chromium.launch_persistent_context(
            profile_path,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )

        try:
            page = context.pages[0] if context.pages else await context.new_page()

            if status_callback:
                status_callback("영상 페이지 이동 중")

            await page.goto(
                f"https://www.youtube.com/watch?v={video_id}",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await page.wait_for_timeout(3000)

            if status_callback:
                status_callback("댓글 창 찾는 중")

            await page.evaluate("window.scrollBy(0, 500)")
            await page.wait_for_timeout(2000)

            comment_box = page.locator("#placeholder-area, #simplebox-placeholder")
            await comment_box.first.click()
            await page.wait_for_timeout(1000)

            if status_callback:
                status_callback("입력 중")

            editable = page.locator("#contenteditable-root")
            await editable.first.click()

            for char in comment:
                await editable.first.type(char, delay=50 + int(50 * (time.time() % 1)))
                await page.wait_for_timeout(30)

            await page.wait_for_timeout(500)

            if status_callback:
                status_callback("게시 중")

            submit_btn = page.locator("#submit-button ytd-button-renderer, #submit-button button")
            await submit_btn.first.click()

            await page.wait_for_timeout(3000)

            if status_callback:
                status_callback("게시 완료 · 댓글 보기")

            await page.wait_for_timeout(2000)
            return {"success": True}

        except Exception as e:
            if status_callback:
                status_callback(f"실패: {str(e)}")
            return {"success": False, "error": str(e)}

        finally:
            await context.close()


def post_comment(video_id: str, comment: str, profile_index: int = 0, status_callback=None) -> dict:
    return _run(
        _post_comment_async(video_id, comment, profile_index, status_callback)
    )
