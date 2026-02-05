"""
Pipeline definitions for Job Agent.

Pipelines orchestrate the daily workflow:
1. Collect - Fetch data from sources
2. Normalize - Clean and deduplicate
3. Enrich - Add LLM summaries and embeddings
4. Rank - Score and select top candidates
5. Digest - Generate daily recommendations
"""
