# Task 10: Chat Frontend (Gradio)

## Status: Done (per PLAN.md)

## Summary

Implement the Gradio-based chat interface that allows users to select a recipient and query their documents through the RAG system.

## Files to Create

- `chat/app.py`

## Details

### Architecture

A Gradio web app that provides:
1. A **recipient selector** dropdown — user picks who they are.
2. A **chat interface** — user asks questions about their documents.
3. **RAG-powered responses** — queries go through DeepFellow's `/v1/responses` endpoint, filtered by recipient.
4. **Source citations** — responses include references to source documents.

### Key Implementation Points

1. **Recipient dropdown**:
   - Populate from `config.yaml` recipients list.
   - Include "All" or "Common" option to search across all documents.
   - Selection filters which documents the RAG searches.

2. **Chat interface**:
   - Use `gr.ChatInterface` or `gr.Chatbot` component.
   - Maintain conversation history per session.
   - Support follow-up questions (context-aware).

3. **RAG query via `/v1/responses` endpoint**:
   - This is DeepFellow's RAG-enabled endpoint.
   - Sends the user's query + recipient filter.
   - Returns an LLM response grounded in retrieved documents.
   - Different from standard `/v1/chat/completions` — it includes RAG retrieval.

4. **Source citations**:
   - Display which documents were used to answer.
   - Show document title, date, category.
   - Link to the output markdown file if possible.

5. **Startup**:
   - Entry point: `uv run python chat/app.py`
   - Loads config on startup.
   - Launches Gradio server (default port 7860).

### Gradio App Structure

```python
import gradio as gr

def create_app(config):
    recipient_names = [r.name for r in config.recipients] + ["All"]

    with gr.Blocks(title="Document Chat") as app:
        gr.Markdown("# Document Chat")

        recipient = gr.Dropdown(
            choices=recipient_names,
            value="All",
            label="Select Recipient",
        )

        chatbot = gr.Chatbot()
        msg = gr.Textbox(placeholder="Ask about your documents...")

        async def respond(message, history, selected_recipient):
            # Query RAG with recipient filter
            response = await query_rag(
                query=message,
                recipient=selected_recipient if selected_recipient != "All" else None,
                config=config,
            )
            # Format response with citations
            answer = format_response(response)
            history.append((message, answer))
            return "", history

        msg.submit(respond, [msg, chatbot, recipient], [msg, chatbot])

    return app
```

### `/v1/responses` API Call

```python
import httpx

async def query_rag(query: str, recipient: str | None, config: Config):
    url = f"{config.deepfellow.base_url}{config.deepfellow.responses_endpoint}"

    payload = {
        "model": config.deepfellow.llm_model,
        "input": query,
        "tools": [{
            "type": "file_search",
            "vector_store_ids": [config.deepfellow.rag_collection],
            # Filter by recipient if specified
        }],
    }

    # Add recipient filter if specified
    if recipient:
        payload["metadata_filter"] = {"recipient": recipient}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {config.deepfellow.api_key}"},
        )
        return response.json()
```

### Citation Formatting

```python
def format_response(rag_response) -> str:
    """Format RAG response with source citations."""
    answer = rag_response["output"]
    sources = rag_response.get("sources", [])

    if sources:
        answer += "\n\n---\n**Sources:**\n"
        for source in sources:
            answer += f"- {source['title']} ({source['date']})\n"

    return answer
```

### UI Considerations

- Clean, minimal interface.
- Recipient selector prominently placed.
- Chat takes up most of the screen.
- Show loading indicator during RAG queries.
- Error messages for failed queries.
- Mobile-friendly (Gradio handles this by default).

## Acceptance Criteria

- [ ] Gradio app launches on `uv run python chat/app.py`
- [ ] Recipient dropdown populated from config
- [ ] Chat queries go through `/v1/responses` RAG endpoint
- [ ] Responses are filtered by selected recipient
- [ ] Source citations displayed with responses
- [ ] Conversation history maintained per session
- [ ] Error handling for API failures
- [ ] Clean, usable interface

## Dependencies

- Task 01 (Project Setup) — needs `gradio` library
- Task 02 (Configuration) — needs recipients, DeepFellow settings
- Task 08 (RAG Indexer) — documents must be indexed first
