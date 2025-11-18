# Set environment variables for LangChain tracing and API access
import os
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGCHAIN_API_KEY'] = <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>

# Install LangChain with OpenAI support
# pip install -U "langchain[openai]"

# Set your OpenAI API key
os.environ['OPENAI_API_KEY'] = <your-api-key>


