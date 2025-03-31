from fastapi import FastAPI
from haystack import Pipeline, Document
from haystack.components.builders import PromptBuilder
from haystack.components.embedders import OpenAITextEmbedder
from haystack.components.generators import OpenAIGenerator
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.document_stores.in_memory import InMemoryDocumentStore
from apify_client import ApifyClient
import os

app = FastAPI()

# Apify Actor ID for web crawling
APIFY_ACTOR_ID = "apify/website-content-crawler"
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")  # Ensure this is set in your environment
START_URL = "https://cpf.gov.sg/member/growing-your-savings/saving-more-with-cpf/"

# Initialize document store
document_store = InMemoryDocumentStore()

# Define LLM components
text_embedder = OpenAITextEmbedder()
retriever = InMemoryEmbeddingRetriever(document_store)
generator = OpenAIGenerator(model="gpt-4o-mini")

# Define prompt template
template = """
Given the following information, answer the question.

Context:
{% for document in documents %}
    {{ document.content }}
{% endfor %}

Question: {{question}}
Answer:
"""
prompt_builder = PromptBuilder(template=template)

# Create pipeline
pipeline = Pipeline()
pipeline.add_component("embedder", text_embedder)
pipeline.add_component("retriever", retriever)
pipeline.add_component("prompt_builder", prompt_builder)
pipeline.add_component("llm", generator)

# Connect components
pipeline.connect("embedder.embedding", "retriever.query_embedding")
pipeline.connect("retriever", "prompt_builder.documents")
pipeline.connect("prompt_builder", "llm")

# Function to fetch website content using Apify
def fetch_web_data():
    print("Starting web crawling with Apify...")
    client = ApifyClient(APIFY_API_TOKEN)
    actor_call = client.actor(APIFY_ACTOR_ID).call(run_input={
        "startUrls": [{"url": START_URL}],
        "maxCrawlPages": 5
    })

    dataset_items = client.dataset(actor_call["defaultDatasetId"]).list_items().items
    documents = [Document(content=item["text"], meta={"url": item["url"]}) for item in dataset_items]

    # Embed documents and store them
    docs_with_embeddings = text_embedder.run(documents)
    document_store.write_documents(docs_with_embeddings["documents"])
    print("Crawled data stored in document store.")

# Run web crawler when FastAPI starts
@app.on_event("startup")
async def startup_event():
    fetch_web_data()

@app.post("/ask")
def ask_question(question: str):
    result = pipeline.run({"embedder": {"text": question}, "prompt_builder": {"question": question}})
    return {"answer": result["llm"]["replies"][0]}
