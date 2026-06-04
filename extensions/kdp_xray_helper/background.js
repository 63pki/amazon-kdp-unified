// background.js — Service Worker
// Message routing hub + Side Panel management + Entity cache

// Import shared modules
importScripts('shared/constants.js', 'shared/diff-engine.js');

// ============ ENTITY CACHE ============
// Cache detailed KDP entities in the service worker so the side panel
// doesn't need to re-fetch (re-navigate all items) after being reloaded.
let _cachedDetailedEntities = null;

// ============ SIDE PANEL SETUP ============

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener(async (tab) => {
  try {
    await chrome.sidePanel.open({ tabId: tab.id });
  } catch (e) {
    console.warn('[Background] Failed to open side panel:', e);
  }
});

// Set side panel behavior: open on action click
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
  .catch(e => console.warn('[Background] setPanelBehavior error:', e));

// ============ MESSAGE ROUTING ============

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // --- Progress/Complete messages from content script ---
  // No need to re-broadcast: chrome.runtime.sendMessage from content scripts
  // already delivers to all extension pages (side panel, options, etc.)
  if (msg.action === 'progress' || msg.action === 'batchComplete') {
    return; // just ignore, sidepanel already receives it directly
  }

  // --- Cache management ---
  if (msg.action === 'getCachedEntities') {
    sendResponse({ entities: _cachedDetailedEntities });
    return;
  }
  if (msg.action === 'clearEntityCache') {
    _cachedDetailedEntities = null;
    console.log('[Background] Entity cache cleared');
    sendResponse({ ok: true });
    return;
  }

  // --- Side panel requests to content script ---
  if (msg.target === 'content') {
    // For detailed getEntities: check cache first
    if (msg.action === XRAY.MSG.GET_ENTITIES && msg.detailed === true) {
      if (_cachedDetailedEntities && _cachedDetailedEntities.length > 0) {
        console.log('[Background] Returning cached detailed entities:', _cachedDetailedEntities.length);
        sendResponse({ entities: _cachedDetailedEntities });
        return; // synchronous response, no need to return true
      }
      // Cache miss: forward to content script, then cache the response
      forwardAndCacheEntities(msg, sendResponse);
      return true; // async
    }

    forwardToContentScript(msg, sendResponse);
    return true; // async
  }
});

// ============ FORWARD + CACHE (for detailed entity requests) ============

async function forwardAndCacheEntities(msg, sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      sendResponse({ error: 'No active tab found' });
      return;
    }

    const { target, ...payload } = msg;

    chrome.tabs.sendMessage(tab.id, payload, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({ error: chrome.runtime.lastError.message });
      } else {
        // Cache the detailed entities for future requests
        if (response && response.entities && response.entities.length > 0) {
          _cachedDetailedEntities = response.entities;
          console.log('[Background] Cached', _cachedDetailedEntities.length, 'detailed entities');
        }
        sendResponse(response);
      }
    });
  } catch (e) {
    sendResponse({ error: e.message });
  }
}

// ============ FORWARD TO CONTENT SCRIPT ============

async function forwardToContentScript(msg, sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      sendResponse({ error: 'No active tab found' });
      return;
    }

    // Remove the target field before forwarding
    const { target, ...payload } = msg;

    chrome.tabs.sendMessage(tab.id, payload, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({ error: chrome.runtime.lastError.message });
      } else {
        sendResponse(response);
      }
    });
  } catch (e) {
    sendResponse({ error: e.message });
  }
}

// ============ INITIALIZATION ============

console.log('[KDP X-Ray Helper] Background service worker loaded.');