// content/dom-writer.js — Write/modify entity fields on KDP X-Ray page

const DomWriter = (() => {
  'use strict';

  // ============ UTILITY FUNCTIONS ============

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function waitForElement(selector, timeout) {
    timeout = timeout || XRAY.LIMITS.ELEMENT_TIMEOUT;
    return new Promise((resolve, reject) => {
      const el = document.querySelector(selector);
      if (el) return resolve(el);

      const observer = new MutationObserver(() => {
        const el = document.querySelector(selector);
        if (el) {
          observer.disconnect();
          resolve(el);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Timeout waiting for ${selector}`));
      }, timeout);
    });
  }

  function simulateClick(el) {
    if (!el) return;
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  }

  function triggerInputEvent(el) {
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  // ============ ENTITY NAVIGATION ============

  async function selectEntityByIndex(dataIndex) {
    const entity = document.querySelector(`${XRAY.SEL.ENTITY_ITEM}[data-index="${dataIndex}"]`);
    if (!entity) throw new Error(`Entity with index ${dataIndex} not found`);

    // Scroll into view
    entity.scrollIntoView({ block: 'center', behavior: 'smooth' });
    await sleep(XRAY.DELAY.AFTER_CLICK);

    // Click to select
    simulateClick(entity);
    await sleep(XRAY.DELAY.AFTER_ACTION);

    // Verify selection loaded
    const detailName = DomReader.getCurrentEntityName();
    const entityName = entity.querySelector(XRAY.SEL.ENTITY_NAME)?.textContent?.trim();
    if (detailName !== entityName) {
      // Retry once
      await sleep(500);
      simulateClick(entity);
      await sleep(XRAY.DELAY.AFTER_ACTION);
    }

    return DomReader.getCurrentEntityName();
  }

  async function selectEntityByName(name) {
    const entities = DomReader.getAllEntities();
    const match = entities.find(e => e.name.toLowerCase() === name.toLowerCase());
    if (!match) throw new Error(`Entity "${name}" not found in sidebar`);
    return selectEntityByIndex(match.index);
  }

  // ============ FIELD OPERATIONS ============

  async function setEntityType(type) {
    const radioSelector = type === XRAY.TYPE.CHARACTER
      ? XRAY.SEL.DETAIL_TYPE_CHAR
      : XRAY.SEL.DETAIL_TYPE_TOPIC;

    const radio = document.querySelector(radioSelector);
    if (!radio) throw new Error(`Radio button for type ${type} not found`);

    if (!radio.checked) {
      const wrapper = radio.closest(XRAY.SEL.RADIO_WRAPPER) || radio.parentElement;
      simulateClick(wrapper);
      await sleep(XRAY.DELAY.AFTER_ACTION);
    }
  }

  async function setIncludeExclude(include) {
    const selector = include ? XRAY.SEL.DETAIL_INCLUDE : XRAY.SEL.DETAIL_EXCLUDE;
    const radio = document.querySelector(selector);
    if (!radio) return;

    if (!radio.checked) {
      const wrapper = radio.closest(XRAY.SEL.RADIO_WRAPPER) || radio.parentElement;
      simulateClick(wrapper);
      await sleep(XRAY.DELAY.AFTER_ACTION);
    }
  }

  async function setDescription(description, commentary) {
    commentary = commentary || '';

    // Open custom description dialog
    const addDescBtn = document.querySelector(XRAY.SEL.DESC_ADD_BTN);
    if (!addDescBtn) throw new Error('Add description button not found');

    simulateClick(addDescBtn);
    await sleep(XRAY.DELAY.DIALOG_OPEN);

    // Wait for dialog
    const dialog = await waitForElement(XRAY.SEL.DESC_DIALOG_VISIBLE)
      .catch(() => document.querySelector(XRAY.SEL.DESC_DIALOG));

    // Find textareas
    const textareas = document.querySelector(XRAY.SEL.DESC_MODAL_BODY)
      ?.querySelectorAll('textarea');
    if (!textareas || textareas.length < 2) {
      throw new Error('Description textareas not found');
    }

    // Fill description
    textareas[0].value = '';
    textareas[0].focus();
    textareas[0].value = description;
    triggerInputEvent(textareas[0]);

    // Fill commentary
    if (commentary) {
      textareas[1].value = '';
      textareas[1].focus();
      textareas[1].value = commentary;
      triggerInputEvent(textareas[1]);
    }

    await sleep(XRAY.DELAY.AFTER_CLICK);

    // Submit — button may be disabled by default; enable it first
    let submitBtn = document.querySelector(XRAY.SEL.DESC_SUBMIT);
    if (!submitBtn) {
      submitBtn = document.querySelector(XRAY.SEL.DESC_SUBMIT_FALLBACK);
    }
    if (submitBtn) {
      // KDP disables submit until textarea input; force-enable for automation
      submitBtn.removeAttribute('disabled');
      const outerSpan = submitBtn.closest('.a-button');
      if (outerSpan) {
        outerSpan.classList.remove('a-button-disabled');
      }
      simulateClick(submitBtn);
    }

    await sleep(XRAY.DELAY.AFTER_ACTION);
  }

  async function setItemReviewed(reviewed) {
    const doneSwitch = document.querySelector(XRAY.SEL.DONE_SWITCH);
    if (!doneSwitch) return;

    if (doneSwitch.checked !== reviewed) {
      const label = document.querySelector(XRAY.SEL.DONE_SWITCH_LABEL);
      simulateClick(label || doneSwitch);
      await sleep(XRAY.DELAY.AFTER_ACTION);
    }
  }

  /**
   * Add a brand-new entity via KDP's "Add a new item" dialog
   * @param {string} name - entity name
   * @param {string} type - CHARACTER or TERM/TOPIC
   * @returns {boolean} true if entity was created
   */
  /**
   * Poll sidebar until an entity with the given name appears
   * @param {string} name - entity name to look for
   * @param {number} timeoutMs - max wait (default 10s)
   * @returns {boolean} true if found
   */
  async function waitForEntityInSidebar(name, timeoutMs) {
    timeoutMs = timeoutMs || 10000;
    const interval = 500;
    const maxAttempts = Math.ceil(timeoutMs / interval);
    const lowerName = name.toLowerCase();

    for (let i = 0; i < maxAttempts; i++) {
      const entities = DomReader.getAllEntities();
      if (entities.some(e => e.name.toLowerCase() === lowerName)) {
        return true;
      }
      await sleep(interval);
    }
    return false;
  }

  /**
   * Wait for submit button to become enabled (KDP auto-enables after validation)
   */
  async function waitForSubmitEnabled(selector, timeoutMs) {
    timeoutMs = timeoutMs || 3000;
    const interval = 200;
    const maxAttempts = Math.ceil(timeoutMs / interval);
    for (let i = 0; i < maxAttempts; i++) {
      const btn = document.querySelector(selector);
      if (btn && !btn.disabled) return btn;
      await sleep(interval);
    }
    return null;
  }

  async function addNewEntity(name, type) {
    // 1. Click "Add a new item" link
    //    KDP uses Bootstrap modal: data-toggle="modal" data-target="#newEntityDialog"
    const addBtn = document.querySelector(XRAY.SEL.NEW_ENTITY_BTN);
    if (!addBtn) throw new Error('Add new item button (#newEntityButton) not found');

    simulateClick(addBtn);
    await sleep(XRAY.DELAY.DIALOG_OPEN);

    // 2. Wait for dialog to become visible
    const dialog = await waitForElement(XRAY.SEL.NEW_ENTITY_DIALOG_VISIBLE)
      .catch(() => document.querySelector(XRAY.SEL.NEW_ENTITY_DIALOG));
    if (!dialog) throw new Error('New entity dialog did not open');

    // 3. Fill in entity name — dispatch all event types KDP listens on
    const nameInput = document.querySelector(XRAY.SEL.NEW_ENTITY_NAME);
    if (!nameInput) throw new Error('Entity name input (#entityName) not found');

    nameInput.value = '';
    nameInput.focus();
    nameInput.value = name;
    nameInput.dispatchEvent(new Event('input', { bubbles: true }));
    nameInput.dispatchEvent(new Event('change', { bubbles: true }));
    nameInput.dispatchEvent(new Event('keyup', { bubbles: true }));

    // 4. Select entity type (CHARACTER or TOPIC)
    //    Real KDP uses button[name="CHARACTER"] / button[name="TOPIC"] inside AUI button group
    const typeValue = (type === XRAY.TYPE.TERM || type === XRAY.TYPE.TOPIC)
      ? 'TOPIC' : 'CHARACTER';
    const typeSel = typeValue === 'TOPIC' ? 'NEW_ENTITY_TYPE_TOPIC' : 'NEW_ENTITY_TYPE_CHAR';
    const typeBtn = document.querySelector(XRAY.SEL[typeSel]);
    if (typeBtn) {
      // Click both the outer .a-button wrapper and the button itself for AUI
      const wrapper = typeBtn.closest('.a-button') || typeBtn;
      simulateClick(wrapper);
      simulateClick(typeBtn);
    }

    // 5. Wait for KDP to auto-enable the submit button (~1.5s after input events)
    //    KDP validates the name field and enables submit automatically
    let submitBtn = await waitForSubmitEnabled(XRAY.SEL.NEW_ENTITY_SUBMIT, 3000);

    if (!submitBtn) {
      // Fallback: force-enable if KDP validation didn't fire
      submitBtn = document.querySelector(XRAY.SEL.NEW_ENTITY_SUBMIT);
      if (submitBtn) {
        submitBtn.removeAttribute('disabled');
        const outerSpan = submitBtn.closest('.a-button');
        if (outerSpan) outerSpan.classList.remove('a-button-disabled');
      }
    }

    if (!submitBtn) {
      throw new Error('Create entity submit button not found');
    }

    // 6. Click submit
    simulateClick(submitBtn);
    await sleep(XRAY.DELAY.AFTER_ACTION);

    // 7. Poll sidebar until the new entity appears
    //    KDP sends POST to get_entity_id + post_contributions, then updates sidebar
    const found = await waitForEntityInSidebar(name, 15000);
    if (!found) {
      // Retry submit once — sometimes click is swallowed by modal animation
      submitBtn = document.querySelector(XRAY.SEL.NEW_ENTITY_SUBMIT);
      if (submitBtn) {
        submitBtn.removeAttribute('disabled');
        simulateClick(submitBtn);
      }
      const retryFound = await waitForEntityInSidebar(name, 10000);
      if (!retryFound) {
        throw new Error(`Entity "${name}" was not created — it did not appear in sidebar after submission`);
      }
    }

    return true;
  }

  async function removeAlias(aliasText) {
    const removeBtn = document.querySelector(
      `${XRAY.SEL.ALIAS_REMOVE}[data-remove-alias-action*='"alias":"${aliasText}"']`
    );
    if (removeBtn) {
      simulateClick(removeBtn);
      await sleep(XRAY.DELAY.AFTER_ACTION);
    }
  }

  return {
    sleep,
    waitForElement,
    simulateClick,
    selectEntityByIndex,
    selectEntityByName,
    setEntityType,
    setIncludeExclude,
    setDescription,
    setItemReviewed,
    addNewEntity,
    removeAlias,
  };
})();