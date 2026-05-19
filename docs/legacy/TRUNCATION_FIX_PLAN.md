# Query Result Truncation Fix - Comprehensive Plan

## Problem Analysis

Based on the user's example, query results show:
1. **Truncated sentences** - Text cut mid-word (e.g., "rcement authority" instead of "enforcement authority")
2. **Incomplete content** - Sentences ending abruptly (e.g., "Residen." instead of complete text)
3. **Poor structure** - Repetitive and poorly formatted output
4. **Missing context** - Important information at chunk boundaries is lost

## Root Causes Identified

### 1. **Document Chunking Issues**
- **Location**: `utils/intelligent_chunking.py`, `utils/page_based_chunking.py`, `utils/semantic_chunking_strategy.py`
- **Problem**: Chunks are being created at arbitrary character boundaries without respecting:
  - Sentence boundaries
  - Word boundaries
  - Paragraph structure
  - Section context

### 2. **Text Cleaning Over-Aggressive**
- **Location**: `utils/text_cleaning.py`
- **Problem**: The `is_noise_text()` function is too aggressive and may be:
  - Removing valid content that starts with lowercase (truncated words)
  - Filtering out legitimate short sentences
  - Not handling page markers properly before chunking

### 3. **Retrieval Result Processing**
- **Location**: `tabs/query_assistant.py` - `_normalize_content_from_result()`
- **Problem**: Content normalization happens AFTER chunking, so truncated chunks are already in the system

### 4. **LLM Context Building**
- **Location**: `utils/enhanced_llm_integration.py` - `_build_comprehensive_context()`
- **Problem**: Context building truncates at arbitrary points (1800 chars) without ensuring complete sentences

## Detailed Fix Plan

### Phase 1: Fix Document Chunking (CRITICAL)

#### File: `utils/intelligent_chunking.py`

**Changes Needed:**
1. **Enhance `_split_into_sentences()` method**:
   - Use proper sentence boundary detection
   - Handle abbreviations (Dr., Mr., etc.)
   - Respect decimal numbers (1.5, 2.3)
   - Handle legal citations (Art. 5, Sec. 2.1)

2. **Fix `_split_large_section()` method**:
   - NEVER split mid-sentence
   - NEVER split mid-word
   - Always end chunks at sentence boundaries
   - Ensure overlap includes complete sentences

3. **Add `_ensure_complete_sentences()` helper**:
   - Verify chunk ends with proper punctuation
   - Extend chunk to next sentence boundary if needed
   - Trim chunk from start if it begins mid-sentence

#### File: `utils/page_based_chunking.py`

**Changes Needed:**
1. **Fix page extraction**:
   - Extract complete pages without truncation
   - Handle page markers properly (--- Page X ---)
   - Preserve content between page markers

2. **Add sentence-aware splitting**:
   - When pages are too large, split at paragraph boundaries
   - If paragraphs are too large, split at sentence boundaries
   - NEVER split mid-sentence

#### File: `utils/semantic_chunking_strategy.py`

**Changes Needed:**
1. **Fix `_optimize_chunk_sizes()` method**:
   - When splitting large chunks, use sentence boundaries
   - Ensure minimum chunk size has complete sentences
   - Add validation to check for truncated content

2. **Add `_validate_chunk_completeness()` method**:
   - Check if chunk starts with lowercase (likely truncated)
   - Check if chunk ends mid-sentence
   - Flag and fix incomplete chunks

### Phase 2: Improve Text Cleaning

#### File: `utils/text_cleaning.py`

**Changes Needed:**
1. **Refine `is_noise_text()` function**:
   - Don't flag text starting with lowercase if it's part of a longer sentence
   - Add context awareness - check surrounding text
   - Be more lenient with technical terms and legal language

2. **Add `detect_truncation()` helper**:
   ```python
   def detect_truncation(text: str) -> bool:
       """Detect if text appears to be truncated"""
       # Check for mid-word truncation
       if text and not text[0].isupper() and text[0].isalpha():
           return True
       # Check for incomplete sentence endings
       if text and text[-1] not in '.!?;:':
           return True
       return False
   ```

3. **Add `repair_truncated_text()` helper**:
   - Attempt to find complete sentence boundaries
   - Remove partial words at start/end
   - Return cleaned, complete sentences only

### Phase 3: Fix Retrieval Processing

#### File: `tabs/query_assistant.py`

**Changes Needed:**
1. **Enhance `_normalize_content_from_result()` function**:
   - Add truncation detection before cleaning
   - Use `QueryResultFormatter.extract_complete_sentences()` 
   - Validate content completeness
   - Log warnings for truncated content

2. **Add pre-processing validation**:
   ```python
   def _validate_and_repair_chunk(chunk: Dict) -> Dict:
       """Validate chunk completeness and repair if possible"""
       content = chunk.get('content', '')
       
       # Detect truncation
       if detect_truncation(content):
           # Try to extract complete sentences
           content = extract_complete_sentences(content)
           chunk['content'] = content
           chunk['metadata']['repaired'] = True
       
       return chunk
   ```

### Phase 4: Enhance LLM Integration

#### File: `utils/enhanced_llm_integration.py`

**Changes Needed:**
1. **Fix `_build_comprehensive_context()` method**:
   - Use `QueryResultFormatter.extract_complete_sentences()` instead of arbitrary truncation
   - Ensure excerpts end at sentence boundaries
   - Increase excerpt length to 2000 chars (from 1800) to allow more complete sentences

2. **Add content validation**:
   ```python
   # Before adding to context
   if is_noise_text(content) or detect_truncation(content):
       logger.warning(f"Skipping truncated/noise content from {source}")
       continue
   ```

### Phase 5: Enhance Result Formatting

#### File: `utils/query_result_formatter.py`

**Changes Needed:**
1. **Enhance `extract_complete_sentences()` method**:
   - Add better sentence boundary detection
   - Handle edge cases (abbreviations, numbers, etc.)
   - Ensure minimum sentence length (avoid fragments)

2. **Add `validate_sentence_completeness()` helper**:
   ```python
   @staticmethod
   def validate_sentence_completeness(text: str) -> Tuple[bool, str]:
       """
       Validate if text contains complete sentences
       Returns: (is_complete, reason)
       """
       if not text:
           return False, "Empty text"
       
       # Check for mid-word start
       if text[0].islower() and text[0].isalpha():
           return False, "Starts mid-word"
       
       # Check for proper ending
       if text[-1] not in '.!?':
           return False, "Incomplete ending"
       
       return True, "Complete"
   ```

## Implementation Priority

### P0 - Critical (Fix Immediately)
1. ✅ Fix `intelligent_chunking.py` - sentence-aware splitting
2. ✅ Fix `text_cleaning.py` - add truncation detection
3. ✅ Fix `query_assistant.py` - validate chunks before display

### P1 - High Priority (Fix Soon)
4. ✅ Fix `enhanced_llm_integration.py` - complete sentence context
5. ✅ Enhance `query_result_formatter.py` - better validation
6. ✅ Fix `page_based_chunking.py` - complete page extraction

### P2 - Medium Priority (Improve Later)
7. ⬜ Add comprehensive logging for truncation detection
8. ⬜ Create validation report for existing indexes
9. ⬜ Add UI indicators for repaired content

## Testing Strategy

### 1. Unit Tests
- Test sentence boundary detection
- Test chunk completeness validation
- Test truncation detection and repair

### 2. Integration Tests
- Test full query flow with known truncated data
- Verify LLM receives complete sentences
- Validate output formatting

### 3. Regression Tests
- Test with user's example query: "What are the requirements of Board Members"
- Verify no truncation in results
- Check for complete sentences in all sections

## Success Criteria

✅ **No truncated words** - All content starts with complete words
✅ **Complete sentences** - All displayed text ends with proper punctuation
✅ **Proper structure** - Clear sections with complete information
✅ **Better context** - Chunks maintain semantic coherence
✅ **User satisfaction** - Query results are professional and complete

## Rollback Plan

If fixes cause issues:
1. Keep original files as `.backup`
2. Implement feature flag for new chunking
3. Allow fallback to original behavior
4. Monitor error rates and user feedback

## Timeline

- **Phase 1**: 2 hours (Critical chunking fixes)
- **Phase 2**: 1 hour (Text cleaning improvements)
- **Phase 3**: 1 hour (Retrieval processing)
- **Phase 4**: 1 hour (LLM integration)
- **Phase 5**: 1 hour (Result formatting)
- **Testing**: 2 hours (Comprehensive testing)

**Total Estimated Time**: 8 hours

## Dependencies

- No new packages required
- Uses existing utilities
- Backward compatible with current indexes
- Can re-index for better results (optional)

## Notes

- The fix addresses both **existing truncated data** (repair on retrieval) and **prevents future truncation** (better chunking)
- Existing indexes will benefit from repair logic
- Re-indexing with new chunking will provide optimal results
- Changes are incremental and can be deployed in phases
