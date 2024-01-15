from dotenv import load_dotenv
import os
import streamlit as st
import openai
import time
import requests
import json

load_dotenv()

# Get the OpenAI API key from environment variables
openai.api_type = "azure"
# Azure OpenAI on your own data is only supported by the 2023-08-01-preview API version
openai.api_version = "2023-08-01-preview"

# Azure OpenAI setup
openai.api_base = os.getenv("OPENAI_ENDPOINT")  # Add your OpenAI endpoint here
openai.api_key = os.getenv("OPENAI_API_KEY")  # Add your OpenAI API key here
deployment_id = os.getenv("OPENAI_DEPLOYMENT")  # Add your deployment ID here

# Azure AI Search setup
search_endpoint = os.getenv("AI_SEARCH_ENDPOINT")
# Add your Azure AI Search endpoint here
search_key = os.getenv("AI_SEARCH_KEY")
# Add your Azure AI Search admin key here
search_index_name = os.getenv("AI_SEARCH_INDEX")
# Add your Azure AI Search index name here

# Azure Embedding model endpoint
embedding_endpoint = os.getenv("VECTOR_EMBEDDING_URI")
embedding_key = os.getenv("VECTOR_EMBEDDING_API_KEY")


topN = 5
strictness = 3
enforce_inscope = True
SYSTEM_PROMPT = """
You are an customer service bot designed to answer questions regarding Telstra. 
You must respond only from the data source provided. 
If you do not know the answer, you can say 'I don't know'. Always be polite and helpful.
You must be clear and concise in your answers. Answer in bullet point format where possible.
"""
role_information = SYSTEM_PROMPT


project_id = os.getenv("PROJECT_ID")
# Initialize feedback list
feedback = []


def setup_byod(deployment_id: str) -> None:
    """Sets up the OpenAI Python SDK to use your own data for the chat endpoint.

    :param deployment_id: The deployment ID for the model to use with your own data.

    To remove this configuration, simply set openai.requestssession to None.
    """

    class BringYourOwnDataAdapter(requests.adapters.HTTPAdapter):
        def send(self, request, **kwargs):
            request.url = f"{openai.api_base}/openai/deployments/{deployment_id}/extensions/chat/completions?api-version={openai.api_version}"
            return super().send(request, **kwargs)

    session = requests.Session()

    # Mount a custom adapter which will use the extensions endpoint for any call using the given `deployment_id`
    session.mount(
        prefix=f"{openai.api_base}/openai/deployments/{deployment_id}",
        adapter=BringYourOwnDataAdapter(),
    )

    openai.requestssession = session


setup_byod(deployment_id)


def get_new_chat_history():
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
    ]


def get_chat_response(
    chat_history: list,
    temperature: float,
    top_p: float,
    max_tokens: int,
    queryType: str,
):
    response = openai.ChatCompletion.create(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        messages=chat_history,
        deployment_id=deployment_id,
        dataSources=[  # camelCase is intentional, as this is the format the API expects
            {
                "type": "AzureCognitiveSearch",
                "parameters": {
                    "endpoint": search_endpoint,
                    "key": search_key,
                    "indexName": search_index_name,
                    "topNDocuments": topN,
                    "inScope": enforce_inscope,
                    "semanticConfiguration": "semantic-config-a0859498-994",
                    "roleInformation": role_information,
                    "strictness": strictness,
                    "queryType": queryType,
                    "embeddingEndpoint": embedding_endpoint,
                    "embeddingKey": embedding_key,
                    "fieldsMapping": {
                        "contentFields": [
                            "chunk",
                        ],
                        # "titleField" : "ADD TITLE TO INDEX",
                        # "urlField" : "ADD URL TO INDEX",
                        # "filepathField" : "ADD FILEPATH TO INDEX",
                    },
                },
            }
        ],
    )
    bot_response = response.choices[0]["message"]["content"]
    usage_data = json.dumps(response["usage"]).strip("{").strip("}")
    return bot_response, usage_data


def add_sliders(variable, display_name, min_value, max_value, default_value):
    if variable not in st.session_state:
        st.session_state[variable] = st.sidebar.slider(
            display_name, min_value, max_value, default_value
        )
    else:
        st.session_state[variable] = st.sidebar.slider(
            display_name, min_value, max_value, st.session_state[variable]
        )


def add_selectbox(variable, display_name, options):
    if variable not in st.session_state:
        st.session_state[variable] = st.sidebar.selectbox(display_name, options)
    else:
        st.session_state[variable] = st.sidebar.selectbox(
            display_name, options, index=options.index(st.session_state[variable])
        )


def main():
    st.title(f"{project_id} - Chat with LLM")

    #############################################################
    # SIDEBAR
    #############################################################
    # Add a slider to control the temperature parameter
    add_sliders("temperature", "Temperature", 0.0, 1.0, 0.7)
    add_sliders("top_p", "Top P", 0.0, 1.0, 0.95)
    add_sliders("max_tokens", "Max Tokens", 1, 5000, 500)
    add_selectbox(
        "queryType",
        "Query Type",
        ["vector", "simple", "semantic", "vectorSimpleHybrid", "vectorSemanticHybrid"],
    )
    # Display chat messages from history on app rerun
    if "messages" not in st.session_state:
        st.session_state.messages = get_new_chat_history()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Ask me something"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
        message_placeholder.markdown("Thinking...")
        start_time = time.time()
        full_response, usage_data = get_chat_response(
            chat_history=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            temperature=st.session_state.temperature,
            top_p=st.session_state.top_p,
            max_tokens=st.session_state.max_tokens,
            queryType=st.session_state.queryType,
        )
        end_time = time.time()
        execution_time = end_time - start_time
        message_placeholder.markdown(full_response)
        with st.chat_message("ai"):
            usage_placeholder = st.empty()

        usage_placeholder.markdown(
            f'<sub><span style="color: lightgrey;font-size: 14px;">Response generated in {execution_time:.2f} seconds. {usage_data}</sub>',
            unsafe_allow_html=True,
        )
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response}
        )


if __name__ == "__main__":
    main()
