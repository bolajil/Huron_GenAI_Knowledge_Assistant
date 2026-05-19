# VaultMIND Knowledge Assistant - Enhanced Documentation Processing

VaultMIND Knowledge Assistant is a powerful tool for ingesting, processing, and querying documents using vector embeddings and large language models (LLMs). This enhanced version provides robust capabilities for handling multiple document formats, maintaining document metadata, and performing sophisticated queries with hybrid search capabilities.

## Features

### Document Ingestion
- **Multi-format Support**: Process PDFs, Word documents, text files, HTML, Markdown, and more
- **Folder Processing**: Ingest entire directories of documents at once
- **Metadata Management**: Track document source, ingestion date, tags, and custom metadata
- **Chunking Strategies**: Configurable chunking with size and overlap settings
- **URL Ingestion**: Import documents directly from URLs

### Querying and Search
- **Semantic Search**: Find documents based on meaning, not just keywords
- **Hybrid Search**: Combine vector search with metadata filtering
- **Query Expansion**: Automatically expand queries with synonyms and related terms
- **Multiple LLM Providers**: Support for OpenAI, Claude, and Deepseek

### Analytics and Feedback
- **Result Tracking**: Keep history of queries and results
- **Feedback Collection**: Gather and store user feedback on search results
- **Performance Metrics**: Monitor system performance and usage statistics

## System Architecture

The system consists of the following components:

1. **Document Processor**: Handles document ingestion, chunking, and metadata management
2. **Vector Database**: Stores document embeddings for semantic search
3. **Query Processor**: Processes user queries and returns relevant results
4. **LLM Integration**: Uses LLMs to synthesize answers from retrieved documents
5. **API Layer**: Provides RESTful API endpoints for integration
6. **Streamlit UI**: User-friendly interface for document management and search

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Required packages:
  ```
  fastapi
  uvicorn
  streamlit
  langchain
  langchain-community
  langchain-huggingface
  sentence-transformers
  faiss-cpu
  pydantic
  pandas
  requests
  ```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/genai-knowledge-assistant.git
   cd genai-knowledge-assistant
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   ```bash
   # API keys for LLM providers
   export OPENAI_API_KEY="your_openai_api_key"
   export CLAUDE_API_KEY="your_claude_api_key"
   export DEEPSEEK_API_KEY="your_deepseek_api_key"
   ```

### Running the Application

1. Start the API server:
   ```bash
   python enhanced_main.py
   ```

2. Start the Streamlit UI (in a separate terminal):
   ```bash
   streamlit run enhanced_streamlit_app.py
   ```

3. Access the UI at http://localhost:8501

## Usage

### Ingesting Documents

1. **Through the UI**:
   - Go to the "Ingest Documents" page
   - Upload files, paste text, or provide a URL
   - Configure chunking settings and tags
   - Click "Process" to ingest the documents

2. **Through the API**:
   ```bash
   # Example: Ingest a file
   curl -X POST http://localhost:8000/ingest/file \
     -F "file=@/path/to/document.pdf" \
     -F "index_name=my_index" \
     -F "chunk_size=500" \
     -F "chunk_overlap=50" \
     -F "tags=report,finance"
   ```

### Searching Documents

1. **Through the UI**:
   - Go to the "Search" page
   - Enter your query
   - Configure search settings
   - View results and generated answers

2. **Through the API**:
   ```bash
   # Example: Query the knowledge base
   curl -X POST http://localhost:8000/enhanced/query \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the benefits of cloud computing?",
       "index_name": "my_index",
       "top_k": 5,
       "provider": "openai"
     }'
   ```

## Advanced Configuration

### Vector Database Configuration

The system supports multiple vector database configurations:

1. **FAISS (default)**: Fast, in-memory vector database
2. **Chroma**: Persistent vector database with metadata filtering
3. **Weaviate**: Scalable vector database with graph capabilities

To change the vector database, modify the `vector_db_config.py` file.

### LLM Provider Configuration

You can configure which LLM providers to use and their parameters in the `llm_config.yml` file.

## Contributing

We welcome contributions to improve VaultMIND Knowledge Assistant! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to the LangChain and Hugging Face teams for their amazing libraries
- Thanks to the Streamlit team for their user-friendly UI framework
- Thanks to all contributors who have helped improve this project
