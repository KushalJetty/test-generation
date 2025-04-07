from ..core.recorder import SeleniumRecorder

class RecorderService:
    def __init__(self):
        self.recorder = SeleniumRecorder()
        
    def start_recording(self, url):
        return self.recorder.start_recording(url)
        
    def stop_recording(self):
        return self.recorder.stop_recording()
        
    def get_actions(self):
        return self.recorder.actions
        
    def update_action(self, index, action_data):
        if index < 0 or index >= len(self.recorder.actions):
            raise ValueError("Invalid action index")
            
        self.recorder.actions[index].update(action_data)
        return True
        
    def delete_action(self, index):
        if index < 0 or index >= len(self.recorder.actions):
            raise ValueError("Invalid action index")
            
        del self.recorder.actions[index]
        return True
        
    def generate_selenium_test(self, test_name):
        return self.recorder.generate_selenium_test(test_name)
        
    def generate_playwright_test(self, test_name):
        # Implement playwright test generation
        pass