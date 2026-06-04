// shared/storage.js — chrome.storage abstraction layer

const Storage = (() => {
  async function get(key, defaultValue = null) {
    try {
      const result = await chrome.storage.sync.get(key);
      return result[key] !== undefined ? result[key] : defaultValue;
    } catch (e) {
      console.warn('[Storage] get error:', key, e);
      return defaultValue;
    }
  }

  async function getAll(keys) {
    try {
      return await chrome.storage.sync.get(keys);
    } catch (e) {
      console.warn('[Storage] getAll error:', e);
      return {};
    }
  }

  async function set(key, value) {
    try {
      await chrome.storage.sync.set({ [key]: value });
    } catch (e) {
      console.warn('[Storage] set error:', key, e);
    }
  }

  async function setMultiple(obj) {
    try {
      await chrome.storage.sync.set(obj);
    } catch (e) {
      console.warn('[Storage] setMultiple error:', e);
    }
  }

  async function remove(key) {
    try {
      await chrome.storage.sync.remove(key);
    } catch (e) {
      console.warn('[Storage] remove error:', key, e);
    }
  }

  return { get, getAll, set, setMultiple, remove };
})();