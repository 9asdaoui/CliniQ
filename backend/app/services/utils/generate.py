import requests
from .prompt import llm_prompt
import mlflow


@mlflow.trace
def ollama_generate(
    prompt: str,
    ollama_url: str,
    model: str,
    temperature: int = 0.2,
    max_tokens: int = 256,
) -> str:
    response = requests.post(
        ollama_url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["response"]


@mlflow.trace
def llm_generate_answer(
    query: str,
    ollama_url: str,
    model: str,
    chunks: list,
    temperature: int = 0.2,
    max_tokens: int = 256,
) -> str:

    # Build context from chunks
    context = "\n\n".join(
        [f"{c['chapter']} | {c['section']}\n{c['text']}" for c in chunks]
    )

    prompt = llm_prompt(query, context)
    answer = ollama_generate(prompt, ollama_url, model, temperature, max_tokens)

    return answer
