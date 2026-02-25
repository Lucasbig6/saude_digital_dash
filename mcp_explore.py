import subprocess
import json
import sys
import time

def send_request(process, method, params, request_id=None):
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }
    if request_id is not None:
        request["id"] = request_id
    
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()

def read_response(process):
    line = process.stdout.readline()
    if not line:
        return None
    try:
        return json.loads(line)
    except Exception as e:
        print(f"Error parsing line: {line[:100]}... {e}", file=sys.stderr)
        return None

def main():
    server_path = r"c:\Users\LUCAS.ARAUJO\Documents\antigravity\mcp-server-ext\extension\server\powerbi-modeling-mcp.exe"
    process = subprocess.Popen(
        [server_path, "--start", "--skipconfirmation"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    send_request(process, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "Antigravity", "version": "1.0"}
    }, request_id=1)
    read_response(process)
    send_request(process, "notifications/initialized", {})

    print("--- Listing Local Instances ---")
    send_request(process, "tools/call", {
        "name": "connection_operations",
        "arguments": {
            "request": {
                "operation": "ListLocalInstances"
            }
        }
    }, request_id=3)
    resp = read_response(process)
    
    if resp and "result" in resp and "content" in resp["result"]:
        content_text = resp["result"]["content"][0]["text"]
        instances = json.loads(content_text)
        print("Instances found:")
        target_found = None
        items = instances.get("items", [])
        if not items:
            print("No instances found in the list.")
        for inst in items:
            name = inst.get("databaseName", "Unknown")
            print(f"- {name} (Port: {inst.get('port')})")
            if "Monitoramento" in name:
                target_found = inst
        
        if target_found:
            print(f"Target found: {target_found['databaseName']} via port {target_found['port']}...")
            send_request(process, "tools/call", {
                "name": "connection_operations",
                "arguments": {
                    "request": {
                        "operation": "Connect",
                        "dataSource": f"localhost:{target_found['port']}",
                        "initialCatalog": target_found['databaseName']
                    }
                }
            }, request_id=4)
            connect_resp = read_response(process)
            print(f"Connect Response: {json.dumps(connect_resp, indent=2)}")

            print("--- Listing Tables ---")
            send_request(process, "tools/call", {
                "name": "table_operations",
                "arguments": {
                    "request": {
                        "operation": "List"
                    }
                }
            }, request_id=5)
            table_resp = read_response(process)
            
            if table_resp and "result" in table_resp and "content" in table_resp["result"]:
                content_text = table_resp["result"]["content"][0]["text"]
                tables = json.loads(content_text)
                print("Tables summary:")
                for table in tables.get("items", []):
                    name = table.get("name")
                    is_hidden = table.get("isHidden", False)
                    print(f"- {name} (Hidden: {is_hidden})")
                
                with open("tables_analysis.json", "w") as f:
                    json.dump(tables, f, indent=2)
            else:
                print(f"Failed to list tables: {table_resp}")

        else:
            print("Target not found. Please ensure the file is fully loaded in Power BI Desktop.")
    else:
        print(f"Failed to list instances: {resp}")
    
    process.terminate()

if __name__ == "__main__":
    main()
