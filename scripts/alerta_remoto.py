#!/usr/bin/env python3
"""
alerta_remoto.py — versão para agente remoto.

Lê dados de arquivos JSON pré-gerados (pelo agente via BigQuery MCP)
e executa a mesma lógica do alerta_diario.py.

Uso:
  python3 alerta_remoto.py --data-dir /tmp/alertas_data
"""

import argparse
import csv
import datetime
import json
import os
import urllib.request
import urllib.error
from collections import defaultdict

# ── Configuração ───────────────────────────────────────────────────────────────
GCHAT_WEBHOOK = (
    "https://chat.googleapis.com/v1/spaces/AAQA7_JxW0Q/messages"
    "?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
    "&token=EVtinsoiO-x4whqjad4FduZ1t-f3LbcmStRWPCLF-TM"
)
APPS_SCRIPT_URL       = "https://script.google.com/macros/s/AKfycbz1tx9n_B0tth90q0c5P3MfNInmgRL8cD4Z5KLp8hlAePYinVFzBksV94v0Vg09NDc1/exec"
SHEET_LINK            = "https://docs.google.com/spreadsheets/d/1ritmf_GFpLzZMmUnQC32p-v7axJynmfwmX4yb3snz9I/edit"
APPS_SCRIPT_URL_TASKS = "https://script.google.com/macros/s/AKfycbwRjRF-1PtY8s9qXGowo6y5aMVNSnlblaswgkxjF40c8Bn_9ErXKqZ2p0tCJf3KDWuu/exec"
SHEET_LINK_TASKS      = "https://docs.google.com/spreadsheets/d/1pNzS756y0u-v7h9gSUlP18Dk846QlmsqZ6K3KlbuBao/edit"
APPS_SCRIPT_URL_DUP   = "https://script.google.com/macros/s/AKfycbyGIgY_ZzyTBVvTI2y6JmcC6L9ENtKKXoALoE3RJi8OJURZH86iZFK-2kgc6iSaAaZSoQ/exec"
SHEET_LINK_DUP        = "https://docs.google.com/spreadsheets/d/1W8Qw7T0kVt9VxR4311-v8qslId4XBLHROA37VAyz-Y4/edit"

# E-mails do time — usados para detectar tarefas fora do time
TEAM_EMAILS = {
    "mariana.santana@estantemagica.com.br",
    "talita.panassol@estantemagica.com.br",
    "carla.gomes@estantemagica.com.br",
    "carine.leite@estantemagica.com.br",
    "julia.loubach@estantemagica.com.br",
    "maria.elvira@estantemagica.com.br",
    "erick.andrade@estantemagica.com.br",
    "mariaeduarda.carvalho@estantemagica.com.br",
    "moreno.loss@estantemagica.com.br",
    "renata.brandao@estantemagica.com.br",
    "andreina.ferreira@estantemagica.com.br",
    "julia.cordeiro@estantemagica.com.br",
    "laura.pagliuzo@estantemagica.com.br",
    "indlayse.ferreira@estantemagica.com.br",
    "thayna.bastos@estantemagica.com.br",
    "larissa.freitas@estantemagica.com.br",
    "tatiana.portela@estantemagica.com.br",
    "shelry.solart@estantemagica.com.br",
    "helena.cabral@estantemagica.com.br",
    "carla.santosdasilva@estantemagica.com.br",
    "pamela.miranda@estantemagica.com.br",
    "anaclara.peres@estantemagica.com.br",
    "anaclaudia.almeida@estantemagica.com.br",
    "viviancristina.souza@estantemagica.com.br",
    "kaian.silva@estantemagica.com.br",
    "claudilene.dias@estantemagica.com.br",
    "stefany.figueredo@estantemagica.com.br",
    "giovanna.munhoz@estantemagica.com.br",
    "mariaclara.lima@estantemagica.com.br",
    "thais.borges@estantemagica.com.br",
    "sarah.moura@estantemagica.com.br",
    "jennifer.anjos@estantemagica.com.br",
    "veronicacristina.carvalho@estantemagica.com.br",
    "agatha.cruz@estantemagica.com.br",
    "junior.gomes@estantemagica.com.br",
    "mariana.mazzero@estantemagica.com.br",
    "paula.valero@estantemagica.com.br",
    "alixibeth.cardiel@estantemagica.com.br",
    "daniela.rojas@estantemagica.com.br",
    "nioximar.villael@estantemagica.com.br",
    "nerbis.carrero@estantemagica.com.br",
    "rubia.toledo@estantemagica.com.br",
    "clarice.silva@estantemagica.com.br",
    "genesis.ramos@estantemagica.com.br",
    "victoria.correa@estantemagica.com.br",
    "erica.fernandez@estantemagica.com.br",
    "julia.alves@estantemagica.com.br",
    "larissa.garcia@estantemagica.com.br",
    "emilia.alves@estantemagica.com.br",
    "maria.fuhr@estantemagica.com.br",
    "mahane@estantemagica.com.br",
}
# ──────────────────────────────────────────────────────────────────────────────


def load_json(path):
    """Lê um arquivo JSON e retorna lista de dicts."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def identificar_manter(grupo):
    resultado = []
    melhor = grupo[0]
    for escola in grupo:
        if escola is melhor:
            if melhor["du_ultima_ef"] < 9999:
                motivo = "Atividade efetiva mais recente"
            elif melhor["du_ultima_atv"] < 9999:
                motivo = "Atividade mais recente"
            elif melhor["score_info"] >= max(e["score_info"] for e in grupo):
                motivo = "Mais informações preenchidas"
            else:
                motivo = "Critério padrão"
            resultado.append({**escola, "decisao": "MANTER", "motivo": motivo})
        else:
            resultado.append({**escola, "decisao": "ARQUIVAR", "motivo": ""})
    return resultado


def build_b1_index(carteiras):
    index = {}
    for row in carteiras:
        sub   = (row.get("sub_segmento") or "").strip()
        email = row.get("email") or row.get("nome")
        carteira = row.get("carteira", 0)
        if "High touch" in sub:
            seg = "High touch"
        elif "Medium touch" in sub:
            seg = "Medium touch"
        elif sub == "Premium touch 40+":
            seg = "Premium touch 40+"
        elif sub == "Premium touch":
            seg = "Premium touch"
        else:
            continue
        index.setdefault(seg, []).append((email, carteira))
    return index


def distribuir_b1(rows_b1, b1_index):
    virtual = {}
    carteira_inicial = {}
    for seg, candidatos in b1_index.items():
        for email, carteira in candidatos:
            virtual.setdefault(seg, {})[email] = carteira
            carteira_inicial[email] = carteira

    por_seg = defaultdict(list)
    for row in rows_b1:
        por_seg[str(row.get("segmentacao") or "")].append(row)

    sugestoes = {}
    contagem  = defaultdict(int)
    for seg, escolas in por_seg.items():
        cands = virtual.get(seg)
        if not cands:
            for e in escolas:
                sugestoes[str(e["id_escola"])] = ""
            continue
        for escola in escolas:
            email = min(cands, key=lambda e: cands[e])
            sugestoes[str(escola["id_escola"])] = email
            cands[email] += 1
            contagem[email] += 1

    resumo = {email: (carteira_inicial.get(email, 0), qt)
              for email, qt in contagem.items()}
    return sugestoes, resumo


def distribuir_ativador(rows_atv, carteiras_atv):
    if not carteiras_atv:
        return {str(r["id_escola"]): "" for r in rows_atv}, {}

    virtual          = {r["nome"]: r["carteira"] for r in carteiras_atv}
    carteira_inicial = dict(virtual)

    sugestoes = {}
    contagem  = defaultdict(int)
    for escola in rows_atv:
        email = min(virtual, key=lambda e: virtual[e])
        sugestoes[str(escola["id_escola"])] = email
        virtual[email] += 1
        contagem[email] += 1

    resumo = {email: (carteira_inicial.get(email, 0), qt)
              for email, qt in contagem.items()}
    return sugestoes, resumo


def adicionar_resumo_b1(matrix, carteiras_b1, resumo_b1):
    ncols = len(matrix[0])
    matrix.append([""] * ncols)
    matrix.append(["Distribuição sugerida"] + [""] * (ncols - 1))
    matrix.append(["Proprietário", "Segmento", "Carteira atual", "Escolas a receber", "Total após"] + [""] * (ncols - 5))
    for row in sorted(carteiras_b1, key=lambda r: (r.get("sub_segmento") or "", r.get("carteira", 0))):
        email = row.get("email") or row.get("nome")
        atual = row.get("carteira", 0)
        receber = resumo_b1.get(email, (atual, 0))[1]
        matrix.append([email, row.get("sub_segmento") or "", atual, receber, atual + receber] + [""] * (ncols - 5))
    return matrix


def adicionar_resumo_atv(matrix, carteiras_atv, resumo_atv):
    ncols = len(matrix[0])
    matrix.append([""] * ncols)
    matrix.append(["Distribuição sugerida"] + [""] * (ncols - 1))
    matrix.append(["Proprietário", "Carteira atual", "Escolas a receber", "Total após"] + [""] * (ncols - 4))
    for row in sorted(carteiras_atv, key=lambda r: r.get("carteira", 0)):
        nome = row.get("nome")
        atual = row.get("carteira", 0)
        receber = resumo_atv.get(nome, (atual, 0))[1]
        matrix.append([nome, atual, receber, atual + receber] + [""] * (ncols - 4))
    return matrix


def post_to_sheet(aba, linhas, url=APPS_SCRIPT_URL, timeout=60):
    try:
        data = json.dumps({"aba": aba, "linhas": linhas}).encode("utf-8")
        req  = urllib.request.Request(url, data=data,
                                      headers={"Content-Type": "application/json"},
                                      method="POST")
        urllib.request.urlopen(req, timeout=timeout)
    except Exception as e:
        print(f"[AVISO] Erro ao escrever aba '{aba}': {e}")


def send_gchat(text):
    data = json.dumps({"text": text}).encode("utf-8")
    req  = urllib.request.Request(GCHAT_WEBHOOK, data=data,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    with urllib.request.urlopen(req, timeout=10):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True,
                        help="Diretório com os JSONs gerados pelo agente")
    args = parser.parse_args()
    d = args.data_dir

    today     = datetime.date.today().strftime("%d/%m/%Y")
    date_short = datetime.date.today().strftime("%d/%m")

    rows_b1          = load_json(os.path.join(d, "sem_b1.json"))
    rows_atv         = load_json(os.path.join(d, "sem_ativador.json"))
    carteiras_b1     = load_json(os.path.join(d, "carteira_b1.json"))
    carteiras_atv    = load_json(os.path.join(d, "carteira_ativador.json"))
    rows_tarefas     = load_json(os.path.join(d, "tarefas.json"))
    rows_tarefas_det = load_json(os.path.join(d, "tarefas_detalhe.json"))
    rows_dup_raw     = load_json(os.path.join(d, "duplicatas.json"))

    b1_index           = build_b1_index(carteiras_b1)
    sug_b1,  resumo_b1  = distribuir_b1(rows_b1, b1_index)
    sug_atv, resumo_atv = distribuir_ativador(rows_atv, carteiras_atv)

    b1_matrix = [["id_escola", "nome", "tipo_de_instituicao", "baldinho", "segmentacao", "etapa", "sugestao_b1"]]
    for row in rows_b1:
        b1_matrix.append([
            str(row.get("id_escola") or ""),
            str(row.get("nome") or ""),
            str(row.get("tipo_de_instituicao") or ""),
            str(row.get("baldinho") or ""),
            str(row.get("segmentacao") or ""),
            str(row.get("etapa") or ""),
            sug_b1.get(str(row.get("id_escola")), ""),
        ])
    adicionar_resumo_b1(b1_matrix, carteiras_b1, resumo_b1)

    atv_matrix = [["id_escola", "nome", "tipo_de_instituicao", "baldinho", "segmentacao", "etapa", "data_para_agendamento_bv", "sugestao_ativador"]]
    for row in rows_atv:
        atv_matrix.append([
            str(row.get("id_escola") or ""),
            str(row.get("nome") or ""),
            str(row.get("tipo_de_instituicao") or ""),
            str(row.get("baldinho") or ""),
            str(row.get("segmentacao") or ""),
            str(row.get("etapa") or ""),
            str(row.get("data_para_agendamento_bv") or ""),
            sug_atv.get(str(row.get("id_escola")), ""),
        ])
    adicionar_resumo_atv(atv_matrix, carteiras_atv, resumo_atv)

    sobrecarregados = [(r["assigned_to"], r["tarefas"]) for r in rows_tarefas if r.get("tarefas", 0) >= 60]
    abaixo_ideal    = [(r["assigned_to"], r["tarefas"]) for r in rows_tarefas if r.get("tarefas", 0) < 30]

    tarefas_matrix = [["proprietario", "tarefas_pendentes", "status"]]
    for row in rows_tarefas:
        qt = row.get("tarefas", 0)
        if qt >= 60:
            status = "Sobrecarregado"
        elif qt < 30:
            status = "Abaixo do ideal"
        else:
            status = "OK"
        tarefas_matrix.append([str(row.get("assigned_to") or ""), str(qt), status])

    tarefas_fora_time = [
        r for r in rows_tarefas_det
        if (r.get("assigned_to") or "").lower() not in TEAM_EMAILS
    ]

    grupos_dup = defaultdict(list)
    for r in rows_dup_raw:
        grupos_dup[r["actor_uuid"]].append(r)

    dup_decididas = []
    for grupo in grupos_dup.values():
        dup_decididas.extend(identificar_manter(grupo))

    n_grupos_dup  = len(grupos_dup)
    n_escolas_dup = len(dup_decididas)

    dup_matrix = [["actor_uuid", "id_escola", "nome", "etapa", "segmentacao", "baldinho",
                   "proprietario_b1", "du_ultima_atv", "du_ultima_ef", "tem_bv", "decisao", "motivo"]]
    for e in dup_decididas:
        du_atv = "" if e.get("du_ultima_atv", 9999) >= 9999 else str(e["du_ultima_atv"])
        du_ef  = "" if e.get("du_ultima_ef",  9999) >= 9999 else str(e["du_ultima_ef"])
        dup_matrix.append([
            str(e.get("actor_uuid")      or ""),
            str(e.get("id_ax")           or ""),
            str(e.get("nome")            or ""),
            str(e.get("etapa")           or ""),
            str(e.get("segmentacao")     or ""),
            str(e.get("baldinho")        or ""),
            str(e.get("proprietario_b1") or ""),
            du_atv, du_ef,
            "Sim" if e.get("tem_bv") else "Não",
            e.get("decisao", ""),
            e.get("motivo", ""),
        ])

    post_to_sheet(f"Sem B1 {date_short}", b1_matrix)
    post_to_sheet(f"Sem Ativador {date_short}", atv_matrix)
    post_to_sheet(f"Tarefas {date_short}", tarefas_matrix, url=APPS_SCRIPT_URL_TASKS)
    if n_grupos_dup > 0:
        post_to_sheet(f"Duplicatas {date_short}", dup_matrix, url=APPS_SCRIPT_URL_DUP)

    if tarefas_fora_time:
        fora_matrix = [["id_tarefa", "task_title", "assigned_to"]]
        for r in tarefas_fora_time:
            fora_matrix.append([
                str(r.get("id_tarefa") or ""),
                str(r.get("task_title") or ""),
                str(r.get("assigned_to") or ""),
            ])
        post_to_sheet(f"Tarefas Fora Time {date_short}", fora_matrix, url=APPS_SCRIPT_URL_TASKS)

    ok_count = len(rows_tarefas) - len(sobrecarregados) - len(abaixo_ideal)

    msg = (
        f"🚨 *Alertas CS Ops — {today}*\n\n"
        f"*1️⃣ Proprietários*\n"
        f"👤 Sem B1: *{len(rows_b1)} escola(s)*\n"
        f"📅 Sem ativador: *{len(rows_atv)} escola(s)*\n"
        f"📊 <{SHEET_LINK}|Ver planilha de proprietários>\n\n"
        + (
            f"*2️⃣ Escolas duplicadas*\n"
            f"🔁 *{n_grupos_dup} grupo(s)* — {n_escolas_dup} escola(s) com actor duplicado\n"
            f"📊 <{SHEET_LINK_DUP}|Ver planilha de duplicatas>\n\n"
            if n_grupos_dup > 0 else ""
        )
        + f"*{'3️⃣' if n_grupos_dup > 0 else '2️⃣'} Tarefas de foco geradas hoje*\n"
        f"⬆️ Sobrecarregados (≥60): *{len(sobrecarregados)} pessoa(s)*\n"
        f"⬇️ Abaixo do ideal (<30): *{len(abaixo_ideal)} pessoa(s)*\n"
        f"✅ OK (30–59): *{ok_count} pessoa(s)*\n"
        + (f"⚠️ *{len(tarefas_fora_time)} tarefa(s) atribuída(s) a pessoa fora do time* — "
           f"ver aba \"Tarefas Fora Time {date_short}\"\n" if tarefas_fora_time else "")
        + f"📊 <{SHEET_LINK_TASKS}|Ver planilha de tarefas>"
    )

    send_gchat(msg)
    print(f"[OK] {today} — sem_b1={len(rows_b1)}, sem_ativador={len(rows_atv)}, duplicatas={n_grupos_dup} grupos")


if __name__ == "__main__":
    main()
