# Hybrid Query System Setup Guide

## Overview

The Hybrid Query System intelligently routes queries between:
- **Fast Retrieval** (< 5s) for simple queries
- **LangGraph Agent** (< 30s) for complex multi-step reasoning

## Prerequisites

### 1. Install Dependencies

```bash
pip install langgraph langchain-openai langchain-core langchain-community
```

### 2. Set OpenAI API Key

Add to `.env` or `.env.local`:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

Or set as environment variable:
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-your-key-here"

# Windows (CMD)
set OPENAI_API_KEY=sk-your-key-here

# Linux/Mac
export OPENAI_API_KEY="sk-your-key-here"
```

### 3. Verify FAISS Indexes

Ensure you have FAISS indexes in `data/faiss_index/`:
```
data/faiss_index/
├── AWS_index/
├── Bylaws2025_index/
├── Bylaws2027_index/
└── Lanre_index/
```

## Testing

### Run Test Suite

```bash
python test_hybrid_system.py
```

Expected output:
```
TEST 1: Query Complexity Analyzer - [PASS]
TEST 2: Configuration Validation - [PASS]
TEST 3: Hybrid System Initialization - [PASS]
TEST 4: Query Routing - [PASS]
TEST 5: Performance Comparison - [PASS]
TEST 6: Statistics Tracking - [PASS]

Success Rate: 100%
```

### Test Individual Components

```python
# Test complexity analyzer
from utils.query_complexity_analyzer import analyze_query_complexity

result = analyze_query_complexity("Compare AWS Bylaws vs ByLaw2000")
print(f"Complexity: {result.complexity.value}")
print(f"Approach: {result.recommended_approach}")
```

## Usage

### Option 1: Use Streamlit UI

1. Add the hybrid tab to your dashboard:

```python
# In genai_dashboard_modular.py
from tabs.agent_assistant_hybrid import render_agent_assistant_hybrid

tabs = {
    "Agent Assistant (Hybrid)": render_agent_assistant_hybrid,
    # ... other tabs
}
```

2. Run the dashboard:
```bash
streamlit run genai_dashboard_modular.py
```

3. Navigate to "Agent Assistant (Hybrid)" tab
4. Click "Initialize Hybrid System"
5. Start querying!

### Option 2: Use Programmatically

```python
from utils.hybrid_agent_integration import (
    initialize_hybrid_system,
    query_hybrid_system,
    get_hybrid_statistics
)

# Initialize
success = initialize_hybrid_system(
    index_names=["AWS_index", "Bylaws2025_index"],
    complexity_threshold=50.0,
    use_langgraph_for_moderate=False
)

# Query
result = query_hybrid_system(
    query="Compare governance frameworks",
    index_name="AWS_index"
)

print(f"Approach: {result['approach']}")
print(f"Response: {result['response']}")
print(f"Time: {result['execution_time']:.2f}s")

# Get statistics
stats = get_hybrid_statistics()
print(f"Total queries: {stats['total_queries']}")
print(f"Fast: {stats['fast_queries']}, LangGraph: {stats['langgraph_queries']}")
```

## Configuration

### Complexity Threshold

Adjust routing sensitivity (0-100):
```python
# Lower threshold = more queries use LangGraph
initialize_hybrid_system(complexity_threshold=40.0)  # Aggressive

# Higher threshold = more queries use fast retrieval
initialize_hybrid_system(complexity_threshold=70.0)  # Conservative
```

### Moderate Query Handling

```python
# Route moderate complexity queries to LangGraph
initialize_hybrid_system(use_langgraph_for_moderate=True)

# Keep moderate queries on fast path (default)
initialize_hybrid_system(use_langgraph_for_moderate=False)
```

### Timeouts

```python
from utils.hybrid_query_orchestrator import HybridQueryOrchestrator

orchestrator = HybridQueryOrchestrator(
    fast_retrieval_func=my_retrieval_func,
    langgraph_agent=my_agent,
    max_fast_time=5.0,      # Max 5s for fast retrieval
    max_langgraph_time=30.0  # Max 30s for LangGraph
)
```

## Query Examples

### Simple Queries (Fast Retrieval)
- "What is the board structure?"
- "Define quorum"
- "List all board members"
- "Who is the chairman?"

### Complex Queries (LangGraph)
- "Compare AWS Bylaws vs ByLaw2000 governance models"
- "Analyze board powers and recommend improvements"
- "What are the implications of the new bylaws on decision-making?"
- "Synthesize all information about voting procedures"

## Monitoring

### View Statistics

```python
from utils.hybrid_agent_integration import get_hybrid_statistics

stats = get_hybrid_statistics()
print(f"Total: {stats['total_queries']}")
print(f"Fast: {stats['fast_queries']} ({stats['fast_percentage']:.1f}%)")
print(f"LangGraph: {stats['langgraph_queries']} ({stats['langgraph_percentage']:.1f}%)")
print(f"Fallbacks: {stats['fallback_count']}")
print(f"Success Rate: {stats['success_rate']:.1f}%")
print(f"Avg Fast Time: {stats['avg_fast_time']:.2f}s")
print(f"Avg LangGraph Time: {stats['avg_langgraph_time']:.2f}s")
```

### Export Metrics

```python
from utils.hybrid_agent_integration import export_hybrid_metrics

export_hybrid_metrics("metrics_2025-10-31.json")
```

### Reset Metrics

```python
from utils.hybrid_agent_integration import reset_hybrid_metrics

reset_hybrid_metrics()
```

## Troubleshooting

### Issue: "System not ready"

**Check:**
1. OpenAI API key set: `echo $OPENAI_API_KEY`
2. LangGraph installed: `pip show langgraph`
3. Indexes exist: `ls data/faiss_index/`

### Issue: "Agent initialization failed"

**Solutions:**
- Verify OpenAI API key is valid
- Check internet connection
- Ensure sufficient API credits
- Check logs for detailed error

### Issue: "Index not found"

**Solutions:**
- Verify index exists in `data/faiss_index/`
- Check index name spelling
- Use `get_available_indexes()` to list valid indexes

### Issue: Slow performance

**Optimizations:**
- Increase complexity threshold to use fast path more
- Reduce `max_iterations` in LangGraph agent
- Use fewer indexes
- Enable caching (if available)

## Performance Expectations

| Query Type | Approach | Expected Time | Accuracy |
|------------|----------|---------------|----------|
| Simple lookup | Fast | 0.5-2s | High |
| Moderate | Fast/LangGraph | 2-5s | Medium-High |
| Complex analysis | LangGraph | 10-25s | Very High |
| Multi-document synthesis | LangGraph | 15-30s | Very High |

## Architecture

```
User Query
    ↓
Query Complexity Analyzer
    ↓
Routing Decision
    ↓
┌─────────────┬─────────────┐
│ Fast Path   │ LangGraph   │
│ (Simple)    │ (Complex)   │
└─────────────┴─────────────┘
    ↓              ↓
Unified Document   Multi-Tool
Retrieval          Agent
    ↓              ↓
    └──────┬───────┘
           ↓
    Response + Metrics
```

## Files Created

- `utils/query_complexity_analyzer.py` - Analyzes query complexity
- `app/utils/langgraph_agent.py` - Enhanced LangGraph agent
- `utils/hybrid_query_orchestrator.py` - Routing orchestrator
- `utils/hybrid_agent_integration.py` - Integration helpers
- `tabs/agent_assistant_hybrid.py` - Streamlit UI
- `test_hybrid_system.py` - Test suite

## Next Steps

1. ✅ Install dependencies
2. ✅ Set OpenAI API key
3. ✅ Run test suite
4. ✅ Integrate into dashboard
5. 📊 Monitor performance
6. 🔧 Tune complexity threshold
7. 🚀 Deploy to production

## Support

For issues or questions:
1. Check logs in console
2. Review `hybrid_test_results.json`
3. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
4. Check OpenAI API status
5. Verify all dependencies installed

## Cost Considerations

**Fast Retrieval:**
- Cost: Free (local FAISS)
- Speed: Very fast (< 5s)

**LangGraph:**
- Cost: OpenAI API calls (~$0.002 per query for GPT-3.5-turbo)
- Speed: Slower (10-30s)
- Value: Much better for complex reasoning

**Recommendation:** Use hybrid approach to balance cost and quality.
