"""
Vercel Serverless Entrypoint for Shopee Agency Pro Web Application.
Exposes 'app' (FastAPI ASGI application) for cloud deployment.
Provides:
- Web Dashboard (HTML/Tailwind) at '/'
- Calculation API at '/api/calculate'
- Health check at '/api/health'
"""

import sys
import os
import tempfile
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse

from services.excel_loader import ExcelLoader
from services.lead_time_calculator import LeadTimeCalculator
from services.revenue_calculator import RevenueCalculator
from models import LeadTimeSummary, RevenueSummary

app = FastAPI(
    title="Shopee Agency Pro - Web API & Dashboard",
    description="SaaS Cloud Platform for Shopee Service Points Lead Time & Revenue Management",
    version="1.0.0",
)


@app.get("/api/health")
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "online", "platform": "Vercel Serverless", "service": "Shopee Agency Pro"}


@app.get("/")
@app.get("/api")
@app.get("/api/index")
@app.get("/api/index.py")
def serve_dashboard():
    """Serves the interactive modern SaaS web dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Shopee Agency Pro - Gestão de Lead Time & Faturamento</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            shopee: '#EE4D2D',
            shopeedark: '#D03E20',
            primarydark: '#1F497D',
          }
        }
      }
    }
  </script>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col font-sans">

  <!-- Header -->
  <header class="bg-primarydark text-white shadow-md">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col md:flex-row justify-between items-center gap-4">
      <div class="flex items-center gap-3">
        <div class="bg-shopee text-white p-2.5 rounded-lg shadow font-bold text-xl">
          <i class="fa-solid fa-box-open"></i>
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">Shopee Agency Pro</h1>
          <p class="text-xs text-amber-300 font-medium">Gestão Oficial de Lead Time Útil & Comissões de Agência</p>
        </div>
      </div>
      <div class="flex items-center gap-2 text-xs bg-slate-800/60 border border-slate-700 rounded-full px-4 py-1.5 text-slate-300">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>Horário Útil: Seg-Sex 08h às 19h30 | Sáb 09h às 15h</span>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">

    <!-- Upload Section -->
    <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 md:p-8 mb-8">
      <div class="max-w-3xl">
        <h2 class="text-lg font-bold text-slate-900 mb-1">Importar Planilhas de Exportação da Shopee</h2>
        <p class="text-sm text-slate-500 mb-6">Envie os relatórios exportados do portal SPX para calcular o Lead Time em horário de funcionamento e as faixas progressivas de faturamento.</p>
      </div>

      <form id="calcForm" class="grid grid-cols-1 md:grid-cols-2 gap-6" onsubmit="handleCalculate(event)">
        <!-- Drop-off File Input -->
        <div class="border-2 border-dashed border-slate-300 hover:border-shopee rounded-xl p-6 transition flex flex-col items-center justify-center text-center bg-slate-50/50 cursor-pointer relative" onclick="document.getElementById('dropoff_file').click()">
          <input type="file" id="dropoff_file" name="dropoff_file" accept=".xlsx,.csv" class="hidden" onchange="updateFileName(this, 'dropoff_label')">
          <i class="fa-solid fa-truck-ramp-box text-3xl text-slate-400 mb-2"></i>
          <span class="text-sm font-semibold text-slate-700">Relatório Drop-off (Postagens & Devoluções)</span>
          <span class="text-xs text-slate-500 mt-1" id="dropoff_label">Selecione o arquivo .xlsx ou .csv</span>
        </div>

        <!-- Collection File Input -->
        <div class="border-2 border-dashed border-slate-300 hover:border-primarydark rounded-xl p-6 transition flex flex-col items-center justify-center text-center bg-slate-50/50 cursor-pointer relative" onclick="document.getElementById('collection_file').click()">
          <input type="file" id="collection_file" name="collection_file" accept=".csv,.xlsx" class="hidden" onchange="updateFileName(this, 'collection_label')">
          <i class="fa-solid fa-people-carry-box text-3xl text-slate-400 mb-2"></i>
          <span class="text-sm font-semibold text-slate-700">Relatório Retiradas (Self-Collection)</span>
          <span class="text-xs text-slate-500 mt-1" id="collection_label">Selecione o arquivo .csv ou .xlsx</span>
        </div>

        <div class="md:col-span-2 flex justify-end">
          <button type="submit" id="btnSubmit" class="w-full md:w-auto px-8 py-3 bg-shopee hover:bg-shopeedark text-white font-bold text-sm rounded-xl shadow-sm transition flex items-center justify-center gap-2 cursor-pointer">
            <i class="fa-solid fa-calculator"></i>
            <span>Calcular Lead Time & Faturamento</span>
          </button>
        </div>
      </form>
    </div>

    <!-- Loading State -->
    <div id="loading" class="hidden bg-white rounded-2xl shadow-sm border border-slate-200 p-12 text-center my-8">
      <div class="inline-block animate-spin rounded-full h-10 w-10 border-4 border-slate-200 border-t-shopee mb-4"></div>
      <p class="text-sm font-semibold text-slate-700">Calculando Lead Time em horário comercial e faixas de remuneração...</p>
      <p class="text-xs text-slate-500 mt-1">Descontando madrugadas, domingos e consolidando volumes.</p>
    </div>

    <!-- Results Section -->
    <div id="results" class="hidden space-y-6">

      <!-- Financial KPI Cards -->
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-700 mb-3 flex items-center gap-2">
          <i class="fa-solid fa-coins"></i> Indicadores Financeiros Consolidados
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
            <span class="text-xs font-bold text-slate-500 uppercase">Faturamento Total</span>
            <div class="text-2xl font-black text-emerald-600 my-1" id="kpi_total_revenue">R$ 0,00</div>
            <span class="text-xs text-slate-400" id="kpi_avg_ticket">Ticket Médio: R$ 0,00 / un</span>
          </div>

          <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
            <span class="text-xs font-bold text-slate-500 uppercase">Devoluções (R$ 0,80)</span>
            <div class="text-2xl font-black text-blue-600 my-1" id="kpi_returns_count">0 un</div>
            <span class="text-xs text-slate-400" id="kpi_returns_rev">R$ 0,00 faturados</span>
          </div>

          <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
            <span class="text-xs font-bold text-slate-500 uppercase">Postagens + Retiradas</span>
            <div class="text-2xl font-black text-slate-800 my-1" id="kpi_pooled_count">0 un</div>
            <span class="text-xs text-slate-400" id="kpi_pooled_detail">0 post. + 0 retiradas</span>
          </div>

          <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
            <span class="text-xs font-bold text-slate-500 uppercase">Volume de Pacotes</span>
            <div class="text-2xl font-black text-purple-600 my-1" id="kpi_volume_count">0 un</div>
            <span class="text-xs text-slate-400" id="kpi_volume_status">Despachados / No ponto</span>
          </div>

        </div>
      </div>

      <!-- Lead Time Card -->
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wider text-primarydark mb-3 flex items-center gap-2">
          <i class="fa-solid fa-stopwatch"></i> SLA Operacional da Agência (Drop-off até o Caminhão)
        </h3>
        <div class="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
            <div>
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wide">Lead Time Útil Médio (Horário de Funcionamento)</span>
              <div class="text-4xl font-black text-shopee my-1" id="kpi_lead_time_formatted">--:--:--</div>
              <p class="text-xs text-slate-500" id="kpi_lead_time_minutes">Média em minutos: -- min</p>
            </div>
            <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 max-w-sm">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>
              <strong>Critério Shopee:</strong> Retiradas de clientes não contam para o Lead Time da agência. Apenas Drop-off (vendedores e devoluções que aguardam coleta).
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 text-center">
            <div>
              <span class="text-[11px] font-bold text-slate-400 uppercase">Menor Tempo</span>
              <div class="text-sm font-bold text-slate-700 mt-0.5" id="stat_min_time">--</div>
            </div>
            <div>
              <span class="text-[11px] font-bold text-slate-400 uppercase">Mediana</span>
              <div class="text-sm font-bold text-slate-700 mt-0.5" id="stat_median_time">--</div>
            </div>
            <div>
              <span class="text-[11px] font-bold text-slate-400 uppercase">Maior Tempo</span>
              <div class="text-sm font-bold text-slate-700 mt-0.5" id="stat_max_time">--</div>
            </div>
            <div>
              <span class="text-[11px] font-bold text-slate-400 uppercase">Pacotes Despachados</span>
              <div class="text-sm font-bold text-slate-700 mt-0.5" id="stat_dispatched_pkgs">--</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Progressive Tiers Breakdown -->
      <div class="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <h4 class="text-xs font-bold uppercase tracking-wider text-slate-600 mb-4">Detalhamento das Faixas Progressivas de Remuneração</h4>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 border-b border-slate-200 font-bold">
              <tr>
                <th class="py-2.5 px-3">Faixa de Volume</th>
                <th class="py-2.5 px-3">Tarifa Unitária</th>
                <th class="py-2.5 px-3">Pacotes Atingidos</th>
                <th class="py-2.5 px-3 text-right">Subtotal Faturado</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100" id="tier_table_body">
              <!-- Dynamically populated -->
            </tbody>
          </table>
        </div>
      </div>

    </div>

  </main>

  <!-- Footer -->
  <footer class="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-400">
    <p>Shopee Agency Pro &copy; 2026. Todos os direitos reservados. Plataforma otimizada para implantação em nuvem Vercel.</p>
  </footer>

  <script>
    function updateFileName(input, labelId) {
      if (input.files && input.files[0]) {
        document.getElementById(labelId).innerText = input.files[0].name;
        document.getElementById(labelId).classList.add('text-shopee', 'font-bold');
      }
    }

    async function handleCalculate(event) {
      event.preventDefault();

      const dropInput = document.getElementById('dropoff_file');
      const collInput = document.getElementById('collection_file');

      if (!dropInput.files[0] && !collInput.files[0]) {
        alert('Por favor, selecione ao menos um arquivo (.xlsx ou .csv) para calcular.');
        return;
      }

      const formData = new FormData();
      if (dropInput.files[0]) formData.append('dropoff_file', dropInput.files[0]);
      if (collInput.files[0]) formData.append('collection_file', collInput.files[0]);

      document.getElementById('loading').classList.remove('hidden');
      document.getElementById('results').classList.add('hidden');

      try {
        const response = await fetch('/api/calculate', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Erro ao processar planilhas.');
        }

        renderResults(data);
      } catch (err) {
        alert('Erro: ' + err.message);
      } finally {
        document.getElementById('loading').classList.add('hidden');
      }
    }

    function renderResults(data) {
      const rev = data.revenue;
      const lead = data.lead_time;

      // KPIs
      document.getElementById('kpi_total_revenue').innerText = 'R$ ' + rev.total_revenue.toFixed(2);
      document.getElementById('kpi_avg_ticket').innerText = 'Ticket Médio: R$ ' + rev.average_ticket.toFixed(2) + ' / un';
      
      document.getElementById('kpi_returns_count').innerText = rev.return_count + ' un';
      document.getElementById('kpi_returns_rev').innerText = 'R$ ' + rev.return_revenue.toFixed(2) + ' faturados';

      document.getElementById('kpi_pooled_count').innerText = rev.pooled_postagem_count + ' un';
      document.getElementById('kpi_pooled_detail').innerText = rev.standard_drop_count + ' post. + ' + rev.collection_count + ' retiradas';

      document.getElementById('kpi_volume_count').innerText = rev.total_packages_moved + ' un';
      document.getElementById('kpi_volume_status').innerText = (rev.total_dispatched_count || rev.total_packages_moved) + ' concluídos | ' + (rev.total_pending_count || 0) + ' pendentes';

      // Lead Time
      if (lead && lead.dispatched_packages > 0) {
        document.getElementById('kpi_lead_time_formatted').innerText = lead.average_business_time_formatted;
        document.getElementById('kpi_lead_time_minutes').innerText = 'Média em minutos: ' + lead.average_business_minutes.toFixed(1) + ' min (' + lead.dispatched_packages + ' despachados)';
        document.getElementById('stat_min_time').innerText = lead.min_business_time_formatted;
        document.getElementById('stat_median_time').innerText = lead.median_business_time_formatted;
        document.getElementById('stat_max_time').innerText = lead.max_business_time_formatted;
        document.getElementById('stat_dispatched_pkgs').innerText = lead.dispatched_packages + ' pacotes';
      } else {
        document.getElementById('kpi_lead_time_formatted').innerText = '--:--:--';
        document.getElementById('kpi_lead_time_minutes').innerText = 'Nenhum pacote despachado no arquivo.';
        document.getElementById('stat_min_time').innerText = '--';
        document.getElementById('stat_median_time').innerText = '--';
        document.getElementById('stat_max_time').innerText = '--';
        document.getElementById('stat_dispatched_pkgs').innerText = '0';
      }

      // Tiers Table
      const tbody = document.getElementById('tier_table_body');
      tbody.innerHTML = `
        <tr>
          <td class="py-2 px-3 font-semibold text-slate-700">Faixa 1 (1 a 500 pacotes)</td>
          <td class="py-2 px-3">R$ 0,70</td>
          <td class="py-2 px-3">${rev.tier1_count} un</td>
          <td class="py-2 px-3 text-right font-bold text-slate-900">R$ ${rev.tier1_revenue.toFixed(2)}</td>
        </tr>
        <tr>
          <td class="py-2 px-3 font-semibold text-slate-700">Faixa 2 (501 a 1.000 pacotes)</td>
          <td class="py-2 px-3">R$ 0,60</td>
          <td class="py-2 px-3">${rev.tier2_count} un</td>
          <td class="py-2 px-3 text-right font-bold text-slate-900">R$ ${rev.tier2_revenue.toFixed(2)}</td>
        </tr>
        <tr>
          <td class="py-2 px-3 font-semibold text-slate-700">Faixa 3 (1.001 a 1.500 pacotes)</td>
          <td class="py-2 px-3">R$ 0,50</td>
          <td class="py-2 px-3">${rev.tier3_count} un</td>
          <td class="py-2 px-3 text-right font-bold text-slate-900">R$ ${rev.tier3_revenue.toFixed(2)}</td>
        </tr>
      `;

      document.getElementById('results').classList.remove('hidden');
      document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.post("/api/calculate")
@app.post("/calculate")
@app.post("/api/index/calculate")
async def calculate_metrics(
    dropoff_file: Optional[UploadFile] = File(None),
    collection_file: Optional[UploadFile] = File(None),
):
    """
    Receives Drop-off (.xlsx) and/or Collection (.csv) files, runs calculation engine,
    and returns full JSON metrics.
    """
    if not dropoff_file and not collection_file:
        return JSONResponse(
            status_code=400,
            content={"detail": "É necessário enviar ao menos um arquivo de Drop-off ou Retiradas."},
        )

    temp_drop_path = None
    temp_coll_path = None

    try:
        lead_calc = LeadTimeCalculator()
        rev_calc = RevenueCalculator()

        df_drop_lead = None
        df_drop_raw = None
        df_coll_raw = None
        drop_lead_summary = None
        d_tag_col = "Tag"

        # 1. Process Drop-off if provided
        if dropoff_file and dropoff_file.filename:
            suffix = Path(dropoff_file.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_drop:
                content = await dropoff_file.read()
                tmp_drop.write(content)
                temp_drop_path = Path(tmp_drop.name)

            loader_drop = ExcelLoader(temp_drop_path)
            df_drop_raw, _, d_tag_col, d_in_col, d_out_col = loader_drop.load_data()
            df_drop_lead, drop_lead_summary = lead_calc.process_lead_times(
                df_drop_raw, d_in_col, d_out_col, is_collection=False
            )

        # 2. Process Collection if provided
        if collection_file and collection_file.filename:
            suffix = Path(collection_file.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_coll:
                content = await collection_file.read()
                tmp_coll.write(content)
                temp_coll_path = Path(tmp_coll.name)

            loader_coll = ExcelLoader(temp_coll_path)
            df_coll_raw, _, _, _, _ = loader_coll.load_data()

        # 3. Consolidated Revenue calculation
        _, _, rev_summary = rev_calc.process_consolidated_revenue(
            df_dropoff=df_drop_lead if df_drop_lead is not None else df_drop_raw,
            tag_col=d_tag_col,
            df_collection=df_coll_raw,
        )

        # 4. Serialize Lead Time results
        lead_dict = None
        if drop_lead_summary:
            lead_dict = {
                "total_packages": drop_lead_summary.total_packages,
                "dispatched_packages": drop_lead_summary.dispatched_packages,
                "pending_packages": drop_lead_summary.pending_packages,
                "average_business_minutes": drop_lead_summary.average_business_minutes,
                "average_business_hours": drop_lead_summary.average_business_hours,
                "average_business_time_formatted": LeadTimeCalculator.format_timedelta(
                    drop_lead_summary.average_business_time
                ),
                "median_business_time_formatted": LeadTimeCalculator.format_timedelta(
                    drop_lead_summary.median_business_time
                ),
                "min_business_time_formatted": LeadTimeCalculator.format_timedelta(
                    drop_lead_summary.min_business_time
                ),
                "max_business_time_formatted": LeadTimeCalculator.format_timedelta(
                    drop_lead_summary.max_business_time
                ),
            }

        # 5. Serialize Revenue results
        rev_dict = {
            "total_packages_moved": rev_summary.total_packages_moved,
            "return_count": rev_summary.return_count,
            "return_revenue": rev_summary.return_revenue,
            "standard_drop_count": rev_summary.standard_drop_count,
            "collection_count": rev_summary.collection_count,
            "pooled_postagem_count": rev_summary.pooled_postagem_count,
            "tier1_count": rev_summary.tier1_count,
            "tier1_revenue": rev_summary.tier1_revenue,
            "tier2_count": rev_summary.tier2_count,
            "tier2_revenue": rev_summary.tier2_revenue,
            "tier3_count": rev_summary.tier3_count,
            "tier3_revenue": rev_summary.tier3_revenue,
            "tier4_count": rev_summary.tier4_count,
            "tier4_revenue": rev_summary.tier4_revenue,
            "pooled_postagem_revenue": rev_summary.pooled_postagem_revenue,
            "total_revenue": rev_summary.total_revenue,
            "average_ticket": rev_summary.average_ticket,
            "total_dispatched_count": drop_lead_summary.dispatched_packages if drop_lead_summary else rev_summary.total_packages_moved,
            "total_pending_count": drop_lead_summary.pending_packages if drop_lead_summary else 0,
        }

        return JSONResponse(content={"status": "success", "revenue": rev_dict, "lead_time": lead_dict})

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Erro interno no cálculo: {str(e)}"})
    finally:
        # Cleanup temporary files
        if temp_drop_path and temp_drop_path.exists():
            try:
                temp_drop_path.unlink()
            except Exception:
                pass
        if temp_coll_path and temp_coll_path.exists():
            try:
                temp_coll_path.unlink()
            except Exception:
                pass
