// sidepanel/diff-viewer.js — Visual diff comparison component

const DiffViewer = (() => {
  'use strict';

  let _diffResults = null;
  let _approvedItems = new Set();
  let _onApprovalChange = null; // callback when approval state changes

  /**
   * Render diff results into the container
   * @param {Array} diffResults - from DiffEngine.generateDiff()
   * @param {HTMLElement} container - DOM element to render into
   * @param {Function} onApprovalChange - callback(approvedSet)
   */
  function render(diffResults, container, onApprovalChange) {
    _diffResults = diffResults;
    _approvedItems = new Set();
    _onApprovalChange = onApprovalChange;

    container.innerHTML = '';

    if (!diffResults || diffResults.length === 0) {
      container.innerHTML = `<p class="placeholder-text">${I18n.t('diff_no_changes')}</p>`;
      _notifyChange();
      return;
    }

    // Summary bar
    const stats = DiffEngine.getDiffStats(diffResults);
    const summaryEl = document.getElementById('diff-summary');
    if (summaryEl) {
      summaryEl.textContent = I18n.t('diff_summary', stats.adds, stats.updates, stats.deletes);
      if (stats.fuzzyMatches > 0) {
        summaryEl.textContent += ` | ${stats.fuzzyMatches} fuzzy match${stats.fuzzyMatches > 1 ? 'es' : ''}`;
      }
    }

    // Render each diff item
    diffResults.forEach((item, idx) => {
      const card = createDiffCard(item, idx);
      container.appendChild(card);
    });

    _notifyChange();
  }

  /**
   * Create a single diff card element
   */
  function createDiffCard(item, idx) {
    const card = document.createElement('div');
    card.className = `diff-item action-${item.action}`;
    card.dataset.index = idx;

    // Auto-approve actionable items (not keep, not kdp_only)
    const isActionable = item.action !== 'keep' && item.action !== 'kdp_only';
    if (isActionable) _approvedItems.add(idx);

    // ---- Header ----
    const header = document.createElement('div');
    header.className = 'diff-item-header';

    // Checkbox
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'diff-checkbox';
    checkbox.checked = isActionable;
    checkbox.disabled = item.action === 'kdp_only'; // can't act on KDP-only items
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) {
        _approvedItems.add(idx);
      } else {
        _approvedItems.delete(idx);
      }
      _notifyChange();
    });

    // Entity name
    const nameEl = document.createElement('span');
    nameEl.className = 'diff-name';
    nameEl.textContent = item.name;

    // Match indicator (for fuzzy matches)
    if (item.matchType && item.matchType !== 'exact' && item.matchType !== 'none' && item.kdp) {
      const matchTag = document.createElement('span');
      matchTag.className = 'diff-match-tag';
      matchTag.textContent = `≈ ${item.kdp.name}`;
      matchTag.title = `${item.matchType} match (${Math.round(item.matchScore * 100)}%)`;
      nameEl.appendChild(document.createTextNode(' '));
      nameEl.appendChild(matchTag);
    }

    // Action badge
    const badge = document.createElement('span');
    const badgeAction = item.action === 'kdp_only' ? 'keep' : item.action;
    badge.className = `diff-badge ${badgeAction}`;
    badge.textContent = getBadgeText(item);

    header.appendChild(checkbox);
    header.appendChild(nameEl);
    header.appendChild(badge);

    // ---- Body (changes) ----
    const body = document.createElement('div');
    body.className = 'diff-item-body';

    if (item.source === 'import_only') {
      const note = document.createElement('div');
      note.className = 'diff-field diff-note';
      note.innerHTML = `<span class="diff-field-label">⚠ </span><span class="diff-new">${I18n.t('diff_not_found_kdp') || 'Not found in KDP — will attempt name match'}</span>`;
      body.appendChild(note);
    }

    if (item.source === 'kdp_only') {
      const note = document.createElement('div');
      note.className = 'diff-field diff-note';
      note.innerHTML = `<span class="diff-field-label">ℹ </span><span style="color:#666">${I18n.t('diff_kdp_only') || 'Only in KDP (not in your import data)'}</span>`;
      body.appendChild(note);
    }

    if (item.changes && item.changes.length > 0) {
      item.changes.forEach(change => {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'diff-field';

        const label = document.createElement('span');
        label.className = 'diff-field-label';
        label.textContent = change.field + ': ';

        fieldDiv.appendChild(label);

        if (change.from && change.from !== '(empty)') {
          const oldSpan = document.createElement('span');
          oldSpan.className = 'diff-old';
          oldSpan.textContent = change.from;
          fieldDiv.appendChild(oldSpan);
          fieldDiv.appendChild(document.createTextNode(' → '));
        }

        const newSpan = document.createElement('span');
        newSpan.className = 'diff-new';
        newSpan.textContent = change.to;
        fieldDiv.appendChild(newSpan);

        body.appendChild(fieldDiv);
      });
    } else if (item.action === 'keep') {
      const keepNote = document.createElement('div');
      keepNote.className = 'diff-field';
      keepNote.style.color = '#999';
      keepNote.textContent = I18n.t('diff_action_keep');
      body.appendChild(keepNote);
    }

    // Type/description summary for context
    if (item.imported && item.action !== 'keep') {
      const typeLine = document.createElement('div');
      typeLine.className = 'diff-field diff-context';
      typeLine.innerHTML = `<span class="diff-field-label">type: </span><span>${escapeHtml(item.imported.type || '?')}</span>`;
      body.appendChild(typeLine);

      if (item.imported.description) {
        const descLine = document.createElement('div');
        descLine.className = 'diff-field diff-context diff-desc-preview';
        const preview = item.imported.description.substring(0, 120);
        descLine.innerHTML = `<span class="diff-field-label">desc: </span><span class="diff-desc-text">${escapeHtml(preview)}${item.imported.description.length > 120 ? '...' : ''}</span>`;

        // Click to expand
        if (item.imported.description.length > 120) {
          descLine.style.cursor = 'pointer';
          descLine.title = 'Click to expand';
          let expanded = false;
          descLine.addEventListener('click', () => {
            expanded = !expanded;
            const textEl = descLine.querySelector('.diff-desc-text');
            textEl.textContent = expanded ? item.imported.description : preview + '...';
          });
        }

        body.appendChild(descLine);
      }
    }

    card.appendChild(header);
    card.appendChild(body);

    return card;
  }

  /**
   * Get badge display text based on action
   */
  function getBadgeText(item) {
    switch (item.action) {
      case XRAY.ACTION.UPDATE: return I18n.t('diff_action_update');
      case XRAY.ACTION.DELETE: return I18n.t('diff_action_delete');
      case XRAY.ACTION.ADD: return I18n.t('diff_action_add');
      case 'keep': return I18n.t('diff_action_keep');
      case 'kdp_only': return 'KDP Only';
      default: return item.action;
    }
  }

  // ============ APPROVAL MANAGEMENT ============

  function approveAll() {
    if (!_diffResults) return;
    _diffResults.forEach((item, idx) => {
      if (item.action !== 'keep' && item.action !== 'kdp_only') {
        _approvedItems.add(idx);
      }
    });
    _updateCheckboxes();
    _notifyChange();
  }

  function rejectAll() {
    _approvedItems.clear();
    _updateCheckboxes();
    _notifyChange();
  }

  function getApprovedItems() {
    if (!_diffResults) return [];
    const items = [];
    _approvedItems.forEach(idx => {
      const item = _diffResults[idx];
      if (item && item.imported && item.action !== 'keep' && item.action !== 'kdp_only') {
        // Clone imported data and attach action + new-entity flag from diff result
        const execItem = Object.assign({}, item.imported);
        execItem.action = item.action;
        execItem._isNew = item.source === 'import_only';
        items.push(execItem);
      }
    });
    return items;
  }

  function getApprovedCount() {
    return _approvedItems.size;
  }

  // ============ INTERNAL ============

  function _updateCheckboxes() {
    document.querySelectorAll('.diff-item').forEach(card => {
      const idx = parseInt(card.dataset.index);
      const cb = card.querySelector('.diff-checkbox');
      if (cb && !cb.disabled) {
        cb.checked = _approvedItems.has(idx);
      }
    });
  }

  function _notifyChange() {
    if (_onApprovalChange) {
      _onApprovalChange(_approvedItems, getApprovedItems());
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  return {
    render,
    approveAll,
    rejectAll,
    getApprovedItems,
    getApprovedCount,
  };
})();