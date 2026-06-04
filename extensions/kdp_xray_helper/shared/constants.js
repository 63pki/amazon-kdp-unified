// shared/constants.js — Global constants and KDP DOM selectors
// Centralized configuration for the entire extension

const XRAY = {
  // ============ TIMING ============
  DELAY: {
    BETWEEN_ENTITIES: 800,    // ms between entity operations
    AFTER_ACTION: 300,        // ms after each field change
    AFTER_CLICK: 200,         // ms after click before verification
    DIALOG_OPEN: 500,         // ms wait for dialog to appear
    RETRY_BASE: 500,          // base ms for exponential backoff
  },

  // ============ LIMITS ============
  LIMITS: {
    MAX_DESCRIPTION: 1175,    // max chars for description field
    MAX_RETRIES: 3,           // max retry attempts per entity
    ELEMENT_TIMEOUT: 5000,    // ms timeout waiting for DOM element
  },

  // ============ KDP DOM SELECTORS ============
  // Centralized so we can quickly update if Amazon changes their page
  SEL: {
    // Entity list (sidebar)
    ENTITY_ITEM:        '.entity.well',
    ENTITY_NAME:        '.displayname',
    ENTITY_STATUS:      '.entity-status',

    // Entity detail panel
    DETAIL_LABEL:       '.entityAttributes .entityLabel',
    DETAIL_TYPE_CHAR:   'input[name="CHARACTER"]',
    DETAIL_TYPE_TOPIC:  'input[name="TOPIC"]',
    DETAIL_INCLUDE:     'input[name="include"]',
    DETAIL_EXCLUDE:     'input[name="exclude"]',
    RADIO_WRAPPER:      '.a-declarative',

    // Description dialog
    DESC_ADD_BTN:       '[data-action="add-description-action"][data-add-description-action*="AUTHOR"]',
    DESC_DIALOG:        '#humanDescriptionDialog',
    DESC_DIALOG_VISIBLE:'#humanDescriptionDialog[style*="display: block"], #humanDescriptionDialog.in',
    DESC_MODAL_BODY:    '#humanDescriptionDialog .modal-body',
    DESC_SUBMIT:        '#humanDescriptionDialog #humanDescriptionButton',
    DESC_SUBMIT_FALLBACK: '#humanDescriptionDialog .a-button-input, #humanDescriptionDialog input[type="submit"]',

    // Review toggle
    DONE_SWITCH:        'input[name="doneSwitch"]',
    DONE_SWITCH_LABEL:  '#doneSwitch label.a-switch-label',

    // Add new entity
    NEW_ENTITY_BTN:     '#newEntityButton a',
    NEW_ENTITY_DIALOG:  '#newEntityDialog',
    NEW_ENTITY_DIALOG_VISIBLE: '#newEntityDialog.in, #newEntityDialog[style*="display: block"]',
    NEW_ENTITY_NAME:    '#entityName',
    NEW_ENTITY_TYPE_CHAR: '#entityType [data-value="CHARACTER"], #entityType button[name="CHARACTER"]',
    NEW_ENTITY_TYPE_TOPIC:'#entityType [data-value="TOPIC"], #entityType button[name="TOPIC"]',
    NEW_ENTITY_SUBMIT:  '#createNewEntityButton input, #createNewEntityButton .a-button-input',

    // Alias
    ALIAS_REMOVE:       '[data-action="remove-alias-action"]',

    // Description text (in detail panel)
    // KDP renders .entityDescription via JS; #descriptionRow exists in description template
    DESC_TEXT:          '.entityDescription, #descriptionRow',
    COMMENTARY_TEXT:    '.entityCommentary, .entityDescriptions .a-box-inner',

    // Alias list — detail panel uses table (tr.alias), alias template uses div.aliases
    ALIAS_LIST:         'tr.alias, .aliases .alias',
    ALIAS_TEXT:         '.aliasText',
  },

  // ============ ENTITY TYPES ============
  TYPE: {
    CHARACTER: 'CHARACTER',
    TERM: 'TERM',
    TOPIC: 'TOPIC',  // KDP internal name for TERM
  },

  // ============ ACTIONS ============
  ACTION: {
    UPDATE: 'update',
    DELETE: 'delete',
    ADD: 'add',
  },

  // ============ WORKFLOW STATES ============
  STATE: {
    INIT: 'init',
    IMPORT: 'import',
    DIFF: 'diff',
    EXECUTE: 'execute',
    DONE: 'done',
  },

  // ============ MESSAGE ACTIONS ============
  MSG: {
    // Content script messages
    PING: 'ping',
    GET_ENTITIES: 'getEntities',
    GET_ENTITY_DETAILS: 'getEntityDetails',
    BATCH_PROCESS: 'batchProcess',
    STOP_PROCESSING: 'stopProcessing',
    PROCESS_SINGLE: 'processSingle',

    // Progress messages
    PROGRESS: 'progress',
    BATCH_COMPLETE: 'batchComplete',
  },
};