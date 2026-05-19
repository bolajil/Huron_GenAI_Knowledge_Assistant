# Web Content Ingestion Guide

## ✅ Web Scraping Already Available!

Your system **already has web content ingestion** built into the **📁 Input Document** tab!

## 📍 How to Use Web Ingestion

### Step 1: Go to Input Document Tab
Navigate to: **📁 Input Document** tab in the main dashboard

### Step 2: Select Storage Backend
Choose where to store the web content:
- **Weaviate (Cloud Vector DB)** - Cloud storage, accessible from anywhere
- **Local FAISS Index** - Local storage, faster access
- **Both** - Store in both locations (recommended)

### Step 3: Select "Website URL"
In the "Select content source" section, choose:
```
○ PDF File
○ Text File  
● Website URL  ← Select this
```

### Step 4: Configure Web Scraping
You'll see these options:

**URL Input:**
```
Enter website URL: https://example.com/article
```

**JavaScript Rendering:**
```
☐ Render JavaScript (for dynamic sites)
```
- Check this if the website uses JavaScript to load content
- Useful for modern single-page applications

**Link Depth:**
```
Link depth (for multi-page scraping): [0] ─────── [3]
```
- **0**: Only scrape the single URL
- **1**: Scrape the URL + all links on that page
- **2**: Scrape 2 levels deep
- **3**: Scrape 3 levels deep (can take a while!)

### Step 5: Set Index Name
```
Index Name: web_content_index
```
Or use a descriptive name like:
- `aws_security_docs`
- `company_blog_posts`
- `technical_documentation`

### Step 6: Configure Chunking
```
Chunk Size: 1000
Chunk Overlap: 200
```

### Step 7: Click "🚀 Ingest and Index"

## 🎯 What Happens During Web Ingestion

### 1. **Content Fetching**
```python
- Sends HTTP request to URL
- Downloads HTML content
- Handles redirects and errors
```

### 2. **Content Extraction**
```python
- Parses HTML with BeautifulSoup
- Extracts text content (removes HTML tags)
- Cleans and formats text
- Saves raw HTML for reference
```

### 3. **Chunking**
```python
- Splits content into manageable chunks
- Creates overlapping chunks for context
- Saves each chunk separately
- Limits to 10 chunks per URL (configurable)
```

### 4. **Vectorization**
```python
- Generates embeddings for each chunk
- Uses sentence-transformers model
- Creates vector representations
```

### 5. **Indexing**
```python
- Stores vectors in Weaviate/FAISS
- Saves metadata (URL, timestamp, chunk info)
- Makes content searchable
```

## 📊 What Gets Saved

### In Weaviate/FAISS Index:
- ✅ Text content (cleaned and chunked)
- ✅ Vector embeddings
- ✅ Source URL
- ✅ Chunk metadata
- ✅ Timestamp

### In Local Files (if using FAISS):
```
indexes/web_content_index/
├── source_url.txt          # Original URL and settings
├── raw_html.html           # Original HTML
├── extracted_content.txt   # Cleaned text
├── extracted_text.txt      # For FAISS indexing
├── chunk_1.txt            # Individual chunks
├── chunk_2.txt
├── ...
├── faiss_index.bin        # FAISS vector index
└── metadata.json          # Index metadata
```

## 🔍 How to Query Web Content

### Option 1: Query Assistant Tab
1. Go to **🔎 Quick Search** or **📚 Index Search**
2. Select your web content index (e.g., `web_content_index`)
3. Ask questions about the content
4. Get AI-generated answers with citations

### Option 2: Chat Assistant Tab
1. Go to **💬 Chat Assistant**
2. Select your web content index
3. Have a conversation about the content

### Option 3: Web Search Tab
1. Go to **🌐 Web Search**
2. This does **live** web search (not from your index)
3. Results are temporary, not stored

## 🆚 Web Search vs Web Ingestion

### 🌐 Web Search Tab (Temporary)
- **Purpose**: Get latest information from the internet
- **Storage**: Results are NOT saved
- **Speed**: Depends on internet/API
- **Use Case**: Current events, latest news, real-time data
- **Persistence**: ❌ Results disappear after session

### 📁 Web Ingestion (Permanent)
- **Purpose**: Build a knowledge base from web content
- **Storage**: Content IS saved to index
- **Speed**: Fast (local/cloud index)
- **Use Case**: Documentation, articles, reference material
- **Persistence**: ✅ Content stays in your knowledge base

## 💡 Use Cases

### 1. **Technical Documentation**
```
URL: https://docs.aws.amazon.com/security/
Index: aws_security_docs
Use: Query AWS security best practices
```

### 2. **Company Blog Posts**
```
URL: https://company.com/blog
Depth: 2 (scrape all blog posts)
Index: company_blog_index
Use: Search company announcements and articles
```

### 3. **Legal/Compliance Documents**
```
URL: https://regulations.gov/document/xyz
Index: compliance_docs
Use: Query regulatory requirements
```

### 4. **Research Papers**
```
URL: https://arxiv.org/abs/12345
Index: research_papers
Use: Search academic research
```

### 5. **Product Documentation**
```
URL: https://product.com/docs
Depth: 3 (full documentation)
Index: product_docs
Use: Customer support queries
```

## ⚙️ Advanced Features

### Multi-Page Scraping
Set **Link Depth > 0** to scrape multiple pages:
```
Depth 0: Single page only
Depth 1: Page + all links on that page
Depth 2: 2 levels of links
Depth 3: 3 levels of links (can be 100+ pages!)
```

**Warning**: Higher depth = more pages = longer processing time

### JavaScript Rendering
Enable for dynamic websites:
```
☑ Render JavaScript (for dynamic sites)
```

**When to use**:
- Single-page applications (React, Vue, Angular)
- Sites that load content with JavaScript
- Dynamic content that doesn't appear in raw HTML

**Note**: Requires additional dependencies (Selenium, Chrome driver)

### Chunking Strategy
Adjust for different content types:

**Long articles** (default):
```
Chunk Size: 1000
Chunk Overlap: 200
```

**Short snippets**:
```
Chunk Size: 500
Chunk Overlap: 100
```

**Technical docs** (preserve context):
```
Chunk Size: 1500
Chunk Overlap: 300
```

## 🔧 Troubleshooting

### Issue 1: "Error fetching URL content"
**Causes**:
- URL is invalid or unreachable
- Website blocks scraping (robots.txt)
- Timeout (slow website)
- SSL certificate issues

**Solutions**:
- Verify URL is correct and accessible
- Check if website allows scraping
- Try a different URL
- Use JavaScript rendering if content is dynamic

### Issue 2: Empty or Incomplete Content
**Causes**:
- Website uses JavaScript to load content
- Content is behind login/paywall
- Anti-scraping measures

**Solutions**:
- Enable "Render JavaScript" option
- Use authenticated access (if available)
- Try a different source

### Issue 3: Too Many Pages Scraped
**Causes**:
- Link depth set too high
- Website has many interconnected pages

**Solutions**:
- Reduce link depth to 0 or 1
- Scrape specific pages individually
- Use more specific URLs

### Issue 4: Content Not Appearing in Search
**Causes**:
- Index not created properly
- Wrong index selected in Query tab
- Content not vectorized

**Solutions**:
- Check if index appears in available indexes list
- Verify index name matches what you created
- Re-run ingestion if needed

## 📈 Best Practices

### 1. **Use Descriptive Index Names**
```
❌ web_index
❌ test_index
✅ aws_security_docs_2025
✅ company_blog_posts
✅ technical_documentation
```

### 2. **Start with Single Pages**
- Test with depth 0 first
- Verify content quality
- Then increase depth if needed

### 3. **Organize by Topic**
- Create separate indexes for different topics
- Don't mix unrelated content in one index
- Makes searching more accurate

### 4. **Regular Updates**
- Re-scrape periodically for updated content
- Delete old indexes before re-ingesting
- Keep track of last update date

### 5. **Respect Robots.txt**
- Check if website allows scraping
- Don't overload servers with requests
- Use reasonable link depths

## 🚀 Quick Start Example

### Example: Scrape AWS Security Documentation

1. **Go to**: 📁 Input Document tab
2. **Select**: Both (Weaviate + Local FAISS)
3. **Choose**: Website URL
4. **Enter URL**: `https://docs.aws.amazon.com/security/`
5. **Settings**:
   - ☑ Render JavaScript: Yes
   - Link Depth: 1
   - Chunk Size: 1000
   - Chunk Overlap: 200
6. **Index Name**: `aws_security_docs`
7. **Click**: 🚀 Ingest and Index
8. **Wait**: 30-60 seconds
9. **Query**: Go to Quick Search, select `aws_security_docs`, ask questions!

## 📊 Summary

### What You Have:
- ✅ **Web scraping** - Built into Input Document tab
- ✅ **Content extraction** - BeautifulSoup HTML parsing
- ✅ **Multi-page scraping** - Configurable link depth
- ✅ **JavaScript rendering** - For dynamic sites
- ✅ **Chunking** - Automatic text splitting
- ✅ **Vectorization** - Automatic embedding generation
- ✅ **Dual storage** - Weaviate + FAISS support
- ✅ **Permanent indexes** - Content saved for future queries

### What's Different from Web Search Tab:
| Feature | Web Search Tab | Web Ingestion |
|---------|---------------|---------------|
| **Storage** | Temporary | Permanent |
| **Speed** | Depends on API | Fast (indexed) |
| **Persistence** | ❌ No | ✅ Yes |
| **Use Case** | Latest info | Knowledge base |
| **Citations** | URLs | Indexed content |

### Next Steps:
1. **Try it**: Go to Input Document → Website URL
2. **Scrape content**: Enter a URL and ingest
3. **Query it**: Use Quick Search to query your web content
4. **Build knowledge base**: Add more web sources to your indexes

---

**Status**: ✅ Web ingestion fully functional and ready to use!
**Location**: 📁 Input Document tab → Website URL option
**Storage**: Permanent indexes (Weaviate/FAISS)
