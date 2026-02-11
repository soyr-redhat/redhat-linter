import json
import asyncio
import sys
import re
from parser import RedHatParser
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

class RedHatAuditor:
    def __init__(self, model_name="llama3.1:8b", base_url="http://localhost:11434"):
        # Model configured for JSON mode to ensure schema reliability
        self.llm = ChatOllama(
            model=model_name,
            temperature=0,
            format="json",
            base_url=base_url
        )

        self.system_prompt = (
            "You are the W.I.P Editorial Auditor. Your goal is to make technical content "
            "Helpful, Brave, and Authentic.\n\n"
            "You will receive content with context (previous/next paragraphs) to maintain document coherence. "
            "Context is marked as [CONTEXT] and the current text to audit is marked as [CURRENT].\n\n"
            "For the [CURRENT] text:\n"
            "1. Use your tools to search for W.I.P style rules.\n"
            "2. Consider the surrounding context to maintain pronoun references, narrative flow, and logical coherence.\n"
            "3. Identify violations (filler words, corporate jargon, passive voice).\n"
            "4. Provide constructive feedback.\n"
            "5. Provide a 'proposed_text' rewrite for ONLY the [CURRENT] text.\n\n"
            "CRITICAL: You must output ONLY a JSON object with these keys: "
            "{'feedback': '...', 'proposed_text': '...'}\n"
            "The 'proposed_text' should ONLY contain the rewritten [CURRENT] text, not the context."
        )

        # Persistent agent/tools to avoid respawning MCP server on each audit
        self.mcp_client = None
        self.tools = None
        self.agent = None

    async def get_agent(self):
        """Lazy initialization of agent - only spawn MCP server once."""
        if self.agent is None:
            await self.initialize_tools()
        return self.agent

    async def initialize_tools(self):
        """Spawns the MCP server as a subprocess and links tools."""
        self.mcp_client = MultiServerMCPClient({
            "style_guide": {
                "command": sys.executable,
                "args": ["redhat_style_server.py"],
                "transport": "stdio"
            }
        })
        self.tools = await self.mcp_client.get_tools()
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt
        )

    async def run_audit(self, doc_path, status_callback=None):
        """
        Audits a document with optimizations:
        - Persistent agent initialization (avoid MCP respawning)
        - Robust JSON extraction with multiple fallback patterns
        - Deduplication of tool calls in paper trail
        - Unfinished sentence detection
        """
        # Ensure agent is initialized (lazy init)
        agent = await self.get_agent()

        parser = RedHatParser(doc_path)
        chunks = parser.get_structured_content()
        report = []

        for i, chunk in enumerate(chunks):
            # If a callback was provided, notify the UI we are starting a new chunk
            if status_callback:
                await status_callback(f"Analyzing chunk {i+1} of {len(chunks)}...")

            # Check for unfinished sentences
            sentence_warnings = self._check_sentence_completion(chunk['text'])

            # Build sliding window context for coherence
            context_parts = []

            # Add previous chunk as context (if exists)
            if i > 0:
                prev_chunk = chunks[i - 1]
                context_parts.append(f"[CONTEXT - Previous {prev_chunk['type']}]:\n{prev_chunk['text']}\n")

            # Add current chunk (the one being audited)
            context_parts.append(f"[CURRENT - {chunk['type']} to audit]:\n{chunk['text']}\n")

            # Add next chunk as context (if exists)
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                context_parts.append(f"[CONTEXT - Next {next_chunk['type']}]:\n{next_chunk['text']}")

            full_context = "\n".join(context_parts)
            query = {"messages": [("human", full_context)]}

            # Debug logging
            print(f"\n[AUDIT DEBUG] Processing chunk {i+1}/{len(chunks)}", file=sys.stderr)
            print(f"[AUDIT DEBUG] Chunk type: {chunk['type']}", file=sys.stderr)
            print(f"[AUDIT DEBUG] Context length: {len(full_context)} chars", file=sys.stderr)

            # We use the stream or events API to catch tool calls in real-time
            result = await agent.ainvoke(query)

            # Extract tool calls with deduplication
            paper_trail = []
            seen_queries = set()
            tool_call_count = 0
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_call_count += 1
                        query_text = tc['args'].get('query', 'Style Rules')
                        print(f"[AUDIT DEBUG] Tool call #{tool_call_count}: '{query_text}'", file=sys.stderr)

                        if query_text not in seen_queries:
                            seen_queries.add(query_text)
                            call_info = f"🔍 Searching: {query_text}"
                            paper_trail.append(call_info)
                            # Notify UI of the specific tool call
                            if status_callback:
                                await status_callback(call_info)
                                # Reduced delay for better performance
                                await asyncio.sleep(0.1)

            if tool_call_count == 0:
                print(f"[AUDIT DEBUG] ⚠️ WARNING: No tool calls made for this chunk!", file=sys.stderr)

            # Parse the Final Response with robust JSON extraction
            raw_content = result["messages"][-1].content
            parsed = self._extract_json(raw_content)

            feedback = parsed.get("feedback", "No specific violations found.")
            proposed = parsed.get("proposed_text", chunk['text'])

            # Validate that proposed text doesn't include context markers
            # (LLM should only return the current chunk, not context)
            proposed = self._strip_context_markers(proposed)

            # Sanity check: if proposed text is way longer than original, keep original
            # (indicates LLM may have included context)
            if len(proposed) > len(chunk['text']) * 2.5:
                feedback = f"{feedback}\n\n⚠️ AI response too long (may include context) - using original text."
                proposed = chunk['text']

            # Append sentence warnings to feedback
            if sentence_warnings:
                feedback = f"{feedback}\n\n⚠️ Sentence issues: {sentence_warnings}"

            report.append({
                "text": chunk['text'],
                "type": chunk['type'],
                "feedback": feedback,
                "proposed_text": proposed,
                "paper_trail": paper_trail,
                "sentence_warnings": sentence_warnings
            })

        return report

    def _strip_context_markers(self, text: str) -> str:
        """
        Remove any context markers that might have slipped into the proposed text.
        Returns cleaned text.
        """
        # Remove context markers
        cleaned = re.sub(r'\[CONTEXT[^\]]*\]:?\s*', '', text)
        cleaned = re.sub(r'\[CURRENT[^\]]*\]:?\s*', '', cleaned)

        # Remove any leading/trailing whitespace
        return cleaned.strip()

    def _extract_json(self, content: str) -> dict:
        """
        Robustly extract JSON from LLM response with multiple fallback strategies.
        Returns a dict with 'feedback' and 'proposed_text' keys.
        """
        # Try multiple extraction patterns
        patterns = [
            r'```json\s*(.*?)\s*```',  # Markdown code block
            r'```\s*(.*?)\s*```',      # Generic code block
            r'\{.*\}',                 # Raw JSON object
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

        # Fallback: return empty feedback
        return {
            "feedback": f"JSON parsing failed. Raw response: {content[:200]}...",
            "proposed_text": ""
        }

    def _check_sentence_completion(self, text: str) -> str:
        """
        Detects incomplete or unfinished sentences.
        Returns a warning string if issues are found, empty string otherwise.
        """
        if not text or not text.strip():
            return ""

        warnings = []

        # Check 1: Missing ending punctuation
        if not re.search(r'[.!?;:]$', text.strip()):
            warnings.append("Missing ending punctuation")

        # Check 2: Trailing conjunctions/prepositions (dangling clauses)
        dangling_words = r'\b(and|or|but|with|for|from|in|on|at|to|of|by|as|if|that|which|because)\s*$'
        if re.search(dangling_words, text.strip(), re.IGNORECASE):
            warnings.append("Sentence ends with conjunction/preposition")

        # Check 3: Unclosed quotes or parentheses
        open_parens = text.count('(') - text.count(')')
        open_quotes = text.count('"') % 2
        if open_parens != 0:
            warnings.append(f"Unclosed parentheses ({abs(open_parens)} unmatched)")
        if open_quotes != 0:
            warnings.append("Unclosed quotation marks")

        # Check 4: Sentence fragments (very short with no verb indicators)
        words = text.split()
        if len(words) < 3 and not re.search(r'[.!?]', text):
            warnings.append("Possible sentence fragment (too short)")

        # Check 5: Trailing ellipsis or incomplete thought markers
        if re.search(r'\.\.\.$', text.strip()):
            warnings.append("Sentence ends with ellipsis (incomplete thought)")

        return "; ".join(warnings)

    def calculate_metrics(self, report):
        """
        Generates scores for the 5 Cs based on keywords in feedback.
        Optimized with regex pre-compilation.
        """
        metrics = {"Clear": 100, "Concise": 100, "Conversational": 100, "Credible": 100, "Compelling": 100}

        # Pre-compile patterns for efficiency
        patterns = {
            "Concise": re.compile(r'\b(wordy|brevity|filler)\b', re.IGNORECASE),
            "Clear": re.compile(r'\b(jargon|acronym|unclear)\b', re.IGNORECASE),
            "Conversational": re.compile(r'\b(formal|passive|corporate)\b', re.IGNORECASE),
        }

        for item in report:
            feedback = item['feedback']
            for metric, pattern in patterns.items():
                if pattern.search(feedback):
                    metrics[metric] = max(0, metrics[metric] - 10)

        return metrics

