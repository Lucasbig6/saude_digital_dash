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
    return None

def tool_call(process, tool_name, arguments, request_id):
    send_request(process, "tools/call", {"name": tool_name, "arguments": arguments}, request_id)
    return read_response(process, timeout=30)

def main():
    process = subprocess.Popen(
        [SERVER_PATH, "--start", "--skipconfirmation"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1
    )
    send_request(process, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "Antigravity", "version": "1.0"}
    }, request_id=1)
    read_response(process, timeout=10)
    send_request(process, "notifications/initialized", {})

    # Connect
    conn = tool_call(process, "connection_operations", {
        "request": {"operation": "Connect", "dataSource": f"localhost:{PBI_PORT}"}
    }, request_id=2)
    print(f"Connected: {json.dumps(get_content(conn), indent=2)}")

    # Get raw table response and dump entirely
    print("\n=== RAW TABLE RESPONSE ===")
    tbl_raw = tool_call(process, "table_operations", {
        "request": {"operation": "List"}
    }, request_id=3)
    # Dump the full raw JSON response
    print(json.dumps(tbl_raw, indent=2))
    
    process.terminate()

def get_content(resp):
    try:
        text = resp["result"]["content"][0]["text"]
        return json.loads(text)
    except:
        return resp

if __name__ == "__main__":
    main()
