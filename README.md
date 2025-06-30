# AI Recipe Analyzer

## Summary
This is an AI chatbot sample designed to test Generative AI Observability.
When you input a recipe page URL, the AI (Amazon Bedrock) will determine if it's a recipe and automatically extract the ingredient list.
If you enter a dish name instead of a URL, a RAG system using an AWS Bedrock Knowledge Base will refer to the recipe from a [Dish Name].pdf file stored in an S3 bucket.
- Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20240620-v1:0)
- Claude 3.5 Sonnet v2(anthropic.claude-3-5-sonnet-20241022-v2:0)
- Claude 3.7 Sonnet(anthropic.claude-3-7-sonnet-20250219-v1:0)

## Tech Stack
- **Main Language**: Python
- **GUI Framework**: Streamlit
- **AI Framework**: LangChain
- **AI Provider**: Amazon Bedrock
- **Web Scraping**: Requests + BeautifulSoup4
- **Configuration**: python-dotenv
- **observability framework**: OpenTelemetry
- **metrics/log collector**: cloudwatch agent
- **Execution environment** ubuntu on wsl2