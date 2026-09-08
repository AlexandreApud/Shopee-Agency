# Shopee Agency Pro 🚀
### Gestão Financeira, Lead Time Útil da Agência & Automação Shopee SPX

[![CI Test Suite](https://github.com/alexandre/shopee-agency-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/alexandre/shopee-agency-pro/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)

**Shopee Agency Pro** é uma solução de engenharia de software de alta performance desenvolvida para donos e operadores de **Pontos de Coleta e Agências Shopee (SPX Service Points)**. 

O sistema automatiza a apuração do novo **SLA de Lead Time Operacional** exigido pela Shopee, consolida o **Faturamento de Comissões por Faixas Progressivas**, persiste o histórico em banco de dados relacional e integra-se diretamente ao portal web da Shopee através de automação headless.

---

## 📌 Principais Funcionalidades

1. **Cálculo Preciso de Lead Time em Horário Comercial Útil:**
   * Desconta automaticamente noites, madrugadas, domingos e intervalos fora do expediente.
   * **Horário da Agência:** Segunda a Sexta das **08:00 às 19:30**, Sábado das **09:00 às 15:00** (Domingo fechado).
   * **Exclusão de Retiradas:** O Lead Time mede estritamente o tempo em que o pacote de **Drop-off (Vendedores e Devoluções)** aguarda a coleta do caminhão. Retiradas de compradores (*Self-Collection*) são excluídas do Lead Time pois o tempo de retirada depende exclusivamente do cliente.

2. **Consolidação Financeira e Pooling de Faixas Progressivas:**
   * **Devoluções (*Return/Refund*):** Remuneração fixa de **R$ 0,80** por pacote.
   * **Postagens Comuns + Retiradas de Compradores:** Compartilham o mesmo teto de volume mensal (*pooled volume*), com virada de faixas progressivas:
     * **Faixa 1 (1 a 500 pacotes):** R$ 0,70 por pacote
     * **Faixa 2 (501 a 1.000 pacotes):** R$ 0,60 por pacote
     * **Faixa 3 (1.001 a 1.500 pacotes):** R$ 0,50 por pacote
     * **Faixa 4 (> 1.500 pacotes):** R$ 0,50 por pacote

3. **Automação Web Headless com o Portal Shopee SPX:**
   * Conexão via **Playwright** utilizando perfil persistente do Google Chrome, mantendo cookies de sessão e login Google com verificação em duas etapas (2FA).
   * Acionamento das rotas de exportação de Drop-off e Retiradas com interceptação direta da API de relatórios (`/sp-api/admin/export/task/list`), realizando o download dos relatórios completos em menos de 5 segundos, sem abrir pop-ups frágeis.

4. **Banco de Dados Local SQLite com Histórico Multi-Mês:**
   * Deduplicação inteligente no nível do banco via `ON CONFLICT(tracking_code) DO UPDATE`.
   * Separação transparente entre **Mês Atual** e **Histórico de Meses Anteriores**.
   * Discriminação operacional clara entre pacotes **Despachados/Coletados** e pacotes **Pendentes no Ponto**.

5. **Interface Gráfica Limpa e Inicializador Invisível:**
   * Interface moderna em abas (`ttk.Notebook`), permitindo alternar entre o dia a dia do mês atual e auditoria de meses passados.
   * Inicializador VBScript (`iniciar_calculadora.vbs`) que executa a aplicação sem abrir ou piscar a janela preta do prompt de comando (CMD).

---

## 🏛️ Arquitetura de Software

O projeto segue os princípios de **Clean Architecture** e responsabilidade única (SRP), desacoplando totalmente as regras de negócio de interfaces ou frameworks externos:

```text
├── .github/
│   └── workflows/
│       └── ci.yml             # Pipeline de testes contínuos automatizados (CI/CD)
├── config.py                  # Parâmetros de negócio, horários, faixas de preço e paths
├── models.py                  # Data Transfer Objects (DTOs) para métricas operacionais e financeiras
├── main.py                    # Ponto de entrada CLI e orquestrador principal
├── requirements.txt           # Dependências de produção
├── iniciar_calculadora.bat    # Script de inicialização rápida com auto-verificação
├── iniciar_calculadora.vbs    # Inicializador silencioso sem janela de console
├── create_shortcut.vbs        # Gerador automático de atalho na Área de Trabalho
├── INSTALADOR_AUTOMATICO.bat  # Auto-instalador de 1 clique para novas máquinas
├── build_distribution_package.py # Compilador do pacote zip de distribuição
├── database/
│   ├── connection.py          # Provedor de conexões SQLite em modo WAL
│   └── repository.py          # Camada de persistência e consultas multi-mês
├── services/
│   ├── business_calendar.py   # Motor de cálculo de tempo útil comercial
│   ├── lead_time_calculator.py# Cálculo estatístico de tempo de permanência (Drop-off)
│   ├── revenue_calculator.py  # Motor de precificação com pooling de faixas
│   ├── monthly_engine.py      # Consolidador histórico mensal do SQLite
│   ├── portal_syncer.py       # Robô Playwright para automação do portal SPX
│   ├── excel_loader.py        # Leitura e sanitização de planilhas (.xlsx e .csv)
│   ├── excel_exporter.py      # Exportador de planilhas enriquecidas e relatórios
│   └── file_classifier.py     # Classificador automático de relatórios
├── ui/
│   └── app_window.py          # Interface gráfica Tkinter com abas limpas
└── tests/
    ├── test_business_calendar.py
    ├── test_lead_time_calculator.py
    ├── test_revenue_calculator.py
    └── test_monthly_engine.py
```

---

## ⚙️ Instalação e Execução

### Opção 1: Inicialização Direta (Ambiente com Python)
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute a aplicação gráfica:
   ```bash
   python main.py
   ```
   *(Ou dê dois cliques em `iniciar_calculadora.bat`)*

### Opção 2: Instalador Automático de 1 Clique (Qualquer PC Novo)
1. Dê dois cliques em **`INSTALADOR_AUTOMATICO.bat`**.
2. O script detecta automaticamente se a máquina tem Python, instala as dependências, verifica o navegador, cria o atalho **`Shopee Agency Pro`** na Área de Trabalho e inicializa o sistema.

### Opção 3: Modo Linha de Comando (CLI)
* Processamento direto de arquivos:
  ```bash
  python main.py --dropoff "caminho/dropoff.xlsx" --collection "caminho/retiradas.csv"
  ```
* Sincronização automatizada com o portal Shopee:
  ```bash
  python main.py --sync
  ```
* Consulta histórica consolidada de um mês:
  ```bash
  python main.py --month 2026-08
  ```

---

## 🧪 Testes Automatizados e CI/CD

O projeto conta com suíte completa de testes unitários para garantir a integridade matemática do faturamento e das regras de Lead Time útil:

```bash
python -m unittest discover -s tests -v
```

### Integração Contínua (GitHub Actions)
Todo `push` ou `pull request` na branch principal dispara o workflow `.github/workflows/ci.yml`, validando os testes em ambientes Linux e Windows com Python 3.11 e 3.12.

---

## 🌐 Roadmap: Expansão SaaS na Nuvem (Vercel)

Com o endurecimento das políticas de Lead Time da Shopee para agências em todo o Brasil, a arquitetura foi desenhada para permitir rápida transição para um modelo **SaaS Web (Software as a Service)**:

* **Frontend Web no Vercel (Next.js / React):** Painel web responsivo onde donos de agência criam conta, sobem suas planilhas e visualizam dashboards gerenciais em tempo real.
* **Banco Multi-Tenant Serverless (Neon Postgres / Turso SQLite):** Armazenamento em nuvem isolando os dados de cada agência.
* **Agente Local de Sincronização:** Pequeno executável cliente que roda na agência do usuário, lê as exportações da Shopee e envia com segurança para a API Web via token de autenticação.
