// shared/diff-engine.js — Intelligent diff matching between AI-extracted and KDP entities
// Supports exact match, fuzzy match (Levenshtein), and alias matching

const DiffEngine = (() => {
  'use strict';

  // ============ LEVENSHTEIN DISTANCE ============

  /**
   * Calculate Levenshtein distance between two strings
   */
  function levenshtein(a, b) {
    const m = a.length, n = b.length;
    if (m === 0) return n;
    if (n === 0) return m;

    const d = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

    for (let i = 0; i <= m; i++) d[i][0] = i;
    for (let j = 0; j <= n; j++) d[0][j] = j;

    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        d[i][j] = Math.min(
          d[i - 1][j] + 1,      // deletion
          d[i][j - 1] + 1,      // insertion
          d[i - 1][j - 1] + cost // substitution
        );
      }
    }

    return d[m][n];
  }

  /**
   * Calculate similarity ratio (0.0 - 1.0) between two strings
   */
  function similarity(a, b) {
    if (a === '' && b === '') return 1.0;
    if (!a || !b) return 0;
    const la = a.toLowerCase().trim();
    const lb = b.toLowerCase().trim();
    if (la === lb) return 1.0;

    const maxLen = Math.max(la.length, lb.length);
    if (maxLen === 0) return 1.0;

    const dist = levenshtein(la, lb);
    return 1.0 - (dist / maxLen);
  }

  /**
   * Check if nameA contains nameB or vice versa (partial match)
   * E.g., "Kyle" matches "Kyle Chen", "Dr. Smith" matches "Smith"
   */
  function partialMatch(a, b) {
    const la = a.toLowerCase().trim();
    const lb = b.toLowerCase().trim();
    if (la.includes(lb) || lb.includes(la)) {
      // Return a score based on how much of the longer string is covered
      const shorter = Math.min(la.length, lb.length);
      const longer = Math.max(la.length, lb.length);
      return shorter / longer;
    }
    return 0;
  }

  /**
   * Check if any alias matches the target name
   */
  function aliasMatch(name, aliases) {
    if (!aliases || aliases.length === 0) return 0;
    const lname = name.toLowerCase().trim();
    for (const alias of aliases) {
      const la = alias.toLowerCase().trim();
      if (la === lname) return 1.0;
      const sim = similarity(la, lname);
      if (sim >= 0.85) return sim;
    }
    return 0;
  }

  // ============ MATCHING ALGORITHM ============

  /**
   * Find best match for an imported entity in KDP entities
   * Returns { kdpEntity, score, matchType } or null
   */
  function findBestMatch(importedEntity, kdpEntities, threshold) {
    threshold = threshold || 0.75;
    let bestMatch = null;
    let bestScore = 0;
    let bestType = 'none';

    const iName = importedEntity.name;

    for (const kdp of kdpEntities) {
      // 1. Exact match (case-insensitive)
      const exactSim = similarity(iName, kdp.name);
      if (exactSim === 1.0) {
        return { kdpEntity: kdp, score: 1.0, matchType: 'exact' };
      }

      // 2. Fuzzy match
      if (exactSim > bestScore && exactSim >= threshold) {
        bestScore = exactSim;
        bestMatch = kdp;
        bestType = 'fuzzy';
      }

      // 3. Partial match (substring)
      const partial = partialMatch(iName, kdp.name);
      if (partial > bestScore && partial >= threshold) {
        bestScore = partial;
        bestMatch = kdp;
        bestType = 'partial';
      }

      // 4. Alias match (if KDP entity has aliases)
      if (kdp.aliases) {
        const aliasScore = aliasMatch(iName, kdp.aliases);
        if (aliasScore > bestScore && aliasScore >= threshold) {
          bestScore = aliasScore;
          bestMatch = kdp;
          bestType = 'alias';
        }
      }

      // 5. Check imported aliases against KDP name
      if (importedEntity.aliases) {
        const reverseAliasScore = aliasMatch(kdp.name, importedEntity.aliases);
        if (reverseAliasScore > bestScore && reverseAliasScore >= threshold) {
          bestScore = reverseAliasScore;
          bestMatch = kdp;
          bestType = 'reverse_alias';
        }
      }
    }

    if (bestMatch && bestScore >= threshold) {
      return { kdpEntity: bestMatch, score: bestScore, matchType: bestType };
    }

    return null;
  }

  // ============ DIFF GENERATION ============

  /**
   * Compare field values and generate change list
   */
  function compareFields(imported, kdp) {
    const changes = [];

    // Type comparison — only flag if BOTH types are known and they differ.
    // When KDP type is empty (e.g. from quick export without details), skip
    // to avoid false "update" flags.
    const importType = normalizeType(imported.type);
    const kdpType = normalizeType(kdp.type);
    if (importType && kdpType && importType !== kdpType) {
      changes.push({
        field: 'type',
        from: kdpType,
        to: importType,
      });
    }

    // Description comparison
    if (imported.description) {
      const iDesc = imported.description.trim();
      const kDesc = (kdp.description || '').trim();
      if (iDesc !== kDesc) {
        changes.push({
          field: 'description',
          from: truncate(kDesc, 100) || '(empty)',
          to: truncate(iDesc, 100),
          fullFrom: kDesc,
          fullTo: iDesc,
        });
      }
    }

    // Commentary comparison
    if (imported.commentary) {
      const iComm = imported.commentary.trim();
      const kComm = (kdp.commentary || '').trim();
      if (iComm !== kComm) {
        changes.push({
          field: 'commentary',
          from: truncate(kComm, 80) || '(empty)',
          to: truncate(iComm, 80),
        });
      }
    }

    // Include/exclude
    if (imported.action === XRAY.ACTION.DELETE) {
      changes.push({
        field: 'visibility',
        from: 'included',
        to: 'excluded',
      });
    }

    return changes;
  }

  /**
   * Generate full diff between imported entities and KDP entities
   * @param {Array} importedEntities - from AI extraction or JSON paste
   * @param {Array} kdpEntities - read from KDP page
   * @param {Object} options - { threshold: 0.75 }
   * @returns {Array} diff items with action, changes, etc.
   */
  function generateDiff(importedEntities, kdpEntities, options) {
    options = options || {};
    const threshold = options.threshold || 0.75;

    const results = [];
    const matchedKdpIndices = new Set();
    const kdpByIndex = new Map();
    kdpEntities.forEach((e, i) => kdpByIndex.set(i, e));

    // --- Phase 1: Match imported entities to KDP entities ---
    importedEntities.forEach((imported) => {
      // Find unmatched KDP entities
      const unmatchedKdp = kdpEntities.filter((_, i) => !matchedKdpIndices.has(i));
      const match = findBestMatch(imported, unmatchedKdp, threshold);

      if (match) {
        // Find the actual index in full array
        const kdpIdx = kdpEntities.indexOf(match.kdpEntity);
        matchedKdpIndices.add(kdpIdx);

        if (imported.action === XRAY.ACTION.DELETE) {
          results.push({
            name: imported.name,
            action: XRAY.ACTION.DELETE,
            source: 'both',
            imported,
            kdp: match.kdpEntity,
            matchScore: match.score,
            matchType: match.matchType,
            changes: [{ field: 'visibility', from: 'included', to: 'excluded' }],
          });
        } else {
          const changes = compareFields(imported, match.kdpEntity);
          results.push({
            name: imported.name,
            action: changes.length > 0 ? XRAY.ACTION.UPDATE : 'keep',
            source: 'both',
            imported,
            kdp: match.kdpEntity,
            matchScore: match.score,
            matchType: match.matchType,
            changes,
          });
        }
      } else {
        // No match found in KDP — new entity to add
        results.push({
          name: imported.name,
          action: imported.action === XRAY.ACTION.DELETE ? XRAY.ACTION.DELETE : XRAY.ACTION.ADD,
          source: 'import_only',
          imported,
          kdp: null,
          matchScore: 0,
          matchType: 'none',
          changes: [{
            field: 'status',
            from: '(not in KDP)',
            to: 'will be added as new entity',
          }],
        });
      }
    });

    // --- Phase 2: Identify unmatched KDP entities (potential deletions) ---
    if (options.showUnmatched !== false) {
      kdpEntities.forEach((kdp, i) => {
        if (!matchedKdpIndices.has(i)) {
          results.push({
            name: kdp.name,
            action: 'kdp_only',
            source: 'kdp_only',
            imported: null,
            kdp: kdp,
            matchScore: 0,
            matchType: 'none',
            changes: [],
          });
        }
      });
    }

    // --- Sort: updates first, then adds, then deletes, then kdp-only, then keeps ---
    const actionOrder = { update: 0, delete: 1, add: 2, kdp_only: 3, keep: 4 };
    results.sort((a, b) => {
      const oa = actionOrder[a.action] ?? 5;
      const ob = actionOrder[b.action] ?? 5;
      return oa - ob;
    });

    return results;
  }

  // ============ STATISTICS ============

  function getDiffStats(diffResults) {
    return {
      total: diffResults.length,
      updates: diffResults.filter(d => d.action === XRAY.ACTION.UPDATE).length,
      adds: diffResults.filter(d => d.action === XRAY.ACTION.ADD).length,
      deletes: diffResults.filter(d => d.action === XRAY.ACTION.DELETE).length,
      keeps: diffResults.filter(d => d.action === 'keep').length,
      kdpOnly: diffResults.filter(d => d.action === 'kdp_only').length,
      importOnly: diffResults.filter(d => d.source === 'import_only').length,
      fuzzyMatches: diffResults.filter(d => d.matchType === 'fuzzy' || d.matchType === 'partial').length,
    };
  }

  // ============ HELPERS ============

  function normalizeType(type) {
    if (!type) return '';
    const t = type.toUpperCase().trim();
    if (t === 'CHARACTER' || t === 'CHAR') return XRAY.TYPE.CHARACTER;
    if (t === 'TERM' || t === 'TOPIC') return XRAY.TYPE.TERM;
    return t;
  }

  function truncate(str, maxLen) {
    if (!str) return '';
    if (str.length <= maxLen) return str;
    return str.substring(0, maxLen) + '...';
  }

  // ============ PUBLIC API ============

  return {
    // Core
    generateDiff,
    findBestMatch,
    getDiffStats,

    // Utilities (exported for testing)
    levenshtein,
    similarity,
    partialMatch,
    aliasMatch,
    compareFields,
    normalizeType,
  };
})();