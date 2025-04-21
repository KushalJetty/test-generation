import time
import os
import json

class ActionTracker:
    def __init__(self, page):
        self.page = page
        self.steps = []

    async def start_tracking(self):
        await self.page.expose_function("recordAction", self._record_action)
        await self.page.add_init_script(self._tracking_script())

    async def _record_action(self, action):
        print("Recorded Step:", action)
        self.steps.append(action)

    def _tracking_script(self):
        return """
            (() => {
                function getSelector(el) {
                    if (el.id) return `#${el.id}`;
                    if (el.name) return `[name="${el.name}"]`;
                    if (el.className && typeof el.className === 'string') return `.${el.className.split(" ").join(".")}`;
                    return el.tagName.toLowerCase();
                }

                document.addEventListener('click', (e) => {
                    const target = e.target;
                    const selector = getSelector(target);
                    window.recordAction({
                        timestamp: Date.now(),
                        action: "click",
                        selector: selector
                    });
                }, true);

                document.addEventListener('input', (e) => {
                    const target = e.target;
                    const selector = getSelector(target);
                    const value = target.value;
                    window.recordAction({
                        timestamp: Date.now(),
                        action: "input",
                        selector: selector,
                        value: value
                    });
                }, true);
            })();
        """

    import os

    def save_steps(self, filename="tests/recorded_steps.json"):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(self.steps, f, indent=4)
