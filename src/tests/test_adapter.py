import asyncio
import sys
import os
import json

# Add current directory and src directory to path so we can import src.main and appwrite_adapter
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.main import main

class MockReq:
    def __init__(self, path='/', method='GET', headers=None, body='', query=None):
        self.path = path
        self.method = method
        self.headers = headers or {}
        self.body = body
        self.query = query or {}
        self.host = 'localhost'

class MockRes:
    def binary(self, body, status_code=200, headers=None):
        return {
            'body': body,
            'status_code': status_code,
            'headers': headers or {}
        }
    def text(self, body, status_code=200, headers=None):
        return self.binary(body.encode('utf-8'), status_code, headers)
    def json(self, obj, status_code=200, headers=None):
        return self.binary(json.dumps(obj).encode('utf-8'), status_code, headers)

class MockContext:
    def __init__(self, req):
        self.req = req
        self.res = MockRes()
    def log(self, msg):
        print(f"LOG: {msg}")
    def error(self, msg):
        print(f"ERROR: {msg}", file=sys.stderr)

async def test_case(name, path, method='GET', expected_status=200, expected_body_part=None):
    print(f"--- Testing {name} ({method} {path}) ---")
    req = MockReq(path=path, method=method)
    context = MockContext(req)
    response = await main(context)
    
    status = response['status_code']
    body = response['body'].decode()
    headers = response['headers']
    
    print(f"Status: {status}")
    print(f"Headers: {headers}")
    print(f"Body: {body}")
    
    assert status == expected_status, f"Expected status {expected_status}, got {status}"
    if expected_body_part:
        assert expected_body_part in body, f"Expected body to contain '{expected_body_part}'"
    print(f"PASS: {name}\n")

async def run_tests():
    try:
        await test_case("Ping", "/ping", expected_body_part="Pong")
        await test_case("Home", "/", expected_body_part="Build like a team of hundreds_")
        await test_case("Not Found", "/404", expected_status=404)
        print("All tests passed successfully!")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_tests())
