# Streamlit Cloud Secrets Configuration

This app requires the following secrets to be configured in Streamlit Cloud:

## Required Secrets

1. **OPENAI_API_KEY**: Your OpenAI API key for accessing GPT and embedding models

## How to configure secrets in Streamlit Cloud:

1. Go to your app dashboard on [Streamlit Cloud](https://share.streamlit.io/)
2. Click on your app
3. Click on "Settings" (gear icon)
4. Go to the "Secrets" tab
5. Add the following configuration:

```toml
OPENAI_API_KEY = "your_openai_api_key_here"
```

Replace `your_openai_api_key_here` with your actual OpenAI API key.

## Local Development

For local development, create a `.env` file in the project root with:

```
OPENAI_API_KEY=your_openai_api_key_here
```

**Note**: Never commit the `.env` file to version control. It's already included in `.gitignore`.