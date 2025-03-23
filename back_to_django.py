import streamlit as st
import webbrowser
import os

st.set_page_config(
    page_title="Returning to BisonBytes",
    page_icon="🏥",
)

# Title and message
st.title("Returning to BisonBytes")
st.markdown("""
### Redirecting you back to the main application...

If you are not redirected automatically, please [click here](/) to return to BisonBytes.
""")

# Auto-redirect script
redirect_url = "/"
st.markdown(
    f"""
    <script>
        window.parent.location.href = "{redirect_url}";
    </script>
    """,
    unsafe_allow_html=True
)

# Close this tab (may not work in all browsers due to security restrictions)
st.markdown(
    """
    <script>
        window.close();
    </script>
    """,
    unsafe_allow_html=True
) 