# EarWax
a local-first personal memory system designed to transform everyday recordings, transcripts, and spoken reflections into structured, reviewable knowledge entries for an Obsidian vault.

This project is intended for building a long-term “living memory” pipeline: a system that passively or semi-passively captures qualitative experience, interprets it with locally hosted language models, and converts useful material into durable Markdown notes. Rather than storing raw audio indefinitely, EarWax emphasizes selective memory distillation: extracting decisions, beliefs, preferences, events, questions, project updates, and reflections while preserving enough provenance for later review.

At its core, EarWax acts as an orchestration layer between local model servers and a local knowledge base. It reads transcript or audio-derived input files, segments them into manageable units, routes those segments through locally running models, validates structured outputs, and writes candidate notes into an Obsidian review workflow. The program is designed to keep the model’s role bounded: models propose interpretations, links, and summaries, while deterministic application code handles validation, file creation, database state, and vault safety.

The initial version of EarWax focuses on a batch-processing workflow. A user can record memos or conversations throughout the day, place resulting transcripts into an input queue, and run the program locally to generate candidate memory notes. These notes are not immediately treated as truth; they are staged for human review, where they can be confirmed, edited, rejected, or promoted into the permanent vault.

EarWax is built around several principles:

- Local-first operation: model inference, file processing, operational state, and Obsidian vault writes are intended to run on the user’s own machine.
- Obsidian compatibility: durable memories are stored as Markdown files with YAML frontmatter, links, tags, and review metadata.
- Human review before permanence: generated notes begin as candidates rather than authoritative memories.
- Structured interpretation: model outputs are validated against explicit schemas before they affect the vault.
- Provenance preservation: generated entries retain source metadata, evidence snippets, confidence values, and processing history where possible.
- Modular model routing: different local models can be assigned to transcription, extraction, linking, assessment, and response generation.
- Vault safety: the system avoids letting models directly edit arbitrary local files; application logic controls all filesystem operations.

The long-term goal of EarWax is to support a personal knowledge graph that grows from lived experience rather than manual note-taking alone. Over time, the system may support richer linking, contradiction detection, temporal belief tracking, review promotion workflows, semantic retrieval, and eventually a local agent capable of answering questions from the user’s accumulated knowledge base.
