// content/dom-reader.js — Read entity data from KDP X-Ray page DOM

const DomReader = (() => {
  'use strict';

  /**
   * Get all entities from the sidebar list
   * Returns basic info: name, status, index
   */
  function getAllEntities() {
    const entities = document.querySelectorAll(XRAY.SEL.ENTITY_ITEM);
    return Array.from(entities).map((el) => {
      const name = el.querySelector(XRAY.SEL.ENTITY_NAME)?.textContent?.trim() || '';
      const status = el.querySelector(XRAY.SEL.ENTITY_STATUS)?.textContent?.trim() || '';
      const index = parseInt(el.getAttribute('data-index'));
      return { name, status, index, element: el };
    });
  }

  /**
   * Get the name of the currently selected entity in detail panel
   */
  function getCurrentEntityName() {
    return document.querySelector(XRAY.SEL.DETAIL_LABEL)?.textContent?.trim() || '';
  }

  /**
   * Read detailed info of the currently selected entity
   * Includes type, description, commentary, aliases, include/exclude state
   */
  function readCurrentEntityDetails() {
    const name = getCurrentEntityName();
    if (!name) return null;

    // Determine type
    const charRadio = document.querySelector(XRAY.SEL.DETAIL_TYPE_CHAR);
    const topicRadio = document.querySelector(XRAY.SEL.DETAIL_TYPE_TOPIC);
    let type = XRAY.TYPE.CHARACTER;
    if (topicRadio && topicRadio.checked) {
      type = XRAY.TYPE.TERM;
    }

    // Include/exclude state
    const includeRadio = document.querySelector(XRAY.SEL.DETAIL_INCLUDE);
    const excludeRadio = document.querySelector(XRAY.SEL.DETAIL_EXCLUDE);
    const included = includeRadio ? includeRadio.checked : true;

    // Description and commentary
    const descEl = document.querySelector(XRAY.SEL.DESC_TEXT);
    const commentEl = document.querySelector(XRAY.SEL.COMMENTARY_TEXT);
    const description = descEl?.textContent?.trim() || '';
    const commentary = commentEl?.textContent?.trim() || '';

    // Review state
    const doneSwitch = document.querySelector(XRAY.SEL.DONE_SWITCH);
    const reviewed = doneSwitch ? doneSwitch.checked : false;

    // Aliases — KDP detail panel uses table (tr.alias) with columns:
    //   Spelling/usage | Occurrences | Display name | Remove
    // Also capture occurrence count and which alias is the display name.
    const aliasEls = document.querySelectorAll(XRAY.SEL.ALIAS_LIST);
    const aliasDetails = [];
    const aliases = [];

    Array.from(aliasEls).forEach(el => {
      let text = '';
      let occurrences = 0;
      let isDisplayName = false;

      if (el.tagName === 'TR') {
        // Table row: first <td> = text, second <td> has .count link = occurrences
        const tds = el.querySelectorAll('td');
        text = tds[0]?.textContent?.trim() || '';
        const countEl = el.querySelector('a.count, .count');
        occurrences = parseInt(countEl?.textContent?.trim()) || 0;
        // Display name: row has class "display" or radio is checked
        isDisplayName = el.classList.contains('display') ||
          !!el.querySelector('input[name="displayName"].checked, input.make-display:checked');
      } else {
        // Div-based fallback
        const textEl = el.querySelector(XRAY.SEL.ALIAS_TEXT);
        text = (textEl || el).textContent?.trim() || '';
      }

      if (text) {
        aliases.push(text);
        aliasDetails.push({ text, occurrences, isDisplayName });
      }
    });

    return {
      name,
      type,
      included,
      description,
      commentary,
      reviewed,
      aliases,
      aliasDetails,
    };
  }

  /**
   * Export all entities with full details
   * Navigates to each entity to read its details (slow but complete)
   */
  async function exportAllEntitiesDetailed(progressCallback) {
    const entities = getAllEntities();
    const results = [];

    for (let i = 0; i < entities.length; i++) {
      const entity = entities[i];

      if (progressCallback) {
        progressCallback({ current: i + 1, total: entities.length, name: entity.name });
      }

      // Navigate to entity
      try {
        await DomWriter.selectEntityByIndex(entity.index);
        await sleep(XRAY.DELAY.AFTER_ACTION);

        const details = readCurrentEntityDetails();
        results.push({
          name: entity.name,
          status: entity.status,
          dataIndex: entity.index,
          ...(details || {}),
        });
      } catch (err) {
        results.push({
          name: entity.name,
          status: entity.status,
          dataIndex: entity.index,
          error: err.message,
        });
      }
    }

    return results;
  }

  /**
   * Quick export: just names, status, and index (no navigation needed)
   */
  function exportEntitiesQuick() {
    const entities = getAllEntities();
    return entities.map(e => ({
      name: e.name,
      status: e.status,
      dataIndex: e.index,
    }));
  }

  /**
   * Check if KDP X-Ray page is ready for automation
   */
  function isPageReady() {
    const entities = document.querySelectorAll(XRAY.SEL.ENTITY_ITEM);
    return entities.length > 0;
  }

  return {
    getAllEntities,
    getCurrentEntityName,
    readCurrentEntityDetails,
    exportAllEntitiesDetailed,
    exportEntitiesQuick,
    isPageReady,
  };
})();