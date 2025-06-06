#!/usr/bin/env python3
"""
Test script to validate the fill action grouping logic in continue_recording.

This script tests that multiple fill/type/input actions for the same selector
are properly grouped into a single final action, eliminating character-by-character
recording that clutters the UI.
"""

import asyncio
import time
from unittest.mock import Mock, AsyncMock
import sys
import os
import queue

# Add the current directory to Python path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the event_queue to avoid Flask app context issues
event_queue = queue.Queue()

# Import after setting up mocks
from app import ActionTracker

class TestGroupingLogic:
    """Test class for validating fill action grouping logic."""
    
    def __init__(self):
        self.test_results = []
        
    async def test_multiple_inputs_same_field_grouped(self):
        """Test that multiple inputs for the same field are grouped into one."""
        print("🧪 Testing: Multiple inputs for same field are grouped")
        
        # Create mock page
        mock_page = Mock()
        mock_page.expose_function = AsyncMock()
        mock_page.add_init_script = AsyncMock()
        
        # Create ActionTracker with continuation parameters
        tracker = ActionTracker(
            page=mock_page,
            existing_steps=[],
            continue_from_step=None
        )
        
        await tracker.start_tracking()
        
        # Simulate typing "hello" character by character
        test_actions = [
            {'action': 'input', 'selector': '#username', 'value': 'h', 'timestamp': time.time()},
            {'action': 'input', 'selector': '#username', 'value': 'he', 'timestamp': time.time()},
            {'action': 'input', 'selector': '#username', 'value': 'hel', 'timestamp': time.time()},
            {'action': 'input', 'selector': '#username', 'value': 'hell', 'timestamp': time.time()},
            {'action': 'input', 'selector': '#username', 'value': 'hello', 'timestamp': time.time()},
        ]
        
        # Record all actions
        for action in test_actions:
            await tracker.record_action(action)
        
        # Wait for grouping timeout to complete
        await asyncio.sleep(2.0)  # Wait longer than buffer_timeout (1.5s)
        
        # Check results
        new_steps = tracker.get_new_steps_only()
        
        if len(new_steps) == 1 and new_steps[0]['value'] == 'hello':
            print("✅ PASS: Multiple inputs grouped into single action")
            self.test_results.append(True)
        else:
            print(f"❌ FAIL: Expected 1 step with value 'hello', got {len(new_steps)} steps")
            for i, step in enumerate(new_steps):
                print(f"   Step {i+1}: {step.get('action')} - {step.get('selector')} - {step.get('value')}")
            self.test_results.append(False)
    
    async def test_click_actions_immediate(self):
        """Test that click actions are processed immediately without grouping."""
        print("🧪 Testing: Click actions are processed immediately")
        
        # Create mock page
        mock_page = Mock()
        mock_page.expose_function = AsyncMock()
        mock_page.add_init_script = AsyncMock()
        
        # Create ActionTracker
        tracker = ActionTracker(
            page=mock_page,
            existing_steps=[],
            continue_from_step=None
        )
        
        await tracker.start_tracking()
        
        # Record click action
        click_action = {
            'action': 'click',
            'selector': '#submit-button',
            'timestamp': time.time()
        }
        
        await tracker.record_action(click_action)
        
        # Check that click was recorded immediately (no delay)
        new_steps = tracker.get_new_steps_only()
        
        if len(new_steps) == 1 and new_steps[0]['action'] == 'click':
            print("✅ PASS: Click action processed immediately")
            self.test_results.append(True)
        else:
            print(f"❌ FAIL: Expected 1 click step, got {len(new_steps)} steps")
            self.test_results.append(False)
    
    async def test_different_fields_separate_groups(self):
        """Test that different fields create separate groups."""
        print("🧪 Testing: Different fields create separate groups")
        
        # Create mock page
        mock_page = Mock()
        mock_page.expose_function = AsyncMock()
        mock_page.add_init_script = AsyncMock()
        
        # Create ActionTracker
        tracker = ActionTracker(
            page=mock_page,
            existing_steps=[],
            continue_from_step=None
        )
        
        await tracker.start_tracking()
        
        # Simulate typing in two different fields
        test_actions = [
            {'action': 'input', 'selector': '#username', 'value': 'user', 'timestamp': time.time()},
            {'action': 'input', 'selector': '#password', 'value': 'pass', 'timestamp': time.time()},
            {'action': 'input', 'selector': '#username', 'value': 'user123', 'timestamp': time.time()},
            {'action': 'input', 'selector': '#password', 'value': 'password', 'timestamp': time.time()},
        ]
        
        # Record all actions
        for action in test_actions:
            await tracker.record_action(action)
        
        # Wait for grouping timeout
        await asyncio.sleep(2.0)
        
        # Check results
        new_steps = tracker.get_new_steps_only()
        
        # Should have 2 steps: one for username, one for password
        username_steps = [s for s in new_steps if s.get('selector') == '#username']
        password_steps = [s for s in new_steps if s.get('selector') == '#password']
        
        if (len(username_steps) == 1 and username_steps[0]['value'] == 'user123' and
            len(password_steps) == 1 and password_steps[0]['value'] == 'password'):
            print("✅ PASS: Different fields grouped separately")
            self.test_results.append(True)
        else:
            print(f"❌ FAIL: Expected 2 separate groups, got {len(new_steps)} total steps")
            for i, step in enumerate(new_steps):
                print(f"   Step {i+1}: {step.get('action')} - {step.get('selector')} - {step.get('value')}")
            self.test_results.append(False)
    
    async def test_pending_actions_finalized_on_stop(self):
        """Test that pending actions are finalized when recording stops."""
        print("🧪 Testing: Pending actions finalized on stop")
        
        # Create mock page
        mock_page = Mock()
        mock_page.expose_function = AsyncMock()
        mock_page.add_init_script = AsyncMock()
        
        # Create ActionTracker
        tracker = ActionTracker(
            page=mock_page,
            existing_steps=[],
            continue_from_step=None
        )
        
        await tracker.start_tracking()
        
        # Record input action but don't wait for timeout
        input_action = {
            'action': 'input',
            'selector': '#email',
            'value': 'test@example.com',
            'timestamp': time.time()
        }
        
        await tracker.record_action(input_action)
        
        # Stop recording immediately (before timeout)
        await tracker.stop_recording()
        
        # Check that pending action was finalized
        new_steps = tracker.get_new_steps_only()
        
        if len(new_steps) == 1 and new_steps[0]['value'] == 'test@example.com':
            print("✅ PASS: Pending actions finalized on stop")
            self.test_results.append(True)
        else:
            print(f"❌ FAIL: Expected 1 finalized step, got {len(new_steps)} steps")
            self.test_results.append(False)
    
    async def run_all_tests(self):
        """Run all test cases."""
        print("🚀 Starting Fill Action Grouping Tests")
        print("=" * 50)
        
        await self.test_multiple_inputs_same_field_grouped()
        await self.test_click_actions_immediate()
        await self.test_different_fields_separate_groups()
        await self.test_pending_actions_finalized_on_stop()
        
        print("=" * 50)
        print("📊 Test Results Summary")
        
        passed = sum(self.test_results)
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed! Fill action grouping is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please review the implementation.")
            return False

async def main():
    """Main test runner."""
    tester = TestGroupingLogic()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
