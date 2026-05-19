# VaultMind Documentation Index

## 📚 Complete Documentation Guide

Welcome to VaultMind! This index helps you find the right documentation for your needs.

---

## 🚀 Getting Started

### For First-Time Users
1. **[README.md](README.md)** - Start here! Overview, features, quick start
2. **[Quick Start Guide](#quickstart-local)** - 5-minute installation
3. **[Demo Guide](DEMO_GUIDE.md)** - See VaultMind in action

### For Deployers
1. **[Quick Publish](QUICK_PUBLISH.md)** - Deploy in 30 minutes
2. **[Deployment Guide](DEPLOYMENT.md)** - All deployment options
3. **[Publishing Checklist](PUBLISH_CHECKLIST.md)** - Go-to-market preparation

---

## 📖 User Guides

### Core Features

**[README.md](README.md)** - Main documentation
- System overview and architecture
- Key features and capabilities
- Installation instructions
- Quick start guide

**[DEMO_GUIDE.md](DEMO_GUIDE.md)** - Demo scenarios
- 5-minute quick demo
- 25-minute full demo
- Audience-specific scenarios
- Talk tracks and sample queries

**[HYBRID_SETUP_GUIDE.md](HYBRID_SETUP_GUIDE.md)** - Hybrid LangGraph system
- Query complexity analysis
- Intelligent routing configuration
- LangGraph agent setup
- Performance tuning

**[DOCUMENT_QUALITY_GUIDE.md](DOCUMENT_QUALITY_GUIDE.md)** - Document quality control
- Quality analysis and scoring
- Automatic cleaning features
- OCR error detection
- Best practices

---

## 🚀 Deployment & Publishing

**[QUICK_PUBLISH.md](QUICK_PUBLISH.md)** - 30-minute deployment
- Repository preparation
- Streamlit Cloud deployment
- Social media announcements
- Quick troubleshooting

**[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- Local development setup
- Docker deployment
- Cloud platforms (AWS, Azure, GCP)
- Security best practices
- Monitoring and observability

**[PUBLISH_CHECKLIST.md](PUBLISH_CHECKLIST.md)** - Publication preparation
- Pre-publication tasks
- GitHub repository setup
- Marketing materials
- Launch day timeline
- Success metrics

---

## 🔧 Technical Documentation

### System Architecture

**Architecture Overview** (in README.md)
- System components
- Data flow diagrams
- Integration points
- Technology stack

**Core Components:**
- **Hybrid Intelligence:** Query routing and LangGraph agent
- **Document Quality:** Quality analysis and cleaning
- **Vector Storage:** Multi-cloud adapters
- **LLM Integration:** Multi-provider support
- **Security:** RBAC and governance

### Configuration Files

**Environment Configuration:**
- `.env` - Main configuration file
- `.env.example` - Template with all options
- `config/weaviate.env` - Weaviate-specific settings
- `config/storage.env` - Storage backend settings

**System Configuration:**
- `requirements-complete.txt` - All dependencies
- `genai_dashboard_modular.py` - Main application
- `scripts/demo_preflight_check.py` - Validation script

---

## 🎯 Feature-Specific Guides

### Hybrid LangGraph System

**Files:**
- `utils/query_complexity_analyzer.py` - Query classification
- `utils/hybrid_query_orchestrator.py` - Intelligent routing
- `app/utils/langgraph_agent.py` - Autonomous agent
- `tabs/agent_assistant_hybrid.py` - UI integration

**Documentation:**
- [HYBRID_SETUP_GUIDE.md](HYBRID_SETUP_GUIDE.md)
- [DEMO_GUIDE.md](DEMO_GUIDE.md) - Section 3

### Document Quality Control

**Files:**
- `utils/document_quality_checker.py` - Quality analysis
- `utils/document_quality_ui.py` - UI components

**Documentation:**
- [DOCUMENT_QUALITY_GUIDE.md](DOCUMENT_QUALITY_GUIDE.md)
- [README.md](README.md) - Document Quality Control section

### Multi-Vector Storage

**Files:**
- `utils/weaviate_manager.py` - Weaviate integration
- `utils/multi_vector_storage_interface.py` - Multi-cloud adapters
- `utils/faiss_to_weaviate_migrator.py` - Migration tools

**Documentation:**
- [DEPLOYMENT.md](DEPLOYMENT.md) - Vector storage configuration
- [README.md](README.md) - Multi-Vector Storage section

### Enterprise Features

**Security & Permissions:**
- `app/auth/enterprise_permissions.py` - RBAC
- `app/auth/resource_request_manager.py` - Approvals
- `app/auth/mfa_manager.py` - Two-factor auth

**Analytics & Monitoring:**
- `utils/user_feedback_system.py` - Feedback collection
- `tabs/feedback_analytics_tab.py` - Analytics dashboard

---

## 🎬 Demo & Presentation Materials

### Demo Scenarios

**Quick Demo (5 minutes):**
1. Document ingestion with quality check
2. Simple query with fast retrieval
3. Complex query with LangGraph reasoning

**Full Demo (25 minutes):**
1. Multi-vector architecture showcase
2. Hybrid retrieval in action
3. Enterprise features walkthrough
4. Analytics and monitoring

**Custom Demos:**
- Technical leaders (architecture focus)
- Business leaders (ROI focus)
- Knowledge teams (accuracy focus)

### Presentation Materials

**Elevator Pitch:**
> "VaultMind is an enterprise GenAI knowledge assistant that turns scattered documents into trustworthy, cited answers. It intelligently routes queries between fast retrieval and deep reasoning, with no vendor lock-in."

**Key Differentiators:**
- ✨ Hybrid intelligence (fast + deep reasoning)
- 🎯 Multi-vector flexibility (9 providers)
- 📊 Document quality control
- 🔒 Enterprise-ready governance
- 🤖 BYO-LLM (5 providers)

**Demo Talk Tracks:**
- See [DEMO_GUIDE.md](DEMO_GUIDE.md) - Talk Track Templates

---

## 🛠️ Development & Contributing

### For Developers

**Getting Started:**
1. Clone repository
2. Install dependencies: `pip install -r requirements-complete.txt`
3. Run preflight check: `python scripts/demo_preflight_check.py`
4. Start development: `streamlit run genai_dashboard_modular.py`

**Key Development Files:**
- `genai_dashboard_modular.py` - Main application
- `tabs/` - UI components
- `utils/` - Core utilities
- `app/` - Backend services

**Testing:**
- `scripts/demo_preflight_check.py` - System validation
- `check_indexes.py` - Index verification
- `check_config.py` - Configuration check

### Contributing

**Process:**
1. Fork repository
2. Create feature branch
3. Make changes and test
4. Submit pull request

**Guidelines:**
- Follow existing code style
- Add tests for new features
- Update documentation
- Keep PRs focused

---

## 📊 Monitoring & Troubleshooting

### Health Checks

**System Status:**
```bash
# Run preflight check
python scripts/demo_preflight_check.py

# Check indexes
python check_indexes.py

# Check configuration
python check_config.py
```

**Common Issues:**

**"No indexes found"**
- Solution: Ingest documents via "📄 Ingest Document" tab
- Or: Run `python check_indexes.py` to see available indexes

**"OpenAI API error"**
- Solution: Verify API key in `.env` file
- Or: Use alternative LLM provider

**"Weaviate connection failed"**
- Solution: Check `WEAVIATE_URL` and `WEAVIATE_API_KEY` in `.env`
- Or: Fallback to FAISS (local)

**"Document quality low"**
- Solution: Use document quality checker
- See: [DOCUMENT_QUALITY_GUIDE.md](DOCUMENT_QUALITY_GUIDE.md)

### Performance Optimization

**Query Performance:**
- Use hybrid routing for optimal speed
- Enable caching for repeated queries
- Adjust complexity thresholds

**Ingestion Performance:**
- Batch process multiple documents
- Use quality checker to improve results
- Optimize chunk size (default: 1500/500)

---

## 📞 Support & Resources

### Getting Help

**Documentation:**
- This index
- Individual guide files
- README.md

**Community:**
- GitHub Issues
- GitHub Discussions
- Email: support@vaultmind.ai

**Professional Support:**
- Enterprise support available
- Custom deployment assistance
- Training and onboarding

### Additional Resources

**External Links:**
- [Streamlit Documentation](https://docs.streamlit.io)
- [LangChain Documentation](https://python.langchain.com)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)

---

## 🗺️ Documentation Roadmap

### Coming Soon

- [ ] API Reference Guide
- [ ] Integration Guide (SharePoint, Confluence, etc.)
- [ ] Advanced Configuration Guide
- [ ] Performance Tuning Guide
- [ ] Security Best Practices
- [ ] Troubleshooting Guide (expanded)

### Planned

- [ ] Video tutorials
- [ ] Interactive demos
- [ ] Case studies
- [ ] Architecture deep-dives
- [ ] Migration guides

---

## 📝 Quick Reference

### Essential Commands

```bash
# Installation
pip install -r requirements-complete.txt

# Run application
streamlit run genai_dashboard_modular.py

# Validation
python scripts/demo_preflight_check.py

# Check indexes
python check_indexes.py

# Check configuration
python check_config.py
```

### Essential Files

| File | Purpose |
|------|---------|
| `README.md` | Main documentation |
| `DEMO_GUIDE.md` | Demo scenarios |
| `DEPLOYMENT.md` | Deployment options |
| `QUICK_PUBLISH.md` | 30-min deployment |
| `DOCUMENT_QUALITY_GUIDE.md` | Quality control |
| `HYBRID_SETUP_GUIDE.md` | Hybrid system |
| `PUBLISH_CHECKLIST.md` | Publication prep |

### Essential Directories

| Directory | Contents |
|-----------|----------|
| `tabs/` | UI components |
| `utils/` | Core utilities |
| `app/` | Backend services |
| `scripts/` | Helper scripts |
| `data/` | Indexes and data |
| `config/` | Configuration files |

---

## 🎓 Learning Path

### Beginner
1. Read [README.md](README.md)
2. Follow Quick Start
3. Try [DEMO_GUIDE.md](DEMO_GUIDE.md) - 5-minute demo
4. Ingest your first document

### Intermediate
1. Explore hybrid system: [HYBRID_SETUP_GUIDE.md](HYBRID_SETUP_GUIDE.md)
2. Learn document quality: [DOCUMENT_QUALITY_GUIDE.md](DOCUMENT_QUALITY_GUIDE.md)
3. Try different LLM providers
4. Configure multi-vector storage

### Advanced
1. Deploy to production: [DEPLOYMENT.md](DEPLOYMENT.md)
2. Customize and extend
3. Integrate with enterprise systems
4. Contribute to the project

---

**Need help finding something?** Check the table of contents above or search this file for keywords.

**Ready to get started?** Begin with [README.md](README.md) and the Quick Start guide!

---

<p align="center">📚 VaultMind Documentation | Updated: November 2025</p>
