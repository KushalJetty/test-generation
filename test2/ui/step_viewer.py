import tkinter as tk
from tkinter import ttk

class StepViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Live Step Recorder")

        self.tree = ttk.Treeview(self.root, columns=("Action", "Selector", "Value"), show='headings')
        self.tree.heading("Action", text="Action")
        self.tree.heading("Selector", text="Selector")
        self.tree.heading("Value", text="Value")
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.steps = []

    def add_step(self, step):
        self.steps.append(step)
        self.tree.insert("", tk.END, values=(
            step.get("action"),
            step.get("selector"),
            step.get("value", "")
        ))

    def run(self):
        self.root.mainloop()
