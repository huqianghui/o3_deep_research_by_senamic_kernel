# O3 Deep Research by Semantic Kernel

A multi-agent deep research system built with Microsoft Semantic Kernel for generating technical reports and analysis.

## Requirements

- Python 3.11+
- Azure OpenAI API access
- Tavily API key

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with your API keys:
```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01

# Tavily API Configuration
TAVILY_API_KEY=your_tavily_api_key

# Model Deployment Names
GPT4_DEPLOYMENT_NAME=gpt-4
GPT4_MINI_DEPLOYMENT_NAME=gpt-4-mini

# Optional: Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=your_connection_string
```

## Usage

Run the main script:
```bash
python main.py
```

To customize the research task, modify the `TASK` variable in `main.py`.

## Testing

Run tests:
```bash
python -m pytest tests/
```

## License

Copyright (c) Microsoft. All rights reserved.
