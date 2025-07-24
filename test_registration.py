#!/usr/bin/env python3
"""
Test script to verify user registration functionality
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_registration():
    """Test user registration endpoint"""
    
    # Test data
    test_email = "test@example.com"
    test_password = "testpassword123"
    
    print("Testing user registration...")
    
    # Test 1: Successful registration
    print("\n1. Testing successful registration...")
    payload = {
        "email": test_email,
        "password": test_password,
        "confirmPassword": test_password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/register", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Registration successful!")
        else:
            print("❌ Registration failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Duplicate email
    print("\n2. Testing duplicate email...")
    try:
        response = requests.post(f"{BASE_URL}/api/register", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 409:
            print("✅ Duplicate email correctly detected!")
        else:
            print("❌ Duplicate email check failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Invalid email format
    print("\n3. Testing invalid email format...")
    payload_invalid = {
        "email": "invalid-email",
        "password": test_password,
        "confirmPassword": test_password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/register", json=payload_invalid)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400:
            print("✅ Invalid email format correctly detected!")
        else:
            print("❌ Invalid email format check failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Password mismatch
    print("\n4. Testing password mismatch...")
    payload_mismatch = {
        "email": "test2@example.com",
        "password": test_password,
        "confirmPassword": "differentpassword"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/register", json=payload_mismatch)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400:
            print("✅ Password mismatch correctly detected!")
        else:
            print("❌ Password mismatch check failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Short password
    print("\n5. Testing short password...")
    payload_short = {
        "email": "test3@example.com",
        "password": "short",
        "confirmPassword": "short"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/register", json=payload_short)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400:
            print("✅ Short password correctly detected!")
        else:
            print("❌ Short password check failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_login():
    """Test user login endpoint"""
    
    print("\n\nTesting user login...")
    
    # Test 1: Successful login
    print("\n1. Testing successful login...")
    payload = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/login", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
        else:
            print("❌ Login failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Invalid credentials
    print("\n2. Testing invalid credentials...")
    payload_invalid = {
        "email": "test@example.com",
        "password": "wrongpassword"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/login", json=payload_invalid)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 401:
            print("✅ Invalid credentials correctly detected!")
        else:
            print("❌ Invalid credentials check failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_email_check():
    """Test email availability check"""
    
    print("\n\nTesting email availability check...")
    
    # Test existing email
    try:
        response = requests.get(f"{BASE_URL}/api/check-email?email=test@example.com")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        
        if response.status_code == 200 and not data.get("available"):
            print("✅ Existing email correctly detected!")
        else:
            print("❌ Existing email check failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test available email
    try:
        response = requests.get(f"{BASE_URL}/api/check-email?email=new@example.com")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        
        if response.status_code == 200 and data.get("available"):
            print("✅ Available email correctly detected!")
        else:
            print("❌ Available email check failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("Currency Converter Registration Test Suite")
    print("=" * 50)
    
    test_registration()
    test_login()
    test_email_check()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")
    print("=" * 50)
