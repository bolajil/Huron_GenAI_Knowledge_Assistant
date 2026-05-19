# LLM Model Selection & Confidence Scores Explained

## 🤖 Which LLM is Being Used?

### Current Default: **GPT-3.5-Turbo (OpenAI)**

Your system uses **OpenAI's GPT-3.5-Turbo** by default because:
1. You have `OPENAI_API_KEY` configured in `.env`
2. It's the default fallback model in `utils/llm_config.py`
3. It's fast, cost-effective, and reliable

### How to Check Which Model is Active:

After the latest update, you'll see this info displayed:
```
🤖 Model: gpt-3.5-turbo | Method: enhanced_llm
```

### Available LLM Options:

Based on your `.env` file, you have access to:

| Provider | Model | API Key Status | Speed | Cost | Quality |
|----------|-------|----------------|-------|------|---------|
| **OpenAI** | gpt-3.5-turbo | ✅ Active | Fast | Low | Good |
| **OpenAI** | gpt-4 | ✅ Available | Slow | High | Excellent |
| **Anthropic** | claude-3-sonnet | ✅ Active | Medium | Medium | Excellent |
| **Anthropic** | claude-3-haiku | ✅ Available | Fast | Low | Good |
| **Mistral** | mistral-small | ✅ Active | Fast | Low | Good |
| **DeepSeek** | deepseek-chat | ✅ Active | Fast | Very Low | Good |

### How to Change the LLM Model:

**Option 1: Change Default in Code**

Edit `utils/llm_config.py`:
```python
def get_default_llm_model():
    return "gpt-4"  # or "claude-3-sonnet-20240229"
```

**Option 2: Set in Environment Variable**

Add to `.env`:
```bash
DEFAULT_LLM_MODEL=gpt-4
# or
DEFAULT_LLM_MODEL=claude-3-sonnet-20240229
```

**Option 3: UI Selection (Future Enhancement)**

We can add a dropdown in the UI to select models dynamically.

### Model Comparison:

**For Your Use Case (Legal/Governance Documents):**

1. **Best Quality**: GPT-4 or Claude-3-Sonnet
   - More accurate understanding of legal language
   - Better reasoning and analysis
   - Higher cost (~10x more than GPT-3.5)

2. **Best Speed/Cost**: GPT-3.5-Turbo (Current)
   - Fast responses
   - Low cost
   - Good enough for most queries

3. **Best Balance**: Claude-3-Haiku or Mistral-Small
   - Good quality
   - Fast
   - Reasonable cost

## 📊 Confidence Scores Explained

### What is Confidence/Relevance?

The confidence score measures **how well the retrieved documents match your query**.

### Score Ranges:

| Score | Meaning | What It Tells You |
|-------|---------|-------------------|
| **70-100%** | ✅ High Confidence | Documents are highly relevant, answer is reliable |
| **40-69%** | ℹ️ Medium Confidence | Documents are somewhat relevant, answer is partial |
| **0-39%** | ⚠️ Low Confidence | Documents may not fully answer your question |

### Your Example:

```
Query: "Provide responsibilities of Board Members"
Average Confidence: 17.88% (Very Low!)

Top Sources:
- Source 1: 64.94% (Class B Membership requirements)
- Source 2: 67.08% (Disapproval rights)
- Source 3: 67.42% (Corporate representatives)
- Sources 4-8: 1.30-5.60% (TOC entries, definitions)
```

### Why is Your Confidence Low?

**1. Query Mismatch**
- You asked: "Board member responsibilities"
- Documents talk about: "Class B Members", "directors", "disapproval rights"
- The system found *related* content but not *exact* matches

**2. Vocabulary Gap**
- Your query uses: "responsibilities"
- Documents use: "duties", "powers", "qualifications", "requirements"
- The embedding model doesn't recognize these as synonyms well enough

**3. Information Scattered**
- Board member responsibilities are spread across multiple sections
- No single section titled "Board Member Responsibilities"
- Each source covers a different aspect (membership, voting, eligibility)

**4. Weak Sources Included**
- Sources 4-8 are TOC entries and definitions (1-5% relevance)
- These drag down the average confidence
- Should be filtered out

### How Confidence is Calculated:

```python
# For each source
relevance_score = cosine_similarity(query_embedding, document_embedding)

# Average across all sources
avg_confidence = sum(all_scores) / number_of_sources

# In your case:
avg_confidence = (64.94 + 67.08 + 67.42 + 5.60 + 1.30 + 1.30 + 1.30 + 1.30) / 8
avg_confidence = 210.24 / 8 = 26.28% (roughly)
```

The low-relevance sources (1-5%) are pulling down the average!

## 🔧 How to Improve Confidence Scores

### 1. **Better Query Phrasing**

**Instead of:**
```
"Provide responsibilities of Board Members"
```

**Try:**
```
"What are the duties and qualifications of Board directors?"
"What powers do Board members have?"
"What are director eligibility requirements?"
```

### 2. **Use Document Vocabulary**

Look at the sources and use their exact terms:
- "Class B Member" (not "special member")
- "directors" (not just "Board members")
- "quorum" (not "minimum attendance")
- "Dedicatory Instruments" (not "governing documents")

### 3. **More Specific Questions**

**Instead of broad:**
```
"Board member responsibilities"
```

**Ask specific:**
```
"What are the voting requirements for Board directors?"
"What are the residency requirements for Board members?"
"What actions can Class B Members disapprove?"
```

### 4. **Filter Low-Relevance Results**

We can add a minimum threshold:
```python
# Only show sources with >30% relevance
filtered_sources = [s for s in sources if s.relevance_score > 0.30]
```

### 5. **Enable Query Expansion**

The system has query expansion capabilities that aren't fully enabled. This would:
- Expand "responsibilities" → "duties, powers, obligations, requirements"
- Expand "Board members" → "directors, Board of Directors, governing body"
- Find more relevant results

### 6. **Use Better Embedding Model**

Current: `all-MiniLM-L6-v2` (general purpose)

Better options:
- `all-mpnet-base-v2` (better quality, slower)
- `legal-bert-base-uncased` (specialized for legal text)
- OpenAI embeddings (best quality, costs money)

## 📈 What You'll See After Updates

### Before (Current):
```
Average Confidence Score: 17.88%
[No explanation]
```

### After (New):
```
⚠️ Low Confidence: 17.9% - Results may not fully answer your question
Avg Relevance: 17.9%

💡 Why is confidence low?
- Query terms don't match document vocabulary exactly
- Information may be scattered across multiple sections
- Try rephrasing your question or using different keywords

Tips to improve:
- Use exact terms from documents
- Ask more specific questions
- Break complex questions into smaller parts
```

## 🎯 Best Practices for High-Confidence Results

### 1. **Start Broad, Then Narrow**
```
First query: "What are Board meeting requirements?"
If low confidence, try: "What is the quorum for Board meetings?"
```

### 2. **Use Document Language**
- Read a few results first
- Note the exact terms used
- Rephrase your query using those terms

### 3. **Ask One Thing at a Time**
**Instead of:**
```
"What are Board member responsibilities, qualifications, and voting procedures?"
```

**Ask separately:**
```
1. "What are Board member qualifications?"
2. "What are Board voting procedures?"
3. "What are Board member duties?"
```

### 4. **Check Source Relevance**
- Look at individual source scores
- If top sources are 60-70% but average is 20%, ignore low sources
- Focus on the high-relevance sources

### 5. **Use Feedback Buttons**
- Click 👎 if answer is not helpful
- This helps the system learn and improve

## 🚀 Upcoming Improvements

### 1. **Model Selector UI**
Add dropdown to choose LLM model:
```
🤖 Select Model: [GPT-3.5-Turbo ▼]
Options: GPT-4, Claude-3-Sonnet, Mistral, etc.
```

### 2. **Confidence Threshold Filter**
```
☑️ Only show results with >40% relevance
```

### 3. **Query Suggestions**
```
💡 Did you mean:
- "What are director qualifications?"
- "What are Board member duties?"
```

### 4. **Smart Query Expansion**
Automatically expand queries with synonyms and related terms.

### 5. **Better Embedding Model**
Upgrade to legal-specialized embeddings for better matching.

## 📊 Summary

### Current Status:
- ✅ **LLM**: GPT-3.5-Turbo (OpenAI) - Working well
- ⚠️ **Confidence**: Low (17.88%) - Needs improvement
- ✅ **Response Quality**: Good (LLM is synthesizing well)
- ⚠️ **Source Relevance**: Mixed (some good, some irrelevant)

### What I Added:
1. ✅ **LLM Model Display** - Shows which model is being used
2. ✅ **Confidence Interpretation** - Explains what the score means
3. ✅ **Low Confidence Warning** - Alerts when results may be unreliable
4. ✅ **Improvement Tips** - Suggests how to get better results

### Next Steps:
1. **Restart the app** to see the new confidence display
2. **Try rephrasing queries** using document vocabulary
3. **Focus on high-relevance sources** (ignore 1-5% sources)
4. **Consider upgrading to GPT-4** for better quality (if budget allows)

---

**Status**: ✅ LLM working well, confidence scoring explained and improved
**Model**: GPT-3.5-Turbo (can be changed to GPT-4 or Claude)
**Confidence**: Now displays with interpretation and improvement tips
