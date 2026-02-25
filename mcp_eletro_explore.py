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

def read_response(process, timeout=90):
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
    return read_response(process, timeout=90)

def get_content(resp):
    try:
        text = resp["result"]["content"][0]["text"]
        return json.loads(text)
    except:
        return {}

def run_dax(process, query, rid):
    r = tool_call(process, "dax_query_operations", {
        "request": {"operation": "EXECUTE", "query": query}
    }, request_id=rid)
    data = get_content(r)
    return data.get("data", {}), r

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
    tool_call(process, "connection_operations", {
        "request": {"operation": "Connect", "dataSource": f"localhost:{PBI_PORT}"}
    }, request_id=2)

    rid = 3

    # Query: Eletro attendance by week (using WEEKNUM and YEAR)
    print("Querying Eletro attendance by week...")
    dax_by_week = """
EVALUATE
ADDCOLUMNS(
  SUMMARIZECOLUMNS(
    tb_atendimentos_telemedicina[profissional_espec],
    DATATABLE("Ano", INTEGER, DATATABLE("Semana", INTEGER, {})),
    "Ano", YEAR(tb_atendimentos_telemedicina[data_registro]),
    "Semana", WEEKNUM(tb_atendimentos_telemedicina[data_registro], 2),
    "Qtd", COUNTROWS(tb_atendimentos_telemedicina)
  )
)"""

    # Simpler query: group by year+week using calculated string
    dax_q = """EVALUATE
FILTER(
  ADDCOLUMNS(
    SUMMARIZECOLUMNS(
      tb_atendimentos_telemedicina[profissional_espec],
      tb_atendimentos_telemedicina[AnoMes],
      "Qtd", COUNTROWS(tb_atendimentos_telemedicina)
    ),
    "Ano", LEFT(tb_atendimentos_telemedicina[AnoMes], 4)
  ),
  CONTAINSSTRING(LOWER(tb_atendimentos_telemedicina[profissional_espec]), "eletro")
)"""
    
    data1, raw1 = run_dax(process, dax_q, rid); rid += 1
    rows1 = data1.get("rows", [])
    print(f"Got {len(rows1)} rows for AnoMes query")
    print(json.dumps(rows1[:5], indent=2, ensure_ascii=False))
    with open("dax_eletro_anomes.json", "w", encoding="utf-8") as f:
        json.dump(raw1, f, indent=2, ensure_ascii=False)

    # Also try with actual date column grouped by week
    dax_week = """EVALUATE
FILTER(
  SUMMARIZECOLUMNS(
    tb_atendimentos_telemedicina[profissional_espec],
    "Semana", FORMAT(tb_atendimentos_telemedicina[data_registro], "YYYY-\\QQ\\W-WW"),
    "DataInicio", MINX(VALUES(tb_atendimentos_telemedicina[data_registro]), tb_atendimentos_telemedicina[data_registro]),
    "Qtd", COUNTROWS(tb_atendimentos_telemedicina)
  ),
  CONTAINSSTRING(LOWER(tb_atendimentos_telemedicina[profissional_espec]), "eletro")
)"""

    # Simpler week grouping using FORMAT
    dax_week2 = """EVALUATE
FILTER(
  SUMMARIZECOLUMNS(
    tb_atendimentos_telemedicina[profissional_espec],
    "Semana_Inicio", FORMAT(
      tb_atendimentos_telemedicina[data_registro] - WEEKDAY(tb_atendimentos_telemedicina[data_registro], 2) + 1,
      "YYYY-MM-DD"
    ),
    "Qtd", COUNTROWS(tb_atendimentos_telemedicina)
  ),
  CONTAINSSTRING(LOWER(tb_atendimentos_telemedicina[profissional_espec]), "eletro")
)"""

    data2, raw2 = run_dax(process, dax_week2, rid); rid += 1
    rows2 = data2.get("rows", [])
    print(f"\nGot {len(rows2)} rows for week query")
    print(json.dumps(rows2[:5], indent=2, ensure_ascii=False))
    with open("dax_eletro_week.json", "w", encoding="utf-8") as f:
        json.dump(raw2, f, indent=2, ensure_ascii=False)

    process.terminate()
    return rows2, rows1

if __name__ == "__main__":
    main()
