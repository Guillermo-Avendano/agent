# files_for_memory

Place files here that should be loaded into the agent's vector memory at
startup.  The agent will use this knowledge as context when answering
questions.

## Supported formats

| Extension | Description          |
|-----------|----------------------|
| `.pdf`    | PDF documents        |
| `.txt`    | Plain text files     |
| `.md`     | Markdown files       |

## Example use cases

- Database schema documentation (ERD descriptions, data dictionaries)
- Business rules or glossaries
- Standard operating procedures
- Any reference material the agent should "know"

## How it works

1. On startup the agent reads every supported file in this directory.
2. Each file is split into overlapping text chunks (~1 000 characters).
3. Chunks are embedded with `nomic-embed-text` and stored in Qdrant.
4. When a user asks a question, the most relevant chunks are retrieved
   and injected into the agent's system prompt as context.
