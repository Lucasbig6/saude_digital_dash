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

def get_content(resp):
    try:
        text = resp["result"]["content"][0]["text"]
        return json.loads(text)
    except:
        return {}

def get_items(data):
    # Response uses 'data' key (array) not 'items'
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

    conn = tool_call(process, "connection_operations", {
        "request": {"operation": "Connect", "dataSource": f"localhost:{PBI_PORT}"}
    }, request_id=2)
    print(f"Connected to: {get_content(conn).get('data')}\n")

    rid = 3
    result = {"tables": [], "measures": {}, "relationships": [], "columns_summary": {}}

    # ============ TABLES ============
    print("=== TABELAS ===")
    tbl_r = tool_call(process, "table_operations", {"request": {"operation": "List"}}, request_id=rid); rid += 1
    tbl_data = get_content(tbl_r)
    tables = get_items(tbl_data)

    visible_tables = []
    for t in tables:
        name = t.get("name", "")
        # Skip hidden date helper tables
        if "DateTable" in name or "LocalDate" in name:
            continue
        hidden = " [oculta]" if t.get("isHidden") else ""
        cols = t.get("columnCount", 0)
        meas = t.get("measureCount", 0)
        print(f"  {'📁' if t.get('isHidden') else '📋'} {name}{hidden}  |  Colunas: {cols}  |  Medidas: {meas}")
        t["_display"] = True
        visible_tables.append(t)
        result["tables"].append({"name": name, "columns": cols, "measures": meas, "hidden": bool(t.get("isHidden"))})

    print(f"\nTotal de tabelas visíveis: {len(visible_tables)}")

    # ============ COLUMNS per table ============
    print("\n=== COLUNAS POR TABELA ===")
    for t in visible_tables:
        if t.get("isHidden"):
            continue
        col_r = tool_call(process, "column_operations", {
            "request": {"operation": "List", "tableName": t["name"]}
        }, request_id=rid); rid += 1
        col_data = get_content(col_r)
        cols = get_items(col_data)
        result["columns_summary"][t["name"]] = [c.get("name") for c in cols]
        if cols:
            print(f"\n  [{t['name']}] — {len(cols)} colunas")
            for c in cols[:10]:  # Show first 10
                dt = c.get("dataType", "")
                print(f"    - {c.get('name')} ({dt})")
            if len(cols) > 10:
                print(f"    ... e mais {len(cols)-10} colunas")

    # ============ MEASURES ============
    print("\n=== MEDIDAS ===")
    for t in visible_tables:
        if t.get("isHidden") or not t.get("measureCount", 0):
            continue
        meas_r = tool_call(process, "measure_operations", {
            "request": {"operation": "List", "tableName": t["name"]}
        }, request_id=rid); rid += 1
        meas_data = get_content(meas_r)
        measures = get_items(meas_data)
        result["measures"][t["name"]] = [{"name": m.get("name"), "expression": m.get("expression"), "format": m.get("formatString")} for m in measures]
        if measures:
            print(f"\n  [{t['name']}] — {len(measures)} medidas")
            for m in measures:
                fmt = f"  ({m.get('formatString','')})" if m.get('formatString') else ""
                print(f"    • {m.get('name')}{fmt}")

    # ============ RELATIONSHIPS ============
    print("\n=== RELACIONAMENTOS ===")
    rel_r = tool_call(process, "relationship_operations", {"request": {"operation": "List"}}, request_id=rid); rid += 1
    rel_data = get_content(rel_r)
    rels = get_items(rel_data)
    for r in rels:
        act = "" if r.get("isActive", True) else " [inativo]"
        cf = r.get("crossFilteringBehavior", "")
        print(f"  {r.get('fromTable')}.{r.get('fromColumn')} ➜ {r.get('toTable')}.{r.get('toColumn')} [{cf}]{act}")
        result["relationships"].append({
            "from": f"{r.get('fromTable')}.{r.get('fromColumn')}",
            "to": f"{r.get('toTable')}.{r.get('toColumn')}",
            "crossFilter": cf,
            "active": r.get("isActive", True)
        })
    print(f"\nTotal: {len(rels)} relacionamentos")

    # Save full result
    with open("model_analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\n✅ Análise completa salva em model_analysis.json")
    process.terminate()

if __name__ == "__main__":
    main()
