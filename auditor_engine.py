from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
from parser import RedHatParser

class RedHatAuditor:
    def __init__(self, model_name="llama3.1"):
        self.llm = ChatOllama(
            model=model_name,
            temperature=0,
            validate_model_on_init=True,
            format="json" 
        )
        self.system_prompt = (
            "You are the Red Hat Editorial Auditor. Audit content for: "
            "Brevity, Tone, and Clarity. Output your final audit in JSON format."
        )

    async def initialize_tools(self):
        self.mcp_client = MultiServerMCPClient({
            "style_guide": {
                "command": "python",
                "args": ["redhat_style_server.py"], # Verify this filename exists!
                "transport": "stdio"
            }
        })
        self.tools = await self.mcp_client.get_tools()
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt
        )

    async def run_audit(self, doc_path):
        parser = RedHatParser(doc_path)
        chunks = parser.get_structured_content()
        report = []

        for chunk in chunks:
            # ReAct Loop via LangGraph
            query = {"messages": [("human", f"Audit this {chunk['type']}: {chunk['text']}")]}
            result = await self.agent.ainvoke(query)
            feedback = result["messages"][-1].content
            
            report.append({
                "text": chunk['text'],
                "type": chunk['type'],
                "feedback": feedback
            })
        return report

    # --- THE MISSING METHOD ---
    def calculate_metrics(self, report):
        metrics = {"Clear": 100, "Concise": 100, "Conversational": 100, "Credible": 100, "Compelling": 100}
        for item in report:
            f = str(item['feedback']).lower()
            if any(w in f for w in ["filler", "brevity", "long"]): metrics["Concise"] -= 5
            if any(w in f for w in ["jargon", "acronym"]): metrics["Clear"] -= 5
        return {k: max(v, 0) for k, v in metrics.items()}
