// sidepanel/entity-editor.js — Inline entity editor for modifying individual items

const EntityEditor = (() => {
  'use strict';

  let _onSave = null;

  /**
   * Open an inline editor for an entity
   * @param {Object} entity - entity data to edit
   * @param {HTMLElement} container - where to render the editor
   * @param {Function} onSave - callback(editedEntity)
   */
  function open(entity, container, onSave) {
    _onSave = onSave;

    const editor = document.createElement('div');
    editor.className = 'entity-editor';
    editor.innerHTML = `
      <div class="editor-header">
        <h3>${I18n.t('editor_title') || 'Edit Entity'}</h3>
        <button class="editor-close btn-sm">✕</button>
      </div>
      <div class="editor-body">
        <label class="editor-label">Name:</label>
        <input type="text" class="editor-input" id="edit-name"
          value="${escapeAttr(entity.name || '')}" />

        <label class="editor-label">Type:</label>
        <select class="editor-select" id="edit-type">
          <option value="CHARACTER" ${entity.type === 'CHARACTER' ? 'selected' : ''}>CHARACTER</option>
          <option value="TERM" ${(entity.type === 'TERM' || entity.type === 'TOPIC') ? 'selected' : ''}>TERM</option>
        </select>

        <label class="editor-label">Action:</label>
        <select class="editor-select" id="edit-action">
          <option value="update" ${entity.action === 'update' ? 'selected' : ''}>Update</option>
          <option value="delete" ${entity.action === 'delete' ? 'selected' : ''}>Delete / Exclude</option>
        </select>

        <label class="editor-label">
          Description
          <span class="char-count" id="edit-desc-count">0 / ${XRAY.LIMITS.MAX_DESCRIPTION}</span>
        </label>
        <textarea class="editor-textarea" id="edit-description" rows="5"
          maxlength="${XRAY.LIMITS.MAX_DESCRIPTION}"
          placeholder="Enter description...">${escapeHtml(entity.description || '')}</textarea>

        <label class="editor-label">Commentary (optional):</label>
        <textarea class="editor-textarea" id="edit-commentary" rows="2"
          placeholder="Optional commentary...">${escapeHtml(entity.commentary || '')}</textarea>

        <label class="editor-label">Aliases (comma-separated):</label>
        <input type="text" class="editor-input" id="edit-aliases"
          value="${escapeAttr((entity.aliases || []).join(', '))}"
          placeholder="alias1, alias2, ..." />
      </div>
      <div class="editor-footer">
        <button class="editor-save btn-primary">Save</button>
        <button class="editor-cancel">Cancel</button>
      </div>
    `;

    // Clear container and show editor
    container.innerHTML = '';
    container.appendChild(editor);

    // Char count
    const descArea = editor.querySelector('#edit-description');
    const countEl = editor.querySelector('#edit-desc-count');
    updateCharCount(descArea, countEl);
    descArea.addEventListener('input', () => updateCharCount(descArea, countEl));

    // Close button
    editor.querySelector('.editor-close').addEventListener('click', () => close(container));
    editor.querySelector('.editor-cancel').addEventListener('click', () => close(container));

    // Save button
    editor.querySelector('.editor-save').addEventListener('click', () => {
      const edited = {
        name: editor.querySelector('#edit-name').value.trim(),
        type: editor.querySelector('#edit-type').value,
        action: editor.querySelector('#edit-action').value,
        description: editor.querySelector('#edit-description').value.trim(),
        commentary: editor.querySelector('#edit-commentary').value.trim(),
        aliases: editor.querySelector('#edit-aliases').value
          .split(',')
          .map(a => a.trim())
          .filter(Boolean),
      };

      if (!edited.name) {
        alert('Name is required');
        return;
      }

      if (edited.description.length > XRAY.LIMITS.MAX_DESCRIPTION) {
        alert(`Description exceeds ${XRAY.LIMITS.MAX_DESCRIPTION} characters`);
        return;
      }

      close(container);
      if (_onSave) _onSave(edited);
    });
  }

  function close(container) {
    container.innerHTML = '';
    _onSave = null;
  }

  function updateCharCount(textarea, countEl) {
    const len = textarea.value.length;
    const max = XRAY.LIMITS.MAX_DESCRIPTION;
    countEl.textContent = `${len} / ${max}`;
    countEl.style.color = len > max * 0.9 ? '#dc3545' : '#666';
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    if (!str) return '';
    return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  return { open, close };
})();