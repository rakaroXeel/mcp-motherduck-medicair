/**
 * MedicAir MCP Tool Tester Widget
 * Integrazione con OpenAI Apps SDK per visualizzare risposte JSON dai tool MCP
 */

(function() {
  'use strict';
  
  console.log('🔵 Widget JS loaded and initialized');

  // Elementi DOM
  const requestInput = document.getElementById('request-input');
  const responseOutput = document.getElementById('response-output');
  const statusDiv = document.getElementById('status');
  
  if (!requestInput || !responseOutput || !statusDiv) {
    console.error('❌ DOM elements not found:', {
      requestInput: !!requestInput,
      responseOutput: !!responseOutput,
      statusDiv: !!statusDiv
    });
    return;
  }
  
  console.log('✅ DOM elements found');

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
      toolOutput: window.openai?.toolOutput
    });
    
    if (!window.openai || !window.openai.toolOutput) {
      console.log('⚠️ No toolOutput available');
      return null;
    }

    const toolOutput = window.openai.toolOutput;
    console.log('✅ ToolOutput found:', toolOutput);
    
    // Restituisce l'intero oggetto toolOutput per mostrare tutto
    return toolOutput;
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
    
    const globals = event.detail?.globals;
    console.log('📦 Globals extracted:', globals);
    
    if (globals?.toolOutput) {
      console.log('✅ toolOutput found in globals');
      window.openai = window.openai || {};
      window.openai.toolOutput = globals.toolOutput;
      
      const data = extractToolOutput();
      if (data) {
        console.log('✅ Data extracted, updating UI');
        updateRequestInput(data);
        displayResponse(data);
      } else {
        console.log('⚠️ No data extracted from toolOutput');
      }
    } else {
      console.log('⚠️ No toolOutput in globals:', Object.keys(globals || {}));
    }
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

    // Prova a leggere i dati se già disponibili
    if (window.openai) {
      console.log('✅ window.openai already available');
      const data = extractToolOutput();
      if (data) {
        console.log('✅ Data found, displaying');
        updateRequestInput(data);
        displayResponse(data);
        return;
      }

      console.log('⚠️ No data in toolOutput yet');
      showStatus('In attesa di dati dal tool MCP...', 'info');
      return;
    } 
    
    console.log('⚠️ window.openai not available, starting polling...');
    showStatus('In attesa di inizializzazione OpenAI Apps SDK...', 'info');
    
    // Polling per aspettare che window.openai sia disponibile
    const checkInterval = setInterval(() => {
      if (window.openai) {
        console.log('✅ window.openai became available');
        clearInterval(checkInterval);
        const data = extractToolOutput();
        if (data) {
          console.log('✅ Data found after polling, displaying');
          updateRequestInput(data);
          displayResponse(data);
          return;
        }

        console.log('⚠️ No data in toolOutput after polling');
        showStatus('In attesa di dati dal tool MCP...', 'info');
      }
    }, 100);

    // Timeout dopo 5 secondi
    setTimeout(() => {
      clearInterval(checkInterval);
      if (!window.openai) {
        console.error('❌ window.openai still not available after 5 seconds');
        showStatus('OpenAI Apps SDK non disponibile', 'error');
      }
    }, 5000);
  }

  // Mostra messaggio iniziale
  showStatus('Widget inizializzato. In attesa di dati...', 'info');
  
  // Inizializza quando il DOM è pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

