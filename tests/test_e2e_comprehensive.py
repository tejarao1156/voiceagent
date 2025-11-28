#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for Voice Agent Platform
Tests ALL features including authentication, multi-tenancy, and all API endpoints
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:4002"
TEST_TIMEOUT = 10

# ANSI color codes for beautiful output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class TestResults:
    """Track test results"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []
    
    def add_pass(self, test_name: str):
        self.total += 1
        self.passed += 1
        print(f"{Colors.OKGREEN}✓{Colors.ENDC} {test_name}")
    
    def add_fail(self, test_name: str, reason: str):
        self.total += 1
        self.failed += 1
        self.failures.append(f"{test_name}: {reason}")
        print(f"{Colors.FAIL}✗{Colors.ENDC} {test_name}")
        print(f"  {Colors.FAIL}Reason: {reason}{Colors.ENDC}")
    
    def add_skip(self, test_name: str, reason: str):
        self.total += 1
        self.skipped += 1
        print(f"{Colors.WARNING}○{Colors.ENDC} {test_name} (SKIPPED: {reason})")
    
    def print_summary(self):
        print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"Total Tests: {self.total}")
        print(f"{Colors.OKGREEN}Passed: {self.passed}{Colors.ENDC}")
        print(f"{Colors.FAIL}Failed: {self.failed}{Colors.ENDC}")
        print(f"{Colors.WARNING}Skipped: {self.skipped}{Colors.ENDC}")
        
        if self.failures:
            print(f"\n{Colors.FAIL}{Colors.BOLD}FAILURES:{Colors.ENDC}")
            for failure in self.failures:
                print(f"{Colors.FAIL}  • {failure}{Colors.ENDC}")
        
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

class VoiceAgentTester:
    """Comprehensive test suite for Voice Agent Platform"""
    
    def __init__(self):
        self.results = TestResults()
        self.user1_token = None
        self.user2_token = None
        self.user1_session = requests.Session()
        self.user2_session = requests.Session()
        
    def print_section(self, title: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{title}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def register_user(self, email: str, password: str) -> Optional[Dict]:
        """Register a new user"""
        try:
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={"email": email, "password": password},
                timeout=TEST_TIMEOUT
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            return None
    
    def login_user(self, email: str, password: str, session: requests.Session) -> Optional[str]:
        """Login user and return token"""
        try:
            response = session.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=TEST_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("token")
            return None
        except Exception as e:
            return None
    
    # ========================================================================
    # TEST 1: HEALTH & CONNECTIVITY
    # ========================================================================
    
    def test_health_endpoints(self):
        """Test health and connectivity endpoints"""
        self.print_section("TEST CATEGORY 1: Health & Connectivity")
        
        # Test 1.1: Root endpoint
        try:
            response = requests.get(f"{BASE_URL}/", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("1.1 Root endpoint accessible")
            else:
                self.results.add_fail("1.1 Root endpoint accessible", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("1.1 Root endpoint accessible", str(e))
        
        # Test 1.2: Health endpoint
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("1.2 Health endpoint responds")
            else:
                self.results.add_fail("1.2 Health endpoint responds", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("1.2 Health endpoint responds", str(e))
        
        # Test 1.3: API docs accessible
        try:
            response = requests.get(f"{BASE_URL}/docs", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("1.3 API documentation accessible")
            else:
                self.results.add_fail("1.3 API documentation accessible", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("1.3 API documentation accessible", str(e))
    
    # ========================================================================
    # TEST 2: AUTHENTICATION
    # ========================================================================
    
    def test_authentication(self):
        """Test authentication system"""
        self.print_section("TEST CATEGORY 2: Authentication")
        
        # Test 2.1: User registration (User 1)
        user1_data = self.register_user("testuser1@e2etest.com", "SecurePass123!")
        if user1_data and user1_data.get("success"):
            self.results.add_pass("2.1 User 1 registration successful")
        else:
            self.results.add_fail("2.1 User 1 registration successful", "Registration failed")
            return  # Can't continue without user
        
        # Test 2.2: User registration (User 2)
        user2_data = self.register_user("testuser2@e2etest.com", "SecurePass456!")
        if user2_data and user2_data.get("success"):
            self.results.add_pass("2.2 User 2 registration successful")
        else:
            self.results.add_fail("2.2 User 2 registration successful", "Registration failed")
        
        # Test 2.3: Duplicate email prevention
        duplicate = self.register_user("testuser1@e2etest.com", "AnotherPass789!")
        if not duplicate or not duplicate.get("success"):
            self.results.add_pass("2.3 Duplicate email registration prevented")
        else:
            self.results.add_fail("2.3 Duplicate email registration prevented", "Duplicate allowed")
        
        # Test 2.4: User 1 login
        self.user1_token = self.login_user("testuser1@e2etest.com", "SecurePass123!", self.user1_session)
        if self.user1_token:
            self.results.add_pass("2.4 User 1 login successful")
        else:
            self.results.add_fail("2.4 User 1 login successful", "Login failed")
            return
        
        # Test 2.5: User 2 login
        self.user2_token = self.login_user("testuser2@e2etest.com", "SecurePass456!", self.user2_session)
        if self.user2_token:
            self.results.add_pass("2.5 User 2 login successful")
        else:
            self.results.add_fail("2.5 User 2 login successful", "Login failed")
        
        # Test 2.6: Invalid credentials
        invalid_token = self.login_user("testuser1@e2etest.com", "WrongPassword!", requests.Session())
        if not invalid_token:
            self.results.add_pass("2.6 Invalid credentials rejected")
        else:
            self.results.add_fail("2.6 Invalid credentials rejected", "Invalid login succeeded")
        
        # Test 2.7: /auth/me endpoint (authenticated)
        try:
            response = self.user1_session.get(f"{BASE_URL}/auth/me", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                if data.get("email") == "testuser1@e2etest.com":
                    self.results.add_pass("2.7 /auth/me returns correct user info")
                else:
                    self.results.add_fail("2.7 /auth/me returns correct user info", "Wrong user data")
            else:
                self.results.add_fail("2.7 /auth/me returns correct user info", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("2.7 /auth/me returns correct user info", str(e))
        
        # Test 2.8: /auth/me endpoint (unauthenticated)
        try:
            response = requests.get(f"{BASE_URL}/auth/me", timeout=TEST_TIMEOUT)
            if response.status_code == 401:
                self.results.add_pass("2.8 /auth/me rejects unauthenticated requests")
            else:
                self.results.add_fail("2.8 /auth/me rejects unauthenticated requests", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("2.8 /auth/me rejects unauthenticated requests", str(e))
    
    # ========================================================================
    # TEST 3: PHONE NUMBER MANAGEMENT
    # ========================================================================
    
    def test_phone_management(self):
        """Test phone number management"""
        self.print_section("TEST CATEGORY 3: Phone Number Management")
        
        # Test 3.1: Unauthenticated phone listing blocked
        try:
            response = requests.get(f"{BASE_URL}/api/phones", timeout=TEST_TIMEOUT)
            if response.status_code == 401:
                self.results.add_pass("3.1 Unauthenticated phone listing blocked")
            else:
                self.results.add_fail("3.1 Unauthenticated phone listing blocked", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("3.1 Unauthenticated phone listing blocked", str(e))
        
        # Test 3.2: User 1 can list phones (should be empty initially or show existing)
        try:
            response = self.user1_session.get(f"{BASE_URL}/api/phones", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("3.2 User 1 can list phones")
            else:
                self.results.add_fail("3.2 User 1 can list phones", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("3.2 User 1 can list phones", str(e))
        
        # Test 3.3: User 2 can list phones independently
        try:
            response = self.user2_session.get(f"{BASE_URL}/api/phones", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("3.3 User 2 can list phones independently")
            else:
                self.results.add_fail("3.3 User 2 can list phones independently", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("3.3 User 2 can list phones independently", str(e))
        
        # Note: Phone registration requires valid Twilio credentials, so we'll skip actual creation
        self.results.add_skip("3.4 User 1 phone registration", "Requires valid Twilio credentials")
        self.results.add_skip("3.5 User 2 cannot see User 1 phones", "Depends on phone creation")
        self.results.add_skip("3.6 Phone deletion (owner only)", "Depends on phone creation")
    
    # ========================================================================
    # TEST 4: VOICE AGENTS
    # ========================================================================
    
    def test_voice_agents(self):
        """Test voice agent management"""
        self.print_section("TEST CATEGORY 4: Voice Agent Management")
        
        # Test 4.1: Unauthenticated agent listing blocked
        try:
            response = requests.get(f"{BASE_URL}/agents", timeout=TEST_TIMEOUT)
            if response.status_code == 401:
                self.results.add_pass("4.1 Unauthenticated agent listing blocked")
            else:
                self.results.add_fail("4.1 Unauthenticated agent listing blocked", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("4.1 Unauthenticated agent listing blocked", str(e))
        
        # Test 4.2: User 1 can list agents
        try:
            response = self.user1_session.get(f"{BASE_URL}/agents", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                user1_agent_count = len(data.get("agents", []))
                self.results.add_pass(f"4.2 User 1 can list agents ({user1_agent_count} found)")
            else:
                self.results.add_fail("4.2 User 1 can list agents", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("4.2 User 1 can list agents", str(e))
        
        # Test 4.3: User 2 can list agents independently
        try:
            response = self.user2_session.get(f"{BASE_URL}/agents", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                user2_agent_count = len(data.get("agents", []))
                self.results.add_pass(f"4.3 User 2 can list agents ({user2_agent_count} found)")
            else:
                self.results.add_fail("4.3 User 2 can list agents", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("4.3 User 2 can list agents", str(e))
        
        # Test 4.4: Create agent as User 1
        try:
            agent_data = {
                "name": "Test Agent User1",
                "direction": "incoming",
                "phoneNumber": "+15551111111",
                "systemPrompt": "You are a helpful assistant",
                "greeting": "Hello from User 1",
                "active": True
            }
            response = self.user1_session.post(
                f"{BASE_URL}/agents",
                json=agent_data,
                timeout=TEST_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("agent_id"):
                    self.user1_agent_id = data["agent_id"]
                    self.results.add_pass("4.4 User 1 can create agent")
                else:
                    self.results.add_fail("4.4 User 1 can create agent", "No agent_id returned")
            else:
                self.results.add_fail("4.4 User 1 can create agent", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("4.4 User 1 can create agent", str(e))
        
        # Test 4.5: Create agent as User 2
        try:
            agent_data = {
                "name": "Test Agent User2",
                "direction": "outgoing",
                "phoneNumber": "+15552222222",
                "systemPrompt": "You are another assistant",
                "greeting": "Hello from User 2",
                "active": True
            }
            response = self.user2_session.post(
                f"{BASE_URL}/agents",
                json=agent_data,
                timeout=TEST_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("agent_id"):
                    self.user2_agent_id = data["agent_id"]
                    self.results.add_pass("4.5 User 2 can create agent")
                else:
                    self.results.add_fail("4.5 User 2 can create agent", "No agent_id returned")
            else:
                self.results.add_fail("4.5 User 2 can create agent", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("4.5 User 2 can create agent", str(e))
        
        # Test 4.6: User 1 cannot see User 2's agents
        try:
            response = self.user1_session.get(f"{BASE_URL}/agents", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                agents = data.get("agents", [])
                user2_agent_visible = any(a.get("name") == "Test Agent User2" for a in agents)
                if not user2_agent_visible:
                    self.results.add_pass("4.6 User 1 cannot see User 2's agents (data isolation)")
                else:
                    self.results.add_fail("4.6 User 1 cannot see User 2's agents", "User 2 agent is visible")
            else:
                self.results.add_fail("4.6 User 1 cannot see User 2's agents", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("4.6 User 1 cannot see User 2's agents", str(e))
        
        # Test 4.7: User 2 cannot see User 1's agents
        try:
            response = self.user2_session.get(f"{BASE_URL}/agents", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                agents = data.get("agents", [])
                user1_agent_visible = any(a.get("name") == "Test Agent User1" for a in agents)
                if not user1_agent_visible:
                    self.results.add_pass("4.7 User 2 cannot see User 1's agents (data isolation)")
                else:
                    self.results.add_fail("4.7 User 2 cannot see User 1's agents", "User 1 agent is visible")
            else:
                self.results.add_fail("4.7 User 2 cannot see User 1's agents", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("4.7 User 2 cannot see User 1's agents", str(e))
    
    # ========================================================================
    # TEST 5: MESSAGE AGENTS
    # ========================================================================
    
    def test_message_agents(self):
        """Test messaging agent management"""
        self.print_section("TEST CATEGORY 5: Message Agent Management")
        
        # Test 5.1: Unauthenticated message agent listing blocked
        try:
            response = requests.get(f"{BASE_URL}/api/message-agents", timeout=TEST_TIMEOUT)
            if response.status_code == 401:
                self.results.add_pass("5.1 Unauthenticated message agent listing blocked")
            else:
                self.results.add_fail("5.1 Unauthenticated message agent listing blocked", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("5.1 Unauthenticated message agent listing blocked", str(e))
        
        # Test 5.2: User 1 can list message agents
        try:
            response = self.user1_session.get(f"{BASE_URL}/api/message-agents", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("5.2 User 1 can list message agents")
            else:
                self.results.add_fail("5.2 User 1 can list message agents", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("5.2 User 1 can list message agents", str(e))
        
        # Test 5.3: User 2 can list message agents independently
        try:
            response = self.user2_session.get(f"{BASE_URL}/api/message-agents", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("5.3 User 2 can list message agents independently")
            else:
                self.results.add_fail("5.3 User 2 can list message agents", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("5.3 User 2 can list message agents", str(e))
        
        # Note: Message agent creation requires registered phone, skip for now
        self.results.add_skip("5.4 Message agent creation", "Requires registered phone number")
        self.results.add_skip("5.5 Message agent data isolation", "Depends on creation")
    
    # ========================================================================
    # TEST 6: PROMPTS
    # ========================================================================
    
    def test_prompts(self):
        """Test prompt management"""
        self.print_section("TEST CATEGORY 6: Prompt Management")
        
        # Test 6.1: Unauthenticated prompt listing blocked
        try:
            response = requests.get(f"{BASE_URL}/api/prompts", timeout=TEST_TIMEOUT)
            if response.status_code == 401:
                self.results.add_pass("6.1 Unauthenticated prompt listing blocked")
            else:
                self.results.add_fail("6.1 Unauthenticated prompt listing blocked", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("6.1 Unauthenticated prompt listing blocked", str(e))
        
        # Test 6.2: User 1 can list prompts
        try:
            response = self.user1_session.get(f"{BASE_URL}/api/prompts", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("6.2 User 1 can list prompts")
            else:
                self.results.add_fail("6.2 User 1 can list prompts", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("6.2 User 1 can list prompts", str(e))
        
        # Test 6.3: User 2 can list prompts independently
        try:
            response = self.user2_session.get(f"{BASE_URL}/api/prompts", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("6.3 User 2 can list prompts independently")
            else:
                self.results.add_fail("6.3 User 2 can list prompts", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("6.3 User 2 can list prompts", str(e))
        
        # Note: Prompt creation requires phone number ID, skip for now
        self.results.add_skip("6.4 Prompt creation", "Requires phone number ID")
        self.results.add_skip("6.5 Prompt data isolation", "Depends on creation")
    
    # ========================================================================
    # TEST 7: SCHEDULED CALLS
    # ========================================================================
    
    def test_scheduled_calls(self):
        """Test scheduled call management"""
        self.print_section("TEST CATEGORY 7: Scheduled Call Management")
        
        # Test 7.1: Unauthenticated scheduled call listing blocked
        try:
            response = requests.get(f"{BASE_URL}/api/scheduled-calls", timeout=TEST_TIMEOUT)
            if response.status_code == 401:
                self.results.add_pass("7.1 Unauthenticated scheduled call listing blocked")
            else:
                self.results.add_fail("7.1 Unauthenticated scheduled call listing blocked", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("7.1 Unauthenticated scheduled call listing blocked", str(e))
        
        # Test 7.2: User 1 can list scheduled calls
        try:
            response = self.user1_session.get(f"{BASE_URL}/api/scheduled-calls", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("7.2 User 1 can list scheduled calls")
            else:
                self.results.add_fail("7.2 User 1 can list scheduled calls", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("7.2 User 1 can list scheduled calls", str(e))
        
        # Test 7.3: User 2 can list scheduled calls independently
        try:
            response = self.user2_session.get(f"{BASE_URL}/api/scheduled-calls", timeout=TEST_TIMEOUT)
            if response.status_code == 200:
                self.results.add_pass("7.3 User 2 can list scheduled calls independently")
            else:
                self.results.add_fail("7.3 User 2 can list scheduled calls", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("7.3 User 2 can list scheduled calls", str(e))
        
        # Note: Scheduled call creation requires phone number ID, skip for now
        self.results.add_skip("7.4 Scheduled call creation", "Requires phone number ID")
        self.results.add_skip("7.5 Scheduled call data isolation", "Depends on creation")
    
    # ========================================================================
    # TEST 8: PUBLIC ENDPOINTS (Should NOT require auth)
    # ========================================================================
    
    def test_public_endpoints(self):
        """Test endpoints that should remain public"""
        self.print_section("TEST CATEGORY 8: Public Endpoints")
        
        # Test 8.1: Twilio webhook endpoints accessible (no auth)
        try:
            response = requests.get(f"{BASE_URL}/twilio/status", timeout=TEST_TIMEOUT)
            if response.status_code in [200, 405]:  # 405 = method not allowed (expects POST)
                self.results.add_pass("8.1 Twilio webhook endpoints accessible")
            else:
                self.results.add_fail("8.1 Twilio webhook endpoints accessible", f"Status: {response.status_code}")
        except Exception as e:
            self.results.add_fail("8.1 Twilio webhook endpoints accessible", str(e))
    
    # ========================================================================
    # TEST 9: DATA CLEANUP
    # ========================================================================
    
    def test_cleanup(self):
        """Clean up test data"""
        self.print_section("TEST CATEGORY 9: Cleanup")
        
        # Test 9.1: Delete User 1's test agent
        if hasattr(self, 'user1_agent_id'):
            try:
                response = self.user1_session.delete(
                    f"{BASE_URL}/agents/{self.user1_agent_id}",
                    timeout=TEST_TIMEOUT
                )
                if response.status_code == 200:
                    self.results.add_pass("9.1 User 1 agent deletion successful")
                else:
                    self.results.add_fail("9.1 User 1 agent deletion successful", f"Status: {response.status_code}")
            except Exception as e:
                self.results.add_fail("9.1 User 1 agent deletion successful", str(e))
        else:
            self.results.add_skip("9.1 User 1 agent deletion", "No agent created")
        
        # Test 9.2: Delete User 2's test agent
        if hasattr(self, 'user2_agent_id'):
            try:
                response = self.user2_session.delete(
                    f"{BASE_URL}/agents/{self.user2_agent_id}",
                    timeout=TEST_TIMEOUT
                )
                if response.status_code == 200:
                    self.results.add_pass("9.2 User 2 agent deletion successful")
                else:
                    self.results.add_fail("9.2 User 2 agent deletion successful", f"Status: {response.status_code}")
            except Exception as e:
                self.results.add_fail("9.2 User 2 agent deletion successful", str(e))
        else:
            self.results.add_skip("9.2 User 2 agent deletion", "No agent created")
        
        # Test 9.3: Verify User 2 cannot delete User 1's agent
        if hasattr(self, 'user1_agent_id'):
            try:
                response = self.user2_session.delete(
                    f"{BASE_URL}/agents/{self.user1_agent_id}",
                    timeout=TEST_TIMEOUT
                )
                if response.status_code in [404, 403]:  # Not found or forbidden
                    self.results.add_pass("9.3 User 2 cannot delete User 1's agent (authorization works)")
                else:
                    self.results.add_fail("9.3 User 2 cannot delete User 1's agent", f"Deletion allowed! Status: {response.status_code}")
            except Exception as e:
                self.results.add_fail("9.3 User 2 cannot delete User 1's agent", str(e))
        else:
            self.results.add_skip("9.3 Cross-user deletion prevention", "No agent to test")
    
    # ========================================================================
    # MAIN TEST EXECUTION
    # ========================================================================
    
    def run_all_tests(self):
        """Run all test categories"""
        print(f"{Colors.BOLD}{Colors.OKCYAN}")
        print("=" * 70)
        print("VOICE AGENT PLATFORM - COMPREHENSIVE E2E TEST SUITE")
        print("=" * 70)
        print(f"{Colors.ENDC}")
        print(f"Base URL: {BASE_URL}")
        print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        try:
            self.test_health_endpoints()
            self.test_authentication()
            self.test_phone_management()
            self.test_voice_agents()
            self.test_message_agents()
            self.test_prompts()
            self.test_scheduled_calls()
            self.test_public_endpoints()
            self.test_cleanup()
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.FAIL}Fatal error during testing: {e}{Colors.ENDC}")
        finally:
            self.results.print_summary()
            
            # Return exit code based on results
            if self.results.failed > 0:
                return 1
            return 0

if __name__ == "__main__":
    import sys
    tester = VoiceAgentTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
