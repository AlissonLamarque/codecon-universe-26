#!/usr/bin/env python3
"""
report.py — Gerador de Métricas Corporativas Sérias™

Lê o arquivo events.jsonl e produz um relatório executivo com KPIs
de prevenção ao burnout, incluindo o prestigiado Índice de Overwork
Evitado (IOE), métrica proprietária do Método Comodoro™.

Uso:
    python report.py
    python report.py --log logs/events.jsonl
    python report.py --log logs/events.jsonl --export relatorio.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Caminho default do log (mesmo usado em config.py)
DEFAULT_LOG_PATH = os.path.join("logs", "events.jsonl")

# Largura do relatório no terminal
REPORT_WIDTH = 72


# ── Modelos de dados ─────────────────────────────────────────────────

@dataclass
class RestCycle:
    """Representa um ciclo completo de descanso."""
    start_ts: datetime
    end_ts: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        if self.end_ts is None:
            return 0.0
        return (self.end_ts - self.start_ts).total_seconds()


@dataclass
class ReportData:
    """Dados agregados extraídos do log de eventos."""
    total_blocks: int = 0
    blocked_apps: Counter = field(default_factory=Counter)
    completed_cycles: int = 0
    incomplete_cycles: int = 0
    total_rest_minutes: float = 0.0
    rest_cycles: list[RestCycle] = field(default_factory=list)
    first_event_ts: datetime | None = None
    last_event_ts: datetime | None = None
    total_events: int = 0
    panic_interventions: int = 0
    relax_escapes: int = 0
    autocratic_blocks: int = 0


# ── Parsing do log ───────────────────────────────────────────────────

def _parse_timestamp(ts_str: str) -> datetime | None:
    """Parse de timestamp ISO. Tenta múltiplos formatos."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def parse_log(log_path: str) -> ReportData:
    """
    Lê o events.jsonl e agrega as métricas em um ReportData.

    Eventos reconhecidos (baseado no logger_utils.py existente):
        - BLOCKED (com reason, process, autocratic)
        - ENTER_REST (início de ciclo de descanso)
        - ENTER_WORK (fim do descanso / início de produtividade)
        - APP_STARTED / APP_STOPPED
    """
    data = ReportData()
    current_rest: RestCycle | None = None

    if not os.path.isfile(log_path):
        print(f"[ERRO] Arquivo de log não encontrado: {log_path}", file=sys.stderr)
        sys.exit(1)

    with open(log_path, "r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                entry: dict[str, Any] = json.loads(raw_line)
            except json.JSONDecodeError:
                print(
                    f"[AVISO] Linha {line_number} ignorada (JSON inválido).",
                    file=sys.stderr,
                )
                continue

            data.total_events += 1
            ts = _parse_timestamp(entry.get("ts", ""))

            # Rastrear primeiro/último evento
            if ts:
                if data.first_event_ts is None or ts < data.first_event_ts:
                    data.first_event_ts = ts
                if data.last_event_ts is None or ts > data.last_event_ts:
                    data.last_event_ts = ts

            event = entry.get("event", "")

            # ── Bloqueios de apps produtivos ──
            if event == "BLOCKED":
                data.total_blocks += 1
                process = entry.get("process", "desconhecido")
                data.blocked_apps[process] += 1

                if entry.get("autocratic", False):
                    data.autocratic_blocks += 1

                reason = entry.get("reason", "")
                if reason == "PANIC":
                    data.panic_interventions += 1
                elif reason == "RELAX_ESCAPE":
                    data.relax_escapes += 1

            # ── Início de descanso ──
            elif event == "ENTER_REST":
                if ts:
                    current_rest = RestCycle(start_ts=ts)

            # ── Fim do descanso (início do trabalho) ──
            elif event == "ENTER_WORK":
                if current_rest and ts:
                    current_rest.end_ts = ts
                    data.rest_cycles.append(current_rest)
                    data.completed_cycles += 1
                    data.total_rest_minutes += current_rest.duration_seconds / 60.0
                    current_rest = None

            # ── O app começa em REST_FORCED, conta como ciclo incompleto
            #    se nunca transitou para ENTER_WORK
            elif event == "APP_STARTED":
                # O app inicia em modo descanso; criamos um ciclo provisório
                if ts:
                    current_rest = RestCycle(start_ts=ts)

    # Se há um ciclo de descanso aberto (app fechado durante descanso),
    # contabiliza como incompleto
    if current_rest is not None:
        data.incomplete_cycles += 1
        if data.last_event_ts and current_rest.start_ts:
            partial_minutes = (
                data.last_event_ts - current_rest.start_ts
            ).total_seconds() / 60.0
            data.total_rest_minutes += max(0, partial_minutes)

    return data


# ── Cálculo do IOE ───────────────────────────────────────────────────

def calculate_ioe(data: ReportData) -> float:
    """
    Calcula o Índice de Overwork Evitado (IOE)™.

    Fórmula proprietária (100% inventada e cientificamente duvidosa):

        IOE = (B × 12.5 + C × 25 + R × 1.8 + P × 50) / max(E, 1) × 100

    Onde:
        B = Total de bloqueios de apps produtivos
        C = Ciclos completos de descanso
        R = Minutos totais em descanso
        P = Intervenções de pânico
        E = Total de eventos registrados

    Interpretação corporativa do IOE:
        0-25    → Colaborador em risco. RH notificado.
        25-50   → Descanso insuficiente. Precisa de mais intervenção.
        50-75   → Bom nível de prevenção. Continue assim.
        75-100  → Excelência em anti-produtividade. Promoção recomendada.
        100+    → Overwork foi completamente erradicado. Nirvana corporativo.
    """
    numerator = (
        data.total_blocks * 12.5
        + data.completed_cycles * 25
        + data.total_rest_minutes * 1.8
        + data.panic_interventions * 50
    )
    denominator = max(data.total_events, 1)
    return (numerator / denominator) * 100


def _ioe_classification(ioe: float) -> str:
    """Retorna a classificação corporativa do IOE."""
    if ioe >= 100:
        return "🏆 NIRVANA CORPORATIVO — Overwork erradicado com sucesso"
    if ioe >= 75:
        return "🌟 EXCELÊNCIA — Promoção ao cargo de Diretor de Ócio recomendada"
    if ioe >= 50:
        return "✅ BOM — Níveis aceitáveis de anti-produtividade"
    if ioe >= 25:
        return "⚠️  ATENÇÃO — Descanso insuficiente detectado"
    return "🚨 CRÍTICO — Colaborador em risco de overwork. RH notificado."


# ── Formatação do relatório ──────────────────────────────────────────

def _header(text: str) -> str:
    """Gera um cabeçalho de seção corporativo."""
    return f"\n{'─' * REPORT_WIDTH}\n  {text}\n{'─' * REPORT_WIDTH}"


def _kpi_line(label: str, value: str) -> str:
    """Formata uma linha de KPI alinhada."""
    dots = "." * max(2, REPORT_WIDTH - len(label) - len(value) - 6)
    return f"  {label} {dots} {value}"


def format_report(data: ReportData) -> str:
    """Gera o relatório completo formatado para terminal."""
    ioe = calculate_ioe(data)
    lines: list[str] = []

    # ── Header do relatório ──
    lines.append("")
    lines.append("╔" + "═" * (REPORT_WIDTH - 2) + "╗")
    lines.append("║" + "RELATÓRIO EXECUTIVO DE PREVENÇÃO AO OVERWORK".center(REPORT_WIDTH - 2) + "║")
    lines.append("║" + "Método Comodoro™ — Departamento de Métricas Sérias".center(REPORT_WIDTH - 2) + "║")
    lines.append("╚" + "═" * (REPORT_WIDTH - 2) + "╝")

    # ── Período de análise ──
    lines.append(_header("PERÍODO DE ANÁLISE"))
    if data.first_event_ts:
        lines.append(_kpi_line(
            "Início da coleta",
            data.first_event_ts.strftime("%d/%m/%Y %H:%M:%S"),
        ))
    if data.last_event_ts:
        lines.append(_kpi_line(
            "Último registro",
            data.last_event_ts.strftime("%d/%m/%Y %H:%M:%S"),
        ))
    lines.append(_kpi_line("Total de eventos processados", str(data.total_events)))

    # ── KPIs de Bloqueio ──
    lines.append(_header("INDICADORES DE CONTENÇÃO PRODUTIVA"))
    lines.append(_kpi_line(
        "Tentativas de abrir apps produtivos (bloqueios)",
        str(data.total_blocks),
    ))
    lines.append(_kpi_line(
        "Bloqueios em modo autocrático",
        str(data.autocratic_blocks),
    ))
    lines.append(_kpi_line(
        "Intervenções de pânico",
        str(data.panic_interventions),
    ))
    lines.append(_kpi_line(
        "Tentativas de fuga do relax",
        str(data.relax_escapes),
    ))

    if data.blocked_apps:
        lines.append("")
        lines.append("  Apps produtivos interceptados:")
        for app, count in data.blocked_apps.most_common():
            lines.append(f"    • {app:.<40s} {count}x")

    # ── KPIs de Descanso ──
    lines.append(_header("INDICADORES DE DESCANSO CORPORATIVO"))
    lines.append(_kpi_line(
        "Ciclos de descanso completos",
        str(data.completed_cycles),
    ))
    lines.append(_kpi_line(
        "Ciclos de descanso incompletos",
        str(data.incomplete_cycles),
    ))
    lines.append(_kpi_line(
        "Total de minutos em descanso",
        f"{data.total_rest_minutes:.1f} min",
    ))
    if data.completed_cycles > 0:
        avg = data.total_rest_minutes / data.completed_cycles
        lines.append(_kpi_line(
            "Média de descanso por ciclo",
            f"{avg:.1f} min",
        ))

    # ── IOE (o grand finale) ──
    lines.append(_header("ÍNDICE DE OVERWORK EVITADO (IOE)™"))
    lines.append("")
    lines.append(f"  {'IOE':>10s} = {ioe:.2f}")
    lines.append("")
    lines.append(f"  Classificação: {_ioe_classification(ioe)}")
    lines.append("")
    lines.append("  Fórmula: IOE = (B×12.5 + C×25 + R×1.8 + P×50) / E × 100")
    lines.append("  Onde: B=bloqueios, C=ciclos, R=min descanso, P=pânico, E=eventos")
    lines.append("")

    # ── Disclaimer ──
    lines.append("─" * REPORT_WIDTH)
    lines.append(
        "  AVISO LEGAL: Este relatório foi gerado pelo Departamento de Métricas"
    )
    lines.append(
        "  Sérias do Método Comodoro™. Os dados aqui apresentados possuem"
    )
    lines.append(
        "  rigor científico equivalente ao de um horóscopo empresarial."
    )
    lines.append(
        "  Qualquer semelhança com métricas reais é mera coincidência."
    )
    lines.append("─" * REPORT_WIDTH)
    lines.append("")

    return "\n".join(lines)


# ── Janela tkinter do relatório ──────────────────────────────────────

def show_report_window(log_path: str | None = None) -> None:
    """
    Exibe o relatório de métricas em uma janela tkinter estilizada,
    com dezenas de gráficos corporativos altamente científicos.
    """
    import threading
    import tkinter as tk

    path = log_path or DEFAULT_LOG_PATH

    def _run() -> None:
        try:
            # ── Coleta de dados ──
            data = parse_log(path)
            ioe = calculate_ioe(data)
            classification = _ioe_classification(ioe)

            # ── Imports do Matplotlib ──
            import matplotlib
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import numpy as np

            matplotlib.use("TkAgg")

            # ── Cores do tema ──
            BG_DARK = "#F5F5F5"
            BG_CARD = "#FFFFFF"
            FG_TITLE = "#D32F2F"
            FG_HEADING = "#D32F2F"
            FG_LABEL = "#757575"
            FG_VALUE = "#000000"
            FG_DIM = "#9E9E9E"
            FG_IOE = "#D32F2F"
            FONT_FAMILY = "Segoe UI"

            # ── Janela principal ──
            root = tk.Tk()
            root.title("Método Comodoro™ — Painel Executivo")
            root.configure(bg=BG_DARK)
            root.attributes("-topmost", True)
            root.resizable(False, False)

            # Janela mais larga para caber os gráficos
            win_w, win_h = 1200, 800
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            x = max(0, (screen_w - win_w) // 2)
            y = max(0, (screen_h - win_h) // 2)
            root.geometry(f"{win_w}x{win_h}+{x}+{y}")

            # ── Layout: Esquerda (Texto) | Direita (Gráficos) ──
            left_frame = tk.Frame(root, bg=BG_DARK, width=450)
            left_frame.pack(side="left", fill="y", padx=10)
            left_frame.pack_propagate(False)

            right_frame = tk.Frame(root, bg=BG_DARK)
            right_frame.pack(side="right", fill="both", expand=True, padx=10)

            # ── Scrollable frame na esquerda ──
            canvas = tk.Canvas(left_frame, bg=BG_DARK, highlightthickness=0)
            scrollbar = tk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
            content = tk.Frame(canvas, bg=BG_DARK)

            content.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
            )
            canvas.create_window((0, 0), window=content, anchor="nw", width=410)
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

            # ── Helpers de layout ──
            def add_title(parent, text, fg=FG_TITLE, size=16):
                tk.Label(
                    parent, text=text, fg=fg, bg=BG_DARK,
                    font=(FONT_FAMILY, size, "bold"), anchor="w",
                ).pack(fill="x", padx=10, pady=(20, 2))

            def add_subtitle(parent, text, fg=FG_DIM, size=9):
                tk.Label(
                    parent, text=text, fg=fg, bg=BG_DARK,
                    font=(FONT_FAMILY, size), anchor="w",
                ).pack(fill="x", padx=10, pady=(0, 10))

            def add_separator(parent):
                tk.Frame(parent, bg="#E0E0E0", height=1).pack(fill="x", padx=10, pady=8)

            def add_section_heading(parent, text):
                tk.Label(
                    parent, text=text, fg=FG_HEADING, bg=BG_DARK,
                    font=(FONT_FAMILY, 10, "bold"), anchor="w",
                ).pack(fill="x", padx=10, pady=(14, 6))

            def add_kpi_row(parent, label, value, value_color=FG_VALUE):
                row = tk.Frame(parent, bg=BG_CARD)
                row.pack(fill="x", padx=10, pady=2)
                tk.Label(
                    row, text=label, fg=FG_LABEL, bg=BG_CARD,
                    font=(FONT_FAMILY, 9), anchor="w",
                ).pack(side="left", padx=(10, 0), pady=6)
                tk.Label(
                    row, text=str(value), fg=value_color, bg=BG_CARD,
                    font=(FONT_FAMILY, 10, "bold"), anchor="e",
                ).pack(side="right", padx=(0, 10), pady=6)

            # ── Conteúdo Texto (Esquerda) ──
            add_title(content, "📊  RELATÓRIO EXECUTIVO")
            add_subtitle(content, "Departamento de Métricas Sérias  •  Método Comodoro™")
            add_separator(content)

            add_section_heading(content, "PERÍODO DE ANÁLISE")
            if data.first_event_ts:
                add_kpi_row(content, "Início", data.first_event_ts.strftime("%H:%M:%S"))
            if data.last_event_ts:
                add_kpi_row(content, "Fim", data.last_event_ts.strftime("%H:%M:%S"))
            add_kpi_row(content, "Eventos", data.total_events)

            add_separator(content)
            add_section_heading(content, "CONTENÇÃO PRODUTIVA")
            add_kpi_row(content, "Bloqueios autocráticos", data.autocratic_blocks, "#2FD34D")
            add_kpi_row(content, "Intervenções pânico", data.panic_interventions, "#2FD34D")
            add_kpi_row(content, "Fugas do relax", data.relax_escapes, "#2FD34D")

            add_separator(content)
            add_section_heading(content, "DESCANSO CORPORATIVO")
            add_kpi_row(content, "Ciclos completos", data.completed_cycles, "#757575")
            add_kpi_row(content, "Minutos descansados", f"{data.total_rest_minutes:.1f}", "#757575")

            add_separator(content)
            add_section_heading(content, "ÍNDICE DE OVERWORK EVITADO (IOE)™")

            ioe_frame = tk.Frame(content, bg=BG_CARD)
            ioe_frame.pack(fill="x", padx=10, pady=(6, 4))
            ioe_color = "#000000"
            tk.Label(
                ioe_frame, text=f"{ioe:.2f}", fg=ioe_color, bg=BG_CARD,
                font=(FONT_FAMILY, 32, "bold"),
            ).pack(pady=(10, 4))
            tk.Label(
                ioe_frame, text=classification, fg=FG_VALUE, bg=BG_CARD,
                font=(FONT_FAMILY, 9), wraplength=350, justify="center",
            ).pack(pady=(0, 6))

            # Botão fechar na esquerda
            btn_frame = tk.Frame(content, bg=BG_DARK)
            btn_frame.pack(fill="x", padx=10, pady=(20, 20))
            tk.Button(
                btn_frame, text="Voltar ao Trabalho (infelizmente)",
                fg="#FFFFFF", bg="#D32F2F", activeforeground="#FFFFFF", activebackground="#B71C1C",
                font=(FONT_FAMILY, 10, "bold"), relief="flat", cursor="hand2",
                padx=20, pady=8, command=root.destroy,
            ).pack(expand=True)

            # ── Gráficos Matplotlib (Direita) ──
            fig = plt.Figure(figsize=(8, 8), dpi=100, facecolor=BG_DARK)

            # Gráfico 1: Evolução do Nível de Estresse (Linha)
            ax1 = fig.add_subplot(221, facecolor=BG_DARK)
            x_stress = np.linspace(0, max(10, data.total_events), 50)
            # Um decaimento exponencial com picos aleatórios simulando intervenções
            base_stress = 100 * np.exp(-0.1 * x_stress)
            noise = np.random.normal(0, 5, len(x_stress))
            stress_level = np.clip(base_stress + noise, 0, 100)
            
            ax1.plot(x_stress, stress_level, color="#2FD34D", linewidth=2, marker='o', markersize=3)
            ax1.set_title("Nível de Estresse Residual (%)", color=FG_VALUE, pad=10, fontsize=10, fontweight="bold")
            ax1.tick_params(colors=FG_LABEL, labelsize=8)
            ax1.spines["top"].set_visible(False)
            ax1.spines["right"].set_visible(False)
            ax1.spines["bottom"].set_color("#E0E0E0")
            ax1.spines["left"].set_color("#E0E0E0")
            ax1.set_ylim(0, 110)

            # Gráfico 2: Alocação de Tempo (Pizza)
            ax2 = fig.add_subplot(222, facecolor=BG_DARK)
            fake_work_minutes = data.completed_cycles * 0.5  # mock para fingir que trabalhou algo
            rest_min = max(0.1, data.total_rest_minutes)
            labels = ["Descanso Merecido", "Trabalho (infelizmente)"]
            sizes = [rest_min, fake_work_minutes]
            colors = ["#2FD34D", "#9E9E9E"]
            explode = (0.1, 0)
            wedges, texts, autotexts = ax2.pie(
                sizes, explode=explode, labels=labels, colors=colors,
                autopct="%1.1f%%", shadow=True, startangle=140,
                textprops=dict(color="w", fontsize=9)
            )
            ax2.set_title("Distribuição do Tempo", color=FG_VALUE, pad=10, fontsize=10, fontweight="bold")

            # Gráfico 3: Top Apps Produtivos Interceptados (Barras Horizontais)
            ax3 = fig.add_subplot(223, facecolor=BG_DARK)
            if data.blocked_apps:
                top_apps = data.blocked_apps.most_common(5)
                apps = [k for k, v in top_apps][::-1]
                counts = [v for k, v in top_apps][::-1]
                bars = ax3.barh(apps, counts, color="#2FD34D", edgecolor="#2FD34D")
                for bar in bars:
                    width = bar.get_width()
                    ax3.annotate(f"{int(width)}x",
                                 xy=(width, bar.get_y() + bar.get_height() / 2),
                                 xytext=(3, 0), textcoords="offset points",
                                 ha="left", va="center", color=FG_VALUE, fontsize=8)
            else:
                ax3.text(0.5, 0.5, "Nenhum app bloqueado", ha="center", va="center", color=FG_LABEL)
            
            ax3.set_title("Apps Mais Inoportunos", color=FG_VALUE, pad=10, fontsize=10, fontweight="bold")
            ax3.tick_params(colors=FG_LABEL, labelsize=8)
            ax3.spines["top"].set_visible(False)
            ax3.spines["right"].set_visible(False)
            ax3.spines["bottom"].set_color("#E0E0E0")
            ax3.spines["left"].set_color("#E0E0E0")

            # Gráfico 4: Tipos de Intervenção (Rosca/Donut)
            ax4 = fig.add_subplot(224, facecolor=BG_DARK)
            interventions = {
                "Bloqueios Padrão": max(0, data.total_blocks - data.autocratic_blocks),
                "Modo Autocrático": data.autocratic_blocks,
                "Fugas Interceptadas": data.relax_escapes,
                "Modo Pânico": data.panic_interventions
            }
            labels_i = []
            sizes_i = []
            for k, v in interventions.items():
                if v > 0:
                    labels_i.append(k)
                    sizes_i.append(v)
            
            if not sizes_i:
                sizes_i = [1]
                labels_i = ["Sem intervenções"]
            
            colors_i = ["#027617", "#2FD34D", "#9E9E9E", "#757575"]
            wedges2, texts2, autotexts2 = ax4.pie(
                sizes_i, labels=labels_i, colors=colors_i, autopct="%1.1f%%",
                startangle=90, textprops=dict(color="w", fontsize=8), pctdistance=0.85
            )
            # Desenha círculo no centro para criar o Donut
            centre_circle = plt.Circle((0, 0), 0.70, fc=BG_DARK)
            ax4.add_patch(centre_circle)
            ax4.set_title("Perfil das Intervenções", color=FG_VALUE, pad=10, fontsize=10, fontweight="bold")

            fig.tight_layout(pad=3.0)

            # Integrar o Canvas no Tkinter
            canvas_mat = FigureCanvasTkAgg(fig, master=right_frame)
            canvas_mat.draw()
            canvas_mat.get_tk_widget().pack(fill="both", expand=True, pady=10)

            root.mainloop()
        except Exception as e:
            print("Erro ao exibir gráficos:", e)

    threading.Thread(target=_run, daemon=True).start()


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    # Força UTF-8 no stdout para Windows (cp1252 não suporta box-drawing)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

    parser = argparse.ArgumentParser(
        description="Gerador de Relatório Executivo do Método Comodoro™",
    )
    parser.add_argument(
        "--log",
        default=DEFAULT_LOG_PATH,
        help=f"Caminho do arquivo events.jsonl (default: {DEFAULT_LOG_PATH})",
    )
    parser.add_argument(
        "--export",
        default=None,
        help="Exportar relatório para arquivo de texto.",
    )
    args = parser.parse_args()

    data = parse_log(args.log)
    report = format_report(data)

    print(report)

    if args.export:
        with open(args.export, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  📄 Relatório exportado para: {args.export}\n")


if __name__ == "__main__":
    main()

