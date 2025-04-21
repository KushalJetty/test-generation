import asyncio
import os
from recorder.browser import launch_browser
from recorder.action_tracker import ActionTracker

async def main():
    page, browser, playwright = await launch_browser()
    tracker = ActionTracker(page)
    await tracker.start_tracking()

    print("Tracking started. Interact with the browser.")
    await page.goto("https://test.teamstreamz.com")

    try:
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print("\n👋 Cancelled by user. Saving recorded steps...")
        os.makedirs("tests", exist_ok=True)
        tracker.save_steps("tests/recorded_steps.json")
        print("✅ Steps saved to tests/recorded_steps.json")
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        task = loop.create_task(main())
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        for task in asyncio.all_tasks(loop):
            task.cancel()
        try:
            loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
        except asyncio.CancelledError:
            pass  # normal cancellation
        except Exception as e:
            print("Error during shutdown:", e)
        finally:
            loop.run_until_complete(asyncio.sleep(0.1))  # allow cleanup
            loop.close()

            # ⬇️ Add this inside finally block to clean up lingering Node subprocesses
            import signal, psutil

            current_process = psutil.Process()
            for child in current_process.children(recursive=True):
                try:
                    child.send_signal(signal.SIGTERM)
                except Exception:
                    pass
