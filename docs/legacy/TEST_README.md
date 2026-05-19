# VaultMIND Knowledge Assistant Testing Suite

This document provides instructions for running the comprehensive test suite for the VaultMIND Knowledge Assistant system.

## Overview

The testing suite consists of multiple test scripts that verify different aspects of the system:

1. **Vector Database Functionality** - Tests vector database connections, fallback mechanisms, and search capabilities
2. **Document Ingestion** - Tests file upload, processing, chunking, and embedding generation
3. **ByLaw Content Access** - Tests ByLaw retrieval, query detection, and enhanced responses
4. **LLM Integration** - Tests language model configuration, response generation, and error handling
5. **System Integration** - Tests end-to-end flows and component interactions
6. **Comprehensive Tests** - Additional tests covering various system aspects

## Running the Tests

### Running All Tests

To run all tests at once, use the master test runner script:

```bash
python run_all_tests.py
```

This will execute all test scripts and provide a comprehensive summary of results. Detailed logs will be saved in the `test_logs` directory.

### Running Individual Tests

You can also run individual test scripts to focus on specific components:

```bash
python test_vector_db_functionality.py
python test_document_ingestion.py
python test_bylaw_content_access.py
python test_llm_integration.py
python test_system_integration.py
python run_comprehensive_tests.py
```

## Interpreting Test Results

Each test script will output detailed information about the tests being run and their results. The output includes:

- ✅ PASS - The test passed successfully
- ⚠️ WARNING - The test passed with some warnings or partial functionality
- ❌ FAIL - The test failed

At the end of each test script, a summary will be displayed showing the overall results.

## Test Dependencies

The tests assume that the following components are properly configured:

1. Environment variables for API keys (if testing with real providers)
2. Access to vector database providers (or fallback to mock provider)
3. Sample documents for ingestion tests
4. ByLaw content for ByLaw access tests

If certain components are not available, some tests may fail or fall back to mock implementations.

## Troubleshooting

If tests are failing, check the following:

1. **API Keys**: Ensure that necessary API keys are set in the environment variables
2. **Vector Database**: Verify that vector database providers are accessible
3. **File Paths**: Check that file paths in the tests point to valid locations
4. **Dependencies**: Make sure all required Python packages are installed
5. **Logs**: Review the detailed logs in the `test_logs` directory

## Adding New Tests

To add new tests:

1. Create a new test script following the pattern of existing scripts
2. Add the script to the `test_scripts` list in `run_all_tests.py`
3. Run the tests to verify that your new tests are included

## Contact

For questions or issues with the testing suite, please contact the VaultMIND development team.