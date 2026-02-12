Problem Overview
Bose Professional speaker datasheets contain technical specifications (e.g., frequency response, SPL,
coverage, impedance, power handling), mechanical details (dimensions, weight, enclosure), and
compliance/installation information. We need an LLM-backed, retrieval-grounded Q&A system
that can precisely answer questions from these datasheets and expose its capabilities through an
MCP (Model Context Protocol) Server for a client to query product details.
Key requirement: Accuracy over breadth. The model must not be hallucinated. When sufficient
evidence is not present in the indexed datasheets, the answer must strictly be: “Sorry, I do not
have the capability to answer that”
Primary Objectives
• Document ingestion & normalization
o Collect representative Bose Pro speaker datasheets (PDF/HTML).
o Extract tables and fields into a normalized schema (model, version/date, frequency
response, SPL, coverage, impedance, sensitivity, power handling, taps, dimensions,
weight, IP rating, connectors, certifications, accessories).
o Preserve provenance metadata (document title, version, page numbers).
• RAG pipeline for grounded answers
o Implement a retrieval-augmented generation pipeline with chunking, embeddings,
and vector search.
o Ensure answers are strictly grounded in retrieved passages and always include
citations (document/page/section).
o If evidence is insufficient or ambiguous, output the mandated fallback message (no
paraphrase).
• MCP Server exposure
o Expose the Q&A via an MCP-compliant server with clear tools/resources:
▪ ask(question: string) → { answer, citations[], confidence }
▪ get_models() → [model_name]
▪ get_specs(model: string) → structured specs object
▪ compare(models: string[]) → normalized, side-by-side key specs + citations
▪ sources() → available documents, versions, last-updated
▪ health() / version() for ops visibility
• Quality, guardrails, and reliability
o Strong hallucination defenses (strict answer schema, retrieval checks, abstention
policy).
o Confidence scoring (Low/Medium/High) based on retrieval strength and citation
alignment.
o Clear error codes (e.g., NO_EVIDENCE, AMBIGUOUS_QUERY, INVALID_MODEL).
• Ops, tests, and documentation
o Containerized deployment (Docker), logs, basic metrics, CI for tests & linting.
o Comprehensive documentation: README, architecture, MCP API, user guide.
Success Criteria (Go/No-go)
• Grounded accuracy: ≥ 95% exact-match correctness on a curated set of Qs.
• Citations: ≥ 95% of answers include correct source references (doc+page/section).
• Zero hallucination policy: 100% of unsupported questions must return the fallback phrase.
• Latency (P95): ≤ 1.5s retrieval, ≤ 4s end-to-end on provided hardware.
• Reliability: 99% success rate on MCP endpoint calls in integration tests.
Getting Started
• Confirm tech stack, embedding model, LLM and vector DB
• Collect initial datasheets; design normalized spec schema with units.
• Implement parsing + provenance + page mapping; build initial index.
• Implement RAG v1 with citation-enforced template and fallback phrase.
• Stand up MCP server; add tools; write integration tests.
• Build evaluation set; baseline metrics; iterate for accuracy & latency.
• Deliver hosted service with design documents & CI pipeline.