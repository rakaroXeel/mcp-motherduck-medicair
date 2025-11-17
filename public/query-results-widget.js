/**
 * MedicAir MCP Tool Tester Widget
 * Integrazione con OpenAI Apps SDK per visualizzare risposte JSON dai tool MCP
 */

(function() {
  'use strict';

  // Elementi DOM
  const requestInput = document.getElementById('request-input');
  const responseOutput = document.getElementById('response-output');
  const statusDiv = document.getElementById('status');

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
    if (!window.openai || !window.openai.toolOutput) {
      return null;
    }

    const toolOutput = window.openai.toolOutput;
    
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
    console.log('openai:set_globals event received:', event.detail);
    
    const globals = event.detail?.globals;
    if (globals?.toolOutput) {
      window.openai = window.openai || {};
      window.openai.toolOutput = globals.toolOutput;
      
      const data = extractToolOutput();
      if (data) {
        updateRequestInput(data);
        displayResponse(data);
      }
    }
  }

  /**
   * Inizializza il widget
   */
  function init() {
    // Ascolta l'evento openai:set_globals
    window.addEventListener('openai:set_globals', handleSetGlobals, {
      passive: true
    });

    // Prova a leggere i dati se già disponibili
    if (window.openai) {
      const data = extractToolOutput();
      if (data) {
        updateRequestInput(data);
        displayResponse(data);
        return;
      }

      showStatus('In attesa di dati dal tool MCP...', 'info');
      return;
    } 
    
      showStatus('In attesa di inizializzazione OpenAI Apps SDK...', 'info');
      
      // Polling per aspettare che window.openai sia disponibile
      const checkInterval = setInterval(() => {
        if (window.openai) {
          clearInterval(checkInterval);
          const data = extractToolOutput();
          if (data) {
            updateRequestInput(data);
            displayResponse(data);
            return;
          }

          showStatus('In attesa di dati dal tool MCP...', 'info');
        }
      }, 100);

      // Timeout dopo 5 secondi
      setTimeout(() => {
        clearInterval(checkInterval);
        if (!window.openai) {
          showStatus('OpenAI Apps SDK non disponibile', 'error');
        }
      }, 5000);
    
  }

  // Inizializza quando il DOM è pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

