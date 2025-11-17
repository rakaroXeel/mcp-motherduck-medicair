/**
 * MedicAir MCP Tool Tester Widget
 * Integrazione con OpenAI Apps SDK per visualizzare risposte JSON dai tool MCP
 */

(function() {
  'use strict';
  
  // Salva i metodi originali della console PRIMA di qualsiasi modifica
  const originalConsoleLog = console.log.bind(console);
  const originalConsoleError = console.error.bind(console);
  const originalConsoleWarn = console.warn.bind(console);
  
  // Riferimento al div dei log (sarà inizializzato quando il DOM è pronto)
  let logOutput = null;
  
  /**
   * Ottiene il riferimento al div dei log (con fallback se non disponibile)
   */
  function getLogOutput() {
    if (!logOutput) {
      logOutput = document.getElementById('log-output');
    }
    return logOutput;
  }
  
  /**
   * Scrive un messaggio nel div dei log
   */
  function writeToLog(message, type = 'log') {
    const logDiv = getLogOutput();
    if (!logDiv) {
      // Se il div non è ancora disponibile, logga solo nella console
      return;
    }
    
    try {
      // Converte il messaggio in stringa
      let logMessage = '';
      if (typeof message === 'string') {
        logMessage = message;
      } else if (message instanceof Error) {
        logMessage = `[ERROR] ${message.message}\n${message.stack || ''}`;
      } else {
        try {
          logMessage = JSON.stringify(message, null, 2);
        } catch (e) {
          logMessage = String(message);
        }
      }
      
      // Aggiunge il prefisso per gli errori
      if (type === 'error') {
        logMessage = `[ERROR] ${logMessage}`;
      }
      
      // Aggiunge il messaggio al div con un a capo
      logDiv.textContent += logMessage + '\n';
      
      // Scroll automatico verso il basso
      logDiv.scrollTop = logDiv.scrollHeight;
    } catch (e) {
      // Se c'è un errore, usa la console originale
      originalConsoleError('Error writing to log div:', e);
    }
  }
  
  /**
   * Wrapper per console.log che scrive anche nel div
   */
  console.log = function(...args) {
    // Chiama la console originale
    originalConsoleLog.apply(console, args);
    
    // Scrive nel div (se disponibile)
    args.forEach(arg => {
      writeToLog(arg, 'log');
    });
  };
  
  /**
   * Wrapper per console.error che scrive anche nel div
   */
  console.error = function(...args) {
    // Chiama la console originale
    originalConsoleError.apply(console, args);
    
    // Scrive nel div (se disponibile)
    args.forEach(arg => {
      writeToLog(arg, 'error');
    });
  };
  
  /**
   * Wrapper per console.warn che scrive anche nel div
   */
  console.warn = function(...args) {
    // Chiama la console originale
    originalConsoleWarn.apply(console, args);
    
    // Scrive nel div (se disponibile) come warning
    args.forEach(arg => {
      const logDiv = getLogOutput();
      if (logDiv) {
        let warnMessage = '';
        if (typeof arg === 'string') {
          warnMessage = `[WARN] ${arg}`;
        } else {
          try {
            warnMessage = `[WARN] ${JSON.stringify(arg, null, 2)}`;
          } catch (e) {
            warnMessage = `[WARN] ${String(arg)}`;
          }
        }
        logDiv.textContent += warnMessage + '\n';
        logDiv.scrollTop = logDiv.scrollHeight;
      }
    });
  };
  
  // Elementi DOM (verranno inizializzati quando il DOM è pronto)
  let requestInput = null;
  let responseOutput = null;
  let statusDiv = null;
  
  /**
   * Inizializza i riferimenti agli elementi DOM
   */
  function initDOMElements() {
    requestInput = document.getElementById('request-input');
    responseOutput = document.getElementById('response-output');
    statusDiv = document.getElementById('status');
    logOutput = document.getElementById('log-output');
    
    console.log('🔵 Widget JS loaded and initialized');
    
    if (!requestInput || !responseOutput || !statusDiv) {
      console.error('❌ Required DOM elements not found:', {
        requestInput: !!requestInput,
        responseOutput: !!responseOutput,
        statusDiv: !!statusDiv
      });
      return false;
    }
    
    if (!logOutput) {
      console.warn('⚠️ Log output div not found, logs will only appear in browser console');
    } else {
      console.log('✅ Log output div found');
      // Aggiungi un messaggio iniziale per confermare che il div funziona
      logOutput.textContent = '📋 Log del Widget inizializzato...\n';
      logOutput.style.display = 'block'; // Assicurati che sia visibile
    }
    
    console.log('✅ DOM elements found');
    return true;
  }

  /**
   * Mostra un messaggio di stato
   */
  function showStatus(message, type = 'info') {
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    statusDiv.style.display = 'block';
  }

  /**
   * Nasconde il messaggio di stato
   */
  function hideStatus() {
    statusDiv.style.display = 'none';
  }

  /**
   * Estrae i dati dal toolOutput di OpenAI Apps SDK
   */
  function extractToolOutput() {
    console.log('🔍 Checking window.openai:', {
      exists: !!window.openai,
      hasToolOutput: !!(window.openai && window.openai.toolOutput),
      toolOutput: window.openai?.toolOutput,
      hasQueryResults: !!(window.openai?.toolOutput?.queryResults)
    });
    
    if (!window.openai) {
      console.log('⚠️ window.openai not available');
      return null;
    }

    // Cerca i dati in diversi possibili percorsi
    const toolOutput = window.openai.toolOutput;
    
    if (!toolOutput) {
      console.log('⚠️ No toolOutput available');
      return null;
    }

    console.log('✅ ToolOutput found:', toolOutput);
    
    // Se c'è queryResults, estrailo (formato EmbeddedResource)
    if (toolOutput.queryResults) {
      console.log('✅ Found queryResults in toolOutput');
      return toolOutput.queryResults;
    }
    
    // Se toolOutput ha una struttura con columns e rows, potrebbe essere già il formato corretto
    if (toolOutput.columns && Array.isArray(toolOutput.rows)) {
      console.log('✅ Found columns/rows structure in toolOutput');
      return toolOutput;
    }
    
    // Se toolOutput è un oggetto con dati strutturati, restituiscilo
    if (typeof toolOutput === 'object' && Object.keys(toolOutput).length > 0) {
      console.log('✅ Using toolOutput as-is');
      return toolOutput;
    }
    
    console.log('⚠️ toolOutput exists but has no usable data');
    return null;
  }

  /**
   * Formatta e mostra la risposta JSON nel textarea
   */
  function displayResponse(data) {
    try {
      if (!data) {
        responseOutput.value = '';
        showStatus('Nessun dato disponibile', 'info');
        return;
      }

      // Serializza in JSON formattato
      const jsonString = JSON.stringify(data, null, 2);
      responseOutput.value = jsonString;
      
      hideStatus();
    } catch (error) {
      console.error('Error displaying response:', error);
      responseOutput.value = `Errore nel formattare la risposta: ${error.message}`;
      showStatus('Errore nel formattare la risposta JSON', 'error');
    }
  }

  /**
   * Aggiorna il campo richiesta se disponibile
   */
  function updateRequestInput(data) {
    if (data && data.toolName) {
      requestInput.value = `Tool: ${data.toolName}`;
      if (data.arguments) {
        requestInput.value += ` | Args: ${JSON.stringify(data.arguments)}`;
      }
    } else if (data && typeof data === 'object') {
      // Prova a estrarre informazioni dalla struttura dati
      const keys = Object.keys(data);
      if (keys.length > 0) {
        requestInput.value = `Dati ricevuti: ${keys.join(', ')}`;
      }
    }
  }

  /**
   * Gestisce l'evento openai:set_globals
   */
  function handleSetGlobals(event) {
    console.log('📨 openai:set_globals event received:', event.detail);

    // Gestisce sia event.detail.globals che event.detail diretto
    const globals = event.detail?.globals ?? event.detail;
    console.log('📦 Globals extracted:', globals);

    if (!globals) {
      console.log('⚠️ Nessun globals presente in event.detail');
      showStatus('Nessun dato ricevuto dal tool MCP', 'error');
      return;
    }

    // 👉 LOG EXTRA per capire la struttura reale
    try {
      console.log('📄 Globals JSON:', JSON.stringify(globals, null, 2));
    } catch (e) {
      console.log('⚠️ Impossibile serializzare globals:', e);
    }

    // 👉 Qui è il punto chiave:
    //  - se esiste globals.toolOutput, usalo
    //  - altrimenti, se esiste globals.text, usalo
    //  - altrimenti, come fallback usa tutto l'oggetto globals
    let toolOutputLike =
      globals.toolOutput ??
      globals.text ??
      globals;

    // Se toolOutputLike è una stringa JSON, prova a parsarla
    if (typeof toolOutputLike === 'string') {
      try {
        const parsed = JSON.parse(toolOutputLike);
        console.log('✅ Parsed JSON string from toolOutput');
        toolOutputLike = parsed;
      } catch (e) {
        console.log('⚠️ toolOutput is string but not valid JSON, using as-is');
      }
    }

    console.log('✅ toolOutput-like data found:', toolOutputLike);

    window.openai = window.openai || {};
    window.openai.toolOutput = toolOutputLike;

    // Usa checkForNewData per gestire l'aggiornamento (evita duplicati)
    if (checkForNewData()) {
      console.log('✅ Data updated via checkForNewData');
    } else {
      // Fallback: prova direttamente extractToolOutput
      const data = extractToolOutput();
      if (data) {
        console.log('✅ Data extracted directly, updating UI');
        updateRequestInput(globals);
        displayResponse(data);
      } else {
        console.log('⚠️ No data extracted from toolOutput');
        showStatus('Nessun dato utilizzabile dal tool MCP', 'info');
      }
    }
  }

  // Variabile per tracciare l'ultimo toolOutput visto (per evitare doppi aggiornamenti)
  let lastToolOutputHash = null;
  
  /**
   * Controlla se ci sono nuovi dati disponibili e aggiorna l'UI
   */
  function checkForNewData() {
    if (!window.openai || !window.openai.toolOutput) {
      return false;
    }
    
    // Crea un hash semplice del toolOutput per vedere se è cambiato
    const currentHash = JSON.stringify(window.openai.toolOutput);
    if (currentHash === lastToolOutputHash) {
      return false; // Nessun cambiamento
    }
    
    lastToolOutputHash = currentHash;
    console.log('🔄 New toolOutput detected, extracting data...');
    
    const data = extractToolOutput();
    if (data) {
      console.log('✅ New data extracted, updating UI');
      updateRequestInput(window.openai.toolOutput);
      displayResponse(data);
      return true;
    }
    
    return false;
  }

  /**
   * Inizializza il widget
   */
  function init() {
    console.log('🚀 Initializing widget...');
    
    // Ascolta l'evento openai:set_globals
    window.addEventListener('openai:set_globals', handleSetGlobals, {
      passive: true
    });
    console.log('👂 Event listener registered for openai:set_globals');
    
    // Ascolta altri possibili eventi
    window.addEventListener('openai:tool_output', function(event) {
      console.log('📨 openai:tool_output event received:', event.detail);
      if (event.detail) {
        window.openai = window.openai || {};
        window.openai.toolOutput = event.detail;
        checkForNewData();
      }
    }, { passive: true });
    console.log('👂 Event listener registered for openai:tool_output');
    
    // Ascolta eventi generici di messaggio (potrebbe essere usato da Apps SDK)
    window.addEventListener('message', function(event) {
      if (event.data && (event.data.type === 'openai:set_globals' || event.data.type === 'tool_output')) {
        console.log('📨 Message event received:', event.data);
        handleSetGlobals({ detail: event.data });
      }
    }, { passive: true });
    console.log('👂 Message event listener registered');

    // Prova a leggere i dati se già disponibili
    if (window.openai) {
      console.log('✅ window.openai already available');
      if (checkForNewData()) {
        return;
      }
      console.log('⚠️ No data in toolOutput yet');
      showStatus('In attesa di dati dal tool MCP...', 'info');
    } else {
      console.log('⚠️ window.openai not available yet');
      showStatus('In attesa di inizializzazione OpenAI Apps SDK...', 'info');
    }
    
    // Polling continuo per controllare nuovi dati (anche dopo l'inizializzazione)
    let pollCount = 0;
    const maxPolls = 300; // 30 secondi (300 * 100ms)
    
    const checkInterval = setInterval(() => {
      pollCount++;
      
      // Controlla se window.openai è diventato disponibile
      if (!window.openai) {
        if (pollCount % 10 === 0) { // Log ogni secondo
          console.log(`⏳ Waiting for window.openai... (${pollCount * 0.1}s)`);
        }
        return;
      }
      
      // Se window.openai esiste, controlla per nuovi dati
      if (checkForNewData()) {
        // Dati trovati, continua il polling per eventuali aggiornamenti
        return;
      }
      
      // Log periodico dello stato
      if (pollCount % 50 === 0) { // Ogni 5 secondi
        console.log(`⏳ Polling for data... (${pollCount * 0.1}s)`, {
          hasOpenAI: !!window.openai,
          hasToolOutput: !!(window.openai && window.openai.toolOutput),
          toolOutputKeys: window.openai?.toolOutput ? Object.keys(window.openai.toolOutput) : []
        });
      }
      
      // Timeout dopo maxPolls
      if (pollCount >= maxPolls) {
        clearInterval(checkInterval);
        console.log('⏱️ Polling timeout reached');
        if (!window.openai) {
          console.error('❌ window.openai still not available after 30 seconds');
          showStatus('OpenAI Apps SDK non disponibile', 'error');
        } else if (!window.openai.toolOutput) {
          console.warn('⚠️ window.openai available but no toolOutput after 30 seconds');
          showStatus('Nessun dato ricevuto dal tool MCP', 'info');
        }
      }
    }, 100);
    
    console.log('🔄 Continuous polling started');
  }

  // Inizializza quando il DOM è pronto
  function onDOMReady() {
    // Prima inizializza gli elementi DOM
    if (!initDOMElements()) {
      return; // Se gli elementi essenziali non sono trovati, esci
    }
    
    // Poi inizializza il widget
    init();
    
    // Mostra messaggio iniziale
    showStatus('Widget inizializzato. In attesa di dati...', 'info');
  }
  
  // Inizializza quando il DOM è pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onDOMReady);
  } else {
    // DOM già pronto
    onDOMReady();
  }
})();

