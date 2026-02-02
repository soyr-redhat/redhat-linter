import json
import os
from parser import RedHatParser
from langchain_ollama import ChatOllama 
# Use the modern agent executor logic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
# Ensure your MCP server file is named mcp_server.py
from mcp_server import search_style_guides 

style_tool = Tool(
    name="search_redhat_style",
    func=search_style_guides,
    description="Searches Red Hat style guides for acronyms, tone, and brevity rules."
)

class RedHatAuditor:
    def __init__(self, model_name="llama3.1"):
        # Local Ollama instance
        self.llm = ChatOllama(model=model_name, temperature=0) 
        self.tools = [style_tool]
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the Red Hat Editorial Auditor. You MUST use the 'search_redhat_style' tool to verify rules."),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Modern tool-calling agent
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    def run_audit(self, doc_path):
        parser = RedHatParser(doc_path)
        chunks = parser.get_structured_content()
        report = []

        for chunk in chunks:
            query = f"Audit this {chunk['type']}: {chunk['text']}"
            result = self.executor.invoke({"input": query})
            
            report.append({
                "text": chunk['text'],
                "type": chunk['type'],
                "feedback": result["output"]
            })
            
        return report

    def calculate_metrics(self, report):
        # Your scoring logic remains the same
        metrics = {"Clear": 100, "Concise": 100, "Conversational": 100, "Credible": 100, "Compelling": 100}
        for item in report:
            f = item['feedback'].lower()
            if "brevity" in f or "wordy" in f: metrics["Concise"] -= 5
            if "jargon" in f or "acronym" in f: metrics["Clear"] -= 5
        return metrics
