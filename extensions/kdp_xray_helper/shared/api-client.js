// shared/api-client.js — Utility functions kept from deprecated API client
// The extension now uses a prompt-based workflow instead of direct API calls.

const APIClient = (() => {
  'use strict';

  /**
   * Parse JSON from AI response (handles markdown code blocks, extra text)
   */
  function parseEntityJSON(content) {
    try {
      const data = JSON.parse(content);
      if (Array.isArray(data)) return data;
    } catch { /* continue */ }

    const jsonMatch = content.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
    if (jsonMatch) {
      try {
        const data = JSON.parse(jsonMatch[1]);
        if (Array.isArray(data)) return data;
      } catch { /* continue */ }
    }

    const bracketMatch = content.match(/\[[\s\S]*\]/);
    if (bracketMatch) {
      try {
        const data = JSON.parse(bracketMatch[0]);
        if (Array.isArray(data)) return data;
      } catch { /* continue */ }
    }

    throw new Error('Could not parse entity JSON from response');
  }

  /**
   * Split text into chunks respecting paragraph boundaries
   */
  function chunkText(text, maxChunkSize) {
    maxChunkSize = maxChunkSize || 10000;
    const paragraphs = text.split(/\n\s*\n/);
    const chunks = [];
    let current = '';

    for (const para of paragraphs) {
      if (current.length + para.length + 2 > maxChunkSize) {
        if (current) chunks.push(current.trim());
        if (para.length > maxChunkSize) {
          const sentences = para.match(/[^.!?]+[.!?]+/g) || [para];
          let sentenceChunk = '';
          for (const sentence of sentences) {
            if (sentenceChunk.length + sentence.length > maxChunkSize) {
              if (sentenceChunk) chunks.push(sentenceChunk.trim());
              sentenceChunk = sentence;
            } else {
              sentenceChunk += sentence;
            }
          }
          current = sentenceChunk;
        } else {
          current = para;
        }
      } else {
        current += (current ? '\n\n' : '') + para;
      }
    }
    if (current.trim()) chunks.push(current.trim());

    return chunks;
  }

  // Stubs for removed functions
  async function extractEntities() { throw new Error('API client removed in v2.0'); }
  async function testConnection() { throw new Error('API client removed in v2.0'); }

  return { extractEntities, testConnection, chunkText, parseEntityJSON };
})();