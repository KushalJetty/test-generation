/**
 * Import Test Case functionality
 * Handles the dynamic loading and importing of test cases between test suites
 */

class ImportTestCaseManager {
    constructor(elementSuffix, targetTestSuiteId) {
        this.elementSuffix = elementSuffix;
        this.targetTestSuiteId = targetTestSuiteId;
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.modal = document.getElementById(`importTestCaseModal${this.elementSuffix}`);
        this.sourceTestSuiteSelect = document.getElementById(`sourceTestSuite${this.elementSuffix}`);
        this.sourceTestCaseSelect = document.getElementById(`sourceTestCase${this.elementSuffix}`);
        this.newTestCaseName = document.getElementById(`newTestCaseName${this.elementSuffix}`);
        this.newTestCaseDescription = document.getElementById(`newTestCaseDescription${this.elementSuffix}`);
        this.previewImportBtn = document.getElementById(`previewImportBtn${this.elementSuffix}`);
        this.confirmImportBtn = document.getElementById(`confirmImportBtn${this.elementSuffix}`);
        this.importPreview = document.getElementById(`importPreview${this.elementSuffix}`);
        this.importStepsList = document.getElementById(`importStepsList${this.elementSuffix}`);
        this.loadingIndicator = document.getElementById(`loadingIndicator${this.elementSuffix}`);
        this.errorAlert = document.getElementById(`errorAlert${this.elementSuffix}`);
        this.errorMessage = document.getElementById(`errorMessage${this.elementSuffix}`);
        this.successToast = document.getElementById(`successToast${this.elementSuffix}`);
    }

    bindEvents() {
        // Load test suites when modal opens
        this.modal.addEventListener('show.bs.modal', () => {
            this.loadTestSuites();
            this.resetForm();
        });

        // Load test cases when test suite is selected
        this.sourceTestSuiteSelect.addEventListener('change', () => {
            this.onTestSuiteChange();
        });

        // Auto-populate test case name when source test case is selected
        this.sourceTestCaseSelect.addEventListener('change', () => {
            this.onTestCaseChange();
        });

        // Preview import
        this.previewImportBtn.addEventListener('click', () => {
            this.previewImport();
        });

        // Confirm import
        this.confirmImportBtn.addEventListener('click', () => {
            this.confirmImport();
        });
    }

    resetForm() {
        this.sourceTestSuiteSelect.innerHTML = '<option value="">Select a test suite...</option>';
        this.sourceTestCaseSelect.innerHTML = '<option value="">Select a test case...</option>';
        this.sourceTestCaseSelect.disabled = true;
        this.newTestCaseName.value = '';
        this.newTestCaseDescription.value = '';
        this.importPreview.style.display = 'none';
        this.confirmImportBtn.disabled = true;
        this.hideError();
    }

    showLoading() {
        this.loadingIndicator.style.display = 'block';
    }

    hideLoading() {
        this.loadingIndicator.style.display = 'none';
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorAlert.style.display = 'block';
    }

    hideError() {
        this.errorAlert.style.display = 'none';
    }

    showSuccess() {
        const toast = new bootstrap.Toast(this.successToast);
        toast.show();
    }

    async loadTestSuites() {
        try {
            this.showLoading();
            this.hideError();

            const response = await fetch('/api/test-suites');
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to load test suites');
            }

            this.sourceTestSuiteSelect.innerHTML = '<option value="">Select a test suite...</option>';
            
            data.test_suites.forEach(suite => {
                // Exclude current test suite
                if (suite.id !== this.targetTestSuiteId) {
                    const option = document.createElement('option');
                    option.value = suite.id;
                    option.textContent = `${suite.name} (${suite.project_name})`;
                    this.sourceTestSuiteSelect.appendChild(option);
                }
            });

        } catch (error) {
            console.error('Error loading test suites:', error);
            this.showError(`Failed to load test suites: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    async onTestSuiteChange() {
        const suiteId = this.sourceTestSuiteSelect.value;
        
        // Reset dependent fields
        this.sourceTestCaseSelect.innerHTML = '<option value="">Select a test case...</option>';
        this.sourceTestCaseSelect.disabled = !suiteId;
        this.importPreview.style.display = 'none';
        this.confirmImportBtn.disabled = true;
        this.hideError();

        if (!suiteId) return;

        try {
            this.showLoading();

            const response = await fetch(`/api/test-suite/${suiteId}/test-cases`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to load test cases');
            }

            data.test_cases.forEach(testCase => {
                const option = document.createElement('option');
                option.value = testCase.id;
                option.textContent = testCase.name;
                option.dataset.description = testCase.description || '';
                this.sourceTestCaseSelect.appendChild(option);
            });

        } catch (error) {
            console.error('Error loading test cases:', error);
            this.showError(`Failed to load test cases: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    onTestCaseChange() {
        const selectedOption = this.sourceTestCaseSelect.selectedOptions[0];
        if (selectedOption && selectedOption.value) {
            // Auto-populate the new test case name
            const originalName = selectedOption.textContent;
            this.newTestCaseName.value = `Copy of ${originalName}`;
            
            // Auto-populate description if available
            const description = selectedOption.dataset.description;
            if (description) {
                this.newTestCaseDescription.value = `Imported from: ${description}`;
            }
        }
    }

    async previewImport() {
        const sourceTestCaseId = this.sourceTestCaseSelect.value;
        const testCaseName = this.newTestCaseName.value.trim();

        if (!sourceTestCaseId) {
            this.showError('Please select a test case to import');
            return;
        }

        if (!testCaseName) {
            this.showError('Please enter a name for the new test case');
            return;
        }

        try {
            this.showLoading();
            this.hideError();

            const response = await fetch(`/api/test-case/${sourceTestCaseId}/steps`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to load test case steps');
            }

            this.displayImportPreview(data.steps);
            this.confirmImportBtn.disabled = false;

        } catch (error) {
            console.error('Error loading test case steps:', error);
            this.showError(`Failed to load test case steps: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    displayImportPreview(steps) {
        this.importStepsList.innerHTML = '';

        if (steps.length === 0) {
            this.importStepsList.innerHTML = '<p class="text-muted mb-0">No steps found in the selected test case.</p>';
        } else {
            steps.forEach((step, index) => {
                const stepDiv = document.createElement('div');
                stepDiv.className = 'border-bottom pb-2 mb-2';
                stepDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <strong>Step ${index + 1}:</strong> 
                            <span class="badge bg-primary me-2">${step.action}</span>
                            ${step.description || 'No description'}
                        </div>
                        <small class="text-muted">Order: ${step.order}</small>
                    </div>
                    ${step.selector ? `<div class="text-muted small mt-1"><i class="bi bi-cursor"></i> Selector: <code>${step.selector}</code></div>` : ''}
                    ${step.value ? `<div class="text-muted small"><i class="bi bi-input-cursor-text"></i> Value: <code>${step.value}</code></div>` : ''}
                `;
                this.importStepsList.appendChild(stepDiv);
            });
        }

        this.importPreview.style.display = 'block';
    }

    async confirmImport() {
        const sourceTestCaseId = this.sourceTestCaseSelect.value;
        const testCaseName = this.newTestCaseName.value.trim();
        const testCaseDescription = this.newTestCaseDescription.value.trim();

        if (!sourceTestCaseId || !testCaseName) {
            this.showError('Please fill in all required fields');
            return;
        }

        try {
            this.showLoading();
            this.hideError();
            this.confirmImportBtn.disabled = true;

            const importData = {
                source_test_case_id: parseInt(sourceTestCaseId),
                name: testCaseName,
                description: testCaseDescription,
                target_test_suite_id: this.targetTestSuiteId
            };

            const response = await fetch('/api/test-suite/import-test-case', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(importData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to import test case');
            }

            // Show success message
            this.showSuccess();
            
            // Close modal and reload page
            const modalInstance = bootstrap.Modal.getInstance(this.modal);
            modalInstance.hide();
            
            // Reload page after a short delay to show the success message
            setTimeout(() => {
                window.location.reload();
            }, 1500);

        } catch (error) {
            console.error('Error importing test case:', error);
            this.showError(`Failed to import test case: ${error.message}`);
            this.confirmImportBtn.disabled = false;
        } finally {
            this.hideLoading();
        }
    }
}

// Global function to initialize import functionality
function setupImportTestCase(elementSuffix, targetTestSuiteId) {
    return new ImportTestCaseManager(elementSuffix, targetTestSuiteId);
}
