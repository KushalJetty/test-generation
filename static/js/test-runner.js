/**
 * Test Runner Functionality
 * This script handles running tests from the test suites page
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const runTestBtn = document.getElementById('runTestBtn');
    const inputModeSelect = document.getElementById('inputMode');
    const existingInputSection = document.getElementById('existingInputSection');
    const inputSetSelect = document.getElementById('inputSet');
    const resultSection = document.getElementById('resultSection');
    const statusAlert = document.getElementById('statusAlert');
    const outputText = document.getElementById('outputText');
    const errorText = document.getElementById('errorText');
    const resetBtn = document.getElementById('resetBtn');
    const testConfigSection = document.getElementById('testConfigSection');

    // Event listeners
    if (inputModeSelect) {
        inputModeSelect.addEventListener('change', function() {
            if (this.value === 'existing') {
                existingInputSection.classList.remove('d-none');
            } else {
                existingInputSection.classList.add('d-none');
            }
        });
    }

    // Handle input values file selection
    const inputValuesFile = document.getElementById('inputValuesFile');
    if (inputValuesFile) {
        inputValuesFile.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const data = JSON.parse(e.target.result);
                    populateInputSets(data);
                } catch (error) {
                    console.error('Error parsing JSON file:', error);
                    alert('Error parsing JSON file. Please make sure it is a valid JSON file.');
                }
            };
            reader.readAsText(file);
        });
    }

    // Run test button
    if (runTestBtn) {
        runTestBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('testFile');
            if (!fileInput.files.length) {
                alert('Please select a test file first.');
                return;
            }

            const suiteId = document.getElementById('suiteId').value;
            const inputMode = inputModeSelect.value;
            const headlessMode = document.getElementById('headlessMode').checked;
            let inputSet = null;
            let inputValuesFile = null;

            if (inputMode === 'existing') {
                // Check if input values file is selected
                const inputValuesFileInput = document.getElementById('inputValuesFile');
                if (!inputValuesFileInput.files.length) {
                    alert('Please select an input values file.');
                    return;
                }

                inputValuesFile = inputValuesFileInput.files[0];
                inputSet = inputSetSelect.value;

                if (!inputSet) {
                    alert('Please select an input set.');
                    return;
                }
            }

            // Disable button and show loading state
            runTestBtn.disabled = true;
            runTestBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Running...';

            // First upload the test file
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('suite_id', suiteId);

            fetch('/api/test-runner/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Failed to upload test file');
                }

                const testFilePath = data.path;

                // If using existing input, upload the input values file
                if (inputMode === 'existing' && inputValuesFile) {
                    const inputFormData = new FormData();
                    inputFormData.append('file', inputValuesFile);

                    return fetch('/api/test-runner/upload-input', {
                        method: 'POST',
                        body: inputFormData
                    }).then(response => response.json())
                    .then(inputData => {
                        if (!inputData.success) {
                            throw new Error(inputData.error || 'Failed to upload input values file');
                        }

                        // Run the test with both files
                        return fetch('/api/test-runner/run', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                file_path: testFilePath,
                                input_mode: inputMode,
                                input_file_path: inputData.path,
                                input_set: inputSet,
                                headless: headlessMode,
                                suite_id: suiteId
                            })
                        });
                    });
                } else {
                    // Run the test with just the test file
                    return fetch('/api/test-runner/run', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            file_path: testFilePath,
                            input_mode: inputMode,
                            input_set: inputSet,
                            headless: headlessMode,
                            suite_id: suiteId
                        })
                    });
                }
            })
            .then(response => response.json())
            .then(data => {
                displayResults(data);
            })
            .catch(error => {
                console.error('Error:', error);
                resultSection.classList.remove('d-none');
                statusAlert.className = 'alert alert-danger';
                statusAlert.textContent = 'Error: ' + error.message;
                outputText.textContent = '';
                errorText.textContent = '';
            })
            .finally(() => {
                runTestBtn.disabled = false;
                runTestBtn.innerHTML = 'Run Test';
            });
        });
    }

    // Reset button
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            // Reset form and hide results
            resultSection.classList.add('d-none');
            testConfigSection.classList.remove('d-none');
            document.getElementById('testConfigForm').reset();
        });
    }

    // Helper functions
    function populateInputSets(data) {
        // Clear existing options
        inputSetSelect.innerHTML = '';

        // Add options for each input set
        if (data.test_sets && data.test_sets.length > 0) {
            // New format with test_sets array
            data.test_sets.forEach(set => {
                const option = document.createElement('option');
                option.value = set.name;
                option.textContent = set.name;
                inputSetSelect.appendChild(option);
            });
        } else {
            // Legacy format (flat key-value pairs)
            const option = document.createElement('option');
            option.value = 'default';
            option.textContent = 'Default Values';
            inputSetSelect.appendChild(option);
        }
    }

    // Display test results
    function displayResults(data) {
        resultSection.classList.remove('d-none');
        testConfigSection.classList.add('d-none');

        if (data.success) {
            statusAlert.className = 'alert alert-success';
            statusAlert.textContent = 'Test completed successfully!';
        } else {
            statusAlert.className = 'alert alert-danger';
            statusAlert.textContent = data.error || 'Test failed with errors.';
        }

        outputText.textContent = data.stdout || 'No output';
        errorText.textContent = data.stderr || 'No errors';
    }
}); 