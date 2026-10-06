# Streamlit Community Cloud deployment

1. Push this repository to GitHub.
2. In Streamlit Community Cloud choose `pragathidevanga/GitHub-Code_Explainer`.
3. Branch: `main`.
4. Main file: `app.py`.
5. No secrets are required.
6. Deploy.

The deployed path is self-contained. Do not configure BACKEND_URL, Ollama, ngrok, cloudflared, or another server.

The first analysis may take longer because the Hugging Face model is downloaded and initialized. Streamlit caches the model for the runtime.
