import json
import urllib.request
import ssl

BASE_URL = "http://127.0.0.1:8000/api/v1/chat"

def query_chat(message: str, history=None):
    if history is None:
        history = []
    payload = {
        "message": message,
        "history": history
    }
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("=== STARTING PRIORITY 2: CHATBOT EVALUATION ===")

# Query 1
q1 = "What luxury developments does DarGlobal offer in Dubai?"
print(f"\n[Query 1]: {q1}")
r1 = query_chat(q1)
print(f"Tool executed: {[t['tool_name'] for t in r1.get('execution_trace', [])]}")
print(f"Citations count: {len(r1.get('citations', []))}")
print(f"Answer:\n{r1.get('answer')[:300]}...\n")

# Query 2
q2 = "Find properties in Riyadh under SAR 5 million."
print(f"\n[Query 2]: {q2}")
r2 = query_chat(q2)
print(f"Tool executed: {[t['tool_name'] for t in r2.get('execution_trace', [])]}")
print(f"Citations count: {len(r2.get('citations', []))}")
print(f"Answer:\n{r2.get('answer')[:300]}...\n")

# Query 3
q3 = "Compare a DarGlobal Dubai project with a Wasalt Riyadh property."
print(f"\n[Query 3]: {q3}")
r3 = query_chat(q3)
print(f"Tool executed: {[t['tool_name'] for t in r3.get('execution_trace', [])]}")
print(f"Citations count: {len(r3.get('citations', []))}")
print(f"Answer:\n{r3.get('answer')[:300]}...\n")

# Query 4 (Follow-up context)
q4 = "What amenities does the first property offer?"
history_for_q4 = [
    {"role": "user", "content": q3},
    {"role": "assistant", "content": r3.get("answer", "")}
]
print(f"\n[Query 4 (Follow-up)]: {q4}")
r4 = query_chat(q4, history=history_for_q4)
print(f"Tool executed: {[t['tool_name'] for t in r4.get('execution_trace', [])]}")
print(f"Citations count: {len(r4.get('citations', []))}")
print(f"Answer:\n{r4.get('answer')[:300]}...\n")

# Query 5 (Negative / out-of-scope test: Tokyo)
q5 = "What properties does DarGlobal offer in Tokyo?"
print(f"\n[Query 5 (Negative - Tokyo)]: {q5}")
r5 = query_chat(q5)
print(f"Tool executed: {[t['tool_name'] for t in r5.get('execution_trace', [])]}")
print(f"Answer:\n{r5.get('answer')}\n")

# Query 6 (Unindexed attribute: exact maintenance fee)
q6 = "What is the exact maintenance fee for DaVinci Tower?"
print(f"\n[Query 6 (Unindexed attribute - maintenance fee)]: {q6}")
r6 = query_chat(q6)
print(f"Tool executed: {[t['tool_name'] for t in r6.get('execution_trace', [])]}")
print(f"Answer:\n{r6.get('answer')}\n")
