import pandas as pd
import json
import os
import re

class TestOptimizer:
    """
    Optimizes test steps by removing redundant operations and handling input values.
    """
    
    def __init__(self, mode='default', inputs=None):
        """
        Initialize the optimizer with a specific mode and input data.
        
        Args:
            mode (str): Optimization mode ('default', 'custom')
            inputs (dict): Input data for custom mode
        """
        self.mode = mode
        self.input_values = {}
        
        # Load input data if provided
        if inputs:
            self._load_inputs(inputs)
    
    def _load_inputs(self, inputs):
        """
        Load input data from various sources.
        
        Args:
            inputs (dict): Input data configuration
        """
        if not inputs:
            return
        
        source_type = inputs.get('type', '')
        source_path = inputs.get('path', '')
        
        if not source_path:
            return
        
        try:
            if source_type == 'excel':
                self._load_excel_inputs(source_path)
            elif source_type == 'csv':
                self._load_csv_inputs(source_path)
            elif source_type == 'json':
                self._load_json_inputs(source_path)
        except Exception as e:
            print(f"Error loading inputs: {str(e)}")
    
    def _load_excel_inputs(self, file_path):
        """
        Load input data from Excel file.
        
        Args:
            file_path (str): Path to Excel file
        """
        df = pd.read_excel(file_path)
        self._process_dataframe(df)
    
    def _load_csv_inputs(self, file_path):
        """
        Load input data from CSV file.
        
        Args:
            file_path (str): Path to CSV file
        """
        df = pd.read_csv(file_path)
        self._process_dataframe(df)
    
    def _load_json_inputs(self, file_path):
        """
        Load input data from JSON file.
        
        Args:
            file_path (str): Path to JSON file
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            self.input_values = data
        elif isinstance(data, list) and len(data) > 0:
            # Assume first item has the variable names
            for key in data[0].keys():
                self.input_values[key] = [item[key] for item in data]
    
    def _process_dataframe(self, df):
        """
        Process DataFrame to extract input values.
        
        Args:
            df (pandas.DataFrame): DataFrame with input data
        """
        # Convert DataFrame to dictionary
        data = df.to_dict(orient='list')
        
        # Process each column
        for key, values in data.items():
            # Remove NaN values
            values = [v for v in values if pd.notna(v)]
            if values:
                self.input_values[key] = values
    
    def process_steps(self, steps):
        """
        Process and optimize test steps.
        
        Args:
            steps (list): List of test steps
            
        Returns:
            list: Optimized test steps
        """
        if not steps:
            return []
        
        if self.mode == 'default':
            return self._optimize_default(steps)
        elif self.mode == 'custom':
            return self._optimize_custom(steps)
        else:
            return steps
    
    def _optimize_default(self, steps):
        """
        Optimize steps in default mode by removing redundant operations.
        
        Args:
            steps (list): List of test steps
            
        Returns:
            list: Optimized test steps
        """
        # Track the last action for each selector
        last_actions = {}
        
        # Process steps in reverse to keep the last action for each selector
        for step in reversed(steps):
            action = step.get('action', '').lower()
            selector = step.get('selector', '')
            
            # Skip steps without selector
            if not selector:
                continue
            
            # Skip if we've already seen this selector
            if selector in last_actions:
                continue
            
            # For input actions, keep only the last value
            if action in ['fill', 'type', 'input']:
                last_actions[selector] = step
            # For other actions, keep all
            else:
                last_actions[selector] = step
        
        # Convert back to list in original order
        optimized_steps = []
        for step in steps:
            selector = step.get('selector', '')
            if selector in last_actions and last_actions[selector] == step:
                optimized_steps.append(step)
                del last_actions[selector]
        
        return optimized_steps
    
    def _optimize_custom(self, steps):
        """
        Optimize steps in custom mode using input data.
        
        Args:
            steps (list): List of test steps
            
        Returns:
            list: Optimized test steps
        """
        # First apply default optimization
        optimized_steps = self._optimize_default(steps)
        
        # Then replace variables with input values
        for step in optimized_steps:
            action = step.get('action', '').lower()
            value = step.get('value', '')
            
            # Check if this is a variable
            if action in ['fill', 'type', 'input'] and value.startswith('{') and value.endswith('}'):
                var_name = value[1:-1]
                
                # Replace with input value if available
                if var_name in self.input_values:
                    if isinstance(self.input_values[var_name], list) and len(self.input_values[var_name]) > 0:
                        step['value'] = self.input_values[var_name][0]
                    else:
                        step['value'] = self.input_values[var_name]
        
        return optimized_steps
    
    def get_input_fields(self, steps):
        """
        Extract input fields from steps.
        
        Args:
            steps (list): List of test steps
            
        Returns:
            list: List of input fields
        """
        input_fields = []
        
        for step in steps:
            action = step.get('action', '').lower()
            selector = step.get('selector', '')
            value = step.get('value', '')
            
            if action in ['fill', 'type', 'input'] and value.startswith('{') and value.endswith('}'):
                var_name = value[1:-1]
                input_fields.append({
                    'name': var_name,
                    'selector': selector
                })
        
        return input_fields 