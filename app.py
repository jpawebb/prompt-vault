import streamlit as st
import sqlite3
from typing import List, Tuple

DB_FILENAME = "prompt_vault.db"

def get_connection():
    conn = sqlite3.connect(DB_FILENAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                prompt TEXT NOT NULL,
                tags TEXT,
                description TEXT
            )
        ''')
        conn.commit()

def add_prompt(title: str, prompt: str, tags: str, description: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO prompts (title, prompt, tags, description) VALUES (?, ?, ?, ?)",
            (title, prompt, tags, description)
        )
        conn.commit()

def get_prompts(search: str = '', tag: str = '') -> List[sqlite3.Row]:
    q = "SELECT * FROM prompts"
    params: Tuple = ()
    if search and tag:
        q += " WHERE (title LIKE ? OR prompt LIKE ? OR description LIKE ?) AND tags LIKE ?"
        params = (f"%{search}%", f"%{search}%", f"%{search}%", f"%{tag}%")
    elif search:
        q += " WHERE title LIKE ? OR prompt LIKE ? OR description LIKE ?"
        params = (f"%{search}%", f"%{search}%", f"%{search}%")
    elif tag:
        q += " WHERE tags LIKE ?"
        params = (f"%{tag}%",)
    q += " ORDER BY id DESC"
    with get_connection() as conn:
        cur = conn.execute(q, params)
        return cur.fetchall()

def delete_prompt(prompt_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()

def get_unique_tags() -> List[str]:
    with get_connection() as conn:
        cur = conn.execute("SELECT tags FROM prompts")
        tags = set()
        for row in cur:
            if row["tags"]:
                tags.update([t.strip() for t in row["tags"].split(",") if t.strip()])
        return sorted(tags)

########################
# Streamlit UI Section #
########################

st.set_page_config(page_title="Prompt Vault", page_icon="🗂️", layout="wide")
st.title("🗂️ Prompt Vault")
st.caption("A minimal LLM prompt management app")

init_db()

tab1, tab2 = st.tabs(["Prompts", "Add Prompt"])

with tab2:
    st.header("Add a New Prompt")
    with st.form("add_prompt"):
        title = st.text_input("Prompt Title", max_chars=80)
        prompt = st.text_area("Prompt Content", height=120)
        tags = st.text_input("Tags (comma-separated)", help="For example: chatgpt,code,python")
        description = st.text_area("Short Description", height=60)
        submitted = st.form_submit_button("Add Prompt")
        if submitted and title and prompt:
            add_prompt(title, prompt, tags, description)
            st.success("Prompt added!")
        elif submitted:
            st.warning("Title and prompt content are required.")

with tab1:
    st.header("Prompt Library")

    col_search, col_tag = st.columns([4, 2])
    with col_search:
        search = st.text_input("Search (title/content/desc)", key="search")
    with col_tag:
        tags_all = get_unique_tags()
        tag_filter = st.selectbox("Filter by tag", [""] + tags_all, index=0)

    prompts = get_prompts(search, tag_filter)

    if prompts:
        for row in prompts:
            
            title = row['title'] if 'title' in row.keys() else ''
            tags = row['tags'] if 'tags' in row.keys() else ''
            expander = st.expander(f"{title}  {'🔖'+tags if tags else ''}")

            with expander:
                st.code(row["prompt"], language="markdown")
                st.markdown(f"**Description:** {row['description'] or '_No description_'}")
                st.markdown(f"**Tags:** {row['tags'] or '_None_'}")
                c1, c2 = st.columns([1, 5])
                with c1:
                    if st.button(f"🗑️ Delete", key=f"del_{row['id']}"):
                        delete_prompt(row['id'])
                        st.experimental_rerun()
    else:
        st.info("No prompts found (yet). Add your first one!")

st.markdown("---")
st.markdown("Made with [Streamlit](https://streamlit.io/) • [Code on GitHub](https://github.com/jpawebb/prompt-vault)")