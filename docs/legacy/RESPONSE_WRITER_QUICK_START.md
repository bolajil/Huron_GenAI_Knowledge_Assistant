# 📝 Response Writer - Quick Start
## Add Beautiful Markdown Formatting in 5 Minutes

---

## 🎯 What It Does

Transforms this:
```
The governance framework establishes three core powers: legislative authority, 
executive oversight, and judicial review. Legislative powers include creating 
bylaws and budget approval.
```

Into this:
```markdown
# 🔍 Query Results

> **Your Question:** What are the governance powers?

---

## 📊 Executive Summary

The governance framework establishes **three core powers**: legislative authority, 
executive oversight, and judicial review.

---

## 🔬 Detailed Analysis

### Legislative Powers
- Creating and amending bylaws
- **Budget approval** authority
- Committee establishment rights

### Executive Powers
- Day-to-day operational control
- Resource allocation decisions

### Judicial Powers
- Dispute resolution authority
- Compliance monitoring

---

## 📚 Sources

1. **bylaws.pdf** - Page 15 `(Relevance: 95.00%)`

---

## ℹ️ Query Information

- **Confidence Score:** 92.00%
- **Response Time:** 1250.50ms
- **Generated:** 2025-01-14 10:45:23
```

---

## 🚀 3-Step Integration

### Step 1: Import (1 line)

```python
# Add to top of tabs/query_assistant.py
from utils.response_writer import rewrite_query_response
```

### Step 2: Add Toggle (3 lines)

```python
# Add before search button
use_formatted = st.checkbox("📝 Format response", value=True)
```

### Step 3: Format Response (5 lines)

```python
# Replace: st.markdown(results)
# With:

if use_formatted:
    formatted = rewrite_query_response(results, query)
    st.markdown(formatted)
else:
    st.markdown(results)
```

**Done!** Your responses are now beautifully formatted. ✅

---

## 💡 Complete Example

```python
# tabs/query_assistant.py

import streamlit as st
from utils.response_writer import rewrite_query_response
from utils.unified_document_retrieval import search_documents

def render_query_assistant():
    st.title("🔍 Query Assistant")
    
    # Query input
    query = st.text_area("Enter your question:", height=100)
    
    # Add formatting toggle
    use_formatted = st.checkbox("📝 Format response", value=True)
    
    # Search button
    if st.button("🔍 Search", type="primary"):
        if not query:
            st.warning("Please enter a question")
            return
        
        # Perform search
        with st.spinner("Searching..."):
            results = search_documents(query, "default_faiss")
        
        # Display results
        if use_formatted:
            formatted = rewrite_query_response(results, query)
            st.markdown(formatted)
        else:
            st.markdown(results)
```

---

## ⚡ Advanced Options

### With Sources and Metadata

```python
formatted = rewrite_query_response(
    raw_response=results,
    query=query,
    sources=[
        {
            'document': 'bylaws.pdf',
            'page': 15,
            'relevance': 0.95
        }
    ],
    metadata={
        'confidence': 0.92,
        'response_time': 1250.5,
        'index_used': 'default_faiss'
    }
)
```

### LLM-Enhanced (Better Quality)

```python
formatted = rewrite_query_response(
    raw_response=results,
    query=query,
    use_llm=True  # Uses OpenAI for better formatting
)
```

### With Enhancements (TOC, etc.)

```python
formatted = rewrite_query_response(
    raw_response=results,
    query=query,
    enhance=True  # Adds table of contents, syntax highlighting
)
```

---

## 🎨 Side-by-Side Comparison

```python
# Show both formats
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Original")
    st.markdown(results)

with col2:
    st.subheader("📝 Formatted")
    formatted = rewrite_query_response(results, query)
    st.markdown(formatted)
```

---

## 🧪 Test It

```python
# test_response_writer.py

from utils.response_writer import rewrite_query_response

raw = "The board has three main powers: legislative, executive, and judicial."

formatted = rewrite_query_response(
    raw_response=raw,
    query="What powers does the board have?"
)

print(formatted)
```

Run:
```bash
python test_response_writer.py
```

---

## ✨ Features

### Automatic Formatting
- ✅ **Headings** with emojis
- ✅ **Bold** for important terms
- ✅ **Lists** for enumerated items
- ✅ **Blockquotes** for important notes
- ✅ **Tables** with proper alignment
- ✅ **Code blocks** with syntax highlighting

### Smart Sections
- ✅ Executive Summary
- ✅ Detailed Analysis
- ✅ Key Takeaways
- ✅ Source Citations
- ✅ Metadata Footer

### Visual Hierarchy
- ✅ Clear structure
- ✅ Proper spacing
- ✅ Visual separators
- ✅ Easy to scan

---

## 📊 Performance

| Mode | Speed | Quality | Cost |
|------|-------|---------|------|
| **Rule-based** | ~50ms | Good | Free |
| **LLM-enhanced** | ~2-5s | Excellent | $0.002 |

---

## 🔧 Customization

### Custom Emojis

```python
from utils.response_writer import ResponseWriter

writer = ResponseWriter()

# Your custom emoji mappings
custom_emojis = {
    'summary': '🎯',
    'analysis': '🔬',
    'findings': '💡'
}
```

### Custom Keywords

```python
# Highlight your important terms
important_keywords = [
    'critical', 'essential', 'must', 'required'
]
```

---

## 🐛 Troubleshooting

### Not Formatting?

```python
# Check if imported correctly
from utils.response_writer import rewrite_query_response
print("✅ Response writer imported")

# Verify it's being called
formatted = rewrite_query_response("test", "test query")
print(f"Length: {len(formatted)}")
```

### LLM Not Working?

```python
# Check LLM configuration
from utils.llm_config import get_llm_client

try:
    llm = get_llm_client('openai')
    print("✅ LLM available")
except Exception as e:
    print(f"❌ LLM error: {e}")
```

---

## 📚 Files Created

1. **utils/response_writer.py** - Core implementation
2. **RESPONSE_WRITER_GUIDE.md** - Complete documentation
3. **utils/query_assistant_integration_example.py** - Integration examples
4. **RESPONSE_WRITER_QUICK_START.md** - This file

---

## ✅ Checklist

- [ ] `response_writer.py` exists
- [ ] Imported in Query Assistant
- [ ] Toggle button added
- [ ] Tested with sample query
- [ ] Formatted response displays correctly
- [ ] Sources showing (if available)
- [ ] Metadata showing (if available)

---

## 🎉 You're Done!

Your query responses are now beautifully formatted with:
- ✅ Clear structure
- ✅ Visual hierarchy
- ✅ Proper emphasis
- ✅ Source citations
- ✅ Metadata footer

**Next:** See RESPONSE_WRITER_GUIDE.md for advanced features!

