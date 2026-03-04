from sentence_transformers import SentenceTransformer
import mlflow


@mlflow.trace
def hierarchical_retriever(
    client,
    cursor,
    query: str,
    embedder: SentenceTransformer,
    retrieval_top_k: int = 20,
    normalise: bool = True,
):

    # Embed the query
    query_vector = embedder.encode(query, normalize_embeddings=normalise).tolist()

    # Retrieve top_k chunks from Qdrant
    hits = client.search(
        collection_name="manual_chunks",
        query_vector=query_vector,
        limit=retrieval_top_k,
        with_payload=True,
    )

    print(client.count("manual_chunks"))

    final_context = []
    seen_parents = set()

    for hit in hits:
        p_id = hit.payload["parent_id"]

        if p_id not in seen_parents:
            # Fetch Parent from SQLite
            cursor.execute(
                "SELECT text, chapter, section, categorie, page FROM parents WHERE id = ?",
                (p_id,),
            )
            parent_data = cursor.fetchone()

            if parent_data:
                text, chapter, section, categorie, page = parent_data
                final_context.append(
                    {
                        "text": text,
                        "categorie": categorie,
                        "chapter": chapter,
                        "section": section,
                        "page": page,
                        "score": hit.score,
                    }
                )
                seen_parents.add(p_id)

    return final_context
