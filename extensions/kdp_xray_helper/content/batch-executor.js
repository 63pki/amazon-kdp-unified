// content/batch-executor.js — Batch processing with retry + cancellation

const BatchExecutor = (() => {
  'use strict';

  // CancelToken: mutable object passed to batch, checked each iteration
  function createCancelToken() {
    return { cancelled: false };
  }

  let _activeCancelToken = null;

  /**
   * Retry wrapper with exponential backoff
   */
  async function withRetry(fn, maxRetries, entityName, progressCallback) {
    maxRetries = maxRetries || XRAY.LIMITS.MAX_RETRIES;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await fn();
      } catch (err) {
        if (attempt === maxRetries) throw err;

        const delay = XRAY.DELAY.RETRY_BASE * Math.pow(2, attempt);
        if (progressCallback) {
          progressCallback({
            phase: 'retry',
            name: entityName,
            attempt: attempt + 1,
            maxRetries: maxRetries,
          });
        }
        await DomWriter.sleep(delay);
      }
    }
  }

  /**
   * Check if an entity exists in the sidebar
   */
  function entityExistsInSidebar(name) {
    const entities = DomReader.getAllEntities();
    return entities.some(e => e.name.toLowerCase() === name.toLowerCase());
  }

  /**
   * Process a single entity — handles add, update, and delete
   *
   * Unified flow:
   *   1. Check if entity exists in sidebar
   *   2. If not → create it first (unless action is delete)
   *   3. Select it and apply all field changes
   *
   * This avoids separate ADD/UPDATE code paths and ensures new entities
   * are always created before any field operations are attempted.
   */
  async function processEntity(entityData) {
    const action = entityData.action || XRAY.ACTION.UPDATE;
    const exists = entityExistsInSidebar(entityData.name);

    // ============ DELETE: exclude the entity ============
    if (action === XRAY.ACTION.DELETE) {
      if (!exists) {
        return { name: entityData.name, status: 'skip', success: true, message: 'Not in KDP, nothing to delete' };
      }
      await DomWriter.selectEntityByName(entityData.name);
      await DomWriter.setIncludeExclude(false);
      await DomWriter.setItemReviewed(true);
      return { name: entityData.name, status: 'excluded', success: true };
    }

    // ============ CREATE if entity doesn't exist in sidebar ============
    let wasCreated = false;
    if (!exists) {
      await DomWriter.addNewEntity(entityData.name, entityData.type || XRAY.TYPE.CHARACTER);
      wasCreated = true;
    }

    // ============ SELECT the entity (with retry for newly created ones) ============
    let selected = false;
    const maxAttempts = wasCreated ? 5 : 3;
    for (let attempt = 0; attempt < maxAttempts && !selected; attempt++) {
      try {
        await DomWriter.selectEntityByName(entityData.name);
        selected = true;
      } catch (e) {
        if (attempt < maxAttempts - 1) {
          await DomWriter.sleep(XRAY.DELAY.BETWEEN_ENTITIES * (attempt + 1));
        }
      }
    }
    if (!selected) {
      throw new Error(`Entity "${entityData.name}" ${wasCreated ? 'was created but' : ''} could not be found in sidebar`);
    }

    // ============ APPLY FIELDS ============

    // Set include/exclude
    const shouldInclude = entityData.show_description !== 'no' && entityData.included !== false;
    await DomWriter.setIncludeExclude(shouldInclude);

    // Set type (CHARACTER or TERM)
    const type = (entityData.type === XRAY.TYPE.TERM || entityData.type === XRAY.TYPE.TOPIC)
      ? XRAY.TYPE.TERM
      : XRAY.TYPE.CHARACTER;
    await DomWriter.setEntityType(type);

    // Set description
    if (entityData.description) {
      await DomWriter.setDescription(
        entityData.description,
        entityData.commentary || ''
      );
    }

    // Mark as reviewed
    await DomWriter.setItemReviewed(true);

    return { name: entityData.name, status: wasCreated ? 'added' : 'updated', success: true };
  }

  /**
   * Batch process an array of entity operations
   * @param {Array} dataArray - entities to process
   * @param {Function} progressCallback - called with progress info
   * @returns {Array} results for each entity
   */
  async function batchProcess(dataArray, progressCallback) {
    const results = [];
    _activeCancelToken = createCancelToken();
    const token = _activeCancelToken;

    for (let i = 0; i < dataArray.length; i++) {
      // *** CHECK CANCEL TOKEN ***
      if (token.cancelled) {
        // Mark remaining as cancelled
        for (let j = i; j < dataArray.length; j++) {
          results.push({
            name: dataArray[j].name,
            status: 'cancelled',
            success: false,
          });
        }
        break;
      }

      const entity = dataArray[i];

      if (progressCallback) {
        progressCallback({
          current: i + 1,
          total: dataArray.length,
          name: entity.name,
          phase: 'processing',
        });
      }

      try {
        const result = await withRetry(
          () => processEntity(entity),
          XRAY.LIMITS.MAX_RETRIES,
          entity.name,
          progressCallback
        );
        results.push(result);
      } catch (err) {
        results.push({
          name: entity.name,
          status: 'error',
          success: false,
          error: err.message,
        });
      }

      // Wait between entities (unless cancelled)
      if (!token.cancelled && i < dataArray.length - 1) {
        await DomWriter.sleep(XRAY.DELAY.BETWEEN_ENTITIES);
      }
    }

    _activeCancelToken = null;
    return results;
  }

  /**
   * Stop the current batch processing
   */
  function stopProcessing() {
    if (_activeCancelToken) {
      _activeCancelToken.cancelled = true;
      return true;
    }
    return false;
  }

  /**
   * Check if batch is currently running
   */
  function isProcessing() {
    return _activeCancelToken !== null && !_activeCancelToken.cancelled;
  }

  return {
    batchProcess,
    stopProcessing,
    isProcessing,
    processEntity,
    createCancelToken,
  };
})();