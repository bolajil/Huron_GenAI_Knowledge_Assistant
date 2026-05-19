# How to See the ML Changes in Your UI

## ✅ I've Already Integrated the ML Features!

The ML intent classification is now **live** in your Query Assistant tab!

---

## 🚀 Steps to See the Changes

### Step 1: Train the Models (Required First!)

The models need to be trained before they work. Run these commands:

```bash
# Train the intent classifier (2-3 minutes)
python utils/ml_training/train_intent_classifier.py
```

**Wait for it to complete** - you'll see:
```
Training completed!
Final training accuracy: 0.95
✅ Model saved to data/ml_models/query_intent_classifier/
```

### Step 2: Restart Your Streamlit App

```bash
# Stop current Streamlit (Ctrl+C if running)
# Then restart:
streamlit run genai_dashboard_modular.py
```

### Step 3: Go to Query Assistant Tab

1. Open your browser: `http://localhost:8501`
2. Click on **"Query Assistant"** tab in the sidebar
3. Enter a query (e.g., "What is VaultMind?")
4. Click **"Get Answer"**

### Step 4: See the ML Features! 🎉

You'll now see:

```
┌─────────────────────────────────────────────────────┐
│ Enter your query:                                    │
│ ┌─────────────────────────────────────────────────┐ │
│ │ What is VaultMind?                              │ │
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ [Get Answer] button                                  │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 🎯 Query Intent: Factual        Confidence: 95% │ │  ← NEW!
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ ▼ 📊 Retrieval Strategy                             │  ← NEW!
│ ┌─────────────────────────────────────────────────┐ │
│ │ {                                                │ │
│ │   "search_type": "precise",                      │ │
│ │   "top_k": 3,                                    │ │
│ │   "response_style": "concise"                    │ │
│ │ }                                                │ │
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ [Search results appear below...]                    │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 What Changed in Your UI

### Location: Query Assistant Tab

**File Modified**: `tabs/query_assistant.py` (line 576-600)

**What Was Added**:
1. **Intent Badge** - Shows the classified intent (Factual, Analytical, etc.)
2. **Confidence Score** - Shows how confident the AI is
3. **Retrieval Strategy** - Expandable section showing the search strategy

**When It Appears**: Immediately after clicking "Get Answer" button

---

## 🧪 Test Different Query Types

Try these queries to see different intents:

### Factual Query
```
Query: "What is VaultMind?"
Expected Intent: Factual (95%+)
Strategy: Precise search, 3 results, concise answer
```

### Analytical Query
```
Query: "Why should I use vector databases?"
Expected Intent: Analytical (90%+)
Strategy: Comprehensive search, 7 results, detailed reasoning
```

### Procedural Query
```
Query: "How to ingest documents?"
Expected Intent: Procedural (85%+)
Strategy: Structured search, 5 results, step-by-step
```

### Comparative Query
```
Query: "Compare Pinecone vs Weaviate"
Expected Intent: Comparative (90%+)
Strategy: Multi-aspect search, 10 results, comparative analysis
```

### Exploratory Query
```
Query: "Tell me about the system architecture"
Expected Intent: Exploratory (85%+)
Strategy: Broad search, 15 results, comprehensive overview
```

---

## ⚠️ Troubleshooting

### Issue: "Intent classification unavailable"

**Cause**: Models not trained yet

**Solution**:
```bash
python utils/ml_training/train_intent_classifier.py
```

### Issue: Import errors

**Cause**: TensorFlow not installed

**Solution**:
```bash
pip install -r requirements-ml-models.txt
```

### Issue: Python 3.14 compatibility

**Solution**: Use Python 3.11
```bash
conda create -n vaultmind python=3.11
conda activate vaultmind
pip install -r requirements-ml-models.txt
python utils/ml_training/train_intent_classifier.py
streamlit run genai_dashboard_modular.py
```

### Issue: Still don't see changes

**Checklist**:
- [ ] Trained the model? (`python utils/ml_training/train_intent_classifier.py`)
- [ ] Restarted Streamlit? (Ctrl+C then restart)
- [ ] Using Query Assistant tab? (not other tabs)
- [ ] Clicked "Get Answer" button?
- [ ] Check terminal for errors?

---

## 📊 What Happens Behind the Scenes

When you click "Get Answer":

1. **Your query** → "What is VaultMind?"
2. **ML Model** → Classifies intent as "Factual"
3. **Strategy** → Selects precise search with 3 results
4. **UI Updates** → Shows intent badge and strategy
5. **Search** → Uses optimized parameters
6. **Results** → Better, more relevant answers!

---

## 🎨 Visual Comparison

### Before (Old UI):
```
[Query box]
[Get Answer button]
↓
[Results immediately]
```

### After (New UI with ML):
```
[Query box]
[Get Answer button]
↓
🎯 Intent: Factual (95%)  ← NEW!
📊 Strategy: {...}         ← NEW!
↓
[Results with better relevance]
```

---

## 🚀 Next Steps

### 1. Add Document Classification

Want to see ML in Document Ingestion too?

**File to edit**: `tabs/multi_vector_document_ingestion.py`

**Code to add**: See `QUICK_INTEGRATION_EXAMPLE.py` - Example 2

### 2. Add Quality Checking

Want to see quality scores during ingestion?

**Same file**: `tabs/multi_vector_document_ingestion.py`

**Code to add**: See `QUICK_INTEGRATION_EXAMPLE.py` - Example 2

### 3. Train Other Models

```bash
# Document classifier
python utils/ml_training/train_document_classifier.py

# Quality checker
python utils/ml_training/train_quality_checker.py
```

---

## ✅ Summary

**What I Did**:
- ✅ Added ML intent classification to Query Assistant tab
- ✅ Shows intent badge after clicking "Get Answer"
- ✅ Shows retrieval strategy (expandable)
- ✅ Adjusts search parameters based on intent

**What You Need to Do**:
1. Train the model: `python utils/ml_training/train_intent_classifier.py`
2. Restart Streamlit
3. Go to Query Assistant tab
4. Enter a query and click "Get Answer"
5. See the ML features! 🎉

**The changes are LIVE in your code** - you just need to train the model to see them work!
