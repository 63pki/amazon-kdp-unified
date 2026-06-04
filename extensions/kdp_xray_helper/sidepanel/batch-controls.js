// sidepanel/batch-controls.js — Progress bar, start/stop, execution results display

const BatchControls = (() => {
  'use strict';

  let _isRunning = false;

  function init() {
    // Start batch button
    document.getElementById('btn-start-batch').addEventListener('click', startBatch);
    // Stop button
    document.getElementById('btn-stop').addEventListener('click', stopBatch);
  }

  function startBatch() {
    const approvedData = SidePanel.getApprovedData();
    if (!approvedData || approvedData.length === 0) {
      showResult('exec-results', I18n.t('no_approved'), 'error');
      return;
    }

    _isRunning = true;
    updateButtons(true);
    resetProgress();
    clearResults();

    addLog(I18n.t('log_started', approvedData.length));

    // Send to content script via background
    chrome.runtime.sendMessage(
      { target: 'content', action: XRAY.MSG.BATCH_PROCESS, data: approvedData },
      (res) => {
        if (res?.status === 'started') {
          addLog('Batch processing started', 'success');
        } else if (res?.error) {
          addLog('Error: ' + res.error, 'error');
          _isRunning = false;
          updateButtons(false);
        }
      }
    );
  }

  function stopBatch() {
    chrome.runtime.sendMessage(
      { target: 'content', action: XRAY.MSG.STOP_PROCESSING },
      (res) => {
        addLog(I18n.t('log_stopped'), 'warn');
      }
    );
  }

  function handleProgress(msg) {
    if (msg.phase === 'retry') {
      const text = I18n.t('exec_retry', msg.name, msg.attempt, msg.maxRetries);
      document.getElementById('exec-status').textContent = text;
      addLog(text, 'warn');
      return;
    }

    const pct = Math.round((msg.current / msg.total) * 100);
    document.getElementById('progress-bar').style.width = `${pct}%`;
    document.getElementById('progress-text').textContent =
      I18n.t('exec_progress', pct, msg.current, msg.total);
    document.getElementById('exec-status').textContent =
      I18n.t('exec_entity', msg.name);

    SidePanel.setStatus(
      I18n.t('status_processing', msg.name, msg.current, msg.total),
      'working'
    );

    addLog(`[${msg.current}/${msg.total}] ${msg.phase}: ${msg.name}`);
  }

  function handleBatchComplete(msg) {
    _isRunning = false;
    updateButtons(false);

    const ok = msg.results.filter(r => r.success).length;
    const fail = msg.results.filter(r => !r.success).length;
    const cancelled = msg.results.filter(r => r.status === 'cancelled').length;

    // Update progress to 100%
    document.getElementById('progress-bar').style.width = '100%';
    document.getElementById('progress-text').textContent = '100%';

    SidePanel.setStatus(
      I18n.t('status_done', ok, fail),
      ok === msg.results.length ? 'ready' : 'error'
    );

    // Render results
    renderResults(msg.results);

    // Log each result
    msg.results.forEach(r => {
      if (r.success) {
        const key = r.status === 'excluded' ? 'exec_excluded' : 'exec_success';
        addLog(I18n.t(key, r.name), 'success');
      } else if (r.status === 'cancelled') {
        addLog(I18n.t('exec_cancelled', r.name), 'warn');
      } else {
        addLog(I18n.t('exec_error', r.name, r.error || 'unknown'), 'error');
      }
    });
  }

  function renderResults(results) {
    const container = document.getElementById('exec-results');
    container.innerHTML = '';

    results.forEach(r => {
      const div = document.createElement('div');
      div.className = 'exec-result-item';

      const icon = document.createElement('span');
      icon.className = 'exec-icon';
      if (r.success) {
        icon.className += ' success';
        icon.textContent = '✓';
      } else if (r.status === 'cancelled') {
        icon.className += ' cancelled';
        icon.textContent = '⊘';
      } else {
        icon.className += ' error';
        icon.textContent = '✗';
      }

      const text = document.createElement('span');
      text.textContent = `${r.name}: ${r.status}${r.error ? ' — ' + r.error : ''}`;

      div.appendChild(icon);
      div.appendChild(text);
      container.appendChild(div);
    });
  }

  function resetProgress() {
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-text').textContent = '0%';
    document.getElementById('exec-status').textContent = '';
  }

  function clearResults() {
    document.getElementById('exec-results').innerHTML = '';
  }

  function updateButtons(running) {
    document.getElementById('btn-start-batch').disabled = running;
    document.getElementById('btn-stop').disabled = !running;
  }

  function isRunning() {
    return _isRunning;
  }

  // Helper: show result message
  function showResult(elementId, text, type) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = `<div class="exec-result-item"><span class="exec-icon ${type}">${type === 'error' ? '✗' : '✓'}</span><span>${text}</span></div>`;
  }

  return {
    init,
    handleProgress,
    handleBatchComplete,
    isRunning,
    updateButtons,
    resetProgress,
  };
})();