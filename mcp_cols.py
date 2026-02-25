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
    return read_response(process, timeout=60)

def get_content(resp):
    try:
        text = resp["result"]["content"][0]["text"]
        return json.loads(text)
    except Exception as e:
        return None

def get_items(data):
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
        if "items" in data and isinstance(data["items"], list):
            return data["items"]
    return []

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
    tool_call(process, "connection_operations", {
        "request": {"operation": "Connect", "dataSource": f"localhost:{PBI_PORT}"}
    }, request_id=2)

    rid = 3

    # Step 1: List all columns from tb_atendimentos_telemedicina to find the specialty column
    print("=== COLUMNS of tb_atendimentos_telemedicina ===")
    col_r = tool_call(process, "column_operations", {
        "request": {"operation": "List", "tableName": "tb_atendimentos_telemedicina"}
    }, request_id=rid); rid += 1
    col_raw = col_r
    print(json.dumps(col_raw, indent=2)[:3000])
    
    with open("columns_raw.json", "w", encoding="utf-8") as f:
        json.dump(col_raw, f, indent=2, ensure_ascii=False)
    
    process.terminate()

if __name__ == "__main__":
    main()
