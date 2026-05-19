# Enhanced Research Performance Optimization

## Performance Issues Identified

1. **Inefficient Caching Implementation**
   - Current caching uses a basic key system that doesn't handle complex inputs well
   - Cache management lacks proper size limits and expiration policies
   - No memory optimization for large result sets

2. **Sequential Processing of Knowledge Sources**
   - Sources are processed one at a time instead of in parallel
   - No timeout mechanism for slow-responding sources
   - No fallback when a source fails to respond

3. **UI Responsiveness**
   - Large result sets can cause UI slowdowns
   - Inefficient session state management with full report copies
   - Lack of virtualization for history items

4. **Memory Optimization**
   - Excessive cloning of data in session state
   - Large history items stored without compression
   - No cleanup of old cache items

## Recommended Optimizations

### 1. Implement Improved Caching System

```python
# Enhanced caching with TTL and size limits
import hashlib
from functools import lru_cache
import time

# Constants
CACHE_EXPIRY_SECONDS = 3600  # 1 hour
MAX_CACHE_SIZE = 50

# In-memory cache
research_cache = {}

def get_cache_key(task, operation, sources):
    """Generate a consistent hash-based cache key"""
    # Sort sources to ensure consistent key regardless of order
    sources_str = ",".join(sorted(sources))
    key_str = f"{task}|{operation}|{sources_str}"
    return hashlib.md5(key_str.encode()).hexdigest()

def clean_cache():
    """Remove expired and excess cache items"""
    current_time = time.time()
    # Remove expired items
    expired_keys = [k for k, v in research_cache.items() 
                   if current_time - v["timestamp"] > CACHE_EXPIRY_SECONDS]
    for key in expired_keys:
        research_cache.pop(key, None)
    
    # If still too large, remove oldest items
    if len(research_cache) > MAX_CACHE_SIZE:
        sorted_items = sorted(research_cache.items(), 
                             key=lambda x: x[1]["timestamp"])
        for key, _ in sorted_items[:len(sorted_items) - MAX_CACHE_SIZE]:
            research_cache.pop(key, None)
```

### 2. Parallel Processing of Knowledge Sources

```python
import concurrent.futures

def search_knowledge_sources(task, sources, max_results=3):
    """Search multiple knowledge sources in parallel"""
    
    def search_single_source(source):
        """Search a single knowledge source"""
        try:
            from utils.simple_search import perform_multi_source_search
            return perform_multi_source_search(task, [source], max_results)
        except Exception as e:
            logger.error(f"Error searching {source}: {str(e)}")
            return []
    
    # Use ThreadPoolExecutor for parallel execution
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(sources), 5)) as executor:
        # Submit all search tasks
        future_to_source = {executor.submit(search_single_source, source): source 
                           for source in sources}
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_source):
            source = future_to_source[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error processing {source}: {str(e)}")
    
    return all_results
```

### 3. UI Performance Improvements

```python
# Optimize large result display with lazy loading
def display_research_results(research_result):
    """Display research results with optimized rendering"""
    
    # Use st.container for better performance with large content
    with st.container():
        # Display the headers first for immediate feedback
        st.markdown("""
        <div class="result-container research-report-container">
            <h3>Research Report</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Split content into sections for more efficient rendering
        sections = research_result.split("###")
        
        # Always show the first section (executive summary)
        st.markdown(sections[0])
        
        # Show other sections in tabs or expanders
        if len(sections) > 1:
            tabs = st.tabs([s.split("\n")[0].strip() for s in sections[1:]])
            for i, tab in enumerate(tabs):
                with tab:
                    st.markdown(f"### {sections[i+1]}")
```

### 4. Memory Optimization for History

```python
def optimize_history_item(item):
    """Optimize a history item to reduce memory usage"""
    # Create a lightweight version for storage
    return {
        "task": item["task"],
        "operation": item["operation"],
        "sources": item["sources"],
        "timestamp": item["timestamp"],
        # Store only first 1000 chars of result for preview
        "result_preview": item["result"][:1000] + "..." if len(item["result"]) > 1000 else item["result"],
        # Store the full result hash for retrieval
        "result_hash": hashlib.md5(item["result"].encode()).hexdigest(),
        "performance": item.get("performance", {})
    }

def save_to_history(task, operation, sources, result, performance):
    """Save research to history with optimization"""
    # Limit history size to prevent memory issues
    MAX_HISTORY = 20
    
    # Create history item
    history_item = {
        "task": task,
        "operation": operation,
        "sources": sources,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "result": result,
        "performance": performance
    }
    
    # Optimize for storage
    optimized_item = optimize_history_item(history_item)
    
    # Save to history
    if "research_history" not in st.session_state:
        st.session_state.research_history = []
    
    st.session_state.research_history.insert(0, optimized_item)
    
    # Limit history size
    if len(st.session_state.research_history) > MAX_HISTORY:
        st.session_state.research_history = st.session_state.research_history[:MAX_HISTORY]
    
    # Also save full result to cache
    cache_key = get_cache_key(task, operation, sources)
    research_cache[cache_key] = {
        "content": result,
        "timestamp": time.time()
    }
```

### 5. Progressive Loading of Results

```python
def show_progressive_research_steps(progress_placeholder, status_placeholder):
    """Show progressive research steps with smooth animation"""
    
    research_steps = [
        ("🔍 Initializing Research", "Loading research modules..."),
        ("📚 Gathering Information", "Searching knowledge sources..."),
        ("🧠 Processing Data", "Analyzing information..."),
        ("📊 Synthesizing Results", "Generating insights..."),
        ("📝 Formatting Report", "Creating final document..."),
    ]
    
    for step_title, step_desc in research_steps:
        # Update progress indicator
        progress_placeholder.markdown(f"""
        <div class="research-in-progress">
            <h4>{step_title}</h4>
            <p>{step_desc}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Update status message
        status_placeholder.info(f"Step: {step_desc}")
        
        # Simulate processing time (in real implementation, this would be actual processing)
        time.sleep(0.5)
```

## Implementation Priority

1. **High Priority**
   - Parallel knowledge source processing
   - Enhanced caching system
   - Memory optimization for history

2. **Medium Priority**
   - Progressive loading of results
   - UI performance improvements
   - Session state optimization

3. **Low Priority**
   - Additional visualizations
   - Export format options
   - Advanced search filters

## Additional Recommendations

1. **Performance Metrics**
   - Add telemetry for tracking response times
   - Monitor memory usage during large research tasks
   - Implement automatic performance reporting

2. **Error Handling**
   - Add graceful degradation when sources are unavailable
   - Implement retry logic for transient failures
   - Provide more informative error messages

3. **User Experience**
   - Add loading indicators for long-running operations
   - Implement background processing for large reports
   - Add abort capability for long-running searches
