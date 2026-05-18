#!/usr/bin/env python3
"""
publicar_remoto.py — versão para agente remoto.

Lê dados de arquivos JSON pré-gerados (pelo agente via BigQuery MCP),
gera os HTMLs de efetividade/esforço/meta e publica no GitHub Pages.

Uso:
  python3 publicar_remoto.py --data-dir /tmp/dados --github-token TOKEN
"""

import argparse, base64, json, math, os, re, sys, urllib.request, urllib.error
from datetime import date, datetime, timedelta

PROJECT  = "lakehouse-378716"
REPO     = "biancamoura-ctrl/dashboards-efetividade"
URL_SITE = "https://biancamoura-ctrl.github.io/dashboards-efetividade/"

GCHAT_WEBHOOK = (
    "https://chat.googleapis.com/v1/spaces/AAQA7_JxW0Q/messages"
    "?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
    "&token=EVtinsoiO-x4whqjad4FduZ1t-f3LbcmStRWPCLF-TM"
)

TEAM = {
    "mariana.santana@estantemagica.com.br":           {"nome": "Mariana Santana",              "cargo": "Analista",    "segmento": "Premium touch",            "lideranca": "Carine Leite"},
    "talita.panassol@estantemagica.com.br":           {"nome": "Talita Panassol",              "cargo": "Analista",    "segmento": "Premium touch",            "lideranca": "Carine Leite"},
    "carla.gomes@estantemagica.com.br":               {"nome": "Carla Ferraz Gomes",           "cargo": "Analista",    "segmento": "Premium touch",            "lideranca": "Carine Leite"},
    "carine.leite@estantemagica.com.br":              {"nome": "Carine Leite",                 "cargo": "Coordenação", "segmento": "Premium touch",            "lideranca": "Mahane"},
    "julia.loubach@estantemagica.com.br":             {"nome": "Julia Loubach",                "cargo": "Supervisor",  "segmento": "Premium touch 40+",        "lideranca": "Carine Leite"},
    "maria.elvira@estantemagica.com.br":              {"nome": "Maria Elvira",                 "cargo": "Analista",    "segmento": "Premium touch 40+",        "lideranca": "Carine Leite"},
    "erick.andrade@estantemagica.com.br":             {"nome": "Erick Andrade",                "cargo": "Analista",    "segmento": "High touch - Novas",       "lideranca": "Julia Alves"},
    "mariaeduarda.carvalho@estantemagica.com.br":     {"nome": "Maria Eduarda Carvalho",       "cargo": "Analista",    "segmento": "High touch - Novas",       "lideranca": "Mahane"},
    "moreno.loss@estantemagica.com.br":               {"nome": "Moreno Loss",                  "cargo": "Analista",    "segmento": "High touch - Novas",       "lideranca": "Emília Alves"},
    "renata.brandao@estantemagica.com.br":            {"nome": "Renata Brandão",               "cargo": "Analista",    "segmento": "High touch - Novas",       "lideranca": "Emília Alves"},
    "andreina.ferreira@estantemagica.com.br":         {"nome": "Andreina Ferreira",            "cargo": "Estagiário",  "segmento": "High touch - Novas",       "lideranca": "Mahane"},
    "julia.cordeiro@estantemagica.com.br":            {"nome": "Julia Cordeiro Campos",        "cargo": "Estagiário",  "segmento": "High touch - Novas",       "lideranca": "Mahane"},
    "laura.pagliuzo@estantemagica.com.br":            {"nome": "Laura Pagliuzo",               "cargo": "Estagiário",  "segmento": "High touch - Novas",       "lideranca": "Mahane"},
    "indlayse.ferreira@estantemagica.com.br":         {"nome": "Indy Ferreira",                "cargo": "Analista",    "segmento": "High touch - Renovação",   "lideranca": "Julia Loubach"},
    "thayna.bastos@estantemagica.com.br":             {"nome": "Thayná Bastos",                "cargo": "Analista",    "segmento": "High touch - Renovação",   "lideranca": "Julia Loubach"},
    "larissa.freitas@estantemagica.com.br":           {"nome": "Larissa Freitas Monteiro",     "cargo": "Analista",    "segmento": "High touch - Renovação",   "lideranca": "Julia Loubach"},
    "tatiana.portela@estantemagica.com.br":           {"nome": "Tatiana Portela",              "cargo": "Analista",    "segmento": "High touch - Renovação",   "lideranca": "Julia Loubach"},
    "shelry.solart@estantemagica.com.br":             {"nome": "Shelry Solart",                "cargo": "Estagiário",  "segmento": "High touch - Renovação",   "lideranca": "Julia Loubach"},
    "helena.cabral@estantemagica.com.br":             {"nome": "Helena Cabral Sampaio",        "cargo": "Estagiário",  "segmento": "High touch - Renovação",   "lideranca": "Julia Loubach"},
    "carla.santosdasilva@estantemagica.com.br":       {"nome": "Carla Santos da Silva",        "cargo": "—",           "segmento": "High touch - Renovação",   "lideranca": "Larissa Garcia"},
    "pamela.miranda@estantemagica.com.br":            {"nome": "Pâmela Miranda",               "cargo": "Estagiário",  "segmento": "Medium touch - Renovação", "lideranca": "Larissa Garcia"},
    "anaclara.peres@estantemagica.com.br":            {"nome": "Ana Clara Peres dos Santos",   "cargo": "Estagiário",  "segmento": "Medium touch - Renovação", "lideranca": "Larissa Garcia"},
    "anaclaudia.almeida@estantemagica.com.br":        {"nome": "Ana Cláudia Santos de Almeida","cargo": "Estagiário",  "segmento": "Medium touch - Renovação", "lideranca": "Larissa Garcia"},
    "viviancristina.souza@estantemagica.com.br":      {"nome": "Vivian Cristina",              "cargo": "Estagiário",  "segmento": "Medium touch - Renovação", "lideranca": "Larissa Garcia"},
    "kaian.silva@estantemagica.com.br":               {"nome": "Kaian Luís",                   "cargo": "Estagiário",  "segmento": "Medium touch - Renovação", "lideranca": "Larissa Garcia"},
    "claudilene.dias@estantemagica.com.br":           {"nome": "Claudilene Santos Dias",       "cargo": "Estagiário",  "segmento": "Medium touch - Renovação", "lideranca": "Larissa Garcia"},
    "stefany.figueredo@estantemagica.com.br":         {"nome": "Stefany Soares Figueredo",     "cargo": "Estagiário",  "segmento": "Medium touch - Renovação", "lideranca": "Larissa Garcia"},
    "giovanna.munhoz@estantemagica.com.br":           {"nome": "Giovanna Munhoz",              "cargo": "Estagiário",  "segmento": "Medium touch - Renovação", "lideranca": "Julia Loubach"},
    "mariaclara.lima@estantemagica.com.br":           {"nome": "Maria Clara Araujo Lima",      "cargo": "Estagiário",  "segmento": "Backup",                   "lideranca": "Larissa Garcia"},
    "thais.borges@estantemagica.com.br":              {"nome": "Thais Souza",                  "cargo": "Estagiário",  "segmento": "Backup",                   "lideranca": "—"},
    "sarah.moura@estantemagica.com.br":               {"nome": "Sarah Moura",                  "cargo": "Analista",    "segmento": "Redes",                    "lideranca": "Julia Loubach"},
    "jennifer.anjos@estantemagica.com.br":            {"nome": "Jennifer dos Anjos",           "cargo": "Estagiário",  "segmento": "SEDUC",                    "lideranca": "Larissa Garcia"},
    "veronicacristina.carvalho@estantemagica.com.br": {"nome": "Verônica Carvalho",            "cargo": "Estagiário",  "segmento": "Squad Confirmação",        "lideranca": "Julia Alves"},
    "agatha.cruz@estantemagica.com.br":               {"nome": "Ágatha de Moura Fernandes Cruz","cargo": "Estagiário", "segmento": "Squad Reagendamento",      "lideranca": "Julia Alves"},
    "junior.gomes@estantemagica.com.br":              {"nome": "Junior Gomes",                 "cargo": "Estagiário",  "segmento": "Squad Reagendamento",      "lideranca": "Julia Alves"},
    "mariana.mazzero@estantemagica.com.br":           {"nome": "Mariana Mazzero",              "cargo": "Estagiário",  "segmento": "Squad Reagendamento",      "lideranca": "Julia Alves"},
    "paula.valero@estantemagica.com.br":              {"nome": "Paula Valero",                 "cargo": "Supervisor",  "segmento": "México",                   "lideranca": "Carine Leite"},
    "alixibeth.cardiel@estantemagica.com.br":         {"nome": "Alixibeth Cardiel",            "cargo": "Analista",    "segmento": "México",                   "lideranca": "Paula Valero"},
    "daniela.rojas@estantemagica.com.br":             {"nome": "Daniela Rojas",                "cargo": "Analista",    "segmento": "México",                   "lideranca": "Paula Valero"},
    "nioximar.villael@estantemagica.com.br":          {"nome": "Nioximar Villael",             "cargo": "Analista",    "segmento": "México",                   "lideranca": "Paula Valero"},
    "nerbis.carrero@estantemagica.com.br":            {"nome": "Nerbis Carrero",               "cargo": "Analista",    "segmento": "México",                   "lideranca": "Paula Valero"},
    "rubia.toledo@estantemagica.com.br":              {"nome": "Rúbia Toledo",                 "cargo": "Analista",    "segmento": "México",                   "lideranca": "Paula Valero"},
    "clarice.silva@estantemagica.com.br":             {"nome": "Clarice Silva",                "cargo": "Analista",    "segmento": "México",                   "lideranca": "Maria Fuhr"},
    "genesis.ramos@estantemagica.com.br":             {"nome": "Génesis Ramos",                "cargo": "Analista",    "segmento": "México",                   "lideranca": "Maria Fuhr"},
    "victoria.correa@estantemagica.com.br":           {"nome": "Victoria Correa",              "cargo": "Analista",    "segmento": "México",                   "lideranca": "Maria Fuhr"},
    "erica.fernandez@estantemagica.com.br":           {"nome": "Erica Fernández",              "cargo": "Analista",    "segmento": "México",                   "lideranca": "Maria Fuhr"},
    "julia.alves@estantemagica.com.br":               {"nome": "Julia Alves",                  "cargo": "Supervisor",  "segmento": "—",                        "lideranca": "Mahane"},
    "larissa.garcia@estantemagica.com.br":            {"nome": "Larissa Garcia",               "cargo": "Supervisor",  "segmento": "—",                        "lideranca": "Carine Leite"},
    "emilia.alves@estantemagica.com.br":              {"nome": "Emília Alves",                 "cargo": "Supervisor",  "segmento": "High touch - Novas",       "lideranca": "Mahane"},
    "maria.fuhr@estantemagica.com.br":                {"nome": "Maria Fuhr",                   "cargo": "Supervisor",  "segmento": "México",                   "lideranca": "Carine Leite"},
    "mahane@estantemagica.com.br":                    {"nome": "Mahane",                       "cargo": "Coordenação", "segmento": "—",                        "lideranca": "Luiz Eduardo"},
}

# ─── Carregamento de dados ─────────────────────────────────────────────────────

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dia_util_anterior(d):
    delta = 3 if d.weekday() == 0 else 1
    return d - timedelta(days=delta)


def email_to_name(email):
    if email in TEAM:
        return TEAM[email]["nome"]
    PARTICLES = {"da", "de", "do", "das", "dos", "e"}
    prefix = email.split("@")[0]
    parts = prefix.replace("-", ".").split(".")
    return " ".join(p if p.lower() in PARTICLES else p.capitalize() for p in parts)


def parse_efetividade(rows):
    result = []
    for row in rows:
        n_atv        = int(row.get("total_atividades") or 0)
        n_ef         = int(row.get("total_efetivas") or 0)
        esc_atv      = int(row.get("escolas_com_atividade") or 0)
        esc_ef       = int(row.get("escolas_com_ativ_efetiva") or 0)
        prazo        = int(row.get("escolas_com_prazo") or 0)
        abord        = int(row.get("abordadas_prazo") or 0)
        esc_ef_prazo = int(row.get("escolas_efetivas_prazo") or 0)
        tasks        = int(row.get("total_tasks") or 0)
        conc         = int(row.get("total_tasks_conc") or 0)
        cart         = int(row.get("carteira") or 0)
        pef     = round(esc_ef_prazo / prazo * 100, 1) if prazo > 0 else 0.0
        pab     = round(abord / prazo * 100, 1) if prazo > 0 else 0.0
        pct_esc = round(esc_ef / esc_atv * 100, 1) if esc_atv > 0 else 0.0
        quad = ("q1" if n_atv >= 50 and pef >= 50 else
                "q2" if n_atv >= 50 and pef < 50  else
                "q3" if n_atv < 50  and pef >= 50 else "q4")
        email = row.get("email", "")
        t = TEAM.get(email, {})
        result.append({
            "email": email, "nome": t.get("nome") or email_to_name(email),
            "lideranca": t.get("lideranca", ""), "segmento": t.get("segmento", ""),
            "cargo": t.get("cargo", ""),
            "atv": n_atv, "ef": esc_ef_prazo, "pef": pef, "pab": pab,
            "tasks": tasks, "conc": conc, "cart": cart, "prazo": prazo,
            "esc_atv": esc_atv, "esc_ef": esc_ef, "pct_ef_esc": pct_esc, "quad": quad,
        })
    return result


def parse_efetividade_total(row):
    if isinstance(row, list):
        row = row[0]
    elegiveis = int(row.get("elegiveis") or 0)
    efetivas  = int(row.get("efetivas_prazo") or 0)
    pef       = round(efetivas / elegiveis * 100, 1) if elegiveis > 0 else 0.0
    return {"elegiveis": elegiveis, "efetivas": efetivas, "pef": pef}


def parse_esforco(rows):
    result = {}
    for row in rows:
        email = row.get("email", "")
        result[email] = {
            "deals_tocados": int(row.get("deals_tocados") or 0),
            "total_atv":     int(row.get("total_atv") or 0),
            "n_whatsapp":    int(row.get("n_whatsapp") or 0),
            "n_chamada":     int(row.get("n_chamada") or 0),
            "n_reuniao":     int(row.get("n_reuniao") or 0),
            "n_email":       int(row.get("n_email") or 0),
            "n_neg":         int(row.get("n_neg") or 0),
            "n_pos":         int(row.get("n_pos") or 0),
        }
    return result


def parse_canal_mix(rows):
    out = {"efetivos": {}, "nao_efetivos": {}}
    for row in rows:
        virou = row.get("virou")
        if virou is True or str(virou).lower() in ("true", "1"):
            key = "efetivos"
        else:
            key = "nao_efetivos"
        n_wh = int(row.get("n_whatsapp") or 0)
        n_ch = int(row.get("n_chamada") or 0)
        n_re = int(row.get("n_reuniao") or 0)
        n_em = int(row.get("n_email") or 0)
        total = n_wh + n_ch + n_re + n_em
        def pct(n): return round(n / total * 100) if total > 0 else 0
        out[key] = {
            "n_deals": int(row.get("n_deals") or 0), "total": total,
            "n_whatsapp": n_wh, "pct_whatsapp": pct(n_wh),
            "n_chamada":  n_ch, "pct_chamada":  pct(n_ch),
            "n_reuniao":  n_re, "pct_reuniao":  pct(n_re),
            "n_email":    n_em, "pct_email":    pct(n_em),
        }
    return out


def parse_carteira_total(rows):
    return {row.get("email", ""): int(row.get("carteira_total") or 0) for row in rows}


def parse_base_cruzada(rows):
    result = {}
    for row in rows:
        quem_raw = row.get("quem_tocou") or []
        if isinstance(quem_raw, str):
            try:
                quem_raw = json.loads(quem_raw)
            except Exception:
                quem_raw = [q.strip() for q in quem_raw.split(",") if q.strip()]
        result[row.get("consultor_dono", "")] = {
            "total":   int(row.get("total_base") or 0),
            "tocadas": int(row.get("ja_tocadas_hoje") or 0),
            "quem":    list(quem_raw),
        }
    return result


def build_comparison(hoje, ontem):
    ontem_map = {r["email"]: r for r in ontem}
    comp = []
    for h in hoje:
        o = ontem_map.get(h["email"])
        if o is None:
            comp.append({"nome": h["nome"], "quad_hoje": h["quad"], "quad_ontem": None,
                         "pef_hoje": h["pef"], "pef_ontem": None, "atv_hoje": h["atv"],
                         "atv_ontem": None, "delta_ef": None, "delta_atv": None, "tendencia": "novo"})
        else:
            delta_ef  = round(h["pef"] - o["pef"], 1)
            delta_atv = h["atv"] - o["atv"]
            tendencia = "melhorou" if delta_ef > 2 else "piorou" if delta_ef < -2 else "manteve"
            comp.append({"nome": h["nome"], "quad_hoje": h["quad"], "quad_ontem": o["quad"],
                         "pef_hoje": h["pef"], "pef_ontem": o["pef"], "atv_hoje": h["atv"],
                         "atv_ontem": o["atv"], "delta_ef": delta_ef, "delta_atv": delta_atv,
                         "tendencia": tendencia})
    return comp


def diagnostico(ef_row, esf):
    if esf is None or esf["total_atv"] == 0:
        return "não fez atividade ontem"
    tot   = esf["total_atv"]
    dt    = esf["deals_tocados"]
    cart  = ef_row["cart"]
    cob   = f"{dt}/{cart}" if cart > 0 else str(dt)
    pct_c = round(esf["n_chamada"] / tot * 100) if tot > 0 else 0
    pct_w = round(esf["n_whatsapp"] / tot * 100) if tot > 0 else 0
    parts = [f"{pct_c}% chamada · {pct_w}% WhatsApp"]
    if esf["n_neg"] > 0:
        parts.append(f"{esf['n_neg']} sentimento(s) negativo(s)")
    if cart > 0:
        pct_cob = round(dt / cart * 100)
        if pct_cob < 20:
            parts.append(f"cobertura crítica: {cob} deals tocados ({pct_cob}%)")
        else:
            parts.append(f"cobertura: {cob} deals tocados")
    return ". ".join(parts)

# ─── HTML ──────────────────────────────────────────────────────────────────────

CSS_COMUM = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f5f6f8;--surface:#fff;--border:#e3e6ea;--text:#1a1d23;--muted:#6b7280;
  --blue:#1d4ed8;--blue-lt:#eff6ff;--green:#15803d;--green-lt:#f0fdf4;
  --amber:#92400e;--amber-lt:#fffbeb;--red:#991b1b;--red-lt:#fef2f2;
  --radius:10px;--shadow:0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.05)
}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.5}
.page{max-width:1280px;margin:0 auto;padding:24px 20px 48px}
.header{margin-bottom:24px;text-align:center}
.header h1{font-size:22px;font-weight:700}
.header p{font-size:13px;color:var(--muted);margin-top:4px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);margin-bottom:16px;overflow:hidden}
.card-head{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}
.card-title{font-size:14px;font-weight:600}
.card-body{padding:18px}
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:900px}
thead th{background:#f8f9fb;padding:9px 12px;text-align:left;font-weight:600;font-size:11px;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap;cursor:pointer;user-select:none}
thead th:hover{background:#f0f2f5}
.sort-icon{opacity:.35;margin-left:4px;font-size:10px}
th.sorted .sort-icon{opacity:1}
tbody tr{border-bottom:1px solid #f0f2f5;transition:background .1s}
tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:#f8f9fb}
tbody td{padding:8px 12px;white-space:nowrap}
td.nome{white-space:normal;min-width:160px;font-weight:500}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.ef-high{color:var(--green);font-weight:600}.ef-mid{color:var(--amber);font-weight:600}.ef-low{color:var(--red);font-weight:600}
.qbadge{display:inline-block;font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px;white-space:nowrap}
.qbadge.q1{background:#dcfce7;color:#15803d}.qbadge.q2{background:#fee2e2;color:#991b1b}
.qbadge.q3{background:#dbeafe;color:#1d4ed8}.qbadge.q4{background:#f3f4f6;color:#6b7280}
.bar-wrap{display:inline-flex;align-items:center;gap:6px;width:100%}
.bar-bg{flex:1;height:6px;background:#e5e7eb;border-radius:3px;overflow:hidden;min-width:50px}
.bar-fill{height:100%;border-radius:3px}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:500;padding:3px 10px;border-radius:20px;border:1px solid transparent;cursor:pointer;transition:all .15s;user-select:none}
.chip.active{border-color:currentColor}
.chip.all{background:#f3f4f6;color:#374151}.chip.all.active{background:#e5e7eb}
.chip.q1{background:#dcfce7;color:#15803d}.chip.q1.active{background:#bbf7d0}
.chip.q2{background:#fee2e2;color:#991b1b}.chip.q2.active{background:#fecaca}
.chip.q3{background:#dbeafe;color:#1d4ed8}.chip.q3.active{background:#bfdbfe}
.chip.q4{background:#f3f4f6;color:#6b7280}.chip.q4.active{background:#e5e7eb}
select,input[type=text]{font-size:12px;padding:6px 10px;border-radius:6px;border:1px solid var(--border);background:#fff;color:var(--text);cursor:pointer;outline:none}
select:focus{border-color:#93c5fd}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.filter-group{display:flex;align-items:center;gap:6px}
.summary-bar{font-size:12px;color:var(--muted);padding:10px 16px}
.summary-bar span{font-weight:600;color:var(--text)}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow)}
.kpi-lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.kpi-val{font-size:28px;font-weight:700;line-height:1}
.kpi-sub{font-size:12px;color:var(--muted);margin-top:4px}
.kpi.blue .kpi-val{color:var(--blue)}.kpi.amber .kpi-val{color:var(--amber)}.kpi.green .kpi-val{color:var(--green)}
.legend{display:flex;gap:16px;flex-wrap:wrap}
.legend-item{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
.legend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.chart-wrap{position:relative;height:380px}
#tooltip{position:fixed;background:rgba(15,23,42,.92);color:#f1f5f9;font-size:12px;padding:10px 14px;border-radius:8px;pointer-events:none;display:none;max-width:220px;line-height:1.6;z-index:999}
#tooltip strong{display:block;margin-bottom:4px;font-size:13px}
@media(max-width:700px){.kpi-row{grid-template-columns:repeat(2,1fr)}.chart-wrap{height:300px}}
"""

CSS_ESFORCO = CSS_COMUM + """
.diff-green{display:inline-block;background:#dcfce7;color:#166534;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}
.diff-red{display:inline-block;background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}
.diff-gray{display:inline-block;background:#f3f4f6;color:#475569;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}
.badge-conv{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;background:#fffbeb;color:#92400e;border:1px solid #fde68a}
.note-box{background:#f8f9fb;border:1px solid var(--border);border-radius:8px;padding:13px 16px;margin-top:12px;font-size:13px;color:#444;line-height:1.65}
.insight-box{border-left:4px solid var(--green);background:var(--green-lt);padding:13px 16px;border-radius:0 8px 8px 0;font-size:13px;color:#166534;margin-top:12px;line-height:1.65}
.insight-box strong{color:#14532d;display:block;margin-bottom:3px}
.canal-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0}
.canal-card{border:1px solid var(--border);border-radius:8px;padding:16px}
.canal-card-title{font-weight:700;font-size:13px;margin-bottom:3px}
.canal-card-sub{font-size:11px;color:var(--muted);margin-bottom:14px}
.canal-bar-row{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.canal-bar-label{font-size:12px;width:105px;flex-shrink:0}
.canal-bar-wrap{flex:1;background:#e5e7eb;border-radius:3px;height:7px;overflow:hidden}
.canal-bar-fill{height:100%;border-radius:3px}
.bar-wh{background:#16a34a}.bar-ch{background:#2563eb}.bar-re{background:#d97706}.bar-em{background:#7c3aed}
.canal-bar-pct{font-size:11px;color:var(--muted);width:32px;text-align:right;flex-shrink:0}
.bloco-list{padding-left:20px;margin-top:10px}
.bloco-list li{margin-bottom:8px;font-size:13px;color:#333;line-height:1.6}
.patterns-list{padding-left:0;list-style:none;counter-reset:pc}
.patterns-list li{counter-increment:pc;display:flex;gap:12px;margin-bottom:14px;font-size:13px;color:#333;line-height:1.65}
.patterns-list li::before{content:counter(pc)".";font-weight:700;color:var(--muted);flex-shrink:0;width:16px}
table{min-width:600px}
@media(max-width:640px){.canal-grid{grid-template-columns:1fr}}
"""

BOTAO_VOLTAR = (
    '<a href="index.html" style="position:fixed;top:16px;left:16px;display:inline-flex;'
    'align-items:center;gap:6px;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;'
    'font-size:12px;font-weight:600;color:#1a1d23;background:#fff;border:1px solid #e3e6ea;'
    'border-radius:8px;padding:7px 12px;text-decoration:none;'
    'box-shadow:0 1px 3px rgba(0,0,0,.08);z-index:9999;transition:all .15s" '
    'onmouseover="this.style.borderColor=\'#93c5fd\'" '
    'onmouseout="this.style.borderColor=\'#e3e6ea\'">← Início</a>'
)


def _canal_bars(data, prefix):
    def bar(key, cls, label):
        pct = data.get(f"pct_{key}", 0)
        return (f'<div class="canal-bar-row">'
                f'<span class="canal-bar-label">{label} {pct}%</span>'
                f'<div class="canal-bar-wrap"><div class="canal-bar-fill {cls}" style="width:{pct}%"></div></div>'
                f'<span class="canal-bar-pct">{pct}%</span></div>')
    return (bar("whatsapp", "bar-wh", "WhatsApp") +
            bar("chamada",  "bar-ch", "Chamada") +
            bar("reuniao",  "bar-re", "Reunião") +
            bar("email",    "bar-em", "Email"))


def _secao_base_cruzada(consultants, base_cruzada):
    if not base_cruzada:
        return ""
    low_emails = {c["email"] for c in consultants if c["pef"] < 50}
    if not low_emails:
        return ""

    rows_html = ""
    total_base_geral = 0
    total_tocadas_geral = 0
    for c in sorted(consultants, key=lambda x: x["pef"]):
        if c["email"] not in low_emails:
            continue
        bc = base_cruzada.get(c["email"], {})
        total   = bc.get("total", c["cart"])
        tocadas = bc.get("tocadas", 0)
        restante = max(0, total - tocadas)
        pct = round(tocadas / total * 100) if total > 0 else 0
        quem = ", ".join(email_to_name(e) for e in bc.get("quem", []))
        total_base_geral   += total
        total_tocadas_geral += tocadas
        rows_html += f"""
<tr>
  <td class="nome">{c["nome"]}</td>
  <td class="num" style="color:var(--amber);font-weight:600">{c["pef"]:.1f}%</td>
  <td class="num">{total}</td>
  <td class="num" style="color:var(--green);font-weight:600">{tocadas}</td>
  <td class="num">{restante}</td>
  <td style="min-width:120px">
    <div style="background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden">
      <div style="background:{'#22c55e' if pct>=70 else '#f59e0b' if pct>=40 else '#3b82f6'};width:{pct}%;height:100%;border-radius:4px"></div>
    </div>
    <span style="font-size:11px;color:var(--muted)">{pct}%</span>
  </td>
  <td style="font-size:11px;color:var(--muted)">{quem or '—'}</td>
</tr>"""

    pct_geral = round(total_tocadas_geral / total_base_geral * 100) if total_base_geral > 0 else 0
    return f"""
<div class="card" style="margin-top:20px">
  <div class="card-head">
    <span class="card-title">⚡ Ação base cruzada — status hoje</span>
    <span style="font-size:12px;color:var(--muted);margin-left:12px">High performers (≥70%) entrando na base de quem está abaixo de 50% após 13h · regra: não abordar 2x</span>
  </div>
  <div class="card-body">
    <div style="display:flex;gap:24px;margin-bottom:16px">
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px 20px;text-align:center">
        <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Escolas já tocadas</div>
        <div style="font-size:26px;font-weight:700;color:var(--green)">{total_tocadas_geral}</div>
        <div style="font-size:11px;color:var(--muted)">de {total_base_geral} ({pct_geral}%)</div>
      </div>
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px 20px;text-align:center">
        <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Restante a cobrir</div>
        <div style="font-size:26px;font-weight:700;color:var(--blue)">{total_base_geral - total_tocadas_geral}</div>
        <div style="font-size:11px;color:var(--muted)">escolas ainda sem contato hoje</div>
      </div>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Consultor (base)</th>
          <th style="text-align:right">Ef. atual</th>
          <th style="text-align:right">Carteira</th>
          <th style="text-align:right">Tocadas hoje</th>
          <th style="text-align:right">Restante</th>
          <th>Cobertura</th>
          <th>Quem entrou</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
  </div>
</div>"""


def gerar_html_efetividade(hoje, ontem, data_ref):
    if not hoje:
        return ""
    data_ant   = dia_util_anterior(data_ref)
    ref_str    = data_ref.strftime("%d/%m/%Y")
    ant_str    = data_ant.strftime("%d/%m/%Y")
    comp       = build_comparison(hoje, ontem)

    total_atv   = sum(r["atv"]   for r in hoje)
    total_ef    = sum(r["ef"]    for r in hoje)
    total_prazo = sum(r["prazo"] for r in hoje)
    total_conc  = sum(r["conc"]  for r in hoje)
    total_task  = sum(r["tasks"] for r in hoje)
    active_n    = sum(1 for r in hoje if r["atv"] > 0)
    taxa        = f"{total_ef/total_prazo*100:.1f}%" if total_prazo > 0 else "—"

    lids = sorted({r["lideranca"] for r in hoje if r["lideranca"]})
    lid_options = "".join(f'<option value="{l}">{l}</option>' for l in lids)
    has_team = bool(lids)

    atv_fmt  = f"{total_atv:,}".replace(",", ".")
    task_fmt = f"{total_task:,}".replace(",", ".")

    raw_rows = ",\n".join(
        f'[{json.dumps(r["nome"])},{r["atv"]},{r["ef"]},{r["pef"]},{r["pab"]},'
        f'{r["tasks"]},{r["conc"]},{r["cart"]},{r["esc_atv"]},{r["esc_ef"]},'
        f'{r["pct_ef_esc"]},{json.dumps(r["quad"])},{json.dumps(r["lideranca"])},'
        f'{json.dumps(r["segmento"])},{json.dumps(r["cargo"])}]'
        for r in hoje
    )
    comp_json = json.dumps(comp)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Efetividade de Contatos — {ref_str}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>{CSS_COMUM}</style>
</head>
<body>
{BOTAO_VOLTAR}
<div class="page">

<div class="header">
  <h1>Efetividade de Contatos por Consultor</h1>
  <p>Pipeline: Sucesso do Cliente &nbsp;·&nbsp; País: Brasil &nbsp;·&nbsp; Referência: {ref_str} &nbsp;·&nbsp; Fontes: atividades · tarefas · retrato de escolas</p>
</div>

<div class="kpi-row">
  <div class="kpi blue"><div class="kpi-lbl">Consultores ativos</div><div class="kpi-val">{active_n}</div><div class="kpi-sub">com atividades em {ref_str}</div></div>
  <div class="kpi blue"><div class="kpi-lbl">Total de atividades</div><div class="kpi-val">{atv_fmt}</div><div class="kpi-sub">realizadas</div></div>
  <div class="kpi amber"><div class="kpi-lbl">Taxa geral de efetividade</div><div class="kpi-val">{taxa}</div><div class="kpi-sub">{total_ef} esc. efetivas de {total_prazo} elegíveis</div></div>
  <div class="kpi green"><div class="kpi-lbl">Tasks concluídas</div><div class="kpi-val">{total_conc}</div><div class="kpi-sub">de {task_fmt} recebidas</div></div>
</div>

<div class="card">
  <div class="card-head">
    <span class="card-title">Esforço × Efetividade</span>
    <div class="legend">
      <span class="legend-item"><span class="legend-dot" style="background:#16a34a"></span>Alto esforço + alta efetiv.</span>
      <span class="legend-item"><span class="legend-dot" style="background:#dc2626"></span>Alto esforço + baixa efetiv.</span>
      <span class="legend-item"><span class="legend-dot" style="background:#2563eb"></span>Baixo esforço + alta efetiv.</span>
      <span class="legend-item"><span class="legend-dot" style="background:#9ca3af"></span>Baixo esforço + baixa efetiv.</span>
      <span class="legend-item" style="font-size:11px;color:#9ca3af">● tamanho = tasks recebidas</span>
    </div>
  </div>
  <div class="card-body"><div class="chart-wrap"><canvas id="scatter"></canvas></div></div>
</div>

<div class="card">
  <div class="card-head">
    <span class="card-title">Detalhamento por consultor</span>
    <div class="filters">
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <span class="chip all active" data-q="all" onclick="setQ(this)">Todos</span>
        <span class="chip q1" data-q="q1" onclick="setQ(this)">⬆ alto + efetivo</span>
        <span class="chip q2" data-q="q2" onclick="setQ(this)">⬆ alto + baixo</span>
        <span class="chip q3" data-q="q3" onclick="setQ(this)">⬇ baixo + efetivo</span>
        <span class="chip q4" data-q="q4" onclick="setQ(this)">⬇ baixo + baixo</span>
      </div>
      <div class="filter-group">
        <select id="sortSel" onchange="render()">
          <option value="atv">Atividades</option><option value="ef">Efetividade</option>
          <option value="tasks">Tasks recebidas</option><option value="conc">Tasks concluídas</option>
          <option value="cart">Carteira</option><option value="esc">Escolas efetivas %</option>
        </select>
      </div>
      {'<div class="filter-group"><select id="lidSel" onchange="render()"><option value="">Todas</option>' + lid_options + '</select></div>' if has_team else ''}
      <div class="filter-group">
        <input type="text" id="search" placeholder="Buscar consultor…" oninput="render()" style="width:160px">
      </div>
    </div>
  </div>
  <div class="card-body" style="padding:0">
    <div class="tbl-wrap">
      <table id="tbl">
        <thead><tr>
          <th onclick="sortBy('nome')" data-col="nome">Consultor <span class="sort-icon">↕</span></th>
          <th onclick="sortBy('atv')" data-col="atv" class="sorted">Atividades <span class="sort-icon">↓</span></th>
          <th onclick="sortBy('ef')" data-col="ef">Esc. efetivas <span class="sort-icon">↕</span></th>
          <th onclick="sortBy('pef')" data-col="pef">% Efetividade <span class="sort-icon">↕</span></th>
          <th onclick="sortBy('pab')" data-col="pab">% Abordagem <span class="sort-icon">↕</span></th>
          <th onclick="sortBy('tasks')" data-col="tasks">Tasks receb. <span class="sort-icon">↕</span></th>
          <th onclick="sortBy('conc')" data-col="conc">Concluídas <span class="sort-icon">↕</span></th>
          <th onclick="sortBy('cart')" data-col="cart">Carteira <span class="sort-icon">↕</span></th>
          <th onclick="sortBy('esc')" data-col="esc">Esc. efetivas % <span class="sort-icon">↕</span></th>
          <th>Quadrante</th>
          {'<th data-col="lideranca" onclick="sortBy(\'lideranca\')">Liderança <span class="sort-icon">↕</span></th>' if has_team else ''}
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <div class="summary-bar" id="summary"></div>
  </div>
</div>

<div class="card" id="sec-comp">
  <div class="card-head">
    <span class="card-title">Comparativo: {ref_str} vs. {ant_str}</span>
    <div class="filters">
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <span class="chip all active" data-ct="all" onclick="setCF(this)">Todos</span>
        <span class="chip q1" data-ct="melhorou" onclick="setCF(this)">✅ Melhorou</span>
        <span class="chip q4" data-ct="manteve" onclick="setCF(this)">➖ Manteve</span>
        <span class="chip q2" data-ct="piorou" onclick="setCF(this)">🔴 Piorou</span>
        <span class="chip q3" data-ct="novo" onclick="setCF(this)">🆕 Novo</span>
      </div>
      <input type="text" id="comp-search" placeholder="Buscar…" oninput="renderComp()" style="width:140px">
    </div>
  </div>
  <div class="card-body" style="padding:16px 18px 8px">
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px">
      <div style="background:#f0fdf4;border:1px solid #86efac;border-top:3px solid #16a34a;border-radius:8px;padding:14px 16px;text-align:center"><div style="font-size:28px;font-weight:800;color:#15803d" id="ck-mel">—</div><div style="font-size:11px;color:#6b7280;margin-top:4px">✅ Melhoraram</div></div>
      <div style="background:#f3f4f6;border:1px solid #e5e7eb;border-top:3px solid #6b7280;border-radius:8px;padding:14px 16px;text-align:center"><div style="font-size:28px;font-weight:800;color:#6b7280" id="ck-man">—</div><div style="font-size:11px;color:#6b7280;margin-top:4px">➖ Mantiveram</div></div>
      <div style="background:#fef2f2;border:1px solid #fecaca;border-top:3px solid #dc2626;border-radius:8px;padding:14px 16px;text-align:center"><div style="font-size:28px;font-weight:800;color:#991b1b" id="ck-pio">—</div><div style="font-size:11px;color:#6b7280;margin-top:4px">🔴 Pioraram</div></div>
      <div style="background:#eff6ff;border:1px solid #bfdbfe;border-top:3px solid #2563eb;border-radius:8px;padding:14px 16px;text-align:center"><div style="font-size:28px;font-weight:800;color:#1d4ed8" id="ck-nov">—</div><div style="font-size:11px;color:#6b7280;margin-top:4px">🆕 Novos</div></div>
    </div>
  </div>
  <div class="card-body" style="padding:0">
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th onclick="sortComp('nome')" data-col="nome">Consultor <span class="sort-icon">↕</span></th>
          <th onclick="sortComp('pef_hoje')" data-col="pef_hoje">% Ef. Hoje <span class="sort-icon">↕</span></th>
          <th onclick="sortComp('pef_ontem')" data-col="pef_ontem">% Ef. Anterior <span class="sort-icon">↕</span></th>
          <th onclick="sortComp('delta_ef')" data-col="delta_ef" class="sorted">Δ Efetividade <span class="sort-icon">↓</span></th>
          <th onclick="sortComp('atv_hoje')" data-col="atv_hoje">Atv. Hoje <span class="sort-icon">↕</span></th>
          <th onclick="sortComp('delta_atv')" data-col="delta_atv">Δ Atividades <span class="sort-icon">↕</span></th>
          <th>Quadrante Hoje</th><th>Tendência</th>
        </tr></thead>
        <tbody id="comp-tbody"></tbody>
      </table>
    </div>
    <div class="summary-bar" id="comp-summary"></div>
  </div>
</div>

</div>
<div id="tooltip"></div>
<script>
const RAW=[{raw_rows}];
const FIELDS=['nome','atv','ef','pef','pab','tasks','conc','cart','esc_atv','esc_ef','pct_ef_esc','quad','lideranca','segmento','cargo'];
const DATA=RAW.map(r=>Object.fromEntries(FIELDS.map((k,i)=>[k,r[i]])));
const QL={{q1:'Alto esforço + Alta efetiv.',q2:'Alto esforço + Baixa efetiv.',q3:'Baixo esforço + Alta efetiv.',q4:'Baixo esforço + Baixa efetiv.'}};
let activeQ='all',sortCol='atv',sortDir=-1;
function setQ(el){{document.querySelectorAll('[data-q]').forEach(c=>c.classList.remove('active'));el.classList.add('active');activeQ=el.dataset.q;render();}}
function sortBy(col){{if(sortCol===col)sortDir*=-1;else{{sortCol=col;sortDir=-1;}}document.querySelectorAll('#tbl thead th').forEach(th=>{{th.classList.toggle('sorted',th.dataset.col===col);if(th.querySelector('.sort-icon'))th.querySelector('.sort-icon').textContent=th.dataset.col===col?(sortDir===-1?'↓':'↑'):'↕';}});render();}}
function efC(v){{return v>=70?'ef-high':v>=50?'ef-mid':'ef-low';}}
function render(){{
  const s=document.getElementById('search').value.toLowerCase();
  const lidF=document.getElementById('lidSel')?.value||'';
  let rows=DATA.filter(r=>(activeQ==='all'||r.quad===activeQ)&&(!lidF||r.lideranca===lidF)&&r.nome.toLowerCase().includes(s));
  const km={{'atv':'atv','ef':'ef','pef':'pef','pab':'pab','tasks':'tasks','conc':'conc','cart':'cart','esc':'pct_ef_esc','nome':'nome','lideranca':'lideranca'}};
  const k=km[sortCol]||sortCol;
  rows.sort((a,b)=>typeof a[k]==='string'?sortDir*a[k].localeCompare(b[k]):sortDir*(a[k]-b[k]));
  document.getElementById('tbody').innerHTML=rows.length?rows.map(r=>`
    <tr>
      <td class="nome">${{r.nome}}${{r.segmento?'<div style="font-size:11px;color:#9ca3af;font-weight:400;margin-top:1px">'+r.segmento+(r.cargo&&r.cargo!=='—'?' · '+r.cargo:'')+'</div>':''}}</td>
      <td class="num">${{r.atv}}</td><td class="num">${{r.ef}}</td>
      <td class="num ${{efC(r.pef)}}"><div class="bar-wrap"><div class="bar-bg"><div class="bar-fill" style="width:${{Math.min(r.pef,100)}}%;background:${{r.pef>=70?'#16a34a':r.pef>=50?'#d97706':'#dc2626'}}"></div></div>${{r.pef.toFixed(1)}}%</div></td>
      <td class="num ${{efC(r.pab)}}">${{r.pab.toFixed(1)}}%</td>
      <td class="num">${{r.tasks}}</td><td class="num">${{r.conc}}</td><td class="num">${{r.cart}}</td>
      <td class="num ${{efC(r.pct_ef_esc)}}">${{r.pct_ef_esc.toFixed(1)}}%</td>
      <td><span class="qbadge ${{r.quad}}">${{QL[r.quad]}}</span></td>
      ${{r.lideranca?'<td class="nome" style="color:#6b7280;font-weight:400">'+r.lideranca+'</td>':''}}
    </tr>`).join(''):'<tr><td colspan="15" style="text-align:center;padding:24px;color:#9ca3af">Nenhum resultado</td></tr>';
  document.getElementById('summary').innerHTML=`Exibindo <span>${{rows.length}}</span> de <span>${{DATA.length}}</span> consultores`;
}}
const QC={{q1:'rgba(22,163,74,.75)',q2:'rgba(220,38,38,.75)',q3:'rgba(37,99,235,.75)',q4:'rgba(156,163,175,.75)'}};
const QB={{q1:'#15803d',q2:'#991b1b',q3:'#1d4ed8',q4:'#6b7280'}};
const datasets=['q1','q2','q3','q4'].map(q=>({{
  label:QL[q],
  data:DATA.filter(r=>r.quad===q).map(r=>({{x:r.atv,y:r.pef,r:Math.max(5,Math.min(24,r.tasks*0.28+6)),_d:r}})),
  backgroundColor:QC[q],borderColor:QB[q],borderWidth:1.5
}}));
const ctx=document.getElementById('scatter').getContext('2d');
const chart=new Chart(ctx,{{
  type:'bubble',data:{{datasets}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{enabled:false}}}},
    scales:{{x:{{title:{{display:true,text:'Atividades realizadas',font:{{size:12}}}},grid:{{color:'#f0f2f5'}},ticks:{{font:{{size:11}}}}}},
             y:{{title:{{display:true,text:'% Efetividade',font:{{size:12}}}},min:0,max:105,grid:{{color:'#f0f2f5'}},ticks:{{callback:v=>v+'%',font:{{size:11}}}}}}}},
    animation:{{duration:400}}}},
  plugins:[{{id:'rl',afterDraw(c){{
    const{{ctx,chartArea,scales}}=c;
    const x50=scales.x.getPixelForValue(50),y50=scales.y.getPixelForValue(50);
    ctx.save();ctx.setLineDash([5,4]);ctx.strokeStyle='rgba(100,116,139,.35)';ctx.lineWidth=1.5;
    ctx.beginPath();ctx.moveTo(x50,chartArea.top);ctx.lineTo(x50,chartArea.bottom);ctx.stroke();
    ctx.beginPath();ctx.moveTo(chartArea.left,y50);ctx.lineTo(chartArea.right,y50);ctx.stroke();
    ctx.restore();
  }}}}]
}});
const tip=document.getElementById('tooltip');
document.getElementById('scatter').addEventListener('mousemove',evt=>{{
  const pts=chart.getElementsAtEventForMode(evt,'nearest',{{intersect:true}},false);
  if(pts.length){{const d=pts[0].element.$context.raw._d;tip.style.display='block';tip.style.left=(evt.clientX+14)+'px';tip.style.top=(evt.clientY-10)+'px';
    tip.innerHTML=`<strong>${{d.nome}}</strong>${{d.segmento?d.segmento+'<br>':''}}Atividades: ${{d.atv}}<br>Esc. efetivas: ${{d.ef}} (${{d.pef.toFixed(1)}}%)<br>Abordagem: ${{d.pab.toFixed(1)}}%<br>Tasks: ${{d.tasks}} receb. · ${{d.conc}} concl.<br>Carteira: ${{d.cart}} escolas`;
  }}else tip.style.display='none';
}});
document.getElementById('scatter').addEventListener('mouseleave',()=>tip.style.display='none');
const COMP={comp_json};
let compF='all',cSortCol='delta_ef',cSortDir=-1;
function setCF(el){{document.querySelectorAll('[data-ct]').forEach(c=>c.classList.remove('active'));el.classList.add('active');compF=el.dataset.ct;renderComp();}}
function sortComp(col){{if(cSortCol===col)cSortDir*=-1;else{{cSortCol=col;cSortDir=-1;}}renderComp();}}
function renderComp(){{
  const s=(document.getElementById('comp-search').value||'').toLowerCase();
  let rows=COMP.filter(r=>(compF==='all'||r.tendencia===compF)&&r.nome.toLowerCase().includes(s));
  rows.sort((a,b)=>{{const va=a[cSortCol],vb=b[cSortCol];if(va===null&&vb===null)return 0;if(va===null)return 1;if(vb===null)return -1;return typeof va==='string'?cSortDir*va.localeCompare(vb):cSortDir*(va-vb);}});
  const ti={{melhorou:'✅',manteve:'➖',piorou:'🔴',novo:'🆕'}};
  document.getElementById('ck-mel').textContent=COMP.filter(r=>r.tendencia==='melhorou').length;
  document.getElementById('ck-man').textContent=COMP.filter(r=>r.tendencia==='manteve').length;
  document.getElementById('ck-pio').textContent=COMP.filter(r=>r.tendencia==='piorou').length;
  document.getElementById('ck-nov').textContent=COMP.filter(r=>r.tendencia==='novo').length;
  document.getElementById('comp-tbody').innerHTML=rows.length?rows.map(r=>`
    <tr>
      <td class="nome">${{r.nome}}</td>
      <td class="num ${{r.pef_hoje>=70?'ef-high':r.pef_hoje>=50?'ef-mid':'ef-low'}}">${{r.pef_hoje.toFixed(1)}}%</td>
      <td class="num">${{r.pef_ontem!==null?r.pef_ontem.toFixed(1)+'%':'—'}}</td>
      <td class="num ${{r.delta_ef!==null?(r.delta_ef>2?'ef-high':r.delta_ef<-2?'ef-low':''):''}}">
        ${{r.delta_ef!==null?(r.delta_ef>0?'+':'')+r.delta_ef.toFixed(1)+'pp':'—'}}
      </td>
      <td class="num">${{r.atv_hoje}}</td>
      <td class="num ${{r.delta_atv!==null&&r.delta_atv>0?'ef-high':r.delta_atv!==null&&r.delta_atv<0?'ef-low':''}}">
        ${{r.delta_atv!==null?(r.delta_atv>0?'+':'')+r.delta_atv:'—'}}
      </td>
      <td><span class="qbadge ${{r.quad_hoje}}">${{QL[r.quad_hoje]}}</span></td>
      <td>${{ti[r.tendencia]||''}} ${{r.tendencia}}</td>
    </tr>`).join(''):'<tr><td colspan="8" style="text-align:center;padding:24px;color:#9ca3af">Nenhum resultado</td></tr>';
  document.getElementById('comp-summary').innerHTML=`Exibindo <span>${{rows.length}}</span> de <span>${{COMP.length}}</span> consultores`;
}}
render(); renderComp();
</script>
</body></html>"""


def gerar_html_esforco(dados_ef, dados_esf, canal_mix, data_ref, totais=None, carteira_total=None, base_cruzada=None):
    ref_str = data_ref.strftime("%d/%m/%Y")
    carteira_total = carteira_total or {}
    base_cruzada   = base_cruzada   or {}

    consultants = []
    for r in dados_ef:
        esf = dados_esf.get(r["email"])
        cart   = carteira_total.get(r["email"], r["cart"])
        base   = r["prazo"] if r["prazo"] > 0 else cart
        meta70 = math.ceil(base * 0.70)
        conv_rec = max(0, meta70 - r["ef"])
        r_total = {**r, "cart": cart}
        consultants.append({**r_total, "esf": esf, "meta70": meta70, "conv_rec": conv_rec,
                            "diagnostico": diagnostico(r_total, esf)})

    gap_list = sorted([c for c in consultants if c["conv_rec"] > 0],
                      key=lambda x: x["conv_rec"], reverse=True)

    high = [c for c in consultants if c["pef"] >= 70 and c["esf"]]
    low  = [c for c in consultants if c["pef"] < 60  and c["esf"]]

    def avg_pct(lst, n_key):
        res = []
        for x in lst:
            esf = x["esf"]
            if esf and esf.get("total_atv", 0) > 0:
                res.append(esf[n_key] / esf["total_atv"] * 100)
        return round(sum(res) / len(res), 1) if res else 0.0

    def avg_cob(lst):
        res = []
        for x in lst:
            esf = x["esf"]
            if esf and x["cart"] > 0:
                res.append(esf["deals_tocados"] / x["cart"] * 100)
        return round(sum(res) / len(res), 1) if res else 0.0

    def avg_conv(lst):
        res = []
        for x in lst:
            esf = x["esf"]
            if esf and esf.get("deals_tocados", 0) > 0:
                res.append(x["ef"] / esf["deals_tocados"] * 100)
        return round(sum(res) / len(res), 1) if res else 0.0

    h_cob  = avg_cob(high);  l_cob  = avg_cob(low)
    h_conv = avg_conv(high); l_conv = avg_conv(low)
    h_wh   = avg_pct(high, "n_whatsapp"); l_wh = avg_pct(low, "n_whatsapp")
    h_ch   = avg_pct(high, "n_chamada");  l_ch = avg_pct(low, "n_chamada")
    h_neg  = sum(c["esf"]["n_neg"] for c in high if c["esf"])
    l_neg  = sum(c["esf"]["n_neg"] for c in low  if c["esf"])
    h_pos_pct = avg_pct(high, "n_pos"); l_pos_pct = avg_pct(low, "n_pos")

    total_conv_rec = sum(c["conv_rec"] for c in consultants)

    def gap_row(c, bold=False):
        nome_td = f'<strong>{c["nome"]}</strong>' if bold else c["nome"]
        ef_cls  = "ef-low" if c["pef"] < 50 else "ef-mid" if c["pef"] < 70 else "ef-high"
        return (f'<tr><td class="nome">{nome_td}</td>'
                f'<td class="num">{c["cart"]}</td>'
                f'<td class="num">{c["ef"]}</td>'
                f'<td class="num {ef_cls}">{c["pef"]:.1f}%</td>'
                f'<td class="num">{c["meta70"]}</td>'
                f'<td class="num"><span class="badge-conv">+{c["conv_rec"]}</span></td>'
                f'<td>{c["diagnostico"]}</td></tr>')

    gap_rows_html = "\n".join(gap_row(c, bold=(i < 8)) for i, c in enumerate(gap_list))

    def bloco_a_row(c):
        esf = c["esf"] or {}
        tot = esf.get("total_atv", 0)
        wh  = round(esf.get("n_whatsapp",0)/tot*100) if tot>0 else 0
        ch  = round(esf.get("n_chamada",0)/tot*100) if tot>0 else 0
        dt  = esf.get("deals_tocados", 0)
        neg = esf.get("n_neg", 0)
        cart = c["cart"]

        acao_parts = []
        if ch > 70:
            acao_parts.append(f"Reduzir chamada de {ch}% para 50%. Migrar para WhatsApp.")
        elif wh < 40:
            acao_parts.append(f"Aumentar WhatsApp (atual {wh}%). Meta: 60% WhatsApp / 40% chamada.")
        if cart > 0 and dt / cart < 0.20:
            acao_parts.append(f"Expandir cobertura: só tocou {dt} de {cart} ({round(dt/cart*100)}%). Meta: 20% da carteira.")
        if neg > 0:
            acao_parts.append(f"Pausar as {neg} escola(s) com sentimento negativo — esfriar 24h.")
        if not acao_parts:
            acao_parts.append("Manter ritmo e refinar canal para elevar conversão por toque.")

        return (f'<tr><td class="nome"><strong>{c["nome"]}</strong></td>'
                f'<td class="num"><span class="badge-conv">+{c["conv_rec"]} conv.</span></td>'
                f'<td>{" ".join(acao_parts)}</td></tr>')

    bloco_a_html = "\n".join(bloco_a_row(c) for c in gap_list[:8])

    ef_data  = canal_mix.get("efetivos", {"n_deals":0,"total":0,"pct_whatsapp":0,"pct_chamada":0,"pct_reuniao":0,"pct_email":0})
    nef_data = canal_mix.get("nao_efetivos", {"n_deals":0,"total":0,"pct_whatsapp":0,"pct_chamada":0,"pct_reuniao":0,"pct_email":0})

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Análise de Esforço do Time — {ref_str}</title>
<style>{CSS_ESFORCO}</style>
</head>
<body>
{BOTAO_VOLTAR}
<div class="page" style="max-width:1100px">

<div class="header">
  <h1>Análise de Esforço do Time</h1>
  <p>Análise da carteira atual + atividades de ontem &nbsp;·&nbsp; Referência: {ref_str}</p>
</div>

<div class="card">
  <div class="card-head"><span class="card-title">1. Onde está o gap (e quem pode fechá-lo)</span></div>
  <div class="card-body">
    <p style="font-size:13px;color:#333;margin-bottom:16px;line-height:1.65">
      {f'As {min(8,len(gap_list))} maiores alavancas concentram a maior parte das {total_conv_rec} conversões necessárias — atacar essas linhas resolve a meta agregada.' if gap_list else 'Nenhuma consultora abaixo da meta hoje.'}
    </p>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Consultor (foco)</th>
          <th style="text-align:right">Carteira</th>
          <th style="text-align:right">Efetivas hoje</th>
          <th style="text-align:right">% atual</th>
          <th style="text-align:right">Para 70%</th>
          <th style="text-align:right">Conv. a recuperar</th>
          <th>Diagnóstico de ontem</th>
        </tr></thead>
        <tbody>{gap_rows_html}</tbody>
      </table>
    </div>
    <div class="note-box">
      <strong>Como ler:</strong> "Conv. a recuperar" = quantas efetivas a mais para chegar a 70% individualmente.
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="card-title">2. O que os top consultores fazem (e os baixos não)</span></div>
  <div class="card-body">
    <p style="font-size:13px;color:#333;margin-bottom:16px;line-height:1.65">
      Comparativo agregado entre os {len(high)} consultores com efetividade ≥70% e os {len(low)} com efetividade &lt;60%:
    </p>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Comportamento</th>
          <th style="text-align:right">Alta perf. (≥70%)</th>
          <th style="text-align:right">Baixa perf. (&lt;60%)</th>
          <th>Diferença</th>
        </tr></thead>
        <tbody>
          <tr><td>Cobertura (deals tocados / carteira)</td><td class="num">{h_cob}%</td><td class="num">{l_cob}%</td>
            <td>{'<span class="diff-green">+' + str(round(h_cob-l_cob,1)) + ' p.p. a favor da alta</span>' if h_cob > l_cob else '<span class="diff-red">' + str(round(h_cob-l_cob,1)) + ' p.p.</span>'}</td></tr>
          <tr><td>Conversão por deal tocado</td><td class="num">{h_conv}%</td><td class="num">{l_conv}%</td>
            <td>{'<span class="diff-green">+' + str(round(h_conv-l_conv,1)) + ' p.p.</span>' if h_conv > l_conv else '<span class="diff-red">' + str(round(h_conv-l_conv,1)) + ' p.p.</span>'}</td></tr>
          <tr><td>% atividades em WhatsApp</td><td class="num">{h_wh}%</td><td class="num">{l_wh}%</td>
            <td>{'<span class="diff-green">+' + str(round(h_wh-l_wh,1)) + ' p.p.</span>' if h_wh > l_wh else '<span class="diff-red">' + str(round(h_wh-l_wh,1)) + ' p.p.</span>'}</td></tr>
          <tr><td>% atividades em Chamada</td><td class="num">{h_ch}%</td><td class="num">{l_ch}%</td>
            <td>{'<span class="diff-green">−' + str(round(l_ch-h_ch,1)) + ' p.p. baixa super-indexa</span>' if l_ch > h_ch else '<span class="diff-gray">similar</span>'}</td></tr>
          <tr><td>Sentimento negativo registrado</td><td class="num">{h_neg}</td><td class="num">{l_neg}</td>
            <td>{'<span class="diff-red">100% nos baixos</span>' if h_neg == 0 and l_neg > 0 else '<span class="diff-gray">similar</span>'}</td></tr>
          <tr><td>Sentimento positivo (%)</td><td class="num">{h_pos_pct}%</td><td class="num">{l_pos_pct}%</td>
            <td>{'<span class="diff-green">+' + str(round(h_pos_pct-l_pos_pct,1)) + ' p.p.</span>' if h_pos_pct > l_pos_pct else '<span class="diff-red">' + str(round(h_pos_pct-l_pos_pct,1)) + ' p.p.</span>'}</td></tr>
        </tbody>
      </table>
    </div>
    <p style="font-size:12px;font-weight:600;color:#333;margin:20px 0 10px">Mix de canal: deals que viraram efetivos vs não viraram</p>
    <div class="canal-grid">
      <div class="canal-card">
        <div class="canal-card-title">Deals que VIRARAM efetivos</div>
        <div class="canal-card-sub">{ef_data.get('n_deals',0)} deals com pelo menos 1 atividade efetiva ontem.</div>
        {_canal_bars(ef_data, "ef")}
      </div>
      <div class="canal-card">
        <div class="canal-card-title">Deals tocados que NÃO viraram</div>
        <div class="canal-card-sub">{nef_data.get('n_deals',0)} deals com atividade mas sem nenhuma efetiva.</div>
        {_canal_bars(nef_data, "nef")}
      </div>
    </div>
    <div class="insight-box">
      <strong>Insight central</strong>
      WhatsApp ({ef_data.get('pct_whatsapp',0)}% nos efetivos) é o canal de conversão; chamada isolada ({nef_data.get('pct_chamada',0)}% nos não efetivos) é o canal de desperdício.
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="card-title">3. Padrões ganhadores — comportamentos para replicar hoje</span></div>
  <div class="card-body">
    <ol class="patterns-list">
      <li><span><strong>Combinar WhatsApp + chamada na mesma escola, com WhatsApp puxando o fechamento.</strong>
        Em deals efetivos o WhatsApp aparece em {ef_data.get('pct_whatsapp',53)}% das atividades; nos que não converteram, chamada domina com {nef_data.get('pct_chamada',67)}%.
        Regra prática: depois de ligar e não fechar, mande WhatsApp no mesmo dia.</span></li>
      <li><span><strong>Cobertura horizontal vence intensidade vertical.</strong>
        Top performers tocam {h_cob}% da carteira por dia; baixos só {l_cob}%.
        Tocar mais escolas diferentes supera insistir várias vezes na mesma.</span></li>
      <li><span><strong>Sentimento negativo é um veto de fechamento.</strong>
        {f'Zero registros negativos nos top consultores; {l_neg} nos baixos.' if h_neg == 0 else f'{h_neg} negativos nos top, {l_neg} nos baixos.'}
        Quando o sentimento sai negativo, pause o contato por 24h e retome via WhatsApp leve.</span></li>
      <li><span><strong>Não existe "chamada-only" funcionando.</strong>
        Consultores com &gt;80% chamada sistematicamente apresentam efetividade abaixo de 50%.</span></li>
      <li><span><strong>Quem tem cobertura 100% e não fecha precisa de qualidade, não volume.</strong>
        Revisar o conteúdo do contato — script, tom e canal — antes de fazer mais atividades.</span></li>
    </ol>
  </div>
</div>

<div class="card">
  <div class="card-head">
    <span class="card-title">Bloco A — Recuperação de gap
      <span style="font-size:11px;font-weight:500;color:var(--red);margin-left:6px">prioridade máxima</span>
    </span>
  </div>
  <div class="card-body">
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Consultor</th>
          <th style="text-align:right">Meta hoje</th>
          <th>Ação específica</th>
        </tr></thead>
        <tbody>{bloco_a_html}</tbody>
      </table>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="card-title">Bloco B — Padrão de execução do dia (todos)</span></div>
  <div class="card-body">
    <ul class="bloco-list">
      <li>Toda escola que não fechar na chamada recebe WhatsApp no mesmo dia (regra do duplo toque).</li>
      <li>Toda escola com sentimento negativo registrado entra em "esfriamento" — não receber novo contato por 24h.</li>
      <li>Meta de cobertura mínima: 20% da carteira tocada por consultor hoje.</li>
      <li>Check-in de meio-dia: revisar quem está abaixo de 10% de cobertura às 12h e redistribuir abordagem.</li>
    </ul>
  </div>
</div>

<div style="margin-top:8px;padding:13px 16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);font-size:11.5px;color:var(--muted);line-height:1.6;box-shadow:var(--shadow)">
  Análise gerada automaticamente em {ref_str} a partir dos dados do BigQuery.
  Comparativos calculados sobre {len(high)} consultores com efetividade ≥70% e {len(low)} com efetividade &lt;60%.
</div>

{_secao_base_cruzada(consultants, base_cruzada)}

</div>
</body></html>"""


def gerar_html_meta_distribuida(dados_ef, data_ref, totais=None):
    ref_str = data_ref.strftime("%d/%m/%Y")

    consultants = sorted(
        [r for r in dados_ef if r["cart"] > 0],
        key=lambda x: x["pef"], reverse=True,
    )
    if not consultants:
        return ""

    rows = []
    for r in consultants:
        nao_ef   = max(0, r["prazo"] - r["ef"])
        meta_dia = math.ceil(nao_ef * 0.50)
        ef_hoje  = r["esc_ef"]
        pef_hoje = round(ef_hoje / nao_ef * 100, 1) if nao_ef > 0 else 0.0
        falta    = max(0, meta_dia - ef_hoje)
        rows.append({**r, "nao_ef": nao_ef, "meta_dia": meta_dia,
                     "ef_hoje": ef_hoje, "pef_hoje": pef_hoje, "falta": falta})

    rows.sort(key=lambda x: (-x["falta"], -x["nao_ef"]))

    total_ef_time    = totais["efetivas"]  if totais else sum(r["ef"]    for r in rows)
    total_prazo_time = totais["elegiveis"] if totais else sum(r["prazo"] for r in rows)
    pef_time = totais["pef"] if totais else (round(total_ef_time / total_prazo_time * 100, 1) if total_prazo_time > 0 else 0.0)
    pef_cls  = "green" if pef_time >= 70 else "amber" if pef_time >= 50 else "blue"
    conv_global = max(0, math.floor(total_prazo_time * 0.70) + 1 - total_ef_time) if total_prazo_time > 0 else 0

    bateram_hoje  = sum(1 for r in rows if r["falta"] == 0 and r["meta_dia"] > 0)
    em_andamento  = sum(1 for r in rows if 0 < r["falta"] and r["ef_hoje"] > 0)
    sem_ef_hoje   = sum(1 for r in rows if r["ef_hoje"] == 0 and r["nao_ef"] > 0)

    table_rows = ""
    for r in rows:
        pct       = r["pef_hoje"]
        ef_cls    = "ef-high" if pct >= 50 else "ef-mid" if pct > 0 else "ef-low"
        bar_color = "#16a34a" if pct >= 50 else "#d97706" if pct > 0 else "#dc2626"
        seg       = r.get("segmento", "")
        seg_html  = f'<div style="font-size:11px;color:#9ca3af;margin-top:1px">{seg}</div>' if seg else ""
        if r["falta"] == 0 and r["meta_dia"] > 0:
            status  = "✅ Meta batida"
            s_style = "color:#15803d;font-weight:600"
        elif r["nao_ef"] == 0:
            status  = "✅ Carteira 100%"
            s_style = "color:#15803d;font-weight:600"
        else:
            status  = f"+{r['falta']} para meta"
            s_style = "color:#991b1b;font-weight:600"
        table_rows += (
            f'<tr>'
            f'<td class="nome">{r["nome"]}{seg_html}</td>'
            f'<td class="num">{r["cart"]}</td>'
            f'<td class="num">{r["nao_ef"]}</td>'
            f'<td class="num">{r["ef_hoje"]}</td>'
            f'<td class="num">{r["meta_dia"]}</td>'
            f'<td class="num">'
            f'<div class="bar-wrap">'
            f'<div class="bar-bg"><div class="bar-fill" style="width:{min(pct,100):.0f}%;background:{bar_color}"></div></div>'
            f'<span class="{ef_cls}">{pct:.1f}%</span>'
            f'</div></td>'
            f'<td style="{s_style}">{status}</td>'
            f'</tr>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Meta Distribuída 70% — {ref_str}</title>
<style>{CSS_COMUM}</style>
</head>
<body>
{BOTAO_VOLTAR}
<div class="page" style="max-width:900px">

<div class="header">
  <h1>Meta Distribuída — 70% de Efetividade</h1>
  <p>Progresso individual de cada consultor &nbsp;·&nbsp; Referência: {ref_str}</p>
</div>

<div style="margin-bottom:10px">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div class="kpi {pef_cls}">
      <div class="kpi-lbl">Efetividade do time</div>
      <div class="kpi-val">{pef_time}%</div>
      <div class="kpi-sub">meta: 70% &nbsp;·&nbsp; {total_ef_time} efetivas de {total_prazo_time} elegíveis</div>
    </div>
    <div class="kpi {'green' if conv_global == 0 else 'blue'}">
      <div class="kpi-lbl">Escolas para atingir 70%</div>
      <div class="kpi-val">{conv_global}</div>
      <div class="kpi-sub">efetivações ainda necessárias</div>
    </div>
  </div>
</div>

<div style="margin-bottom:20px">
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
    <div class="kpi green"><div class="kpi-lbl">Bateram a meta hoje</div><div class="kpi-val">{bateram_hoje}</div><div class="kpi-sub">≥ 50% das não efetivas</div></div>
    <div class="kpi amber"><div class="kpi-lbl">Em andamento</div><div class="kpi-val">{em_andamento}</div><div class="kpi-sub">efetivaram, mas ainda abaixo de 50%</div></div>
    <div class="kpi blue"><div class="kpi-lbl">Sem efetivação hoje</div><div class="kpi-val">{sem_ef_hoje}</div><div class="kpi-sub">precisam de atenção urgente</div></div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="card-title">Análise do dia — meta: efetivação de 50% das escolas não efetivas</span></div>
  <div class="card-body" style="padding:0">
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Consultor</th>
          <th style="text-align:right">Carteira</th>
          <th style="text-align:right">Não efetivas</th>
          <th style="text-align:right">Efetivadas hoje</th>
          <th style="text-align:right">Meta do dia</th>
          <th>% Ef. hoje</th>
          <th>Status</th>
        </tr></thead>
        <tbody>
{table_rows}        </tbody>
      </table>
    </div>
  </div>
</div>

<div style="margin-top:8px;padding:13px 16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);font-size:11.5px;color:var(--muted);line-height:1.6;box-shadow:var(--shadow)">
  Não efetivas = escolas elegíveis da carteira sem efetividade acumulada. Meta do dia = 50% das não efetivas.
  Análise gerada automaticamente em {ref_str} a partir dos dados do BigQuery.
</div>

</div>
</body></html>"""


# ─── GitHub ────────────────────────────────────────────────────────────────────

def _gh_headers(token):
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}

def _gh_get_sha(token, path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    req = urllib.request.Request(url, headers=_gh_headers(token))
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())["sha"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise

def gh_put(token, path, content_bytes, msg):
    sha  = _gh_get_sha(token, path)
    data = {"message": msg, "content": base64.b64encode(content_bytes).decode()}
    if sha:
        data["sha"] = sha
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/{path}",
        data=json.dumps(data).encode(), headers=_gh_headers(token), method="PUT")
    with urllib.request.urlopen(req):
        pass

def _adicionar_links_portal(token, nome_ef, nome_esf, data_ref):
    url = f"https://api.github.com/repos/{REPO}/contents/index.html"
    req = urllib.request.Request(url, headers=_gh_headers(token))
    with urllib.request.urlopen(req) as r:
        resp       = json.loads(r.read())
        sha        = resp["sha"]
        html_atual = base64.b64decode(resp["content"]).decode("utf-8")

    ref_str  = data_ref.strftime("%d/%m/%Y")
    now_str  = datetime.now().strftime("%d/%m/%Y às %H:%M")

    btn_ef = (
        f'    <a href="{nome_ef}" class="btn">\n'
        f'      <span class="btn-icon">📈</span>\n'
        f'      <div><div class="btn-title">Efetividade · {ref_str}</div>'
        f'<div class="btn-sub">{nome_ef}</div></div>\n'
        f'    </a>'
    )
    btn_esf = (
        f'    <a href="{nome_esf}" class="btn">\n'
        f'      <span class="btn-icon">🎯</span>\n'
        f'      <div><div class="btn-title">Análise de Esforço · {ref_str}</div>'
        f'<div class="btn-sub">{nome_esf}</div></div>\n'
        f'    </a>'
    )

    html_novo = html_atual

    if nome_ef not in html_novo:
        m = re.search(r'(<a href="efetividade_[^"]+\.html")', html_novo)
        if m:
            html_novo = html_novo[:m.start()] + btn_ef + "\n" + html_novo[m.start():]
        else:
            m2 = re.search(r'(<a href=)', html_novo)
            if m2:
                html_novo = html_novo[:m2.start()] + btn_ef + "\n" + html_novo[m2.start():]

    if nome_esf not in html_novo:
        m = re.search(r'(<a href="esforco_[^"]+\.html")', html_novo)
        if m:
            html_novo = html_novo[:m.start()] + btn_esf + "\n" + html_novo[m.start():]
        else:
            if btn_ef in html_novo:
                html_novo = html_novo.replace(btn_ef, btn_ef + "\n" + btn_esf, 1)

    badge = (
        f'<div id="last-updated" style="position:fixed;bottom:16px;right:16px;'
        f'font-size:11px;color:#9ca3af;background:rgba(255,255,255,0.92);'
        f'padding:5px 12px;border-radius:20px;border:1px solid #e3e6ea;'
        f'box-shadow:0 1px 3px rgba(0,0,0,.06);z-index:9999">'
        f'Atualizado {now_str}</div>'
    )
    if 'id="last-updated"' in html_novo:
        html_novo = re.sub(r'<div id="last-updated"[^>]*>.*?</div>', badge, html_novo, flags=re.DOTALL)
    else:
        html_novo = html_novo.replace("</body>", badge + "\n</body>", 1)

    if html_novo == html_atual:
        print("  portal já contém esses links, nada alterado")
        return

    data = {"message": f"Adiciona links {data_ref} ao portal", "content": base64.b64encode(html_novo.encode("utf-8")).decode(), "sha": sha}
    req  = urllib.request.Request(url, data=json.dumps(data).encode(), headers=_gh_headers(token), method="PUT")
    with urllib.request.urlopen(req):
        pass
    print("  portal index.html atualizado")


def gerar_diretivo(dados_ef, canal_mix, data_ref, totais=None):
    if totais:
        pef_time = totais["pef"]
    else:
        total_ef    = sum(r["ef"]    for r in dados_ef)
        total_prazo = sum(r["prazo"] for r in dados_ef)
        pef_time    = round(total_ef / total_prazo * 100, 1) if total_prazo > 0 else 0

    gap = []
    for r in dados_ef:
        if r["cart"] > 0:
            conv_rec = max(0, math.ceil(r["cart"] * 0.70) - r["ef"])
            if conv_rec > 0:
                gap.append((r["nome"].split()[0], conv_rec))
    gap.sort(key=lambda x: x[1], reverse=True)
    top3 = gap[:3]

    ef_data = canal_mix.get("efetivos", {})
    canais = {
        "WhatsApp": ef_data.get("pct_whatsapp", 0),
        "Chamada":  ef_data.get("pct_chamada",  0),
        "Reunião":  ef_data.get("pct_reuniao",  0),
    }
    canal_top = max(canais, key=canais.get) if canais else "WhatsApp"
    canal_pct = canais.get(canal_top, 0)

    linhas = ["🎯 *Foco de hoje:*"]
    if pef_time >= 70:
        linhas.append(f"• Time em *{pef_time}%* de efetividade — meta atingida! Manter ritmo.")
    else:
        if totais:
            conv_total = max(0, math.floor(totais["elegiveis"] * 0.70) + 1 - totais["efetivas"])
        else:
            conv_total = sum(c[1] for c in gap)
        linhas.append(f"• Time em *{pef_time}%* — faltam {conv_total} conversões para chegar a 70%.")
    if top3:
        nomes_gap = ", ".join(f"{n} (+{c})" for n, c in top3)
        linhas.append(f"• Maior alavanca: {nomes_gap} — priorizar hoje.")
    if canal_pct > 0:
        linhas.append(f"• Canal que mais converte: *{canal_top}* ({canal_pct}% das atividades efetivas) — usar como principal abordagem.")
    return "\n".join(linhas)


def send_gchat(text):
    data = json.dumps({"text": text}).encode("utf-8")
    req  = urllib.request.Request(GCHAT_WEBHOOK, data=data,
                                  headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10):
        pass


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir",      required=True,  help="Diretório com os JSONs do agente")
    parser.add_argument("--github-token",  required=True,  help="GitHub Personal Access Token")
    args = parser.parse_args()

    d     = args.data_dir
    token = args.github_token

    data_ref = date.today()
    data_ant = dia_util_anterior(data_ref)
    sufixo   = data_ref.strftime("%d%m")

    print(f"▶ Gerando análises para {data_ref.strftime('%d/%m/%Y')}...")

    print("  carregando dados do BigQuery (via JSON)...")
    dados_hoje  = parse_efetividade(load_json(os.path.join(d, "efetividade_hoje.json")))
    dados_ontem = parse_efetividade(load_json(os.path.join(d, "efetividade_ontem.json")))
    dados_esf   = parse_esforco(load_json(os.path.join(d, "esforco.json")))
    canal_mix   = parse_canal_mix(load_json(os.path.join(d, "canal_mix.json")))
    totais      = parse_efetividade_total(load_json(os.path.join(d, "efetividade_total.json")))
    carteira_total = parse_carteira_total(load_json(os.path.join(d, "carteira_total.json")))
    base_cruzada   = parse_base_cruzada(load_json(os.path.join(d, "base_cruzada.json")))

    if not dados_hoje:
        sys.exit(f"❌  Nenhum dado encontrado em efetividade_hoje.json")

    print(f"  efetividade total: {totais['pef']}% ({totais['efetivas']} de {totais['elegiveis']} escolas)")

    print("  gerando HTMLs...")
    html_ef   = gerar_html_efetividade(dados_hoje, dados_ontem, data_ref)
    html_esf  = gerar_html_esforco(dados_hoje, dados_esf, canal_mix, data_ref, totais, carteira_total, base_cruzada)
    html_meta = gerar_html_meta_distribuida(dados_hoje, data_ref, totais)

    nome_ef  = f"efetividade_{data_ref.strftime('%d_%m')}.html"
    nome_esf = "analise_de_esforco_time.html"

    print("  publicando no GitHub Pages...")
    gh_put(token, nome_ef,                       html_ef.encode("utf-8"),   f"Atualiza efetividade {data_ref}")
    gh_put(token, nome_esf,                       html_esf.encode("utf-8"),  f"Atualiza análise de esforço {data_ref}")
    gh_put(token, "meta_distribuida_70pct.html", html_meta.encode("utf-8"), f"Atualiza meta distribuída {data_ref}")

    print("  atualizando portal...")
    _adicionar_links_portal(token, nome_ef, nome_esf, data_ref)

    ref_str = data_ref.strftime("%d/%m/%Y")
    print(f"\n✅  Publicado com sucesso! {URL_SITE}")

    diretivo = gerar_diretivo(dados_hoje, canal_mix, data_ref, totais)
    msg = (
        f"📊 *Dashboards CS Ops atualizados — {ref_str}*\n"
        f"Efetividade · Esforço · Meta 70% publicados.\n\n"
        f"{diretivo}\n\n"
        f"🔗 {URL_SITE}"
    )
    send_gchat(msg)
    print("💬  Mensagem enviada ao GChat.")


if __name__ == "__main__":
    main()
