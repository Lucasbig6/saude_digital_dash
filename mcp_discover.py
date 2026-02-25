import subprocess
import json
import sys
import time

SERVER_PATH = r"c:\Users\LUCAS.ARAUJO\Documents\antigravity\mcp-server-ext\extension\server\powerbi-modeling-mcp.exe"
PBI_PORT = 54373

def send_request(process, method, params, request_id=None):
    request = {"jsonrpc": "2.0", "method": method, "params": params}
    if request_id is not None:
        request["id"] = request_id
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()

def read_response(process, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        line = process.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        try:
            return json.loads(line)
        except:
            continue
    print(f"TIMEOUT after {timeout}s waiting for response", file=sys.stderr)
    return None

def tool_call(process, tool_name, arguments, request_id):
    send_request(process, "tools/call", {"name": tool_name, "arguments": arguments}, request_id)
    return read_response(process, timeout=30)

def get_content(resp):
    try:
        text = resp["result"]["content"][0]["text"]
        return json.loads(text)
    except Exception as e:
        print(f"Error parsing response: {e}, resp={resp}", file=sys.stderr)
        return None

def main():
    process = subprocess.Popen(
        [SERVER_PATH, "--start", "--skipconfirmation"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1
    )

    # Initialize
    send_request(process, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "Antigravity", "version": "1.0"}
    }, request_id=1)
    read_response(process, timeout=10)
    send_request(process, "notifications/initialized", {})

    # First: try to list databases without connecting (ListConnections or database_operations/List)
    print("Listing existing connections...")
    list_conn = tool_call(process, "connection_operations", {
        "request": {"operation": "ListConnections"}
    }, request_id=2)
    print(f"Existing connections: {json.dumps(get_content(list_conn), indent=2)}")

    # Connect to port only (no catalog)
    print(f"\nConnecting to localhost:{PBI_PORT} (no catalog)...")
    conn_resp = tool_call(process, "connection_operations", {
        "request": {
            "operation": "Connect",
            "dataSource": f"localhost:{PBI_PORT}"
        }
    }, request_id=3)
    print(f"Connect result: {json.dumps(get_content(conn_resp), indent=2)}")

    # List databases
    print("\nListing databases...")
    db_resp = tool_call(process, "database_operations", {
        "request": {"operation": "List"}
    }, request_id=4)
    db_data = get_content(db_resp)
    print(f"Databases: {json.dumps(db_data, indent=2)}")

    process.terminate()

if __name__ == "__main__":
    main()
