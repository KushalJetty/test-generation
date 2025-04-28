# Advanced Test Runner

A powerful web-based test execution platform with real-time monitoring, smart optimization, and comprehensive reporting capabilities.

## Features

- **Real-time Test Execution**: Monitor test progress with live updates
- **Test Optimization**: Smart handling of redundant steps and input values
- **Custom Input Support**: Data-driven testing with Excel, CSV, or JSON inputs
- **VPN Integration**: Run tests through VPN connections
- **Cross-Browser Testing**: Support for Chromium, Firefox, and WebKit
- **Comprehensive Reporting**: Generate reports in JSON, HTML, CSV, or Excel formats
- **Test Scheduling**: Schedule tests to run at specific times
- **Retry Mechanism**: Automatically retry failed steps

## Installation

1. Clone the repository
2. Install the requirements:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```

## Usage

1. Start the application:
   ```
   python run.py
   ```
2. Open your browser and navigate to `http://localhost:5000`
3. Upload a test case file or configure a new test
4. Click "Run Test" to execute the test

## Test Configuration

Test cases can be defined in JSON format with the following structure:

```json
{
  "url": "https://example.com",
  "mode": "default",
  "browser": "chromium",
  "headless": false,
  "retries": 3,
  "stopOnFailure": false,
  "report_format": "json",
  "test_steps": [
    {
      "action": "click",
      "selector": "#login-button"
    },
    {
      "action": "fill",
      "selector": "#username",
      "value": "testuser"
    },
    {
      "action": "fill",
      "selector": "#password",
      "value": "password123"
    },
    {
      "action": "click",
      "selector": "#submit-button"
    }
  ]
}
```

## Optimization Modes

- **Default Mode**: Optimizes redundant steps by keeping only the final value for each selector
- **Custom Mode**: Uses values from a provided data source (Excel, CSV, or JSON)

## VPN Configuration

To use VPN functionality, upload an OpenVPN configuration file (.ovpn) when configuring the test.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
