// sidepanel/sidepanel.js — Main panel logic, workflow state, event handlers

const SidePanel = (() => {
  'use strict';

  let _currentTabId = null;
  let _importedData = null;    // Parsed JSON or AI-extracted entities
  let _kdpEntities = null;     // Entities read from KDP page
  let _diffResults = null;     // Diff comparison results
  let _approvedItems = new Set(); // Indices of approved diff items

  // ============ INITIALIZATION ============

  async function init() {
    // Initialize sub-modules
    BatchControls.init();

    // Bind events
    bindTabEvents();
    bindImportEvents();
    bindDiffEvents();
    bindExportEvents();
    bindLogEvents();

    // Listen for messages from background/content
    chrome.runtime.onMessage.addListener(handleMessage);

    // Check if on KDP page
    checkConnection();
  }

  // ============ CONNECTION CHECK ============

  function checkConnection() {
    chrome.runtime.sendMessage(
      { target: 'content', action: XRAY.MSG.PING },
      (res) => {
        if (chrome.runtime.lastError || !res || res.error) {
          setStatus(I18n.t('status_not_kdp'), 'error');
          return;
        }
        if (res.status === 'ready') {
          setStatus(I18n.t('status_ready', res.entityCount), 'ready');
          document.getElementById('btn-validate').disabled = false;
          document.getElementById('btn-export').disabled = false;
          document.getElementById('btn-gen-prompt').disabled = false;
        } else {
          setStatus(I18n.t('status_no_script'), 'error');
        }
      }
    );
  }

  // ============ TAB SWITCHING ============

  function bindTabEvents() {
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
      });
    });
  }

  function switchToTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-content').forEach(tc => {
      tc.classList.toggle('active', tc.id === `tab-${tabName}`);
    });
  }

  // ============ IMPORT EVENTS ============

  function bindImportEvents() {
    // File upload
    initFileUpload();

    // Toggle paste section
    bindToggle('toggle-paste-section', 'paste-section', 'lbl-or-paste', 'import_or_paste');

    // Toggle export section
    bindToggle('toggle-export-section', 'export-section', 'lbl-toggle-export', 'quick_export');

    // Validate JSON
    document.getElementById('btn-validate').addEventListener('click', validateJSON);

    // Compare with KDP
    document.getElementById('btn-compare').addEventListener('click', compareWithKDP);

    // Prompt section
    initPromptSection();
  }

  function bindToggle(toggleId, sectionId, labelId, i18nKey) {
    document.getElementById(toggleId).addEventListener('click', () => {
      const section = document.getElementById(sectionId);
      const label = document.getElementById(labelId);
      const isHidden = section.classList.contains('hidden');
      section.classList.toggle('hidden');
      label.textContent = (isHidden ? '▼ ' : '▶ ') + I18n.t(i18nKey);
    });
  }

  // ============ FILE UPLOAD ============

  function initFileUpload() {
    const zone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');

    // Click to select file
    zone.addEventListener('click', () => fileInput.click());

    // File selected via input
    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) handleFile(e.target.files[0]);
    });

    // Drag & drop
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => {
      zone.classList.remove('drag-over');
    });
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
    });
  }

  function handleFile(file) {
    if (!file.name.endsWith('.json')) {
      showResultEl(document.getElementById('validation-result'), I18n.t('upload_error_type'), 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      // Show filename
      document.getElementById('upload-filename').textContent = '✓ ' + file.name;
      document.getElementById('upload-filename').classList.remove('hidden');
      document.getElementById('upload-zone').classList.add('has-file');

      // Fill into json-input (for validateJSON to read)
      document.getElementById('json-input').value = content;

      // Auto-validate
      validateJSON();
    };
    reader.onerror = () => {
      showResultEl(document.getElementById('validation-result'), I18n.t('upload_error_read'), 'error');
    };
    reader.readAsText(file);
  }

  function validateJSON() {
    const input = document.getElementById('json-input').value.trim();
    const resultEl = document.getElementById('validation-result');

    try {
      const data = JSON.parse(input);
      if (!Array.isArray(data)) throw new Error(I18n.t('valid_error_not_array'));

      let addCount = 0, updateCount = 0, deleteCount = 0, errors = [];
      data.forEach((item, i) => {
        if (!item.name) errors.push(I18n.t('valid_error_missing', i, 'name'));
        if (!item.type) errors.push(I18n.t('valid_error_missing', i, 'type'));
        // Default action to "update" if not specified
        if (!item.action) item.action = XRAY.ACTION.UPDATE;
        if (item.action === XRAY.ACTION.ADD) addCount++;
        if (item.action === XRAY.ACTION.UPDATE) updateCount++;
        if (item.action === XRAY.ACTION.DELETE) deleteCount++;
        if (item.description && item.description.length > XRAY.LIMITS.MAX_DESCRIPTION) {
          errors.push(I18n.t('valid_error_desc_long', i, item.name, XRAY.LIMITS.MAX_DESCRIPTION));
        }
      });

      if (errors.length > 0) {
        showResultEl(resultEl, errors.join('\n'), 'error');
      } else {
        showResultEl(resultEl, I18n.t('valid_ok_full', data.length, addCount, updateCount), 'success');
        _importedData = data;
        document.getElementById('btn-compare').disabled = false;
      }
    } catch (e) {
      showResultEl(resultEl, I18n.t('valid_error_json', e.message), 'error');
    }
  }

  function compareWithKDP() {
    if (!_importedData) return;

    setStatus(I18n.t('status_checking'), 'working');

    // Background.js caches detailed entities automatically.
    // If Generate Prompt already fetched them, background returns cached data instantly
    // without re-triggering the content script to navigate all entities.
    chrome.runtime.sendMessage(
      { target: 'content', action: XRAY.MSG.GET_ENTITIES, detailed: true },
      (res) => {
        if (res?.error) {
          setStatus(res.error, 'error');
          return;
        }

        _kdpEntities = res.entities || [];
        _diffResults = compareEntities(_importedData, _kdpEntities);
        renderDiff(_diffResults);
        switchToTab('diff');
        setStatus(I18n.t('status_ready', _kdpEntities.length), 'ready');
      }
    );
  }

  // ============ PROMPT SECTION ============

  // Prompt template — {EXISTING_ENTITIES} placeholder will be replaced with KDP data
  const PROMPT_TEMPLATE = `You are a Kindle X-Ray editing assistant. I will provide you with:
1. The current entities already in my Kindle X-Ray (KDP existing data), including their aliases with occurrence counts
2. My novel text

Your task:
- For EVERY existing KDP entity: enrich its description based on the novel content. These entities were suggested by Amazon's algorithm and are important for readers — do NOT remove any of them.
- For new important characters and terms found in the novel but NOT in KDP: add them.

For each entity in the output, set the "action" field:
- "update" — entity already exists in KDP (enrich its description, fix type if wrong, add missing aliases)
- "add" — new entity found in the novel but NOT in KDP existing data

Rules:
- name: MUST match KDP name exactly for "update" items; use the canonical name for "add" items
- type: "CHARACTER" for people/beings, "TERM" for places, objects, concepts, organizations
- description: Write a SPECIFIC, UNIQUE description for EACH entity based on its actual role in the novel (max 1175 characters). The description should help a Kindle reader understand who this character is or what this term means in the context of THIS story. Write in English. CRITICAL: every description must be unique and specific to that entity. NEVER use generic/template descriptions like "A character in the story" or "A term referenced in the text". If you cannot determine an entity's role from the provided text, write "Appears in the text but role unclear from provided excerpt" instead of a generic filler.
- aliases: array of alternate names/nicknames/spellings used in the text (plain strings)
- Do NOT use "delete" — all existing KDP entities should be kept and improved
- Do NOT fabricate details not present in the novel text. Base descriptions only on what the text actually says or clearly implies.

Return ONLY a valid JSON array. No markdown code blocks, no explanation, no extra text.
IMPORTANT: Please provide the result as a downloadable .json file so the user can upload it directly.

=== KDP EXISTING ENTITIES ===
{EXISTING_ENTITIES}

=== NOVEL TEXT ===
[PASTE YOUR NOVEL TEXT HERE]`;

  function initPromptSection() {
    // Generate prompt button — fetches KDP entities first
    document.getElementById('btn-gen-prompt').addEventListener('click', generatePrompt);

    // Copy prompt button
    document.getElementById('btn-copy-prompt').addEventListener('click', () => {
      const promptOutput = document.getElementById('prompt-output');
      if (!promptOutput.value) return;
      promptOutput.select();
      navigator.clipboard.writeText(promptOutput.value).then(() => {
        showResultEl(document.getElementById('prompt-result'), I18n.t('prompt_copied'), 'success');
      }).catch(() => {
        document.execCommand('copy');
        showResultEl(document.getElementById('prompt-result'), I18n.t('prompt_copied'), 'success');
      });
    });
  }

  function generatePrompt() {
    setStatus(I18n.t('status_checking'), 'working');

    // Use detailed mode to include type, description, aliases in prompt
    chrome.runtime.sendMessage(
      { target: 'content', action: XRAY.MSG.GET_ENTITIES, detailed: true },
      (res) => {
        if (res?.error) {
          setStatus(res.error, 'error');
          showResultEl(document.getElementById('prompt-result'), res.error, 'error');
          return;
        }

        _kdpEntities = res.entities || [];
        const prompt = buildPrompt(_kdpEntities);
        const promptArea = document.getElementById('prompt-output');
        promptArea.value = prompt;
        promptArea.classList.remove('hidden');

        setStatus(I18n.t('status_ready', _kdpEntities.length), 'ready');
        showResultEl(
          document.getElementById('prompt-result'),
          I18n.t('prompt_generated', _kdpEntities.length),
          'success'
        );
        addLog(I18n.t('prompt_generated', _kdpEntities.length));
      }
    );
  }

  function buildPrompt(entities) {
    // Build entity list with rich alias data for the AI
    const simplified = entities.map(e => {
      const entry = {
        name: e.name,
        type: e.type,
        description: e.description || '',
      };
      // Include rich alias details (with occurrence counts) when available
      if (e.aliasDetails && e.aliasDetails.length > 0) {
        entry.aliases = e.aliasDetails.map(a => {
          const alias = { text: a.text, occurrences: a.occurrences };
          if (a.isDisplayName) alias.displayName = true;
          return alias;
        });
      } else {
        entry.aliases = e.aliases || [];
      }
      return entry;
    });
    const entitiesJson = JSON.stringify(simplified, null, 2);
    return PROMPT_TEMPLATE.replace('{EXISTING_ENTITIES}', entitiesJson);
  }

  // ============ DIFF LOGIC (delegated to DiffEngine + DiffViewer) ============

  function compareEntities(importedData, kdpEntities) {
    return DiffEngine.generateDiff(importedData, kdpEntities, {
      threshold: 0.75,
      showUnmatched: true,
    });
  }

  function renderDiff(diffResults) {
    const container = document.getElementById('diff-container');
    DiffViewer.render(diffResults, container, onApprovalChanged);
  }

  function onApprovalChanged(approvedSet, approvedItems) {
    const btn = document.getElementById('btn-execute-approved');
    const count = DiffViewer.getApprovedCount();
    btn.disabled = count === 0;
    btn.textContent = count > 0
      ? `${I18n.t('btn_execute_approved')} (${count})`
      : I18n.t('btn_execute_approved');
  }

  // ============ DIFF EVENTS ============

  function bindDiffEvents() {
    document.getElementById('btn-approve-all').addEventListener('click', () => {
      DiffViewer.approveAll();
    });

    document.getElementById('btn-reject-all').addEventListener('click', () => {
      DiffViewer.rejectAll();
    });

    document.getElementById('btn-execute-approved').addEventListener('click', executeApproved);
  }

  function executeApproved() {
    const execData = DiffViewer.getApprovedItems();
    if (!execData || execData.length === 0) return;

    // Switch to execute tab and start
    switchToTab('execute');
    BatchControls.resetProgress();
    BatchControls.updateButtons(true);

    addLog(I18n.t('log_started', execData.length));

    chrome.runtime.sendMessage(
      { target: 'content', action: XRAY.MSG.BATCH_PROCESS, data: execData },
      (res) => {
        if (res?.status === 'started') {
          addLog('Batch execution started', 'success');
        } else if (res?.error) {
          addLog('Error: ' + res.error, 'error');
          BatchControls.updateButtons(false);
        }
      }
    );
  }

  // ============ EXPORT EVENTS ============

  function bindExportEvents() {
    document.getElementById('btn-export').addEventListener('click', () => {
      chrome.runtime.sendMessage(
        { target: 'content', action: XRAY.MSG.GET_ENTITIES },
        (res) => {
          if (res?.entities) {
            document.getElementById('export-output').value = JSON.stringify(res.entities, null, 2);
            addLog(I18n.t('export_count', res.entities.length));
          }
        }
      );
    });

    document.getElementById('btn-copy-export').addEventListener('click', () => {
      const output = document.getElementById('export-output');
      output.select();
      navigator.clipboard.writeText(output.value).then(() => {
        addLog(I18n.t('export_copied'), 'success');
      }).catch(() => {
        document.execCommand('copy');
        addLog(I18n.t('export_copied'), 'success');
      });
    });
  }

  // ============ LOG EVENTS ============

  function bindLogEvents() {
    document.getElementById('btn-clear-log').addEventListener('click', () => {
      document.getElementById('log-output').innerHTML = '';
      addLog(I18n.t('log_cleared'), 'info');
    });
  }

  // ============ MESSAGE HANDLER ============

  function handleMessage(msg) {
    if (msg.action === XRAY.MSG.PROGRESS) {
      BatchControls.handleProgress(msg);
    }
    if (msg.action === XRAY.MSG.BATCH_COMPLETE) {
      BatchControls.handleBatchComplete(msg);
    }
    if (msg.action === 'apiProgress') {
      addLog(`AI extraction: processing chunk ${msg.current}/${msg.total}`);
    }
  }

  // ============ PUBLIC API ============

  function setStatus(text, cls) {
    const bar = document.getElementById('status-bar');
    bar.textContent = text;
    bar.className = `status ${cls || ''}`;
  }

  function getApprovedData() {
    // Use DiffViewer if available, otherwise raw import
    const approved = DiffViewer.getApprovedItems();
    if (approved && approved.length > 0) return approved;
    return _importedData;
  }

  // ============ UTILITY ============

  function showResultEl(el, text, type) {
    el.textContent = text;
    el.className = `result show ${type}`;
  }

  return {
    init,
    setStatus,
    getApprovedData,
    switchToTab,
  };
})();

// ============ GLOBAL LOG FUNCTION ============

function addLog(text, cls) {
  cls = cls || 'info';
  const log = document.getElementById('log-output');
  if (!log) return;
  const line = document.createElement('div');
  line.className = cls;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

// ============ BOOT ============

document.addEventListener('DOMContentLoaded', () => {
  SidePanel.init();
});