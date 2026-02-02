import json
import asyncio
import sys
from parser import RedHatParser
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

class RedHatAuditor:
    def __init__(self, model_name="llama3.1"):
        # Model configured for JSON mode to ensure schema reliability
        self.llm = ChatOllama(
            model=model_name,
            temperature=0,
            format="json" 
        )
        
        self.system_prompt = (
            "You are the Red Hat Editorial Auditor. Your goal is to make technical content "
            "Helpful, Brave, and Authentic. For every piece of text provided:\n"
            "1. Use your tools to search for Red Hat style rules.\n"
            "2. Identify violations (filler words, corporate jargon, passive voice).\n"
            "3. Provide constructive feedback.\n"
            "4. Provide a 'proposed_text' rewrite.\n\n"
            "CRITICAL: You must output ONLY a JSON object with these keys: "
            "{'feedback': '...', 'proposed_text': '...'}"
        )

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
        parser = RedHatParser(doc_path)
        chunks = parser.get_structured_content()
        report = []

        for i, chunk in enumerate(chunks):
            # If a callback was provided, notify the UI we are starting a new chunk
            if status_callback:
                await status_callback(f"Analyzing chunk {i+1} of {len(chunks)}...")

            query = {"messages": [("human", f"Audit this {chunk['type']}: {chunk['text']}")]}
            
            # We use the stream or events API to catch tool calls in real-time
            result = await self.agent.ainvoke(query)
            
            paper_trail = []
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        call_info = f"🔍 Searching: {tc['args'].get('query', 'Style Rules')}"
                        paper_trail.append(call_info)
                        # Notify UI of the specific tool call
                        if status_callback:
                            await status_callback(call_info)
                            await asyncio.sleep(0.5) # Brief pause so the user can read i
           # 2. Parse the Final Response
            raw_content = result["messages"][-1].content
            try:
                # Remove markdown wrapping if present
                clean_json = raw_content.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_json)
                feedback = parsed.get("feedback", "No specific violations found.")
                proposed = parsed.get("proposed_text", chunk['text'])
            except Exception:
                feedback = "Check style manually (JSON parsing failed)."
                proposed = chunk['text']

            report.append({
                "text": chunk['text'],
                "type": chunk['type'],
                "feedback": feedback,
                "proposed_text": proposed,
                "paper_trail": paper_trail
            })
            
        return report

    def calculate_metrics(self, report):
        """Generates scores for the 5 Cs based on keywords in feedback."""
        metrics = {"Clear": 100, "Concise": 100, "Conversational": 100, "Credible": 100, "Compelling": 100}
        for item in report:
            f = item['feedback'].lower()
            if any(w in f for w in ["wordy", "brevity", "filler"]): metrics["Concise"] -= 10
            if any(w in f for w in ["jargon", "acronym", "unclear"]): metrics["Clear"] -= 10
            if any(w in f for w in ["formal", "passive", "corporate"]): metrics["Conversational"] -= 10
        return {k: max(v, 0) for k, v in metrics.items()}
