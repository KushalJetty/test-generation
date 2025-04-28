import asyncio
import threading
from flask import Response
import queue
from flask import Flask, render_template, request, jsonify
from playwright.async_api import async_playwright
import json

app = Flask(__name__)

# Add after global variables
event_queue = queue.Queue()

# Async thread for Playwright operations
class AsyncThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

async_thread = AsyncThread()
async_thread.start()

def run_async(coroutine):
    future = asyncio.run_coroutine_threadsafe(coroutine, async_thread.loop)
    return future.result()

# Global variables in async context
browser = None
playwright = None
page = None
tracker = None
recorded_url = None

class ActionTracker:
    def __init__(self, page):
        self.page = page
        self.steps = []

    async def start_tracking(self):
        await self.page.expose_function("recordAction", self.record_action)
        await self.page.add_init_script(self.tracking_script())

    async def record_action(self, action):
        self.steps.append(action)
        try:
            event_queue.put_nowait({'type': 'action', 'data': action})
        except queue.Full:
            pass

    def tracking_script(self):
        return """
            (() => {
                function getSelector(el) {
                    if (el.id) return `#${el.id}`;
                    if (el.name) return `[name="${el.name}"]`;
                    if (el.className) return `.${el.className.split(" ").join(".")}`;
                    return el.tagName.toLowerCase();
                }

                document.addEventListener('click', e => {
                    const selector = getSelector(e.target);
                    window.recordAction({
                        action: "click",
                        selector: selector,
                        timestamp: Date.now()
                    });
                }, true);

                document.addEventListener('input', e => {
                    const selector = getSelector(e.target);
                    window.recordAction({
                        action: "input",
                        selector: selector,
                        value: e.target.value,
                        timestamp: Date.now()
                    });
                }, true);
            })();
        """

    def save_steps(self, filename="tests/recorded_steps.json"):
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(self.steps, f, indent=4)

def generate_code(steps):
    global recorded_url
    code = [
        "from playwright.async_api import async_playwright\n",
        "import asyncio\n\n",
        "async def test_recorded_actions():\n",
        "    async with async_playwright() as p:\n",
        "        browser = await p.chromium.launch(headless=False)\n",
        "        page = await browser.new_page()\n",
        f"        await page.goto('{recorded_url}')\n"
    ]
    for step in steps:
        if step['action'] == 'click':
            code.append(f"        await page.click('{step['selector']}')\n")
        elif step['action'] == 'input':
            code.append(f"        await page.fill('{step['selector']}', '{step['value']}')\n")
    code.append("        await browser.close()\n")
    code.append("asyncio.run(test_recorded_actions())")
    return ''.join(code)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-recording', methods=['POST'])
def handle_start():
    global recorded_url
    data = request.get_json()
    recorded_url = data['url']
    run_async(start_recording())
    return '', 204

@app.route('/clear-recording', methods=['POST'])
def handle_clear():
    run_async(clear_recording())
    return '', 204

async def clear_recording():
    global tracker
    if tracker:
        tracker.steps = []
    # Clear any pending events in the queue
    while not event_queue.empty():
        try:
            event_queue.get_nowait()
        except queue.Empty:
            break
    event_queue.put({'type': 'clear', 'data': None})
    

@app.route('/stream')
def stream():
    def event_stream():
        while True:
            try:
                event = event_queue.get(timeout=1)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                continue
    return Response(event_stream(), mimetype="text/event-stream")

async def start_recording():
    global browser, playwright, page, tracker
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    tracker = ActionTracker(page)
    await tracker.start_tracking()
    await page.goto(recorded_url)

@app.route('/stop-recording', methods=['POST'])
def handle_stop():
    result = run_async(stop_recording())
    return jsonify(result)

async def stop_recording():
    global browser, playwright, tracker
    tracker.save_steps()
    code = generate_code(tracker.steps)
    event_queue.put({'type': 'code', 'data': code})
    await browser.close()
    await playwright.stop()
    return {'steps': tracker.steps, 'code': code}

if __name__ == '__main__':
    app.run(debug=True)