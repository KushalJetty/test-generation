import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict
import csv

class TestCaseOptimizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Playwright Test Optimizer")
        
        # Variables
        self.original_steps = []
        self.optimized_steps = []
        self.variable_mapping = {}
        self.current_vars = {}
        
        # UI Setup
        self.create_widgets()
        
    def create_widgets(self):
        # File Upload Section
        ttk.Button(self.root, text="Upload Test Case", command=self.upload_file).grid(row=0, column=0, padx=5, pady=5)
        
        # Processing Section
        ttk.Button(self.root, text="Optimize Test Case", command=self.optimize_steps).grid(row=0, column=1, padx=5, pady=5)
        
        # Variable Mapping Display
        self.tree = ttk.Treeview(self.root, columns=('Selector', 'Variable'), show='headings')
        self.tree.heading('Selector', text='Selector')
        self.tree.heading('Variable', text='Variable')
        self.tree.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # Export Section
        ttk.Button(self.root, text="Export Optimized JSON", command=self.export_json).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(self.root, text="Export CSV Template", command=self.export_csv).grid(row=2, column=1, padx=5, pady=5)
        
        # Console-like Text Area
        self.console = tk.Text(self.root, height=15, width=80)
        self.console.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

    def upload_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'r') as f:
                self.original_steps = json.load(f)
            self.log_message("Original test case loaded successfully!")

    def optimize_steps(self):
        if not self.original_steps:
            messagebox.showerror("Error", "Please upload a test case first!")
            return

        optimized = []
        current_selector = None
        current_action = None
        input_buffer = []

        for step in self.original_steps:
            if step['action'] == 'input':
                if step['selector'] == current_selector and current_action == 'input':
                    input_buffer.append(step)
                else:
                    if input_buffer:
                        optimized.append(self.create_optimized_input(input_buffer))
                        input_buffer = []
                    current_selector = step['selector']
                    current_action = 'input'
                    input_buffer.append(step)
            else:
                if input_buffer:
                    optimized.append(self.create_optimized_input(input_buffer))
                    input_buffer = []
                current_selector = None
                current_action = None
                optimized.append(step)

        if input_buffer:
            optimized.append(self.create_optimized_input(input_buffer))

        self.optimized_steps = optimized
        self.generate_variable_mapping()
        self.display_variables()
        self.log_message("Optimization complete! Generated variable mapping.")

    def create_optimized_input(self, steps):
        final_value = steps[-1]['value']
        return {
            "action": "input",
            "selector": steps[0]['selector'],
            "value": final_value,
            "timestamp": steps[0]['timestamp']
        }

    def generate_variable_mapping(self):
        self.variable_mapping = defaultdict(str)
        var_counter = 1
        
        for step in self.optimized_steps:
            if step['action'] == 'input':
                selector = step['selector']
                if selector not in self.variable_mapping:
                    self.variable_mapping[selector] = f"var_{var_counter}"
                    var_counter += 1
                step['value'] = f"{{{self.variable_mapping[selector]}}}"

    def display_variables(self):
        self.tree.delete(*self.tree.get_children())
        for selector, var in self.variable_mapping.items():
            self.tree.insert('', 'end', values=(selector, var))

    def export_json(self):
        if not self.optimized_steps:
            messagebox.showerror("Error", "No optimized test case to export!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.optimized_steps, f, indent=2)
            self.log_message("Optimized JSON exported successfully!")

    def export_csv(self):
        if not self.variable_mapping:
            messagebox.showerror("Error", "Generate variable mapping first!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if file_path:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = list(self.variable_mapping.values())
                writer.writerow(headers)
                writer.writerow([''] * len(headers))
            self.log_message("CSV template exported successfully!")

    def log_message(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = TestCaseOptimizer(root)
    root.mainloop()