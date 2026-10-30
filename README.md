# Sunidhi AI

A Streamlit portfolio website with an AI chat assistant, project gallery, and password-protected project management.

Projects can optionally include a project or demo URL; visitors open it in a new tab.

## Run locally

1. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `secrets.toml.example` to `.streamlit/secrets.toml` and set `GEMINI_API_KEY` and `ADMIN_PASSWORD`.
3. Start the app:

   ```bash
   streamlit run app.py
   ```

## Deploy with Streamlit Community Cloud

1. Push this repository to GitHub.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from the repository, select the deployment branch, and set the app file to `app.py`.
3. Add `GEMINI_API_KEY` and `ADMIN_PASSWORD` in the app's **Settings → Secrets** using TOML format. Never commit real keys or passwords.
4. Save and wait for the app to deploy.

The portfolio PDF and profile image are part of the public repository and will be accessible to anyone who can access the app.

## Project management persistence

The app filesystem on Streamlit Community Cloud is temporary. Without GitHub sync, project additions and deletions may disappear when the app restarts. To persist them, add these values to the app's Secrets:

```toml
GITHUB_TOKEN = "github_pat_..."
GITHUB_REPO = "your-username/your-repo"
GITHUB_BRANCH = "main"
```

Use a fine-grained GitHub token limited to this repository with **Contents: Read and write** permission. Keep the token private; do not commit it or paste it into chat. After saving the secrets, verify that Manage reports GitHub sync is enabled and that new projects appear in `data/projects.json` in the repository.
