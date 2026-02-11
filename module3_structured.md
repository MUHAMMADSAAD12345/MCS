# Module 3: Adaptive Reasoning Agent

**Reasoning depth adapts to network; answer quality stays constant**

## The Goal
Build a chatbot that adjusts how it reasons, not what it answers.

## The Twist
The agent senses network conditions and dynamically switches its reasoning depth:
- Slow connection → fast, efficient thinking
- Strong connection → deeper analysis
- Answer quality stays constant. Only the reasoning path changes.

## Custom Reasoning Engine
Design your own reasoning logic with multiple modes:
- Fast response (single-pass reasoning)
- Standard reasoning (step-based logic)
- Deep reasoning (multi-step analysis)
- Auto mode — selects strategy at runtime
- No reasoning-specialized models. No agent frameworks. Logic must be self-architected using standard models only.

## Tool-Oriented Agent
The agent must intelligently route between tools:
- Web search (shallow vs deep retrieval)
- Document creation (PDF, Word, Excel)
- Live datetime awareness
- RAG tool

## Native RAG Pipeline
Build a raw retrieval system:
- Accept user documents
- Parse, chunk, and vectorize content
- Answer using document context + tools + web data
- No RAG libraries. Full pipeline is yours.

## Bonus
- Voice input/output
- Token-level streaming responses
- Auth-based persistent sessions
- Clean and functional UI

## Why this challenge?
Real-world AI doesn't run on perfect networks. This tests whether your agent can stay smart under constraints — adapting its thinking without sacrificing outcomes.

## AI tools & APIs
Use free or paid AI tools. You can use the Mistral API key.

## Instructions & guidelines
- Use free or paid AI tools for your build.
- Include an architecture design in your submission (e.g. diagram or doc showing components, data flow, and tools).
- You can use the Mistral API — get your key at console.mistral.ai.
- For vector DB: use Quadrant or other vector databases.
- For tool calling / web: use free options such as Trivily, Firecrawl, DuckDuckGo, etc.

## Submission steps
1. Complete your project.
2. Push your code to GitHub.
3. Share the link of your public repo with us.

## Evaluation criteria
- Code quality will be checked.
- Failure scenarios — how your solution handles errors and edge cases.
- Architecture diagram — clear design showing components, data flow, and integration points.
- Design patterns — use of appropriate patterns and structure in your code.
