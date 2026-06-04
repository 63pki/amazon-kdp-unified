// content/content.js — Thin message router for KDP X-Ray page
// Dispatches messages to dom-reader, dom-writer, batch-executor

(function () {
  'use strict';

  // Shared sleep function (also used by dom-reader for detailed export)
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Make sleep available globally for dom-reader's exportAllEntitiesDetailed
  window._xraySleep = sleep;

  // ============ MESSAGE HANDLER ============

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    switch (msg.action) {
      case XRAY.MSG.PING:
        sendResponse({
          status: 'ready',
          entityCount: DomReader.getAllEntities().length,
          pageReady: DomReader.isPageReady(),
        });
        break;

      case XRAY.MSG.GET_ENTITIES:
        if (msg.detailed) {
          // Async detailed export
          DomReader.exportAllEntitiesDetailed((progress) => {
            chrome.runtime.sendMessage({
              action: XRAY.MSG.PROGRESS,
              ...progress,
              phase: 'exporting',
            });
          }).then(entities => {
            sendResponse({ entities });
          });
        } else {
          sendResponse({ entities: DomReader.exportEntitiesQuick() });
        }
        break;

      case XRAY.MSG.GET_ENTITY_DETAILS:
        // Get details of currently selected entity
        sendResponse({ details: DomReader.readCurrentEntityDetails() });
        break;

      case XRAY.MSG.BATCH_PROCESS:
        // Start async batch processing
        BatchExecutor.batchProcess(msg.data, (progress) => {
          chrome.runtime.sendMessage({
            action: XRAY.MSG.PROGRESS,
            ...progress,
          });
        }).then(results => {
          chrome.runtime.sendMessage({
            action: XRAY.MSG.BATCH_COMPLETE,
            results,
          });
        });
        sendResponse({ status: 'started' });
        break;

      case XRAY.MSG.STOP_PROCESSING:
        const stopped = BatchExecutor.stopProcessing();
        sendResponse({ status: stopped ? 'stopping' : 'not_running' });
        break;

      case XRAY.MSG.PROCESS_SINGLE:
        // Process a single entity (for manual operations)
        BatchExecutor.processEntity(msg.data).then(result => {
          sendResponse(result);
        }).catch(err => {
          sendResponse({ success: false, error: err.message });
        });
        break;

      default:
        sendResponse({ error: 'Unknown action: ' + msg.action });
    }

    return true; // keep message channel open for async responses
  });

  // ============ INITIALIZATION ============

  console.log(
    '[KDP X-Ray Helper] Content script loaded. Entities found:',
    DomReader.getAllEntities().length
  );
})();