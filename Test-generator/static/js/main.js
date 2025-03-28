// StreamzAI Test Generator Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-close alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Handle test run status updates
    function updateTestRunStatus() {
        var runningTests = document.querySelectorAll('.test-run-status[data-status="running"]');
        if (runningTests.length > 0) {
            runningTests.forEach(function(element) {
                var runId = element.getAttribute('data-run-id');
                fetch('/api/test-run/' + runId + '/status')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status !== 'running') {
                            // Update status without page refresh
                            element.setAttribute('data-status', data.status);
                            var statusBadge = element.querySelector('.badge');
                            if (statusBadge) {
                                statusBadge.className = 'badge ' + getStatusBadgeClass(data.status);
                                statusBadge.textContent = capitalizeFirstLetter(data.status);
                            }
                            
                            // If we're on the test run detail page, update results
                            if (window.location.pathname.includes('/test-run/')) {
                                loadTestResults(runId);
                            }
                        }
                    })
                    .catch(error => console.error('Error updating test run status:', error));
            });
            
            // Continue polling if there are still running tests
            setTimeout(updateTestRunStatus, 5000);
        }
    }

    // Start polling for running tests
    if (document.querySelectorAll('.test-run-status[data-status="running"]').length > 0) {
        updateTestRunStatus();
    }

    // Helper function to get badge class based on status
    function getStatusBadgeClass(status) {
        switch(status) {
            case 'completed': return 'bg-success';
            case 'running': return 'bg-info';
            case 'failed': return 'bg-danger';
            case 'pending': return 'bg-secondary';
            default: return 'bg-secondary';
        }
    }

    // Helper function to capitalize first letter
    function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    // Function to load test results on test run detail page
    function loadTestResults(runId) {
        fetch('/api/test-run/' + runId + '/results')
            .then(response => response.json())
            .then(data => {
                var resultsContainer = document.getElementById('test-results-container');
                if (resultsContainer && data.results) {
                    resultsContainer.innerHTML = '';
                    
                    // Update summary counts
                    document.getElementById('passed-count').textContent = data.summary.passed || 0;
                    document.getElementById('failed-count').textContent = data.summary.failed || 0;
                    document.getElementById('skipped-count').textContent = data.summary.skipped || 0;
                    document.getElementById('error-count').textContent = data.summary.error || 0;
                    
                    // Render results
                    data.results.forEach(function(result) {
                        var resultHtml = createTestResultHtml(result);
                        resultsContainer.innerHTML += resultHtml;
                    });
                    
                    // Initialize any new tooltips
                    var newTooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
                    newTooltipTriggerList.map(function (tooltipTriggerEl) {
                        return new bootstrap.Tooltip(tooltipTriggerEl);
                    });
                }
            })
            .catch(error => console.error('Error loading test results:', error));
    }

    // Helper function to create HTML for a test result
    function createTestResultHtml(result) {
        var statusClass = '';
        switch(result.status) {
            case 'passed': statusClass = 'success'; break;
            case 'failed': statusClass = 'danger'; break;
            case 'skipped': statusClass = 'warning'; break;
            case 'error': statusClass = 'danger'; break;
            default: statusClass = 'secondary';
        }
        
        var html = `
            <div class="card mb-3 border-${statusClass}">
                <div class="card-header bg-${statusClass} bg-opacity-10 d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">${result.test_case.test_file_path.split('/').pop()}</h5>
                    <span class="badge bg-${statusClass}">${capitalizeFirstLetter(result.status)}</span>
                </div>
                <div class="card-body">
                    <p><strong>Original File:</strong> ${result.test_case.original_file_path}</p>
                    <p><strong>Language:</strong> ${result.test_case.language}</p>
                    <p><strong>Execution Time:</strong> ${result.execution_time ? result.execution_time.toFixed(2) + 's' : 'N/A'}</p>
                    ${result.error_message ? `<div class="alert alert-danger">${result.error_message}</div>` : ''}
                </div>
                <div class="card-footer bg-transparent">
                    <a href="/test-case/${result.test_case.id}" class="btn btn-sm btn-outline-primary">View Test Case</a>
                </div>
            </div>
        `;
        
        return html;
    }

    // Form validation for project creation
    var projectForm = document.getElementById('project-form');
    if (projectForm) {
        projectForm.addEventListener('submit', function(event) {
            if (!projectForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            projectForm.classList.add('was-validated');
        });
    }
});