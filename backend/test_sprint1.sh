#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token","FAIL"))')
echo "Token: ${TOKEN:0:20}..."
echo ""
echo "=== Test 1: robrock f25 gia ==="
curl -s http://localhost:8000/api/ask -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"query":"robrock f25 gia"}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print("no_result:",d.get("no_result")); print("answer:",d.get("answer","")[:500]); print("citations:",len(d.get("citations",[])))'
echo ""
echo "=== Test 2: gia F25 Ultra ==="
curl -s http://localhost:8000/api/ask -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"query":"gia F25 Ultra"}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print("no_result:",d.get("no_result")); print("answer:",d.get("answer","")[:500]); print("citations:",len(d.get("citations",[])))'
echo ""
echo "=== DONE ==="
