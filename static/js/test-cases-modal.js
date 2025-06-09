/**
 * Test Cases Modal functionality
 * Handles opening test cases modal for different test suites
 */

class TestCasesModalManager {
    constructor() {
        this.modals = new Map();
        this.initializeGlobalModal();
    }

    /**
     * Initialize a global modal that can be reused for different test suites
     */
    initializeGlobalModal() {
        // Create modal HTML if it doesn't exist
        if (!document.getElementById('globalTestCasesModal')) {
            this.createGlobalModal();
        }
    }

    /**
     * Create the global modal HTML structure
     */
    createGlobalModal() {
        const modalHTML = `
            <div class="modal fade" id="globalTestCasesModal" tabindex="-1" aria-labelledby="globalTestCasesModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="globalTestCasesModalLabel">
                                <i class="bi bi-play-circle"></i> Test Cases - <span id="modalTestSuiteName"></span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <i class="bi bi-info-circle"></i>
                                <strong>Test Suite:</strong> <span id="modalTestSuiteNameInfo"></span>
                                <span class="text-muted">- Select a test case to run or manage</span>
                            </div>

                            <!-- Loading indicator -->
                            <div id="modalLoadingIndicator" class="text-center py-4">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2">Loading test cases...</p>
                            </div>

                            <!-- Error alert -->
                            <div id="modalErrorAlert" class="alert alert-danger" style="display: none;">
                                <i class="bi bi-exclamation-triangle"></i>
                                <span id="modalErrorMessage"></span>
                            </div>

                            <!-- Test cases content -->
                            <div id="modalTestCasesContent" style="display: none;">
                                <!-- Content will be populated dynamically -->
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="bi bi-x-circle"></i> Close
                            </button>
                            <a id="modalOpenTestSuiteBtn" href="#" class="btn btn-primary">
                                <i class="bi bi-folder-open"></i> Open Test Suite
                            </a>
                            <a id="modalNewTestRunBtn" href="#" class="btn btn-success">
                                <i class="bi bi-play"></i> New Test Run
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to the body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * Open test cases modal for a specific test suite
     * @param {number} suiteId - Test suite ID
     * @param {string} suiteName - Test suite name (optional, will be fetched if not provided)
     */
    async openTestCasesModal(suiteId, suiteName = null) {
        const modal = document.getElementById('globalTestCasesModal');
        const modalInstance = new bootstrap.Modal(modal);

        try {
            // Show loading state
            this.showLoading();
            this.hideError();

            // Fetch test suite data if name not provided
            if (!suiteName) {
                const suiteData = await this.fetchTestSuite(suiteId);
                suiteName = suiteData.name;
            }

            // Update modal title and info
            document.getElementById('modalTestSuiteName').textContent = suiteName;
            document.getElementById('modalTestSuiteNameInfo').textContent = suiteName;

            // Update footer links
            document.getElementById('modalOpenTestSuiteBtn').href = `/test-suite/${suiteId}`;
            document.getElementById('modalNewTestRunBtn').href = `/test-suite/${suiteId}/run`;

            // Fetch and display test cases
            await this.loadTestCases(suiteId);

            // Show the modal
            modalInstance.show();

        } catch (error) {
            console.error('Error opening test cases modal:', error);
            this.showError(`Failed to load test cases: ${error.message}`);
            modalInstance.show();
        }
    }

    /**
     * Fetch test suite information
     * @param {number} suiteId - Test suite ID
     * @returns {Promise<Object>} Test suite data
     */
    async fetchTestSuite(suiteId) {
        const response = await fetch(`/api/test-suite/${suiteId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch test suite information');
        }
        return await response.json();
    }

    /**
     * Load test cases for a test suite
     * @param {number} suiteId - Test suite ID
     */
    async loadTestCases(suiteId) {
        try {
            const response = await fetch(`/api/test-suite/${suiteId}/test-cases`);
            if (!response.ok) {
                throw new Error('Failed to fetch test cases');
            }

            const data = await response.json();
            this.displayTestCases(data.test_cases, suiteId);

        } catch (error) {
            throw error;
        }
    }

    /**
     * Display test cases in the modal
     * @param {Array} testCases - Array of test cases
     * @param {number} suiteId - Test suite ID
     */
    displayTestCases(testCases, suiteId) {
        const contentDiv = document.getElementById('modalTestCasesContent');

        if (testCases.length === 0) {
            contentDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> No test cases found for this test suite.
                    <a href="/test-suite/${suiteId}" class="alert-link">Go to test suite details</a> to create test cases.
                </div>
            `;
        } else {
            const tableHTML = `
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Description</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${testCases.map(testCase => `
                                <tr>
                                    <td>${testCase.name}</td>
                                    <td>${testCase.description || 'No description'}</td>
                                    <td>${this.formatDate(testCase.created_at)}</td>
                                    <td>
                                        <div class="btn-group">
                                            <a href="/test-case/${testCase.id}" class="btn btn-sm btn-info" title="View & Edit Steps">
                                                <i class="bi bi-eye"></i> View Steps
                                            </a>
                                            <a href="/test-case/${testCase.id}/run" class="btn btn-sm btn-success" title="Run Test">
                                                <i class="bi bi-play-fill"></i> Run
                                            </a>
                                            <button onclick="testCasesModalManager.deleteTestCase(${testCase.id})" class="btn btn-sm btn-danger" title="Delete">
                                                <i class="bi bi-trash"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            contentDiv.innerHTML = tableHTML;
        }

        this.hideLoading();
        this.showContent();
    }

    /**
     * Delete a test case
     * @param {number} testCaseId - Test case ID
     */
    async deleteTestCase(testCaseId) {
        if (!confirm('Are you sure you want to delete this test case? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/test-case/${testCaseId}/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                // Reload the current modal content
                const modal = document.getElementById('globalTestCasesModal');
                if (modal.classList.contains('show')) {
                    // Get current suite ID from the "Open Test Suite" button href
                    const openBtn = document.getElementById('modalOpenTestSuiteBtn');
                    const suiteId = openBtn.href.split('/').pop();
                    await this.loadTestCases(suiteId);
                }
            } else {
                const data = await response.json();
                alert(`Failed to delete test case: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error deleting test case:', error);
            alert('An error occurred while deleting the test case.');
        }
    }

    /**
     * Show loading state
     */
    showLoading() {
        document.getElementById('modalLoadingIndicator').style.display = 'block';
        document.getElementById('modalTestCasesContent').style.display = 'none';
        document.getElementById('modalErrorAlert').style.display = 'none';
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        document.getElementById('modalLoadingIndicator').style.display = 'none';
    }

    /**
     * Hide loading state and show content
     */
    showContent() {
        document.getElementById('modalLoadingIndicator').style.display = 'none';
        document.getElementById('modalTestCasesContent').style.display = 'block';
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        document.getElementById('modalErrorMessage').textContent = message;
        document.getElementById('modalErrorAlert').style.display = 'block';
        document.getElementById('modalLoadingIndicator').style.display = 'none';
    }

    /**
     * Hide error message
     */
    hideError() {
        document.getElementById('modalErrorAlert').style.display = 'none';
    }

    /**
     * Format date string for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date string
     */
    formatDate(dateString) {
        try {
            if (!dateString) return 'No date';
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return 'Invalid Date';
            return date.toLocaleDateString();
        } catch (error) {
            console.error('Error formatting date:', error);
            return 'Invalid Date';
        }
    }
}

// Global instance
let testCasesModalManager;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Test Cases Modal script loaded');
    testCasesModalManager = new TestCasesModalManager();
    console.log('TestCasesModalManager initialized');
});

// Global function to open test cases modal (for backward compatibility)
function openTestCasesModal(suiteId, suiteName = null) {
    console.log('openTestCasesModal called with:', suiteId, suiteName);
    if (testCasesModalManager) {
        testCasesModalManager.openTestCasesModal(suiteId, suiteName);
    } else {
        console.error('TestCasesModalManager not initialized');
    }
}
