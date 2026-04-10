import streamlit as st
import sqlite3
from typing import List, Tuple

from core.renderer import extract_variables, render_prompt


DB_FILENAME = "prompt_vault.db"



def get_connection():
    conn = sqlite3.connect(DB_FILENAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                prompt      TEXT NOT NULL,
                tags        TEXT,
                description TEXT
            )
        """)
        conn.commit()

def add_prompt(title: str, prompt: str, tags: str, description: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO prompts (title, prompt, tags, description) VALUES (?, ?, ?, ?)",
            (title, prompt, tags, description)
        )
        conn.commit()


def get_prompts(search: str = "", tag: str = "") -> List[sqlite3.Row]:
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
        return conn.execute(q, params).fetchall()


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


# Streamlit UI helper
def _render_section(prompt_id: int, prompt_body: str):
    """Render the Jinja2 fill-in section for a single prompt card.

    Uses st.session_state keys namespaced to prompt_id so multiple prompts
    can be open and rendered simultaneously wihtout state collisions.
    """
    variables = extract_variables(prompt_body)

    st.markdown("---")
    st.markdown("**Render**")

    if not variables:
        # No {{ }} tokens, render prompt as plain text (some prompts have no variables).
        rendered, err = render_prompt(prompt_body, {})
        if err:
            st.error({err})
        else:
            st.info("No template variables detected. Rendered output is the same as the template.")
            st.code(rendered, language="markdown")
            st.button(
                "Copy rendered prompt",
                key=f"copy_{prompt_id}",
                on_click=lambda: None,  # Streamlit clipboard workaround: https://discuss.streamlit.io/t/copy-to-clipboard-button/2655/2
                help="Select all text in the box above and copy manually (Ctrl-A/Cmd-A, Ctrl-C/Cmd-C)."
            )
        return
    
    # Fill in form
    with st.form(key=f"render_form_{prompt_id}"):
        st.caption(f"Fill in the {len(variables)} variable(s) detected in this template:")
        context: dict[str, str] = {}
        cols = st.columns(min(len(variables), 3))
        for i, var in enumerate(variables):
            state_key = f"render_{prompt_id}_{var}"
            default = st.session_state.get(state_key, "")
            value = cols[i % len(cols)].text_input(
                label=var,
                value=default,
                key=f"input_{prompt_id}_{var}",
                placeholder=f"Enter {var}...",
            )
            context[var] = value

        submitted = st.form_submit_button("Render → ", use_container_width=True)

    if submitted:
        # Persist values so they survive returns
        for var, val in context.items():
            st.session_state[f"render_{prompt_id}_{var}"] = val

        rendered, err = render_prompt(prompt_body, context)
        if err:
            st.error({err})
        else:
            st.success("Rendered successfully")
            st.code(rendered, language="markdown")

    elif any(st.session_state.get(f"render_{prompt_id}_{v}") for v in variables):
        # Re-render with previously saved values on rerun (e.g. after deleting a different prompt)
        saved_ctx = {v: st.session_state.get(f"render_{prompt_id}_{v}", "") for v in variables}
        rendered, err = render_prompt(prompt_body, saved_ctx)
        if not err:
            st.code(rendered, language="markdown")


# Streamlit UI

st.set_page_config(page_title="Prompt Vault", page_icon="🗂️", layout="wide")
st.title("🗂️ Prompt Vault")
st.caption("A versioned, renderable vault for Jinja2 prompt templates")

init_db()

tab1, tab2 = st.tabs(["Prompt Library", "Add Prompt"])

with tab2:
    st.header("Add a New Prompt")
    st.caption(
        "Use `{{ variable_name }}` syntax anywhere in the prompt body to create a "
        "Jinja2 template variable. Variables will be auto-detected on the library tab."
    )
    with st.form("add_prompt_form"):
        title = st.text_input("Title", max_chars=80)
        prompt = st.text_area(
            "Prompt / Template", 
            height=160,
            placeholder="Write a haiku about {{ topic }} in the style of {{ style }}.",
        )
        tags = st.text_input(
            "Tags (comma-separated)", 
            help="For example: chatgpt, code, python",
        )
        description = st.text_area("Short description", height=60)
        submitted = st.form_submit_button("Add Prompt", use_container_width=True)

    if submitted and title and prompt:
        add_prompt(title, prompt, tags, description)
        st.success(f"Prompt **{title}** added")
    elif submitted:
        st.warning("Title and prompt body are required.")


# Prompt Library
with tab1:
    st.header("Prompt Library")

    col_search, col_tag = st.columns([4, 2])
    with col_search:
        search = st.text_input("Search (title / content / description)", key="search")
    with col_tag:
        all_tags = get_unique_tags()
        tag_filter = st.selectbox("Filter by tag", [""] + all_tags, index=0)

    prompts = get_prompts(search, tag_filter)

    if prompts:
        for row in prompts:

            title = row["title"] or ""
            tags = row["tags"] or ""
            body = row["prompt"]

            variables = extract_variables(body)
            var_badge = f"  `{len(variables)} var{'s' if len(variables) != 1 else ''}`" if variables else ""

            expander_label = f"{title}{var_badge}  {'🔖' + tags if tags else ''}"

            with st.expander(expander_label):
                st.code(body, language="markdown")
                st.markdown(f"**Description:** {row['description'] or '_No description_'}")
                st.markdown(f"**Tags:** {row['tags'] or '_None_'}")

                c1, c2 = st.columns([1, 5])
                with c1:
                    if st.button(f"🗑️ Delete", key=f"del_{row["id"]}"):
                        delete_prompt(row["id"])
                        st.rerun()
                
                # Jinja render section
                _render_section(row["id"], body)

    else:
        st.info("No prompts found (yet). Add your first one!")

st.markdown("---")
st.markdown(
    "Made with [Streamlit](https://streamlit.io/) • "
    "[Jinja2](https://jinja.palletsprojects.com/) • "
    "[Code on GitHub](https://github.com/jpawebb/prompt-vault)"
)