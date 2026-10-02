import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:5000/api/auth/login', 
    data=json.dumps({"username": "demo_owner", "password": "password123"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        print(response.getcode())
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode('utf-8'))
