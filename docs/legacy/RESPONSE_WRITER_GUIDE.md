# 📝 Response Writer Guide
## Beautiful Markdown Formatting for Query Responses

---

## 🎯 Overview

The Response Writer automatically rewrites query responses in beautiful, readable markdown format with:

- ✅ **Clear structure** with headings and sections
- ✅ **Visual hierarchy** with proper formatting
- ✅ **Emphasis** on important points
- ✅ **Source citations** with relevance scores
- ✅ **Metadata** footer with query info
- ✅ **Table of contents** for long responses
- ✅ **Collapsible sections** for better navigation

---

## 🚀 Quick Start

### Basic Usage

```python
from utils.response_writer import rewrite_query_response

# Simple rewrite
formatted_response = rewrite_query_response(
    raw_response="Your raw response text here...",
    query="What are the governance powers?"
)

# Display in Streamlit
st.markdown(formatted_response)
```

### With Sources and Metadata

```python
from utils.response_writer import rewrite_query_response

formatted_response = rewrite_query_response(
    raw_response=raw_text,
    query=user_query,
    sources=[
        {
            'document': 'bylaws.pdf',
            'page': 15,
            'section': 'Article 2',
            'relevance': 0.95
        }
    ],
    metadata={
        'confidence': 0.92,
        'response_time': 1250.5,
        'sources_count': 3,
        'index_used': 'default_faiss'
    }
)

st.markdown(formatted_response)
```

---

## 📊 Output Example

### Before (Raw Response):
```
The governance framework establishes three core powers: legislative authority, 
executive oversight, and judicial review. Legislative powers include creating 
bylaws and budget approval. Executive powers cover operational control. 
Judicial powers handle disputes.
```

### After (Formatted Response):
```markdown
# 🔍 Query Results

> **Your Question:** What are the governance powers?

---

## 📊 Executive Summary

The governance framework establishes **three core powers**: legislative authority, 
executive oversight, and judicial review, creating a balanced system of checks 
and balances.

---

## 🔬 Detailed Analysis

### Legislative Powers
- Creating and amending bylaws
- **Budget approval** authority
- Committee establishment rights

### Executive Powers
- Day-to-day operational control
- Resource allocation decisions
- Policy implementation oversight

### Judicial Powers
- Dispute resolution authority
- Compliance monitoring
- Enforcement mechanisms

---

## 🔑 Key Takeaways

- **Three-branch power structure ensures checks and balances**
- **Each power domain has specific scope and limitations**
- **Cross-functional oversight prevents power concentration**

---

## 📚 Sources

1. **bylaws.pdf** - Page 15 - Article 2 `(Relevance: 95.00%)`
2. **governance_guide.pdf** - Page 8 - Section 3 `(Relevance: 88.00%)`

---

## ℹ️ Query Information

- **Confidence Score:** 92.00%
- **Response Time:** 1250.50ms
- **Sources Consulted:** 3
- **Index:** default_faiss
- **Generated:** 2025-01-14 10:45:23
```

---

## 🔧 Integration with Query Assistant

### Option 1: Add Toggle Button

```python
# In tabs/query_assistant.py

import streamlit as st
from utils.response_writer import rewrite_query_response

# Add toggle in sidebar or settings
use_formatted_response = st.checkbox(
    "📝 Use formatted response",
    value=True,
    help="Rewrite response in beautiful markdown format"
)

# After getting search results
if use_formatted_response:
    formatted_response = rewrite_query_response(
        raw_response=results,
        query=query,
        sources=sources,
        metadata={
            'confidence': confidence_score,
            'response_time': response_time_ms,
            'sources_count': len(sources),
            'index_used': selected_index
        }
    )
    st.markdown(formatted_response)
else:
    st.markdown(results)  # Original format
```

### Option 2: Always Use Formatted Response

```python
# In tabs/query_assistant.py

from utils.response_writer import rewrite_query_response

def handle_query(query, index):
    # Get search results
    results = search_documents(query, index)
    
    # Extract sources (if available)
    sources = extract_sources(results)
    
    # Rewrite response
    formatted_response = rewrite_query_response(
        raw_response=results,
        query=query,
        sources=sources,
        metadata={
            'index_used': index,
            'sources_count': len(sources)
        }
    )
    
    return formatted_response
```

### Option 3: Side-by-Side Comparison

```python
# Show both formats
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Original Response")
    st.markdown(raw_response)

with col2:
    st.subheader("📝 Formatted Response")
    formatted = rewrite_query_response(raw_response, query)
    st.markdown(formatted)
```

---

## 🎨 Formatting Options

### Rule-Based Formatting (Default)

Fast, no LLM required:

```python
formatted = rewrite_query_response(
    raw_response=text,
    query=query,
    use_llm=False  # Default
)
```

### LLM-Enhanced Formatting

Better quality, uses LLM:

```python
formatted = rewrite_query_response(
    raw_response=text,
    query=query,
    use_llm=True  # Uses OpenAI GPT-3.5
)
```

### With Enhancements

Add table of contents, collapsible sections:

```python
formatted = rewrite_query_response(
    raw_response=text,
    query=query,
    enhance=True  # Adds TOC, syntax highlighting, etc.
)
```

---

## 📋 Complete Integration Example

```python
# tabs/query_assistant_with_writer.py

import streamlit as st
from utils.unified_document_retrieval import search_documents
from utils.response_writer import rewrite_query_response
import time

def render_query_assistant():
    st.title("🔍 Query Assistant")
    
    # Query input
    query = st.text_area("Enter your question:", height=100)
    
    # Settings
    with st.expander("⚙️ Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            index = st.selectbox(
                "Select Index",
                ["default_faiss", "AWS_index", "ByLaw_index"]
            )
            
            use_formatted = st.checkbox(
                "📝 Format response",
                value=True,
                help="Rewrite in beautiful markdown"
            )
        
        with col2:
            use_llm_rewrite = st.checkbox(
                "🤖 Use LLM rewriting",
                value=False,
                help="Better quality, slower"
            )
            
            add_enhancements = st.checkbox(
                "✨ Add enhancements",
                value=True,
                help="TOC, collapsible sections"
            )
    
    # Search button
    if st.button("🔍 Search", type="primary"):
        if not query:
            st.warning("Please enter a question")
            return
        
        # Show progress
        with st.spinner("Searching documents..."):
            start_time = time.time()
            
            # Perform search
            results = search_documents(query, index)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Extract sources (implement based on your system)
            sources = [
                {
                    'document': 'example.pdf',
                    'page': 15,
                    'section': 'Article 2',
                    'relevance': 0.95
                }
            ]
        
        # Display results
        st.markdown("---")
        
        if use_formatted:
            # Rewrite response
            formatted_response = rewrite_query_response(
                raw_response=results,
                query=query,
                sources=sources,
                metadata={
                    'confidence': 0.92,
                    'response_time': response_time,
                    'sources_count': len(sources),
                    'index_used': index
                },
                use_llm=use_llm_rewrite,
                enhance=add_enhancements
            )
            
            st.markdown(formatted_response)
        else:
            # Show original
            st.markdown(results)
        
        # Add feedback buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("👍 Helpful"):
                st.success("Thanks for your feedback!")
        with col2:
            if st.button("👎 Not helpful"):
                st.info("We'll work on improving this!")
```

---

## 🎯 Features

### Automatic Section Detection

The writer automatically detects and formats:

- Executive summaries
- Detailed analysis
- Key points
- Findings and results
- Recommendations
- Conclusions

### Smart Formatting

- **Bold** for important terms and numbers
- *Italic* for emphasis
- `Code blocks` for technical terms
- > Blockquotes for important notes
- Lists for enumerated items
- Tables with proper alignment

### Visual Hierarchy

```markdown
# Main Title (H1)
## Section (H2)
### Subsection (H3)

- Bullet points
- Organized lists

1. Numbered items
2. Sequential information
```

### Source Attribution

```markdown
## 📚 Sources

1. **document.pdf** - Page 15 - Section 2 `(Relevance: 95.00%)`
2. **guide.pdf** - Page 8 `(Relevance: 88.00%)`
```

### Metadata Footer

```markdown
## ℹ️ Query Information

- **Confidence Score:** 92.00%
- **Response Time:** 1250.50ms
- **Sources Consulted:** 3
- **Index:** default_faiss
- **Generated:** 2025-01-14 10:45:23
```

---

## 🔧 Customization

### Custom Section Emojis

```python
from utils.response_writer import ResponseWriter

writer = ResponseWriter()

# Customize emoji map
writer._format_heading.emoji_map = {
    'summary': '🎯',
    'analysis': '🔬',
    'findings': '💡',
    # Add your custom mappings
}
```

### Custom Emphasis Keywords

```python
# Add your own important keywords
writer._add_emphasis.important_keywords = [
    'critical', 'essential', 'must', 'required',
    'your', 'custom', 'keywords'
]
```

### Custom Source Formatting

```python
def custom_format_sources(sources):
    formatted = ["## 📚 References\n"]
    for i, source in enumerate(sources, 1):
        formatted.append(f"[{i}] {source['document']} (p. {source['page']})")
    return '\n'.join(formatted)

# Use custom formatter
writer._format_sources = custom_format_sources
```

---

## 📊 Performance

### Rule-Based Formatting
- **Speed:** ~50ms for typical response
- **Quality:** Good
- **LLM Required:** No
- **Cost:** Free

### LLM-Enhanced Formatting
- **Speed:** ~2-5 seconds
- **Quality:** Excellent
- **LLM Required:** Yes (OpenAI GPT-3.5)
- **Cost:** ~$0.002 per response

---

## 🎨 Styling Tips

### For Streamlit

```python
# Add custom CSS for better markdown rendering
st.markdown("""
<style>
    .markdown-text-container {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .markdown-text-container h2 {
        color: #1f77b4;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 0.3em;
    }
    .markdown-text-container blockquote {
        border-left: 4px solid #1f77b4;
        padding-left: 1em;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Display formatted response
st.markdown(formatted_response, unsafe_allow_html=True)
```

---

## 🐛 Troubleshooting

### Response Not Formatting Properly

**Problem:** Response looks the same as before

**Solution:**
```python
# Check if response_writer is imported
from utils.response_writer import rewrite_query_response

# Verify it's being called
formatted = rewrite_query_response(raw_response, query)
print(f"Formatted length: {len(formatted)}")
print(f"Original length: {len(raw_response)}")
```

### LLM Rewriting Fails

**Problem:** LLM enhancement not working

**Solution:**
```python
# Check LLM configuration
from utils.llm_config import get_llm_client

try:
    llm = get_llm_client('openai')
    print("✅ LLM available")
except Exception as e:
    print(f"❌ LLM error: {e}")
    # Falls back to rule-based formatting
```

### Sources Not Showing

**Problem:** Source section is empty

**Solution:**
```python
# Ensure sources are in correct format
sources = [
    {
        'document': 'filename.pdf',  # Required
        'page': 15,                   # Optional
        'section': 'Article 2',       # Optional
        'relevance': 0.95             # Optional
    }
]

formatted = rewrite_query_response(
    raw_response=text,
    query=query,
    sources=sources  # Pass sources
)
```

---

## 📚 Examples

### Example 1: Simple Query

```python
raw = "The board has three main powers: legislative, executive, and judicial."

formatted = rewrite_query_response(
    raw_response=raw,
    query="What powers does the board have?"
)

# Output:
# # 🔍 Query Results
# > **Your Question:** What powers does the board have?
# ---
# ## 📄 Main Content
# The board has **three main powers**: legislative, executive, and judicial.
```

### Example 2: Complex Analysis

```python
raw = """
Executive Summary: The governance framework establishes comprehensive oversight.

Detailed Analysis: 
1. Legislative powers include policy creation
2. Executive powers cover implementation
3. Judicial powers handle compliance

Key Points:
- Balanced power distribution
- Clear accountability
- Regular audits required
"""

formatted = rewrite_query_response(
    raw_response=raw,
    query="Explain the governance framework",
    use_llm=True,
    enhance=True
)

# Output includes:
# - Table of contents
# - Formatted sections
# - Key takeaways
# - Metadata footer
```

### Example 3: With Sources

```python
formatted = rewrite_query_response(
    raw_response="The policy requires annual reviews.",
    query="What are the review requirements?",
    sources=[
        {
            'document': 'policy_manual.pdf',
            'page': 42,
            'section': 'Section 5.2',
            'relevance': 0.98
        },
        {
            'document': 'procedures.pdf',
            'page': 15,
            'relevance': 0.85
        }
    ],
    metadata={
        'confidence': 0.95,
        'response_time': 850.5,
        'sources_count': 2,
        'index_used': 'policy_index'
    }
)

# Output includes full source citations and metadata
```

---

## 🚀 Next Steps

1. **Test the writer:**
   ```bash
   python -c "from utils.response_writer import rewrite_query_response; print('✅ Writer ready!')"
   ```

2. **Integrate into Query Assistant:**
   - Add toggle for formatted responses
   - Pass sources and metadata
   - Test with real queries

3. **Customize formatting:**
   - Adjust emoji mappings
   - Add custom keywords
   - Style with CSS

4. **Enable LLM enhancement:**
   - Configure OpenAI API key
   - Test LLM rewriting
   - Compare quality

---

## ✅ Checklist

- [ ] `response_writer.py` created
- [ ] Imported in Query Assistant
- [ ] Toggle button added
- [ ] Sources extracted and passed
- [ ] Metadata collected
- [ ] Tested with sample queries
- [ ] LLM enhancement configured (optional)
- [ ] Custom styling applied (optional)
- [ ] User feedback collected

---

**Your query responses are now beautiful and readable!** 🎉

