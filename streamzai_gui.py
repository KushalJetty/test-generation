import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import json
from streamzai_test_generator import StreamzAITestGenerator, logger

class StreamzAIGUI(tk.Tk):
    """Tkinter GUI for StreamzAI Test Generator."""
    
    def __init__(self):
        """Initialize the GUI."""
        super().__init__()
        
        self.title("StreamzAI Test Generator")
        self.geometry("600x500")
        self.resizable(True, True)
        
        # Set icon if available
        try:
            self.iconbitmap("icon.ico")
        except:
            pass
        
        # Configure style
        self.style = ttk.Style(self)
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TEntry", font=("Arial", 10))
        
        # Create main frame
        self.main_frame = ttk.Frame(self, padding="20 20 20 20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create form elements
        self._create_widgets()
        
        # Load API key from environment if available
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if api_key:
            self.api_key_entry.insert(0, api_key)
        
        # Initialize generator
        self.generator = None
        
        # Progress variables
        self.progress_var = tk.DoubleVar(self)
        self.status_var = tk.StringVar(self)
        self.status_var.set("Ready")
    
    def _create_widgets(self):
        """Create all widgets for the GUI."""
        # API Key
        ttk.Label(self.main_frame, text="Google API Key:", style="TLabel").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.api_key_entry = ttk.Entry(self.main_frame, width=50, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=(0, 5))
        
        # Show/Hide API Key
        self.show_api_key = tk.BooleanVar()
        self.show_api_key.set(False)
        self.show_api_key_check = ttk.Checkbutton(
            self.main_frame, 
            text="Show API Key", 
            variable=self.show_api_key,
            command=self._toggle_api_key_visibility
        )
        self.show_api_key_check.grid(row=1, column=1, sticky=tk.W, pady=(0, 10))
        
        # Project Directory
        ttk.Label(self.main_frame, text="Project Directory:", style="TLabel").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.project_dir_frame = ttk.Frame(self.main_frame)
        self.project_dir_frame.grid(row=2, column=1, sticky=tk.W+tk.E, pady=(0, 5))
        
        self.project_dir_entry = ttk.Entry(self.project_dir_frame, width=40)
        self.project_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.project_dir_button = ttk.Button(
            self.project_dir_frame, 
            text="Browse...", 
            command=self._browse_project_dir
        )
        self.project_dir_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Output Directory
        ttk.Label(self.main_frame, text="Output Directory:", style="TLabel").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.output_dir_frame = ttk.Frame(self.main_frame)
        self.output_dir_frame.grid(row=3, column=1, sticky=tk.W+tk.E, pady=(0, 5))
        
        self.output_dir_entry = ttk.Entry(self.output_dir_frame, width=40)
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.output_dir_entry.insert(0, "generated_tests")
        
        self.output_dir_button = ttk.Button(
            self.output_dir_frame, 
            text="Browse...", 
            command=self._browse_output_dir
        )
        self.output_dir_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Progress bar
        ttk.Label(self.main_frame, text="Progress:", style="TLabel").grid(row=4, column=0, sticky=tk.W, pady=(20, 5))
        self.progress_bar = ttk.Progressbar(
            self.main_frame, 
            orient=tk.HORIZONTAL, 
            length=400, 
            mode='determinate'
        )
        # Configure progress bar manually instead of using variable binding
        self.progress_bar.grid(row=4, column=1, sticky=tk.W+tk.E, pady=(20, 5))
        
        # Status label
        self.status_label = ttk.Label(self.main_frame, text="Ready", style="TLabel")
        self.status_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(5, 20))
        
        # Generate button
        self.generate_button = ttk.Button(
            self.main_frame, 
            text="Generate Tests", 
            command=self._generate_tests
        )
        self.generate_button.grid(row=6, column=1, sticky=tk.E, pady=(0, 5))
        
        # Configure grid
        self.main_frame.columnconfigure(1, weight=1)
    
    def _toggle_api_key_visibility(self):
        """Toggle API key visibility."""
        if self.show_api_key.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
    
    def _browse_project_dir(self):
        """Open file dialog to select project directory."""
        directory = filedialog.askdirectory(title="Select Project Directory")
        if directory:
            self.project_dir_entry.delete(0, tk.END)
            self.project_dir_entry.insert(0, directory)
    
    def _browse_output_dir(self):
        """Open file dialog to select output directory."""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, directory)
    
    def _validate_inputs(self):
        """Validate user inputs before generating tests."""
        # Check API key
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter your Google API key.")
            return False
        
        # Check project directory
        project_dir = self.project_dir_entry.get().strip()
        if not project_dir:
            messagebox.showerror("Error", "Please select a project directory.")
            return False
        
        if not os.path.isdir(project_dir):
            messagebox.showerror("Error", "The selected project directory does not exist.")
            return False
        
        # Check output directory
        output_dir = self.output_dir_entry.get().strip()
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory.")
            return False
        
        return True
    
    def _update_progress(self, current, total):
        """Update progress bar."""
        progress = (current / total) * 100 if total > 0 else 0
        # Update progress bar directly instead of using variable
        self.progress_bar["value"] = progress
        # Update status text directly
        self.status_label.config(text=f"Processing file {current} of {total}")
        self.update_idletasks()
    
    def _generate_tests(self):
        """Generate test cases for the selected project."""
        if not self._validate_inputs():
            return
        
        # Get input values
        api_key = self.api_key_entry.get().strip()
        project_dir = self.project_dir_entry.get().strip()
        output_dir = self.output_dir_entry.get().strip()
        
        # Disable UI elements during generation
        self._set_ui_state(tk.DISABLED)
        
        # Reset progress
        self.progress_var.set(0)
        self.status_var.set("Initializing...")
        
        # Start generation in a separate thread
        threading.Thread(target=self._run_generation, args=(api_key, project_dir, output_dir), daemon=True).start()
    
    def _run_generation(self, api_key, project_dir, output_dir):
        """Run test generation in a separate thread."""
        try:
            # Initialize generator
            self.generator = StreamzAITestGenerator(api_key=api_key)
            
            # Find supported files
            self.status_var.set("Scanning project directory...")
            self.update_idletasks()
            supported_files = self.generator.traverse_directory(project_dir)
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate test cases
            total_files = len(supported_files)
            successful = 0
            failed = 0
            test_files = []
            
            for i, file_path in enumerate(supported_files):
                # Update progress
                self._update_progress(i + 1, total_files)
                
                # Analyze file
                file_analysis = self.generator.analyze_file(file_path)
                
                # Generate test case
                test_case = self.generator.generate_test_case(file_analysis)
                
                # Save test case
                save_result = self.generator.save_test_case(test_case, output_dir)
                
                if isinstance(save_result, str) and save_result.startswith("Error"):
                    failed += 1
                    test_files.append({
                        "original_file": file_path,
                        "status": "failed",
                        "error": save_result
                    })
                else:
                    successful += 1
                    test_files.append({
                        "original_file": file_path,
                        "test_file": save_result,
                        "status": "success"
                    })
            
            # Save summary
            results = {
                "total_files": total_files,
                "successful": successful,
                "failed": failed,
                "test_files": test_files
            }
            
            summary_path = os.path.join(output_dir, "test_generation_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            # Update UI
            self.status_var.set(f"Completed: {successful} successful, {failed} failed")
            messagebox.showinfo("Generation Complete", 
                               f"Test generation complete!\n\n"
                               f"Total files: {total_files}\n"
                               f"Successful: {successful}\n"
                               f"Failed: {failed}\n\n"
                               f"Results saved to: {os.path.abspath(output_dir)}")
            
        except Exception as e:
            logger.error(f"Error generating tests: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred during test generation:\n{str(e)}")
        
        finally:
            # Re-enable UI elements
            self._set_ui_state(tk.NORMAL)
    
    def _set_ui_state(self, state):
        """Enable or disable UI elements."""
        self.api_key_entry.config(state=state)
        self.show_api_key_check.config(state=state)
        self.project_dir_entry.config(state=state)
        self.project_dir_button.config(state=state)
        self.output_dir_entry.config(state=state)
        self.output_dir_button.config(state=state)
        self.generate_button.config(state=state)


def main():
    """Main entry point for the GUI application."""
    app = StreamzAIGUI()
    app.mainloop()


if __name__ == "__main__":
    main()