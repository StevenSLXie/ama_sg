from pathlib import Path
from typing import List
from haystack import Pipeline
from hayhooks import BasePipelineWrapper

urls = "https://cpf.gov.sg/member/growing-your-savings/saving-more-with-cpf/"

import os
os.environ["APIFY_API_TOKEN"] = 'apify_api_cRxwEbM1gMMshb1cpp2x1hBiTziYr81C8Olk'
os.environ["APIFY_TOKEN"] = 'apify_api_cRxwEbM1gMMshb1cpp2x1hBiTziYr81C8Olk'
os.environ['OPENAI_API_KEY'] = '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'

class PipelineWrapper(BasePipelineWrapper):
    def build_pipeline(self):
        from haystack import Pipeline
        from haystack.components.builders import PromptBuilder
        from haystack.components.embedders import OpenAITextEmbedder
        from haystack.components.generators import OpenAIGenerator
        from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever

        text_embedder = OpenAITextEmbedder()
        retriever = InMemoryEmbeddingRetriever(self.document_store)
        generator = OpenAIGenerator(model="gpt-4o-mini")

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

        # Add components to your pipeline
        print("Initializing pipeline...")
        pipe = Pipeline()
        pipe.add_component("embedder", text_embedder)
        pipe.add_component("retriever", retriever)
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", generator)

        # Now, connect the components to each other
        pipe.connect("embedder.embedding", "retriever.query_embedding")
        pipe.connect("retriever", "prompt_builder.documents")
        pipe.connect("prompt_builder", "llm")
        self.pipeline = pipe

    def setup(self) -> None:
        actor_id = "apify/website-content-crawler"
        run_input = {
            "maxCrawlPages": 5,  # limit the number of pages to crawl
            "startUrls": [{"url": "https://cpf.gov.sg/member/growing-your-savings/saving-more-with-cpf/"}],
        }

        from haystack import Document

        def dataset_mapping_function(dataset_item: dict) -> Document:
            return Document(content=dataset_item.get("text"), meta={"url": dataset_item.get("url")})

        from apify_haystack import ApifyDatasetFromActorCall

        apify_dataset_loader = ApifyDatasetFromActorCall(
            actor_id=actor_id,
            run_input=run_input,
            dataset_mapping_function=dataset_mapping_function,
        )
        docs = apify_dataset_loader.run()

        from haystack.components.embedders import OpenAIDocumentEmbedder
        from haystack.document_stores.in_memory import InMemoryDocumentStore

        self.document_store = InMemoryDocumentStore()
        docs_embedder = OpenAIDocumentEmbedder()
        embeddings = docs_embedder.run(docs.get("documents"))
        self.document_store.write_documents(embeddings["documents"])
        self.build_pipeline()

    def run_api(self, question: str) -> str:
        result = self.pipeline.run({"embedder": {"text": question}, "prompt_builder": {"question": question}})
        return result["llm"]["replies"][0]


"""
curl -X POST "http://localhost:1416/my_pipeline/run" \
     -H "Content-Type: application/json" \
     -d '{
          "fetcher": {"urls": ["https://example.com"]},
          "prompt": {"question": "how much can I top up to SA account?"}
         }'

"""