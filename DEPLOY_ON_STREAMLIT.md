# Streamlit Community Cloud Deployment Guide

Follow these steps to deploy your application publicly:

1. **Push your code to GitHub:**
   Make sure all latest commits are pushed to:
   `https://github.com/keerthi19hub/GITHUB-CODE-EXPLAINER`
   Branch: `main`

2. **Open Streamlit Community Cloud:**
   Visit: [https://share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.

3. **Deploy New App:**
   Click **"Create app"** or **"New app"**.

4. **Fill in App Settings:**
   - **Repository:** `keerthi19hub/GITHUB-CODE-EXPLAINER`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **Python version:** `3.12`

5. **Secrets & Environment Variables:**
   - **None required!** Leave secrets blank.

6. **Click "Deploy!":**
   Streamlit Cloud will automatically clone the repository, install `requirements.txt`, and start `app.py`.

7. **Share Your Link:**
   Once the build completes, copy the generated public Streamlit URL and test it from any browser.
