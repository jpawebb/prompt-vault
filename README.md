# PromptVault: Organized Platform for Managing Prompt Collections
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Database](https://img.shields.io/badge/Database-SQLite-lightgrey)
![Frontend](https://img.shields.io/badge/Frontend-Streamlit-21c18f)

![promptvault-logo](images/promptvault-logo.png)


## Overview

PromptVault is a powerful tool for managing, organizing, and retrieving prompt collections for AI, LLM, and creative workflows. Inspired by modern productivity and data management platforms, PromptVault enables effective CRUD operations, tagging, search, and sharing of textual prompts from a user-friendly interface.

## Architecture

**Modular Application Stack**
```
🖥️ STREAMLIT UI → 📄 PROMPT DATABASE (SQLite) → 🔎 Query/Tag Engine → ⚙️ CI/CD Integration
```


| Component        | Technology           | Purpose                                |
|------------------|---------------------|----------------------------------------|
| **Frontend**     | Streamlit           | Interactive prompt entry & management  |
| **Database**     | SQLite              | Lightweight storage solution           |
| **Backend**      | Python 3.10+        | CRUD logic & integrations              |
| **CI/CD**        | GitHub Actions      | Automated testing & deployment         |
| **Documentation**| Markdown/Streamlit  | Usage instructions & API docs          |

## Features

- 📦 Store and manage multiple prompt templates
- 🔎 Advanced search and filtering by tags
- 🏷️ Categorization and labeling
- 📝 In-browser editing/creation
- 🗂️ Bulk import/export (CSV, JSON support)
- 🔗 Easy prompt sharing


## Roadmap / TODO

- [ ] Add user authentication for multi-user support
- [ ] Integrate cloud database options (e.g., PostgreSQL)
- [ ] Extend prompt sharing and collaboration features
- [ ] Advanced analytics and prompt usage stats
