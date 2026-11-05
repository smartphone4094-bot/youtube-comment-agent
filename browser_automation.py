import asyncio
from playwright.async_api import async_playwright
from config import CHROME_PROFILES
import time


def get_available_profiles() -> list[dict]:
    return [
        {"index": i, "name": f"유튜브{i + 1}", "path": path}
        for i, path in enumerate(CHROME_PROFILES)
    ]


async def _post_comment_async(video_id: str, comment: str, profile_index: int, status_callback=None):
    if profile_index >= len(CHROME_PROFILES):
        return {"success": False, "error": f"프로필 {profile_index + 1} 경로가 설정되지 않았습니다."}

    profile_path = CHROME_PROFILES[profile_index]

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
    return asyncio.run(
        _post_comment_async(video_id, comment, profile_index, status_callback)
    )
