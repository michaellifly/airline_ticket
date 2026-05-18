import urllib.request, json, sys

TOKEN = "8954809469:AAFEC0clUupiWNvKTw5MSBFZTY4XTqhUNY8"
CHAT_ID = "6622252961"

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
r = urllib.request.urlopen(url, timeout=10)
data = json.loads(r.read())
print("ok:", data["ok"], "| updates:", len(data.get("result", [])))
for u in data.get("result", []):
    msg = u.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "")
    match = chat_id == CHAT_ID
    print(f"  update_id={u['update_id']} chat_id={chat_id!r} match={match} text={text!r}")
