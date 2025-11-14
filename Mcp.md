# MCP Server MedicAir

Server MCP (Model Context Protocol) per l'interazione con database DuckDB e MotherDuck, progettato per fornire capacità di analisi SQL ad assistenti AI e IDE.

## Scopo

Il server consente di eseguire query SQL su database DuckDB locali, cloud-based MotherDuck e database S3, facilitando l'analisi dati direttamente da assistenti AI come Claude o IDE come Cursor e VS Code.

## Funzionalità Principali

- **Esecuzione query SQL**: strumento `query` per eseguire query nel dialetto SQL di DuckDB
- **Supporto multi-database**: connessione a DuckDB locale, MotherDuck cloud e database S3
- **Modalità read-only**: supporto per connessioni read-only con connessioni short-lived per accesso concorrente
- **SaaS mode**: modalità sicura per MotherDuck che disabilita accesso filesystem e permessi di scrittura
- **Trasporti multipli**: supporto per stdio, SSE e HTTP stream

## Componenti

### Tools
- `query`: esegue query SQL su DuckDB o MotherDuck e restituisce risultati formattati
- `get_starting_prompt`: restituisce il prompt di contesto MedicAir o DuckDB/MotherDuck. **Usa questo tool all'inizio di una conversazione in ChatGPT per ottenere il contesto completo** (vedi nota sotto)

### Prompts
- `duckdb-motherduck-initial-prompt`: prompt iniziale per interagire con DuckDB/MotherDuck (disponibile tramite MCP prompts o tool `get_starting_prompt`)
- `medicair-starting-prompt`: prompt specifico per MedicAir con contesto aziendale e struttura database (disponibile tramite MCP prompts o tool `get_starting_prompt`)

**Nota per ChatGPT/Apps SDK**: ChatGPT non supporta direttamente i prompt MCP nell'interfaccia. Per ottenere il contesto iniziale MedicAir, chiama il tool `get_starting_prompt` all'inizio della conversazione. Questo tool restituisce il prompt completo con tutte le informazioni sul contesto MedicAir, struttura del database e come usare i tools disponibili.

### Database Client
Gestisce connessioni a:
- **DuckDB locale**: file database locali o in-memory (`:memory:`)
- **MotherDuck**: database cloud con autenticazione via token
- **S3**: database DuckDB archiviati su Amazon S3 con supporto httpfs

## Contesto MedicAir

Il server è configurato per supportare MedicAir, gruppo leader nell'home care, fornendo:
- Accesso a database di gestione inventario (`medic_air_demo`) con tabelle per:
  - Catalogo articoli (dati)
  - Giacenze magazzino (giacenze)
  - Tracking lavorazioni (inbound_garage)
  - Macchine in lavorazione (laboratorio, sxt)
  - Storico movimentazioni (uscite_tot)
- Integrazione con server MCP per conoscenza tecnica e gestione inventario

## Caratteristiche Tecniche

- **Versione**: 0.7.2
- **Python**: >=3.10
- **Dipendenze principali**: DuckDB, MCP SDK, Starlette, Uvicorn
- **Formato risposte**: tabelle formattate con tabulate
- **Logging**: configurazione dedicata per debug e monitoraggio

## Utilizzo

Il server può essere eseguito in tre modalità di trasporto:
- **stdio**: comunicazione standard input/output (default)
- **sse**: Server-Sent Events su HTTP
- **stream**: HTTP streamable con supporto JSON opzionale

Configurazione tipica per Cursor/VS Code:
```json
{
  "mcpServers": {
    "mcp-server-medicair": {
      "command": "uvx",
      "args": [
        "mcp-server-medicair",
        "--db-path",
        "md:",
        "--motherduck-token",
        "<TOKEN>"
      ]
    }
  }
}
```

# Integrazione con OpenAI Apps SDK

Per integrare il server MCP con le [OpenAI Apps SDK](https://developers.openai.com/apps-sdk/quickstart/) e renderlo disponibile in ChatGPT, sono necessari i seguenti passaggi:

### Requisiti

L'integrazione con Apps SDK richiede:
1. **Componente Web (Widget HTML)**: Un widget HTML che verrà renderizzato in un iframe in ChatGPT per visualizzare i risultati delle query SQL
2. **Resource Registration**: Registrazione di una resource con tipo `text/html+skybridge` che espone il widget HTML
3. **Tool Metadata OpenAI**: Aggiunta di metadata specifici OpenAI ai tools per l'integrazione
4. **Structured Content**: I tools devono restituire `structuredContent` insieme al contenuto testuale
5. **Transport Stream**: Il server deve essere eseguito in modalità `stream` (già supportato)
6. **CORS**: Gestione corretta delle richieste CORS da ChatGPT
7. **Endpoint `/mcp`**: L'endpoint deve essere `/mcp` (già presente nel trasporto stream)

### Passaggi di Implementazione

#### 1. Creare il Widget HTML ✅

Creare un file `public/query-results-widget.html` che visualizzi i risultati delle query SQL:

```html
<!DOCTYPE html>
<html lang="it">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>MedicAir - Risultati Query</title>
    <style>
      * {
        box-sizing: border-box;
      }
      
      :root {
        --medicair-primary: #0066cc;
        --medicair-primary-dark: #0052a3;
        --medicair-secondary: #00a8e8;
        --medicair-text: #333333;
        --medicair-text-light: #666666;
        --medicair-bg: #f8f9fa;
        --medicair-white: #ffffff;
        --medicair-border: #e0e0e0;
        --medicair-success: #28a745;
        --medicair-shadow: rgba(0, 0, 0, 0.1);
      }
      
      body {
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background: var(--medicair-bg);
        color: var(--medicair-text);
        line-height: 1.6;
      }
      
      .medicair-container {
        width: 100%;
        max-width: 1200px;
        margin: 0 auto;
        padding: 24px;
      }
      
      .medicair-header {
        background: var(--medicair-white);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px var(--medicair-shadow);
        border-left: 4px solid var(--medicair-primary);
      }
      
      .medicair-header h1 {
        margin: 0 0 8px 0;
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--medicair-primary);
      }
      
      .medicair-header p {
        margin: 0;
        color: var(--medicair-text-light);
        font-size: 0.95rem;
      }
      
      .medicair-card {
        background: var(--medicair-white);
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px var(--medicair-shadow);
        margin-bottom: 24px;
      }
      
      .medicair-card h2 {
        margin: 0 0 20px 0;
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--medicair-text);
        border-bottom: 2px solid var(--medicair-border);
        padding-bottom: 12px;
      }
      
      .medicair-table-wrapper {
        overflow-x: auto;
        border-radius: 8px;
        border: 1px solid var(--medicair-border);
      }
      
      table {
        width: 100%;
        border-collapse: collapse;
        margin: 0;
        background: var(--medicair-white);
      }
      
      thead {
        background: linear-gradient(135deg, var(--medicair-primary) 0%, var(--medicair-secondary) 100%);
        color: var(--medicair-white);
      }
      
      th {
        padding: 16px;
        text-align: left;
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      
      td {
        padding: 14px 16px;
        border-bottom: 1px solid var(--medicair-border);
        color: var(--medicair-text);
      }
      
      tbody tr {
        transition: background-color 0.2s ease;
      }
      
      tbody tr:hover {
        background-color: #f5f8ff;
      }
      
      tbody tr:last-child td {
        border-bottom: none;
      }
      
      .medicair-empty {
        text-align: center;
        padding: 48px 24px;
        color: var(--medicair-text-light);
      }
      
      .medicair-empty svg {
        width: 64px;
        height: 64px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
      
      .medicair-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
      }
      
      .medicair-stat-card {
        background: var(--medicair-white);
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 2px 4px var(--medicair-shadow);
        border-left: 3px solid var(--medicair-primary);
      }
      
      .medicair-stat-label {
        font-size: 0.85rem;
        color: var(--medicair-text-light);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
      }
      
      .medicair-stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--medicair-primary);
      }
      
      .medicair-loading {
        text-align: center;
        padding: 48px;
        color: var(--medicair-text-light);
      }
      
      .medicair-loading::after {
        content: "...";
        animation: dots 1.5s steps(4, end) infinite;
      }
      
      @keyframes dots {
        0%, 20% { content: "."; }
        40% { content: ".."; }
        60%, 100% { content: "..."; }
      }
      
      @media (max-width: 768px) {
        .medicair-container {
          padding: 16px;
        }
        
        .medicair-card {
          padding: 16px;
        }
        
        th, td {
          padding: 12px 8px;
          font-size: 0.85rem;
        }
        
        .medicair-stats {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <div class="medicair-container">
      <div class="medicair-header">
        <h1>MedicAir - Risultati Query</h1>
        <p>Analisi dati e reportistica in tempo reale</p>
      </div>
      
      <div id="results-container" class="medicair-card">
        <div class="medicair-loading">Caricamento risultati</div>
      </div>
    </div>

    <script type="module">
      let queryResults = window.openai?.toolOutput?.queryResults ?? null;
      
      const renderResults = () => {
        const container = document.querySelector("#results-container");
        
        if (!queryResults) {
          container.innerHTML = `
            <div class="medicair-empty">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <p>Nessun risultato disponibile</p>
            </div>
          `;
          return;
        }
        
        // Renderizza i risultati della query
        if (queryResults.table || queryResults.data) {
          const data = queryResults.table || queryResults.data;
          const headers = data.headers || Object.keys(data[0] || {});
          const rows = data.rows || data;
          
          if (rows.length === 0) {
            container.innerHTML = `
              <h2>Risultati Query</h2>
              <div class="medicair-empty">
                <p>La query non ha restituito risultati</p>
              </div>
            `;
            return;
          }
          
          let tableHTML = '<h2>Risultati Query</h2>';
          tableHTML += '<div class="medicair-table-wrapper"><table><thead><tr>';
          
          headers.forEach(header => {
            tableHTML += `<th>${header}</th>`;
          });
          
          tableHTML += '</tr></thead><tbody>';
          
          rows.forEach(row => {
            tableHTML += '<tr>';
            headers.forEach(header => {
              const value = row[header] !== undefined ? row[header] : '';
              tableHTML += `<td>${value}</td>`;
            });
            tableHTML += '</tr>';
          });
          
          tableHTML += '</tbody></table></div>';
          
          container.innerHTML = tableHTML;
        } else {
          container.innerHTML = `
            <h2>Risultati Query</h2>
            <div class="medicair-empty">
              <p>Formato dati non supportato</p>
            </div>
          `;
        }
      };
      
      const handleSetGlobals = (event) => {
        const globals = event.detail?.globals;
        if (globals?.toolOutput?.queryResults) {
          queryResults = globals.toolOutput.queryResults;
          renderResults();
        }
      };
      
      window.addEventListener("openai:set_globals", handleSetGlobals, {
        passive: true,
      });
      
      // Renderizza i risultati iniziali se disponibili
      if (queryResults) {
        renderResults();
      }
    </script>
  </body>
</html>
```

#### 2. Registrare la Resource nel Server ✅

Modificare `server.py` per registrare la resource del widget:

**Nota**: Se si verifica l'errore "Unsupported URI scheme: ui", il codice è stato aggiornato per gestire diversi formati di parsing dell'URI. Verificare i log del server per vedere come viene parsato l'URI.

```python
@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available resources including the query results widget."""
    return [
        types.Resource(
            uri="ui://widget/query-results.html",
            name="Query Results Widget",
            description="Widget HTML per visualizzare i risultati delle query SQL",
            mimeType="text/html+skybridge",
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """Read the query results widget HTML."""
    if uri.scheme == "ui" and uri.path == "/widget/query-results.html":
        # Leggi il file HTML del widget
        widget_path = Path("public/query-results-widget.html")
        if widget_path.exists():
            return widget_path.read_text(encoding="utf-8")
        raise ValueError(f"Widget file not found: {widget_path}")
    raise ValueError(f"Unsupported URI scheme: {uri.scheme}")
```

#### 3. Aggiungere Metadata OpenAI ai Tools ✅

Modificare il tool `query` per includere i metadata OpenAI:

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools with OpenAI metadata."""
    return [
        types.Tool(
            name="query",
            description="Use this to execute a query on the MotherDuck or DuckDB database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute that is a dialect of DuckDB SQL",
                    },
                },
                "required": ["query"],
            },
            _meta={
                "openai/outputTemplate": "ui://widget/query-results.html",
                "openai/toolInvocation/invoking": "Eseguendo query SQL...",
                "openai/toolInvocation/invoked": "Query eseguita con successo",
            },
        ),
    ]
```

#### 4. Modificare il Tool Call per Restituire Structured Content ✅

Aggiornare `handle_tool_call` per includere `structuredContent`:

```python
@server.call_tool()
async def handle_tool_call(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution with structured content for Apps SDK."""
    if name == "query":
        if arguments is None:
            return [
                types.TextContent(type="text", text="Error: No query provided")
            ]
        
        tool_response = db_client.query(arguments["query"])
        
        # Parsing dei risultati per structuredContent
        # (dipende dal formato restituito da db_client.query)
        
        return [
            types.TextContent(type="text", text=str(tool_response)),
            # Aggiungere structuredContent con i dati della query
            # types.StructuredContent(...) se supportato dal SDK
        ]
```

**Approccio Corretto per Passare Dati Strutturati al Widget**:

Per passare dati strutturati al widget HTML quando si usa `outputTemplate` con OpenAI Apps SDK, è necessario utilizzare `EmbeddedResource` con la struttura corretta:

```python
embedded_resource = types.EmbeddedResource(
    type="resource",
    resource=types.Resource(
        uri="ui://widget/query-results.html",
        mimeType="application/json",
        name="Query Results Data",
        description="Structured query results data for widget",
        text=json.dumps({"queryResults": structured_data}),
    ),
)
```

**Struttura Richiesta**:
- `EmbeddedResource` richiede i campi obbligatori: `type="resource"` e `resource=Resource(...)`
- Il campo `resource` deve essere un oggetto `types.Resource` con:
  - `uri`: URI del widget (deve corrispondere a quello specificato in `outputTemplate`)
  - `mimeType`: Tipo MIME dei dati (`application/json` per dati strutturati)
  - `text`: I dati strutturati serializzati come JSON

**Come Funziona**:
Quando OpenAI Apps SDK vede `outputTemplate` nel metadata del tool, passa automaticamente i dati strutturati del tool output al widget tramite `window.openai.toolOutput`. Il widget HTML può quindi accedere ai dati tramite l'evento `openai:set_globals` o direttamente da `window.openai.toolOutput.queryResults`.

**Nota**: Se `EmbeddedResource` fallisce la validazione, il codice fa fallback a restituire solo il contenuto testuale formattato.

#### 5. Verificare CORS nel Transport Stream ✅

Il trasporto `stream` gestisce CORS tramite `StreamableHTTPSessionManager`, ma è necessario aggiungere un middleware CORS esplicito per garantire che ChatGPT possa accedere al server:

```python
from starlette.middleware.cors import CORSMiddleware

# Aggiungere middleware CORS dopo la creazione di starlette_app
starlette_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)
```

**Nota**: In produzione, sostituire `allow_origins=["*"]` con gli origin specifici di ChatGPT per maggiore sicurezza.

#### 6. Eseguire il Server in Modalità Stream ✅

Il server supporta già il trasporto `stream` tramite il parametro `--transport`. Avviare il server con:

```bash
uvx mcp-server-medicair --transport stream --port 8787 --db-path md: --motherduck-token <TOKEN>
```

**Parametri disponibili:**
- `--transport stream`: Abilita il trasporto HTTP streamable (necessario per Apps SDK)
- `--port 8787`: Porta su cui ascoltare (default: 8000)
- `--host`: Host su cui ascoltare (default: 127.0.0.1)
- `--db-path md:`: Path al database MotherDuck
- `--motherduck-token <TOKEN>`: Token di autenticazione MotherDuck
- `--json-response`: Abilita risposte JSON invece di SSE streams (opzionale)

**Verifica:**
Dopo l'avvio, il server dovrebbe loggare:
```
🦆 Connect to Medicair MCP Server at http://127.0.0.1:8787/mcp
CORS middleware configured for Apps SDK integration
```

L'endpoint `/mcp` sarà disponibile per le richieste da ChatGPT.

#### 7. Esporre il Server su Internet Pubblico ✅

**Opzione B: Deploy su Render.com (produzione)**

Per il deploy su Render, configurare il Web Service con:

**Build Command:**
```bash
pip install .
```

**Start Command:**
```bash
python -m mcp_server_medicair --transport stream --host 0.0.0.0 --port $PORT --db-path md: --motherduck-token $MOTHERDUCK_TOKEN
```

**Variabili d'Ambiente su Render:**
- `MOTHERDUCK_TOKEN`: Token di autenticazione MotherDuck
- `PORT`: Gestito automaticamente da Render (non impostare manualmente)

**Note per Render:**
- Il server si lega a `0.0.0.0` per accettare connessioni esterne
- La porta viene letta dalla variabile d'ambiente `$PORT` fornita da Render
- L'endpoint `/mcp` sarà disponibile all'URL pubblico di Render
- L'endpoint `/health` è disponibile per health checks
- CORS è già configurato per permettere richieste da ChatGPT

#### 8. Configurare il Connector in ChatGPT

1. Abilitare la modalità sviluppatore in **Settings → Apps & Connectors → Advanced settings**
2. Cliccare **Create** in **Settings → Connectors**
3. Inserire l'URL HTTPS con `/mcp` (es. `https://<subdomain>.ngrok.app/mcp`)
4. Fornire nome e descrizione del connector
5. Cliccare **Create**

#### 9. Testare l'Integrazione

1. Aprire una nuova chat in ChatGPT
2. Aggiungere il connector dal menu **More** (accessibile dopo il pulsante **+**)
3. **Importante**: All'inizio della conversazione, chiama il tool `get_starting_prompt` per ottenere il contesto completo MedicAir. Puoi chiedere a ChatGPT: "Ottieni il prompt di contesto iniziale" oppure "Chiama get_starting_prompt"
4. Eseguire una query di esempio (es. "Esegui una query per vedere le giacenze disponibili")
5. Verificare che il widget venga renderizzato correttamente con i risultati

### Note Importanti

- **Prompt MCP in ChatGPT**: ChatGPT non supporta direttamente i prompt MCP nell'interfaccia. Per ottenere il contesto MedicAir, usa il tool `get_starting_prompt` all'inizio di ogni conversazione. Questo tool restituisce tutto il contesto necessario (azienda, struttura database, come usare i tools).
- **Aggiornamento Connector**: Dopo ogni modifica al server MCP (tools, metadata, ecc.), aggiornare il connector cliccando **Refresh** in **Settings → Connectors**
- **Structured Content**: Il formato esatto dipende dalla versione del MCP SDK. Potrebbe essere necessario adattare il formato dei dati restituiti
- **Widget HTML**: Il widget deve gestire correttamente gli eventi `openai:set_globals` per aggiornarsi quando i dati cambiano
- **Sicurezza**: In produzione, implementare autenticazione e validazione delle richieste

### Riferimenti

- [OpenAI Apps SDK Quickstart](https://developers.openai.com/apps-sdk/quickstart/)
- [MCP SDK Documentation](https://modelcontextprotocol.io/)
- [Apps SDK Reference](https://developers.openai.com/apps-sdk/reference/)

