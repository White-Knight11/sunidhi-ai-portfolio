# Sunidhi AI

A Streamlit portfolio website with an AI chat assistant. The assistant uses the portfolio PDF and existing project data as its source of information.

## Run locally

1. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `secrets.toml.example` to `.streamlit/secrets.toml` and set `GEMINI_API_KEY`.
3. Start the app:

   ```bash
   streamlit run app.py
   ```

## Deploy with Streamlit Community Cloud

1. Select this repository, the deployment branch, and `app.py` in [Streamlit Community Cloud](https://share.streamlit.io/).
2. Add `GEMINI_API_KEY` in the app's **Settings → Secrets** using TOML format. Never commit real keys.
3. Save and wait for the app to deploy.

The portfolio PDF, profile image, and existing project data are part of the public repository. Project data remains available to the chat assistant; the app no longer includes a project gallery or project-management page.
