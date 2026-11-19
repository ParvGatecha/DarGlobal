import json
import urllib.request
import sys

PUBLIC_BASE = "https://3509c8bb26acb4.app.lhr.life"

def test_health():
    url = f"{PUBLIC_BASE}/api/v1/health"
    print(f"\n--- Testing Health Endpoint: {url} ---")
    req = urllib.request.Request(url, headers={"User-Agent": "Verification-Suite/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"Health returned {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Status: {data.get('status')}")
        print(f"Total Chunks: {data.get('total_indexed_chunks')}")
        print(f"Active Model: {data.get('active_model')}")
        print(f"Agentic Tools: {len(data.get('registered_tools', []))} tools registered")
        assert data.get("vector_db_connected") is True
        assert data.get("total_indexed_chunks") == 32
        print("✓ Health check PASSED")

def test_properties():
    url = f"{PUBLIC_BASE}/api/v1/properties?city=Dubai"
    print(f"\n--- Testing Properties Endpoint: {url} ---")
    req = urllib.request.Request(url, headers={"User-Agent": "Verification-Suite/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"Properties returned {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Retrieved {len(data)} properties for Dubai")
        assert len(data) > 0
        first = data[0]
        print(f"First property: {first.get('title')} ({first.get('price')})")
        print("✓ Properties catalog PASSED")

def test_chat():
    url = f"{PUBLIC_BASE}/api/v1/chat"
    print(f"\n--- Testing Chat REST Endpoint: {url} ---")
    payload = {
        "message": "What is Urban Oasis by Missoni and where is it located?",
        "history": []
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Verification-Suite/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        assert resp.status == 200, f"Chat returned {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Model used: {data.get('model_used')}")
        print(f"Citations count: {len(data.get('citations', []))}")
        print(f"Execution trace steps: {len(data.get('execution_trace', []))}")
        if data.get('execution_trace'):
            print(f"Tool executed: {data['execution_trace'][0]['tool_name']}")
        print(f"Answer snippet: {data.get('answer')[:120]}...")
        assert len(data.get("citations", [])) > 0
        print("✓ Chat REST PASSED")

def test_stream():
    url = f"{PUBLIC_BASE}/api/v1/chat/stream"
    print(f"\n--- Testing Chat SSE Streaming Endpoint: {url} ---")
    payload = {
        "message": "Find luxury properties in Riyadh on Wasalt.",
        "history": []
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Verification-Suite/1.0"}
    )
    events = []
    with urllib.request.urlopen(req, timeout=20) as resp:
        assert resp.status == 200, f"Stream returned {resp.status}"
        for line in resp:
            text = line.decode("utf-8").strip()
            if text.startswith("data:"):
                json_str = text[5:].strip()
                if json_str:
                    evt = json.loads(json_str)
                    events.append(evt.get("type"))
    print(f"Stream received {len(events)} events: {set(events)}")
    assert "token" in events or "metadata" in events or "done" in events
    print("✓ Chat SSE Streaming PASSED")

if __name__ == "__main__":
    try:
        test_health()
        test_properties()
        test_chat()
        test_stream()
        print("\n==========================================")
        print("ALL PUBLIC ENDPOINT TESTS COMPLETED: 100% SUCCESS")
        print("==========================================")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
