"""
ELK Stack Linux Desktop Guide — Compact PDF
Run:  python generate_pdf.py
Out:  elk-linux-desktop-guide.pdf
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Preformatted, KeepTogether
)

BLUE   = HexColor("#005f87")
AMBER  = HexColor("#f5a623")
DARK   = HexColor("#1a1a2e")
GREY   = HexColor("#666666")
WHITE  = colors.white
CODEBG = HexColor("#f2f2f2")
NOTEBG = HexColor("#e8f4fb")
WARNBG = HexColor("#fff3cd")
LIGHTBG= HexColor("#f4f8fb")
BORDER = HexColor("#c8dce8")
RED    = HexColor("#c0392b")

W, H   = A4
ML=MR  = 16*mm
MT=MB  = 20*mm
TW     = W - ML - MR

def ps(name, **kw): return ParagraphStyle(name, **kw)

sBody  = ps("body",  fontName="Helvetica",      fontSize=9,   leading=13, textColor=DARK, spaceAfter=3)
sCode  = ps("code",  fontName="Courier",        fontSize=8,   leading=11.5, textColor=DARK, backColor=CODEBG, leftIndent=8, rightIndent=8, spaceBefore=3, spaceAfter=4)
sH2    = ps("h2",    fontName="Helvetica-Bold", fontSize=13,  leading=16, textColor=BLUE, spaceBefore=14, spaceAfter=2)
sH3    = ps("h3",    fontName="Helvetica-Bold", fontSize=10,  leading=13, textColor=DARK, spaceBefore=9, spaceAfter=2)
sH4    = ps("h4",    fontName="Helvetica-Bold", fontSize=9,   leading=12, textColor=BLUE, spaceBefore=6, spaceAfter=1)
sSmall = ps("small", fontName="Helvetica",      fontSize=7.5, leading=10, textColor=GREY, alignment=TA_CENTER)
sCov1  = ps("cov1",  fontName="Helvetica-Bold", fontSize=26,  leading=30, textColor=BLUE, alignment=TA_CENTER)
sCov2  = ps("cov2",  fontName="Helvetica-Bold", fontSize=13,  leading=17, textColor=DARK, alignment=TA_CENTER, spaceAfter=4)
sCov3  = ps("cov3",  fontName="Helvetica",      fontSize=9.5, leading=14, textColor=GREY, alignment=TA_CENTER, spaceAfter=16)
sNote  = ps("note",  fontName="Helvetica",      fontSize=8.5, leading=12, textColor=DARK)
sStep  = ps("step",  fontName="Helvetica-Bold", fontSize=9.5, leading=13, textColor=BLUE, spaceBefore=8, spaceAfter=2)

SP  = lambda n=5: Spacer(1, n)
HR  = lambda: HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceAfter=4)

def code(text):
    return Preformatted(text.rstrip(), sCode)

def note(text, bg=NOTEBG, border=BLUE):
    t = Table([[Paragraph(text, sNote)]], colWidths=[TW])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), bg),
        ("LINEBEFORE",   (0,0),(0,-1),  3, border),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("RIGHTPADDING", (0,0),(-1,-1), 8),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ]))
    return t

def warn(text): return note(text, WARNBG, AMBER)

def tbl(headers, rows, widths=None):
    w = widths or ([TW/len(headers)]*len(headers))
    data = [[Paragraph(f"<b>{h}</b>", ps("th", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE, leading=11))
             for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), ps("td", fontName="Helvetica", fontSize=8, leading=11, textColor=DARK))
                     for c in row])
    t = Table(data, colWidths=w, repeatRows=1)
    ts = TableStyle([
        ("BACKGROUND",   (0,0),(-1,0),  BLUE),
        ("GRID",         (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",  (0,0),(-1,-1), 5),
        ("RIGHTPADDING", (0,0),(-1,-1), 5),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
    ])
    for i in range(1, len(data)):
        if i % 2 == 0: ts.add("BACKGROUND",(0,i),(-1,i), LIGHTBG)
    t.setStyle(ts)
    return t

def sec(text):  return [Paragraph(text, sH2), HR()]
def h3(text):   return Paragraph(text, sH3)
def h4(text):   return Paragraph(text, sH4)
def body(text): return Paragraph(text, sBody)
def step(n, t): return Paragraph(f"<font color='#005f87'><b>Step {n}</b></font>  {t}", sStep)

def on_page(canv, doc):
    canv.saveState()
    if doc.page > 1:
        canv.setStrokeColor(BLUE); canv.setLineWidth(0.4)
        canv.line(ML, H-MT+5*mm, W-MR, H-MT+5*mm)
        canv.setFont("Helvetica-Bold", 7); canv.setFillColor(BLUE)
        canv.drawString(ML, H-MT+6*mm, "ELK Stack — Linux Desktop Installation Guide")
        canv.setFont("Helvetica", 7); canv.setFillColor(GREY)
        canv.drawRightString(W-MR, H-MT+6*mm, "v1.1  |  ELK 8.13.4")
        canv.setStrokeColor(BORDER)
        canv.line(ML, MB-4*mm, W-MR, MB-4*mm)
        canv.setFont("Helvetica", 7); canv.setFillColor(GREY)
        canv.drawString(ML, MB-8*mm, "2026-06-13")
        canv.drawRightString(W-MR, MB-8*mm, f"Page {doc.page}")
    canv.restoreState()

# ─────────────────────────────────────────────────────────────────────────────
def build():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "elk-linux-desktop-guide.pdf")
    doc = SimpleDocTemplate(out, pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT+8*mm, bottomMargin=MB+8*mm,
        title="ELK Stack Linux Desktop Installation Guide")
    S = []

    # ── COVER ────────────────────────────────────────────────────────────────
    S += [SP(36),
          Paragraph('<font color="#005f87">EL</font><font color="#f5a623">K</font>', sCov1),
          SP(6),
          Paragraph("Linux Desktop Installation Guide", sCov2),
          Paragraph("Elasticsearch · Logstash · Kibana · Filebeat<br/>"
                    "Debian / Ubuntu  |  All-in-one single host  |  ELK 8.13.4", sCov3),
          SP(20)]
    meta = [["ELK Version","8.13.4"], ["OS","Debian 11/12, Ubuntu 22.04/24.04"],
            ["RAM needed","8 GB min (16 GB recommended)"], ["Disk needed","40 GB free"],
            ["Date","2026-06-13"]]
    mt = Table([[Paragraph(f"<b>{r[0]}</b>", ps("mk",fontName="Helvetica-Bold",fontSize=9,textColor=BLUE)),
                 Paragraph(r[1], ps("mv",fontName="Helvetica",fontSize=9,textColor=DARK))]
                for r in meta], colWidths=[45*mm, TW-45*mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),LIGHTBG), ("BACKGROUND",(0,0),(0,-1),HexColor("#d0e4f0")),
        ("GRID",(0,0),(-1,-1),0.4,BORDER), ("LEFTPADDING",(0,0),(-1,-1),8),
        ("RIGHTPADDING",(0,0),(-1,-1),8), ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    S += [mt, PageBreak()]

    # ── 1. ARCHITECTURE ──────────────────────────────────────────────────────
    S += sec("1.  Architecture")
    arch = Preformatted(
        "  Linux Desktop\n"
        "  +-------------------------------------------------------------+\n"
        "  |  /var/log/syslog  \\                                          |\n"
        "  |  /var/log/auth.log >-- Filebeat --> Logstash:5044 --> ES:9200|\n"
        "  |  /var/log/kern.log/    :5066       :5514 :5000               |\n"
        "  |  Docker containers                                            |\n"
        "  |  App log files                        Kibana:5601            |\n"
        "  +-------------------------------------------------------------+",
        ps("arch", fontName="Courier", fontSize=8, leading=11, textColor=DARK,
           backColor=HexColor("#e8eef2"), leftIndent=0))
    S += [arch, SP(8),
          tbl(["Index","Contents","Source"],
              [["syslog-*",      "System + kernel",        "/var/log/syslog, kern.log"],
               ["auth-logs-*",  "SSH, sudo, PAM",          "/var/log/auth.log"],
               ["docker-logs-*","Container stdout/stderr", "Docker socket"],
               ["app-logs-*",   "Nginx, custom apps",      "/var/log/app/"],
               ["journal-logs-*","systemd journal",         "journald"],
               ["misc-logs-*",  "Untagged events",          "Fallthrough"]],
              [35*mm, 52*mm, TW-87*mm]),
          PageBreak()]

    # ── 2. PREREQUISITES ─────────────────────────────────────────────────────
    S += sec("2.  Prerequisites")
    S += [h3("2.1  System checks"),
          code("free -h && df -h / && nproc"),
          h3("2.2  Set vm.max_map_count"),
          code("sudo sysctl -w vm.max_map_count=262144\n"
               'echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf'),
          h3("2.3  Add Elastic APT repository"),
          code("curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch \\\n"
               "  | sudo gpg --dearmor -o /usr/share/keyrings/elastic.gpg\n\n"
               'echo "deb [signed-by=/usr/share/keyrings/elastic.gpg] \\\n'
               '  https://artifacts.elastic.co/packages/8.x/apt stable main" \\\n'
               "  | sudo tee /etc/apt/sources.list.d/elastic-8.x.list\n\n"
               "sudo apt-get update"),
          PageBreak()]

    # ── 3. ELASTICSEARCH ─────────────────────────────────────────────────────
    S += sec("3.  Install Elasticsearch")
    S += [step(1, "Install"),
          code("sudo apt-get install -y elasticsearch=8.13.4\n"
               "sudo apt-mark hold elasticsearch"),
          step(2, "Write clean config  (replaces the entire file)"),
          warn("<b>Important:</b> Elasticsearch 8.x auto-appends a security block to elasticsearch.yml "
               "that enables TLS and references certificate files that do not exist. This causes "
               "an immediate startup failure (exit-code 1). It also adds cluster.initial_master_nodes "
               "which conflicts with discovery.type: single-node. "
               "Use the tee command below to overwrite the whole file cleanly."),
          SP(4),
          code("sudo tee /etc/elasticsearch/elasticsearch.yml > /dev/null << 'EOF'\n"
               "cluster.name: elk-desktop-lab\n"
               "node.name: desktop-node-1\n"
               "\n"
               "path.data: /var/lib/elasticsearch\n"
               "path.logs: /var/log/elasticsearch\n"
               "\n"
               "network.host: 0.0.0.0\n"
               "http.port: 9200\n"
               "\n"
               "discovery.type: single-node\n"
               "\n"
               "xpack.security.enabled: true\n"
               "xpack.security.enrollment.enabled: false\n"
               "xpack.security.http.ssl.enabled: false\n"
               "xpack.security.transport.ssl.enabled: false\n"
               "EOF"),
          step(3, "Set JVM heap  (half of available RAM, max 8g)"),
          code("sudo mkdir -p /etc/elasticsearch/jvm.options.d\n"
               "sudo tee /etc/elasticsearch/jvm.options.d/heap.options > /dev/null << 'EOF'\n"
               "-Xms4g\n"
               "-Xmx4g\n"
               "EOF\n"
               "# For 8 GB machine use -Xms2g / -Xmx2g"),
          step(4, "Start & set elastic password"),
          code("sudo systemctl daemon-reload\n"
               "sudo systemctl enable elasticsearch\n"
               "sudo systemctl start elasticsearch\n\n"
               "# Watch startup (wait for 'started')\n"
               "sudo journalctl -fu elasticsearch\n\n"
               "# Set password — enter: ElkLab@2024 when prompted\n"
               "sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic -i"),
          step(5, "Verify"),
          code("curl -u elastic:ElkLab@2024 http://localhost:9200/_cluster/health?pretty\n"
               '# Expect: "status" : "green"  "number_of_nodes" : 1'),
          PageBreak()]

    # ── 4. LOGSTASH ──────────────────────────────────────────────────────────
    S += sec("4.  Install Logstash")
    S += [step(1, "Install"),
          code("sudo apt-get install -y logstash=1:8.13.4-1\n"
               "sudo apt-mark hold logstash"),
          step(2, "logstash.yml"),
          code("sudo tee /etc/logstash/logstash.yml > /dev/null << 'EOF'\n"
               'http.host: "0.0.0.0"\n'
               "xpack.monitoring.enabled: false\n"
               "config.reload.automatic: true\n"
               "config.reload.interval: 30s\n"
               "pipeline.workers: 2\n"
               "EOF"),
          step(3, "JVM heap"),
          code("# Edit /etc/logstash/jvm.options — find and change:\n"
               "-Xms512m\n"
               "-Xmx1g"),
          step(4, "Create logstash_internal user in Elasticsearch"),
          code("curl -u elastic:ElkLab@2024 -X PUT http://localhost:9200/_security/role/logstash_writer \\\n"
               '  -H "Content-Type: application/json" -d \'{\n'
               '    "cluster":["manage_index_templates","monitor"],\n'
               '    "indices":[{"names":["syslog-*","auth-logs-*","docker-logs-*",\n'
               '      "app-logs-*","journal-logs-*","misc-logs-*"],\n'
               '      "privileges":["write","create_index","create"]}]}\'\n\n'
               "curl -u elastic:ElkLab@2024 -X PUT http://localhost:9200/_security/user/logstash_internal \\\n"
               '  -H "Content-Type: application/json" -d \'{\n'
               '    "password":"LogstashLab@2024","roles":["logstash_writer"]}\''),
          PageBreak()]

    # ── 5. PIPELINES ─────────────────────────────────────────────────────────
    S += sec("5.  Logstash Pipeline Files  (/etc/logstash/conf.d/)")
    S += [note("Hot-reload is enabled — Logstash picks up changes within 30 s. No restart needed after editing."),
          SP(6),
          h3("01-input.conf"),
          code("sudo tee /etc/logstash/conf.d/01-input.conf > /dev/null << 'EOF'\n"
               "input {\n"
               "  beats  { port => 5044 }\n"
               "  tcp    { port => 5000  codec => json  tags => [\"tcp_json\"] }\n"
               "  syslog { port => 5514  tags => [\"syslog_raw\"] }\n"
               "}\n"
               "EOF"),
          h3("10-auth-filter.conf"),
          code("sudo tee /etc/logstash/conf.d/10-auth-filter.conf > /dev/null << 'EOF'\n"
               "filter {\n"
               "  if \"linux_auth\" in [tags] {\n"
               "    grok {\n"
               "      match => { \"message\" => \"%{SYSLOGTIMESTAMP:ts} %{SYSLOGHOST:hn}\"\n"
               "        \" %{DATA:proc}(?:\\[%{POSINT:pid}\\])?: %{GREEDYDATA:msg}\" }\n"
               "    }\n"
               "    date   { match => [\"ts\",\"MMM  d HH:mm:ss\",\"MMM dd HH:mm:ss\"]\n"
               "             target => \"@timestamp\" }\n"
               "    mutate { rename => { \"proc\" => \"[process][name]\"  \"msg\" => \"message\" } }\n"
               "    if [message] =~ /Accepted (password|publickey)/ {\n"
               "      mutate { add_tag => [\"ssh_login_success\"] } }\n"
               "    if [message] =~ /Failed password/ {\n"
               "      mutate { add_tag => [\"ssh_login_failure\"] } }\n"
               "    if [message] =~ /sudo.*COMMAND/ {\n"
               "      mutate { add_tag => [\"sudo_command\"] } }\n"
               "  }\n"
               "}\n"
               "EOF"),
          h3("20-syslog-filter.conf"),
          code("sudo tee /etc/logstash/conf.d/20-syslog-filter.conf > /dev/null << 'EOF'\n"
               "filter {\n"
               "  if \"syslog\" in [tags] or \"syslog_raw\" in [tags] {\n"
               "    grok {\n"
               "      match => { \"message\" => \"%{SYSLOGTIMESTAMP:ts} %{SYSLOGHOST:hn}\"\n"
               "        \" %{DATA:proc}(?:\\[%{POSINT:pid}\\])?: %{GREEDYDATA:msg}\" }\n"
               "    }\n"
               "    date   { match => [\"ts\",\"MMM  d HH:mm:ss\",\"MMM dd HH:mm:ss\"]\n"
               "             target => \"@timestamp\" }\n"
               "    mutate { rename => { \"msg\" => \"message\"  \"proc\" => \"[process][name]\" } }\n"
               "    if [process][name] in [\"sshd\",\"sudo\",\"su\",\"login\",\"passwd\"] {\n"
               "      mutate { add_tag => [\"linux_auth\"] } }\n"
               "  }\n"
               "}\n"
               "EOF"),
          h3("30-docker-filter.conf"),
          code("sudo tee /etc/logstash/conf.d/30-docker-filter.conf > /dev/null << 'EOF'\n"
               "filter {\n"
               "  if \"docker_log\" in [tags] {\n"
               "    mutate { add_field => { \"[event][dataset]\" => \"docker\" } }\n"
               "    if [message] =~ /^\\{/ {\n"
               "      json { source => \"message\"  target => \"parsed\"\n"
               "             skip_on_invalid_json => true }\n"
               "    }\n"
               "  }\n"
               "}\n"
               "EOF"),
          h3("99-output.conf"),
          code("sudo tee /etc/logstash/conf.d/99-output.conf > /dev/null << 'EOF'\n"
               "output {\n"
               "  if \"linux_auth\" in [tags] {\n"
               "    elasticsearch { hosts => [\"http://localhost:9200\"]\n"
               "      user => \"logstash_internal\"  password => \"LogstashLab@2024\"\n"
               "      index => \"auth-logs-%{+YYYY.MM.dd}\" }\n"
               "  } else if \"syslog\" in [tags] or \"kernel_event\" in [tags] {\n"
               "    elasticsearch { hosts => [\"http://localhost:9200\"]\n"
               "      user => \"logstash_internal\"  password => \"LogstashLab@2024\"\n"
               "      index => \"syslog-%{+YYYY.MM.dd}\" }\n"
               "  } else if \"docker_log\" in [tags] {\n"
               "    elasticsearch { hosts => [\"http://localhost:9200\"]\n"
               "      user => \"logstash_internal\"  password => \"LogstashLab@2024\"\n"
               "      index => \"docker-logs-%{+YYYY.MM.dd}\" }\n"
               "  } else if \"journal\" in [tags] {\n"
               "    elasticsearch { hosts => [\"http://localhost:9200\"]\n"
               "      user => \"logstash_internal\"  password => \"LogstashLab@2024\"\n"
               "      index => \"journal-logs-%{+YYYY.MM.dd}\" }\n"
               "  } else if \"app_log\" in [tags] {\n"
               "    elasticsearch { hosts => [\"http://localhost:9200\"]\n"
               "      user => \"logstash_internal\"  password => \"LogstashLab@2024\"\n"
               "      index => \"app-logs-%{+YYYY.MM.dd}\" }\n"
               "  } else {\n"
               "    elasticsearch { hosts => [\"http://localhost:9200\"]\n"
               "      user => \"logstash_internal\"  password => \"LogstashLab@2024\"\n"
               "      index => \"misc-logs-%{+YYYY.MM.dd}\" }\n"
               "  }\n"
               "}\n"
               "EOF"),
          h3("Test + start"),
          code("sudo -u logstash /usr/share/logstash/bin/logstash \\\n"
               "  --path.settings /etc/logstash --config.test_and_exit\n\n"
               "sudo systemctl start logstash"),
          PageBreak()]

    # ── 6. KIBANA ────────────────────────────────────────────────────────────
    S += sec("6.  Install Kibana")
    S += [step(1, "Install"),
          code("sudo apt-get install -y kibana=8.13.4\n"
               "sudo apt-mark hold kibana"),
          step(2, "kibana.yml"),
          code("sudo tee /etc/kibana/kibana.yml > /dev/null << 'EOF'\n"
               "server.port: 5601\n"
               'server.host: "0.0.0.0"\n'
               'server.name: "elk-desktop"\n'
               'elasticsearch.hosts: ["http://localhost:9200"]\n'
               'elasticsearch.username: "kibana_system"\n'
               'elasticsearch.password: "KibanaLab@2024"\n'
               "EOF"),
          step(3, "Set kibana_system password"),
          code("curl -u elastic:ElkLab@2024 -X POST \\\n"
               "  http://localhost:9200/_security/user/kibana_system/_password \\\n"
               '  -H "Content-Type: application/json" \\\n'
               "  -d '{\"password\":\"KibanaLab@2024\"}'"),
          step(4, "Start"),
          code("sudo systemctl enable kibana && sudo systemctl start kibana\n"
               "sudo journalctl -fu kibana   # wait for: 'Kibana is now available'"),
          note("URL: http://localhost:5601   Login: elastic / ElkLab@2024"),
          PageBreak()]

    # ── 7. FILEBEAT ──────────────────────────────────────────────────────────
    S += sec("7.  Install Filebeat")
    S += [step(1, "Install"),
          code("sudo apt-get install -y filebeat=8.13.4\n"
               "sudo apt-mark hold filebeat"),
          step(2, "filebeat.yml"),
          code("sudo tee /etc/filebeat/filebeat.yml > /dev/null << 'EOF'\n"
               "filebeat.inputs:\n\n"
               "  - type: log\n"
               "    enabled: true\n"
               "    paths: [/var/log/syslog, /var/log/messages]\n"
               "    tags: [\"syslog\"]\n"
               "    fields: { log_type: syslog, host_type: linux-desktop }\n\n"
               "  - type: log\n"
               "    enabled: true\n"
               "    paths: [/var/log/auth.log, /var/log/secure]\n"
               "    tags: [\"linux_auth\"]\n"
               "    fields: { log_type: auth, host_type: linux-desktop }\n\n"
               "  - type: log\n"
               "    enabled: true\n"
               "    paths: [/var/log/kern.log]\n"
               "    tags: [\"syslog\", \"kernel_event\"]\n"
               "    fields: { log_type: kernel }\n\n"
               "  - type: log\n"
               "    enabled: true\n"
               "    paths: [/var/log/nginx/*.log, /var/log/apache2/*.log, /var/log/app/*.log]\n"
               "    tags: [\"app_log\"]\n"
               "    ignore_older: 24h\n\n"
               "  - type: container\n"
               "    enabled: true\n"
               "    paths: [/var/lib/docker/containers/*/*.log]\n"
               "    stream: all\n"
               "    tags: [\"docker_log\"]\n"
               "    processors:\n"
               "      - add_docker_metadata:\n"
               '          host: "unix:///var/run/docker.sock"\n\n'
               "  - type: journald\n"
               "    enabled: true\n"
               "    id: journald-local\n"
               "    tags: [\"journal\"]\n\n"
               "processors:\n"
               "  - add_host_metadata:\n"
               "      when.not.contains.tags: forwarded\n\n"
               "output.logstash:\n"
               '  hosts: ["localhost:5044"]\n\n'
               "setup.kibana:\n"
               '  host: "localhost:5601"\n'
               '  username: "elastic"\n'
               '  password: "ElkLab@2024"\n\n'
               "logging.level: info\n"
               "logging.to_files: false\n"
               "EOF"),
          step(3, "Fix permissions + groups"),
          code("sudo chmod go-w /etc/filebeat/filebeat.yml\n"
               "sudo chown root:root /etc/filebeat/filebeat.yml\n"
               "sudo usermod -aG docker filebeat\n"
               "sudo usermod -aG adm filebeat"),
          step(4, "Test + start"),
          code("sudo filebeat test config -c /etc/filebeat/filebeat.yml\n"
               "sudo filebeat test output -c /etc/filebeat/filebeat.yml\n"
               "sudo systemctl enable filebeat && sudo systemctl start filebeat"),
          PageBreak()]

    # ── 8. KIBANA INDEX PATTERNS ──────────────────────────────────────────────
    S += sec("8.  Kibana — Index Patterns")
    S += [body("Run once after Kibana is up:"),
          code('for P in "auth-logs-*" "syslog-*" "docker-logs-*" \\\n'
               '         "app-logs-*" "journal-logs-*" "misc-logs-*"; do\n'
               '  curl -s -u elastic:ElkLab@2024 \\\n'
               '    -X POST http://localhost:5601/api/data_views/data_view \\\n'
               '    -H "kbn-xsrf: true" -H "Content-Type: application/json" \\\n'
               '    -d "{\\"data_view\\":{\\"title\\":\\"$P\\",\\"timeFieldName\\":\\"@timestamp\\"}}"\n'
               '  echo " Created: $P"\n'
               'done'),
          SP(6),
          tbl(["Pattern","Time Field","Use for"],
              [["auth-logs-*",   "@timestamp","SSH logins, sudo, PAM"],
               ["syslog-*",      "@timestamp","System + kernel events"],
               ["docker-logs-*", "@timestamp","Container stdout/stderr"],
               ["app-logs-*",    "@timestamp","Nginx, custom apps"],
               ["journal-logs-*","@timestamp","systemd journal"],
               ["misc-logs-*",   "@timestamp","Unmatched events"]],
              [42*mm, 34*mm, TW-76*mm]),
          PageBreak()]

    # ── 9. VERIFY ─────────────────────────────────────────────────────────────
    S += sec("9.  Verify")
    S += [h3("All services running"),
          code("for s in elasticsearch logstash kibana filebeat; do\n"
               "  printf '  %-18s %s\\n' $s $(systemctl is-active $s)\n"
               "done"),
          h3("Indices have data"),
          code('curl -s -u elastic:ElkLab@2024 \\\n'
               '  "http://localhost:9200/_cat/indices?h=index,docs.count,health&s=index&v"'),
          h3("Trigger a test event"),
          code("sudo ls /root          # generates a sudo event\n\n"
               "# Check it arrived (wait 15 s):\n"
               "curl -s -u elastic:ElkLab@2024 \\\n"
               '  "http://localhost:9200/auth-logs-*/_count?q=tags:sudo_command"'),
          PageBreak()]

    # ── 10. DASHBOARDS ───────────────────────────────────────────────────────
    S += sec("10.  Kibana Dashboards  (manual — Lens editor)")
    S += [body("Path: Analytics -> Dashboards -> Create dashboard -> Create visualization"),
          SP(4),
          h3("Authentication & Security  (auth-logs-*)"),
          tbl(["Panel","Chart","X / Group by","Y / Metric","KQL Filter"],
              [["Login timeline",        "Area",      "@timestamp",           "Count",  "tags: linux_auth"],
               ["SSH success/failure",   "Pie",       "top values: tags",     "Count",  "tags: ssh_login_success OR tags: ssh_login_failure"],
               ["Top failed IPs",        "Horiz bar", "top values: message",  "Count",  "tags: ssh_login_failure"],
               ["sudo commands",         "Table",     "top values: message",  "Count",  "tags: sudo_command"],
               ["Failed logins (count)", "Metric",    "—",                    "Count",  "tags: ssh_login_failure"]],
              [32*mm, 22*mm, 40*mm, 24*mm, TW-118*mm]),
          SP(8),
          h3("System Overview  (syslog-*)"),
          tbl(["Panel","Chart","X / Group by","Y / Metric","KQL Filter"],
              [["Log volume",      "Area",      "@timestamp",              "Count", ""],
               ["Top processes",   "Horiz bar", "top values: process.name","Count", ""],
               ["Kernel events",   "Bar",       "@timestamp",              "Count", "tags: kernel_event"],
               ["Error count",     "Metric",    "—",                       "Count", "message: *error*"]],
              [32*mm, 22*mm, 42*mm, 24*mm, TW-120*mm]),
          SP(8),
          h3("Docker  (docker-logs-*)"),
          tbl(["Panel","Chart","X / Group by","Y / Metric","KQL Filter"],
              [["Logs per container", "Horiz bar","top values: service.name","Count",""],
               ["Error spike",        "Bar",      "@timestamp",              "Count","message: *error* OR message: *ERROR*"],
               ["Recent errors",      "Table",    "@timestamp, service.name, message","—","message: *error*"]],
              [32*mm, 22*mm, 52*mm, 24*mm, TW-130*mm]),
          SP(8),
          h3("Journal & Services  (journal-logs-*)"),
          tbl(["Panel","Chart","X / Group by","Y / Metric","KQL Filter"],
              [["Failed services", "Metric",    "—",                         "Count",'message: "failed"'],
               ["Top units",       "Horiz bar", "top values: systemd.unit",  "Count",""],
               ["Failed units",    "Table",     "@timestamp, systemd.unit, message","—",'message: "failed"']],
              [32*mm, 22*mm, 52*mm, 24*mm, TW-130*mm]),
          PageBreak()]

    # ── 11. ALERTS ───────────────────────────────────────────────────────────
    S += sec("11.  Alert Rules  (Stack Management -> Rules -> Create rule)")
    S += [body("Rule type: <b>Elasticsearch query</b>  |  Check every: <b>1 min</b>  |  Action: Server log (no setup needed)"),
          SP(6),
          tbl(["Rule Name","Index","KQL Query","Threshold","Window","Severity"],
              [
               ["SSH Brute Force",      "auth-logs-*",   "tags: ssh_login_failure",                    "> 5 matches",  "5 min",  "Critical"],
               ["Root Login",           "auth-logs-*",   "tags: ssh_login_success AND message: *root*","any match",    "1 min",  "Critical"],
               ["Excessive sudo",       "auth-logs-*",   "tags: sudo_command",                         "> 10 matches", "10 min", "High"],
               ["New User Created",     "syslog-*",      "message: *useradd* OR message: *adduser*",   "any match",    "5 min",  "High"],
               ["Service Failure",      "journal-logs-*",'message: "failed"',                          "any match",    "2 min",  "Medium"],
               ["Docker Error Spike",   "docker-logs-*", "message: *error* OR message: *ERROR*",       "> 20 matches", "5 min",  "Medium"],
               ["Grok Parse Failures",  "*-logs-*",      "tags: _grokparsefailure",                    "> 10 matches", "10 min", "Low"],
              ],
              [38*mm, 24*mm, 54*mm, 22*mm, 14*mm, TW-152*mm]),
          SP(10),
          h3("Steps to create a rule"),
          tbl(["Step","Action"],
              [["1","Stack Management -> Rules -> Create rule"],
               ["2","Name the rule  (e.g. SSH Brute Force)"],
               ["3","Rule type: Elasticsearch query"],
               ["4","Index: as shown in table above"],
               ["5","KQL query: paste from table above"],
               ["6","Threshold and window: as shown in table above"],
               ["7","Check every: 1 minute"],
               ["8","Actions -> Server log (always available, no connector setup needed)"],
               ["9","Save  — rule activates immediately"]],
              [10*mm, TW-10*mm]),
          SP(8),
          h3("View fired alerts"),
          body("Stack Management -> Rules -> click rule name -> Alerts tab. "
               "Shows: start time, duration, status (Active / Recovered)."),
          PageBreak()]

    # ── 12. TROUBLESHOOTING ──────────────────────────────────────────────────
    S += sec("12.  Troubleshooting")

    S += [h3("Elasticsearch — exit-code 1 / FAILURE on startup"),
          body("Read the actual error first:"),
          code("sudo journalctl -u elasticsearch --no-pager -n 60"),
          SP(4),
          tbl(["Error in journal","Cause","Fix"],
              [
               ["certs/http.p12 does not exist\nSSL keystore not found",
                "Auto-generated TLS block in yml references cert files that don't exist",
                "Replace elasticsearch.yml with the clean config from Section 3 Step 2"],
               ["cluster.initial_master_nodes is not allowed\nwith discovery.type single-node",
                "Auto-generated block added cluster.initial_master_nodes",
                "Remove that line OR use the clean config from Section 3 Step 2"],
               ["max virtual memory areas too low",
                "vm.max_map_count below 262144",
                "sudo sysctl -w vm.max_map_count=262144"],
               ["OutOfMemoryError / Cannot allocate",
                "JVM heap too large for available RAM",
                "Reduce -Xms / -Xmx in jvm.options.d/heap.options"],
               ["No space left on device",
                "Disk > 95% full",
                "Free space on /var/lib/elasticsearch"],
              ],
              [55*mm, 52*mm, TW-107*mm]),
          SP(6),
          h3("Logstash fails to load pipeline"),
          code("sudo -u logstash /usr/share/logstash/bin/logstash \\\n"
               "  --path.settings /etc/logstash --config.test_and_exit"),
          warn("Logstash config does NOT support semicolons as separators. "
               "Wrong: tcp { port => 5000; codec => json }  "
               "Correct: each setting on its own line."),
          SP(6),
          h3("Filebeat not connecting"),
          code("sudo filebeat test output -c /etc/filebeat/filebeat.yml\n"
               "nc -zv localhost 5044\n"
               "ls -la /etc/filebeat/filebeat.yml   # must not be world-writable"),
          SP(6),
          h3("No data in Kibana"),
          code("# 1. Check indices exist\n"
               "curl -s -u elastic:ElkLab@2024 'http://localhost:9200/_cat/indices?v'\n\n"
               "# 2. Check Logstash event count\n"
               "curl -s http://localhost:9600/_node/stats | grep '\"in\"'\n\n"
               "# 3. Set Kibana time range to 'Last 1 hour'\n\n"
               "# 4. Check misc-logs-* for unmatched events\n"
               "curl -s -u elastic:ElkLab@2024 \\\n"
               "  'http://localhost:9200/misc-logs-*/_count'"),
          SP(6),
          h3("Quick health check"),
          code("for s in elasticsearch logstash kibana filebeat; do\n"
               "  printf '  %-18s %s\\n' $s $(systemctl is-active $s)\n"
               "done\n\n"
               "curl -s -u elastic:ElkLab@2024 'http://localhost:9200/_cluster/health' \\\n"
               "  | python3 -c \"import sys,json; h=json.load(sys.stdin); \\\n"
               "    print(f'ES: {h[\\\"status\\\"]}  shards={h[\\\"active_shards\\\"]}')\""),
          PageBreak()]

    # ── CREDENTIALS ──────────────────────────────────────────────────────────
    S += sec("Credentials")
    S += [tbl(["Account","Username","Password","Used For"],
              [["Elasticsearch superuser", "elastic",           "ElkLab@2024",       "Kibana login, API"],
               ["Kibana system user",      "kibana_system",     "KibanaLab@2024",     "Kibana -> ES connection"],
               ["Logstash writer",         "logstash_internal", "LogstashLab@2024",   "Logstash -> ES indexing"]],
              [44*mm, 38*mm, 38*mm, TW-120*mm]),
          SP(8),
          warn("Change all passwords before using on a shared or public network."),
          SP(20),
          HR(),
          SP(4),
          Paragraph("ELK Stack Linux Desktop Guide  v1.1  |  2026-06-13  |  ELK 8.13.4", sSmall)]

    doc.build(S, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Done -> {out}")

if __name__ == "__main__":
    build()
