import sqlite3
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from deepeval.models import OllamaModel

from .utils.extract import extract_content_from_uploaded_pdf
from .utils.chunk import chunk_markdown_documents
from .utils.store import store_chunks, store_parent_chunks

from .utils.retrieve import hierarchical_retriever
from .utils.rerank import chunks_reranker
from .utils.generate import llm_generate_answer

from utils.mlflow_evaluation import (
    start_run,
    log_params,
    log_dict,
    log_text,
    log_metrics,
)
from .utils.prompt import llm_prompt
from .utils.evaluate import evaluate_rag
from .utils.queries import eval_queries

from random import choice
from models.query import QueryModel


class RAGService:

    def __init__(self, emb_model):
        self.client = QdrantClient(url="http://qdrant:6333")
        self.conn = sqlite3.connect("/app/rag_chunks.db")
        self.ollama_url = "http://host.docker.internal:11434/api/generate"
        self.cursor = self.conn.cursor()
        self.embedder = SentenceTransformer(emb_model)
        self.ollama_model = OllamaModel(
            model="llama2:latest", base_url="http://host.docker.internal:11434"
        )

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS parents (
                id TEXT PRIMARY KEY,
                text TEXT,
                chapter TEXT,
                section TEXT,
                categorie TEXT,
                page INTEGER
            )
        """)
        self.conn.commit()

    def chunk_store_pipeline(self, uploaded_file, emb_model, emb_size, normalize=True):

        documents = extract_content_from_uploaded_pdf(uploaded_file)

        chunks = chunk_markdown_documents(documents, uploaded_file.filename)

        store_parent_chunks(self.cursor, self.conn, chunks[0])

        store_chunks(self.client, chunks[1], emb_model, emb_size, normalize)

        return chunks

    def retrieve_generate_pipeline(
        self,
        db,
        query,
        user_id,
        emb_model,
        cross_model,
        llm_model,
        retrieval_top_k=20,
        rerank_top_k=5,
        rerank_min_score=0.3,
        normalise=True,
        temperature=0.2,
        max_tokens=150,
        op=False,
    ):

        chunks = hierarchical_retriever(
            self.client,
            self.cursor,
            query,
            self.embedder,
            retrieval_top_k,
            normalise,
        )

        reranked_chunks = chunks_reranker(
            query, chunks, cross_model, rerank_top_k, rerank_min_score
        )

        answer = llm_generate_answer(
            query, self.ollama_url, llm_model, reranked_chunks, temperature, max_tokens
        )

        if op:
            QueryModel(db).create_query(query, answer, user_id)

        return answer

    def evaluate_chunking_pipeline(
        self, uploaded_file, emb_model, emb_size, normalize=True
    ):

        with start_run("RAG-Chunking"):

            log_params(
                {
                    "Uploaded file name": uploaded_file.filename,
                    "Embedding Model": emb_model,
                    "Embedding Size": emb_size,
                    "Embedding Normalize": normalize,
                }
            )

            documents = extract_content_from_uploaded_pdf(uploaded_file)

            chunks = chunk_markdown_documents(documents, uploaded_file.filename)

            log_params(
                {
                    "Parser": "LlamaParse",
                    "Parsing Format": "Markdown",
                    "Pages Parsed": len(documents),
                    "Chunking Type": "hierarchical chunking",
                    "Parent Chunks Count": len(chunks[0]),
                    "Child Chunks Count": len(chunks[1]),
                    "Vector DB": "Qdrant",
                }
            )

            return {"chunks": chunks}

    def evaluate_retrieval_generation_pipeline(
        self,
        emb_model,
        cross_model,
        llm_model,
        retrieval_top_k=20,
        rerank_top_k=5,
        rerank_min_score=0.3,
        normalise=True,
        temperature=0.2,
        max_tokens=256,
    ):

        chosen_item = choice(eval_queries)
        query = chosen_item["query"]
        expected_answer = chosen_item["answer"]

        with start_run("RAG-Generation"):

            log_params(
                {
                    "Embedding Model": emb_model,
                    "Retrieval Top K": retrieval_top_k,
                    "Cross Encoder": cross_model,
                    "Rerank Top K": rerank_top_k,
                    "Min Rerank Score": rerank_min_score,
                    "LLM Model": llm_model,
                    "LLM Temperature": temperature,
                    "LLM Max Tokens": max_tokens,
                }
            )

            chunks = hierarchical_retriever(
                self.client,
                self.cursor,
                query,
                self.embedder,
                retrieval_top_k,
                normalise,
            )

            reranked_chunks = chunks_reranker(
                query, chunks, cross_model, rerank_top_k, rerank_min_score
            )

            answer = llm_generate_answer(
                query,
                self.ollama_url,
                llm_model,
                reranked_chunks,
                temperature,
                max_tokens,
            )

            metrics = evaluate_rag(
                query, self.ollama_model, reranked_chunks, answer, expected_answer
            )

            log_params(
                {
                    "Number of retrived chunks": len(chunks),
                    "Number of reranked chunks": len(reranked_chunks),
                }
            )

            log_text(llm_prompt("[Query]", "[Context]"), "prompt_template.txt")

            log_dict(
                {
                    "Query": query,
                    "Answer": answer,
                    "Retrieved Chunks": chunks,
                    "Reranked Chunks": reranked_chunks,
                },
                "generation_details.json",
            )

            log_metrics(metrics)

            return {"query": query, "answer": answer, "metrics": metrics}

    def get_chunks(
        self,
        query,
        emb_model,
        cross_model,
        retrieval_top_k=20,
        rerank_top_k=5,
        rerank_min_score=0.3,
        normalise=True,
    ):

        chunks = hierarchical_retriever(
            self.client,
            self.cursor,
            query,
            self.embedder,
            retrieval_top_k,
            normalise,
        )

        reranked_chunks = chunks_reranker(
            query, chunks, cross_model, rerank_top_k, rerank_min_score
        )

        return {"chunks": chunks, "reranked_chunks": reranked_chunks}

    def get_queries(self, db, user_id):
        queries = QueryModel(db).get_user_queries(user_id)

        return queries
