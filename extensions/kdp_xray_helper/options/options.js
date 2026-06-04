// options/options.js — Developer Tools page
// Quick-test harness for KDP X-Ray Helper operations.
// Communicates with the content script via chrome.runtime.sendMessage (routed through background.js).

(function () {
  'use strict';

  const logEl = document.getElementById('log-output');

  // ============ LOGGING ============

  function log(msg, level) {
    level = level || 'info';
    const ts = new Date().toLocaleTimeString();
    const prefix = { info: '▸', ok: '✓', err: '✗', warn: '⚠' }[level] || '▸';
    const color = { info: '#aaa', ok: '#4caf50', err: '#f44336', warn: '#ff9800' }[level] || '#aaa';
    const line = document.createElement('span');
    line.style.color = color;
    line.textContent = `[${ts}] ${prefix} ${msg}\n`;
    logEl.appendChild(line);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function logJSON(label, obj) {
    log(label + ':');
    const pre = document.createElement('span');
    pre.style.color = '#6ec6ff';
    pre.textContent = JSON.stringify(obj, null, 2) + '\n';
    logEl.appendChild(pre);
    logEl.scrollTop = logEl.scrollHeight;
  }

  // ============ MESSAGE HELPERS ============

  function sendToContent(payload) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(
        Object.assign({ target: 'content' }, payload),
        (response) => {
          if (chrome.runtime.lastError) {
            resolve({ error: chrome.runtime.lastError.message });
          } else {
            resolve(response || { error: 'No response' });
          }
        }
      );
    });
  }

  // Listen for progress messages from content script
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === XRAY.MSG.PROGRESS) {
      const phase = msg.phase || '';
      const name = msg.name || '';
      const current = msg.current || '';
      const total = msg.total || '';
      if (msg.attempt) {
        log(`  Retry ${msg.attempt}/${msg.maxRetries} for "${name}"`, 'warn');
      } else {
        log(`  [${current}/${total}] ${phase}: ${name}`);
      }
    }
    if (msg.action === XRAY.MSG.BATCH_COMPLETE) {
      log('Batch complete!', 'ok');
      logJSON('Results', msg.results);
    }
  });

  // ============ CONNECTION ============

  document.getElementById('btn-ping').addEventListener('click', async () => {
    log('Pinging content script...');
    const res = await sendToContent({ action: XRAY.MSG.PING });
    const badge = document.getElementById('ping-status');
    if (res.error) {
      log('Ping failed: ' + res.error, 'err');
      badge.textContent = 'FAIL';
      badge.className = 'status-badge fail';
    } else {
      log(`Ping OK — ${res.entityCount} entities, pageReady=${res.pageReady}`, 'ok');
      badge.textContent = `OK (${res.entityCount})`;
      badge.className = 'status-badge ok';
    }
  });

  // ============ READ OPERATIONS ============

  document.getElementById('btn-quick-export').addEventListener('click', async () => {
    log('Quick export (names only)...');
    const res = await sendToContent({ action: XRAY.MSG.GET_ENTITIES, detailed: false });
    if (res.error) {
      log('Quick export failed: ' + res.error, 'err');
    } else {
      log(`Got ${res.entities.length} entities`, 'ok');
      logJSON('Entities', res.entities);
    }
  });

  document.getElementById('btn-detailed-export').addEventListener('click', async () => {
    log('Detailed export (navigating all entities — this takes a while)...');
    const res = await sendToContent({ action: XRAY.MSG.GET_ENTITIES, detailed: true });
    if (res.error) {
      log('Detailed export failed: ' + res.error, 'err');
    } else {
      log(`Got ${res.entities.length} entities with details`, 'ok');
      logJSON('Entities', res.entities);
    }
  });

  document.getElementById('btn-read-current').addEventListener('click', async () => {
    log('Reading current entity details...');
    const res = await sendToContent({ action: XRAY.MSG.GET_ENTITY_DETAILS });
    if (res.error) {
      log('Read failed: ' + res.error, 'err');
    } else if (!res.details) {
      log('No entity selected (details is null)', 'warn');
    } else {
      log(`Current entity: "${res.details.name}"`, 'ok');
      logJSON('Details', res.details);
    }
  });

  // ============ WRITE OPERATIONS ============

  function getEntityInputs() {
    return {
      name: document.getElementById('input-entity-name').value.trim(),
      type: document.getElementById('input-entity-type').value,
      description: document.getElementById('input-entity-desc').value.trim(),
    };
  }

  document.getElementById('btn-select-entity').addEventListener('click', async () => {
    const { name } = getEntityInputs();
    if (!name) { log('Enter an entity name first', 'warn'); return; }
    log(`Selecting entity "${name}"...`);

    // First verify the entity exists in sidebar
    const listRes = await sendToContent({ action: XRAY.MSG.GET_ENTITIES, detailed: false });
    if (listRes.error) {
      log('Failed to get entity list: ' + listRes.error, 'err');
      return;
    }
    const match = listRes.entities.find(
      e => e.name.toLowerCase() === name.toLowerCase()
    );
    if (!match) {
      log(`Entity "${name}" not found in sidebar (${listRes.entities.length} entities total)`, 'err');
      return;
    }
    log(`Found "${match.name}" at index ${match.dataIndex}. Sending processSingle to select + update...`);

    // Process single will select it and apply fields
    const res = await sendToContent({
      action: XRAY.MSG.PROCESS_SINGLE,
      data: { name: match.name, type: 'CHARACTER', action: XRAY.ACTION.UPDATE },
    });
    if (res.error) {
      log('Select failed: ' + res.error, 'err');
    } else {
      log(`Select result: ${res.status} (success=${res.success})`, res.success ? 'ok' : 'err');
      logJSON('Result', res);
    }
  });

  document.getElementById('btn-add-entity').addEventListener('click', async () => {
    const { name, type } = getEntityInputs();
    if (!name) { log('Enter an entity name first', 'warn'); return; }
    log(`Adding new entity "${name}" (type=${type})...`);

    const res = await sendToContent({
      action: XRAY.MSG.PROCESS_SINGLE,
      data: {
        name: name,
        type: type,
        description: getEntityInputs().description || `[Dev test] Entity created at ${new Date().toLocaleTimeString()}`,
        action: XRAY.ACTION.ADD,
      },
    });
    if (res.error) {
      log('Add entity failed: ' + res.error, 'err');
    } else {
      log(`Add result: ${res.status} (success=${res.success})`, res.success ? 'ok' : 'err');
      logJSON('Result', res);
    }
  });

  document.getElementById('btn-process-single').addEventListener('click', async () => {
    const inputs = getEntityInputs();
    if (!inputs.name) { log('Enter an entity name first', 'warn'); return; }
    log(`Processing single entity "${inputs.name}" (update)...`);

    const data = {
      name: inputs.name,
      type: inputs.type,
      action: XRAY.ACTION.UPDATE,
    };
    if (inputs.description) data.description = inputs.description;

    const res = await sendToContent({
      action: XRAY.MSG.PROCESS_SINGLE,
      data: data,
    });
    if (res.error) {
      log('Process single failed: ' + res.error, 'err');
    } else {
      log(`Process result: ${res.status} (success=${res.success})`, res.success ? 'ok' : 'err');
      logJSON('Result', res);
    }
  });

  // ============ DUPLICATE UPDATE TEST ============

  document.getElementById('btn-dup-test').addEventListener('click', async () => {
    log('=== Duplicate Update Test ===');
    log('Step 1: Reading current entity details...');

    const detailsRes = await sendToContent({ action: XRAY.MSG.GET_ENTITY_DETAILS });
    if (detailsRes.error) {
      log('Failed to read current entity: ' + detailsRes.error, 'err');
      return;
    }
    if (!detailsRes.details) {
      log('No entity currently selected — click an entity on the KDP page first', 'warn');
      return;
    }

    const d = detailsRes.details;
    log(`Current entity: "${d.name}" | type=${d.type} | desc=${d.description ? d.description.substring(0, 60) + '...' : '(empty)'}`, 'ok');
    logJSON('Full details (before)', d);

    log('Step 2: Sending update with IDENTICAL data...');
    const updateData = {
      name: d.name,
      type: d.type,
      description: d.description || undefined,
      action: XRAY.ACTION.UPDATE,
    };

    const t0 = performance.now();
    const res = await sendToContent({
      action: XRAY.MSG.PROCESS_SINGLE,
      data: updateData,
    });
    const elapsed = Math.round(performance.now() - t0);

    if (res.error) {
      log(`Duplicate update failed: ${res.error}`, 'err');
    } else {
      log(`Duplicate update result: ${res.status} (success=${res.success}) — took ${elapsed}ms`, res.success ? 'ok' : 'err');
    }

    log('Step 3: Re-reading entity to verify no unintended changes...');
    const afterRes = await sendToContent({ action: XRAY.MSG.GET_ENTITY_DETAILS });
    if (afterRes.error) {
      log('Failed to re-read entity: ' + afterRes.error, 'err');
      return;
    }

    const a = afterRes.details;
    const diffs = [];
    if (d.type !== a.type) diffs.push(`type: ${d.type} → ${a.type}`);
    if (d.description !== a.description) diffs.push(`description changed`);
    if (d.included !== a.included) diffs.push(`included: ${d.included} → ${a.included}`);
    if (d.reviewed !== a.reviewed) diffs.push(`reviewed: ${d.reviewed} → ${a.reviewed}`);

    if (diffs.length === 0) {
      log('No unintended changes detected — duplicate update is safe', 'ok');
    } else {
      log(`Detected ${diffs.length} change(s) after duplicate update:`, 'warn');
      diffs.forEach(diff => log('  · ' + diff, 'warn'));
    }
    log('=== Test Complete ===');
  });

  // ============ BATCH TEST ============

  document.getElementById('btn-batch-run').addEventListener('click', async () => {
    const jsonText = document.getElementById('input-batch-json').value.trim();
    if (!jsonText) { log('Enter batch JSON first', 'warn'); return; }

    let data;
    try {
      data = JSON.parse(jsonText);
    } catch (e) {
      log('Invalid JSON: ' + e.message, 'err');
      return;
    }

    if (!Array.isArray(data) || data.length === 0) {
      log('JSON must be a non-empty array', 'err');
      return;
    }

    log(`Starting batch with ${data.length} entities...`);
    const res = await sendToContent({
      action: XRAY.MSG.BATCH_PROCESS,
      data: data,
    });
    if (res.error) {
      log('Batch start failed: ' + res.error, 'err');
    } else {
      log('Batch started (status=' + res.status + '). Progress updates will appear below.', 'ok');
    }
  });

  document.getElementById('btn-batch-stop').addEventListener('click', async () => {
    log('Sending stop...');
    const res = await sendToContent({ action: XRAY.MSG.STOP_PROCESSING });
    if (res.error) {
      log('Stop failed: ' + res.error, 'err');
    } else {
      log('Stop result: ' + res.status, res.status === 'stopping' ? 'ok' : 'warn');
    }
  });

  // ============ CLEAR LOG ============

  document.getElementById('btn-clear-log').addEventListener('click', () => {
    logEl.innerHTML = '';
    log('Log cleared.');
  });

  // ============ INIT ============

  log('Developer Tools loaded. Open a KDP X-Ray page and click "Ping" to start.');
})();