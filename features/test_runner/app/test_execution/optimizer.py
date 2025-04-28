
import pandas as pd
import os

class TestOptimizer:
    """
    Optimizes test steps based on different modes and input configurations.

    Modes:
    - default: Optimizes by removing redundant steps and using final values
    - custom-batch: Uses custom input values from provided data source (all at once)
    - custom-dynamic: Prompts for input values during test execution
    """

    def __init__(self, mode='default', inputs=None, input_type='batch'):
        """
        Initialize the optimizer with a specific mode and optional input data.

        Args:
            mode (str): Optimization mode ('default', 'custom-batch', or 'custom-dynamic')
            inputs (str or list): Path to input file or list of input values
            input_type (str): Type of custom input ('batch' or 'dynamic')
        """
        self.mode = mode
        self.input_type = input_type if mode.startswith('custom') else None
        self.input_map = self._process_inputs(inputs) if inputs else None
        self.dynamic_inputs = []  # For storing inputs provided during execution

    def process_steps(self, steps):
        """
        Process and optimize test steps based on the configured mode.

        Args:
            steps (list): List of test step dictionaries

        Returns:
            list: Optimized list of test steps
        """
        if not steps:
            return []

        optimized = []
        current_selector = None
        selector_values = {}
        input_fields = set()  # Track unique input fields for dynamic mode

        # First pass: identify all input fields and their final values
        for step in steps:
            if 'action' not in step:
                continue

            if step['action'] in ['fill', 'input'] and 'selector' in step:
                selector = step.get('selector')
                if selector:
                    selector_values[selector] = step.get('value', '')
                    input_fields.add(selector)

        # For dynamic input mode, prepare the list of fields that will need input
        if self.mode == 'custom-dynamic':
            self.dynamic_inputs = []
            for selector in input_fields:
                self.dynamic_inputs.append({
                    'selector': selector,
                    'original_value': selector_values.get(selector, ''),
                    'custom_value': None,
                    'screenshot': None
                })

        # Second pass: optimize steps
        for step in steps:
            # Skip steps without an action
            if 'action' not in step:
                continue

            # Handle fill/input actions with optimization
            if step['action'] in ['fill', 'input']:
                selector = step.get('selector')

                if not selector:
                    # Keep steps without selectors as-is
                    optimized.append(step)
                    continue

                if self.mode == 'default':
                    # In default mode, store the latest value for each selector

                    # Only add this step if it's a new selector
                    if selector != current_selector:
                        current_selector = selector
                        optimized.append(step)

                elif self.mode.startswith('custom'):
                    # In custom modes, replace values with custom inputs
                    if self.input_type == 'batch':
                        # For batch mode, get value from input map
                        custom_value = self._get_custom_value(selector)
                        if custom_value is not None:
                            step['value'] = custom_value

                        # Only add this step if it's a new selector
                        if selector != current_selector:
                            current_selector = selector
                            optimized.append(step)
                    else:
                        # For dynamic mode, we'll add a placeholder that will be replaced during execution
                        # Only add this step if it's a new selector
                        if selector != current_selector:
                            current_selector = selector
                            # Create a copy to avoid modifying the original
                            new_step = step.copy()
                            new_step['requires_input'] = True
                            optimized.append(new_step)
            else:
                # For non-fill actions, add them as-is
                optimized.append(step)

        # Update the values based on mode
        if self.mode == 'default':
            # In default mode, update to final values
            for step in optimized:
                if step['action'] in ['fill', 'input'] and 'selector' in step:
                    step['value'] = selector_values.get(step['selector'], step.get('value', ''))

        return optimized

    def _get_custom_value(self, selector):
        """
        Get a custom value for a selector from the input data.

        Args:
            selector (str): The selector to find a value for

        Returns:
            str or None: The custom value if found, None otherwise
        """
        if not self.input_map:
            return None

        # Try to match the selector with input map keys
        # First, try exact match
        if isinstance(self.input_map, dict) and selector in self.input_map:
            return self.input_map[selector]

        # For list of dicts, try to find a matching field
        if isinstance(self.input_map, list):
            for item in self.input_map:
                if isinstance(item, dict):
                    # Try to match by selector, id, name, or other common attributes
                    selector_parts = selector.replace('[', ' ').replace(']', ' ').replace('=', ' ').split()
                    for key, value in item.items():
                        if key in selector_parts or key.lower() in selector.lower():
                            return str(value)

        return None

    def get_dynamic_input_fields(self):
        """
        Get the list of fields that require dynamic input.

        Returns:
            list: List of input field information
        """
        return self.dynamic_inputs

    def set_dynamic_input(self, selector, value, screenshot=None):
        """
        Set a dynamic input value for a selector.

        Args:
            selector (str): The selector to set the value for
            value (str): The input value
            screenshot (str, optional): Path to the screenshot of the element

        Returns:
            bool: True if the value was set, False otherwise
        """
        for input_field in self.dynamic_inputs:
            if input_field['selector'] == selector:
                input_field['custom_value'] = value
                if screenshot:
                    input_field['screenshot'] = screenshot
                return True
        return False

    def get_dynamic_value(self, selector):
        """
        Get the dynamic input value for a selector.

        Args:
            selector (str): The selector to get the value for

        Returns:
            str or None: The custom value if set, None otherwise
        """
        for input_field in self.dynamic_inputs:
            if input_field['selector'] == selector:
                return input_field.get('custom_value')
        return None

    def _process_inputs(self, inputs):
        """
        Process input data from various sources.

        Args:
            inputs: Path to file or direct input data

        Returns:
            dict or list: Processed input data
        """
        if not inputs:
            return None

        # If inputs is a string, treat it as a file path
        if isinstance(inputs, str):
            if not os.path.exists(inputs):
                return None

            file_ext = os.path.splitext(inputs)[1].lower()

            if file_ext == '.xlsx' or file_ext == '.xls':
                return pd.read_excel(inputs).to_dict('records')

            elif file_ext == '.csv':
                return pd.read_csv(inputs).to_dict('records')

        # If inputs is already a dict or list, return as-is
        return inputs

