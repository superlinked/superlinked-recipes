import uuid
import json

import streamlit as st

from app.superlinked import SuperlinkedClient

from app.utils.logging import setup_logging
from app.utils.utils import (
    load_image_urls,
    get_kick_start_options,
    flatten_response,
    clean_knn_params,
)
from app.frontend.components import format_header, format_amenities, format_filters

from app.config import settings


logger = setup_logging()

st.set_page_config(
    page_title="Superlinked hotel search demo",
    initial_sidebar_state="expanded",
    layout="wide",
)


@st.cache_resource
def load_resources():
    sl_client = SuperlinkedClient()
    id_to_image_url = load_image_urls(settings.path_dataset)
    return sl_client, id_to_image_url


if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


sl_client, id_to_image_url = load_resources()

# - - - Page header - - -

st.title("Hotels search")


st.markdown("**🚀 Kick start your discovery**")

kick_start_options = get_kick_start_options()

cols = st.columns(len(kick_start_options))
for option, col in zip(kick_start_options, cols):
    if col.button(option, use_container_width=True):
        st.session_state.text = option

col_query_text, col_limit = st.columns([0.85, 0.15])
with col_query_text:
    st.write("🧠 **Natural Language Interface**")
    text = st.text_input(
        label="🧠 **Natural Language Interface**",
        value=kick_start_options[0],
        placeholder="What are you searching for?",
        key="text",
        label_visibility="collapsed",
    )

with col_limit:
    st.write("**Limit**")
    limit = st.number_input(
        "**Limit**", min_value=1, value=5, label_visibility="collapsed"
    )


st.info(
    (
        "Learn more about how Superlinked handles natural language queries in [our github]"
        "(https://github.com/superlinked/superlinked/blob/main/notebook/feature/natural_language_querying.ipynb)"
        "!"
    ),
    icon="💡",
)


# # - - - Query - - -

with st.sidebar:
    st.markdown("### Query params")

params = {"natural_query": text, "limit": limit}
response = sl_client.query("hotel", params)
response_flattened = flatten_response(response)
knn_params = response["metadata"]["search_params"]

with st.sidebar:
    knn_params_clean = clean_knn_params(knn_params)
    updated_query = st.text_area(
        label="Query params",
        value=json.dumps(knn_params_clean, indent=2),
        height=700,
        label_visibility="collapsed",
    )

# # - - - Logging - - -

log_object = {
    "session_id": st.session_state.session_id,
    "params": knn_params,
    "natural_query": text,
    "response_ids": [x["id"] for x in response_flattened],
}
logger.info(log_object)


# # - - - Rendering results - - -


filters_formatted = format_filters(knn_params)

st.markdown("---")


if filters_formatted:
    st.markdown("##### Applied filters")
    st.markdown(filters_formatted)
else:
    st.markdown("##### No filters applied")


if len(response_flattened) > 0:

    for item in response_flattened:
        with st.container(border=True):

            col_main, col_amenities = st.columns([0.5, 0.5])

            with col_main:
                col_image, col_text = st.columns([0.25, 0.75])
                with col_image:
                    url = id_to_image_url[item["id"]]
                    try:
                        st.image(url)
                    except Exception as e:
                        st.write("🏙️ No image available")
                with col_text:
                    st.markdown(format_header(item))

                description = item["description"]
                if len(description.split()) < 3:
                    description = "No description available"
                st.markdown("*" + description + "*")

            with col_amenities:
                st.markdown(format_amenities(item, knn_params))

else:
    st.info("No results found. Please try another query.", icon="🔎")
