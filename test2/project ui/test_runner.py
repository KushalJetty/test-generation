import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from playwright.sync_api import sync_playwright
import threading
import queue
import validators

class TestCaseRunner:
    def __init__(self, root):
        self.root = root
        self.root.title("Test Case Executor")
        
        # Execution control
        self.running = False
        self.paused = False
        self.current_step = 0
        self.user_input_queue = queue.Queue()
        self.execution_thread = None
        self.target_url = ""
        
        # UI Setup
        self.create_widgets()
        
    def create_widgets(self):
        # Test Case Load Section
        ttk.Button(self.root, text="Load Test Case", command=self.load_test_case).grid(row=0, column=0, padx=5, pady=5)
        
        # URL Input
        ttk.Label(self.root, text="Target URL:").grid(row=0, column=1, padx=5, pady=5)
        self.url_entry = ttk.Entry(self.root, width=50)
        self.url_entry.grid(row=0, column=2, padx=5, pady=5)
        
        # Headless Mode Toggle
        self.headless_var = tk.BooleanVar()
        ttk.Checkbutton(self.root, text="Headless Mode", variable=self.headless_var).grid(row=0, column=3, padx=5, pady=5)
        
        # Execution Controls
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5)
        
        ttk.Button(self.control_frame, text="Start", command=self.start_execution).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.control_frame, text="Pause", command=self.toggle_pause).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.control_frame, text="Stop", command=self.stop_execution).pack(side=tk.LEFT, padx=2)
        
        # Test Case Steps List
        self.steps_tree = ttk.Treeview(self.root, columns=('Step', 'Action', 'Selector'), show='headings')
        self.steps_tree.heading('Step', text='Step')
        self.steps_tree.heading('Action', text='Action')
        self.steps_tree.heading('Selector', text='Selector')
        self.steps_tree.grid(row=2, column=0, columnspan=4, padx=5, pady=5)
        
        # Execution Log
        self.log_text = tk.Text(self.root, height=10, width=80)
        self.log_text.grid(row=4, column=0, columnspan=4, padx=5, pady=5)

    def load_test_case(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'r') as f:
                self.test_steps = json.load(f)
            self.populate_steps_list()
            self.log_message("Test case loaded successfully!")

    def populate_steps_list(self):
        self.steps_tree.delete(*self.steps_tree.get_children())
        for idx, step in enumerate(self.test_steps, 1):
            self.steps_tree.insert('', 'end', values=(idx, step['action'], step.get('selector', '')))

    def start_execution(self):
        if not hasattr(self, 'test_steps'):
            messagebox.showerror("Error", "Please load a test case first!")
            return
        
        self.target_url = self.url_entry.get().strip()
        if not self.target_url:
            messagebox.showerror("Error", "Please enter a target URL!")
            return
            
        if not validators.url(self.target_url):
            messagebox.showerror("Error", "Please enter a valid URL!")
            return

        self.running = True
        self.paused = False
        self.current_step = 0
        self.log_text.delete(1.0, tk.END)
        self.execution_thread = threading.Thread(target=self.execute_test_case)
        self.execution_thread.start()

    def toggle_pause(self):
        self.paused = not self.paused
        self.log_message(f"Execution {'paused' if self.paused else 'resumed'}")

    def stop_execution(self):
        self.running = False
        self.paused = False
        self.log_message("Execution stopped by user")

    def execute_test_case(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless_var.get())
            page = browser.new_page()
            
            try:
                self.log_message(f"Navigating to {self.target_url}")
                page.goto(self.target_url)
                
                for idx, step in enumerate(self.test_steps):
                    if not self.running:
                        break
                    
                    while self.paused:
                        if not self.running: break
                        self.root.update()
                        
                    self.current_step = idx
                    self.highlight_current_step(idx)
                    
                    if step['action'] == 'click':
                        page.click(step['selector'])
                        self.log_message(f"Step {idx+1}: Clicked {step['selector']}")
                    elif step['action'] == 'input':
                        value = step['value']
                        
                        if value.startswith('{') and value.endswith('}'):
                            var_name = value[1:-1]
                            self.show_input_prompt(var_name)
                            input_value = self.user_input_queue.get()
                            if input_value is None:
                                self.running = False
                                break
                            value = input_value
                        
                        page.fill(step['selector'], value)
                        self.log_message(f"Step {idx+1}: Filled {step['selector']} with {value}")
                        
                    self.root.update()
                
                browser.close()
                self.log_message("Test execution completed!")
            except Exception as e:
                self.log_message(f"Error occurred: {str(e)}")
                browser.close()

    def show_input_prompt(self, var_name):
        input_dialog = tk.Toplevel(self.root)
        input_dialog.title(f"Input for {var_name}")
        
        ttk.Label(input_dialog, text=f"Enter value for {var_name}:").pack(padx=10, pady=5)
        entry = ttk.Entry(input_dialog)
        entry.pack(padx=10, pady=5)
        
        def submit():
            self.user_input_queue.put(entry.get())
            input_dialog.destroy()
            
        def cancel():
            self.user_input_queue.put(None)
            input_dialog.destroy()
            
        ttk.Button(input_dialog, text="Submit", command=submit).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(input_dialog, text="Cancel", command=cancel).pack(side=tk.RIGHT, padx=5, pady=5)
        
        input_dialog.transient(self.root)
        input_dialog.grab_set()
        self.root.wait_window(input_dialog)

    def highlight_current_step(self, idx):
        for item in self.steps_tree.get_children():
            self.steps_tree.item(item, tags=())
        self.steps_tree.item(self.steps_tree.get_children()[idx], tags=('current',))
        self.steps_tree.tag_configure('current', background='lightblue')
        self.steps_tree.see(self.steps_tree.get_children()[idx])

    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = TestCaseRunner(root)
    root.mainloop()