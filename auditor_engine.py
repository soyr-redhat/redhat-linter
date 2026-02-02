import json
from parser import RedHatParser
from langchain_ollama import ChatOllama # Use the Ollama-specific class
from langchain_classic.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent # Use the generic tool agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from mcp_server import search_style_guides 

style_tool = Tool(
    name="search_redhat_style",
    func=search_style_guides,
    description="Searches Red Hat style guides for acronyms, tone, and brevity rules."
)

class RedHatAuditor:
    def __init__(self):
        # Point this to your local Ollama instance (ensure 'ollama run llama3' works)
        self.llm = ChatOllama(
            model="llama3", 
            temperature=0,
            format="json" # Useful for forcing structured feedback
        ) 
        self.tools = [style_tool]
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the Red Hat Editorial Auditor. You must use the 'search_redhat_style' tool to check every sentence against official guides."),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 'create_tool_calling_agent' is the modern standard for models that support tools (like Llama 3)
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
    def run_audit(self, doc_path):
        parser = RedHatParser(doc_path)
        chunks = parser.get_structured_content()
        report = []

        for chunk in chunks:
            # We ask the agent to specifically look for violations in this chunk
            query = f"Audit this Red Hat {chunk['type']}: {chunk['text']}"
            result = self.executor.invoke({"input": query})
            
            report.append({
                "text": chunk['text'],
                "type": chunk['type'],
                "feedback": result["output"]
            })
            
        return report

    def calculate_metrics(self, report):
        # Simple logic: count the number of times "Brevity" or "Clarity" 
        # was mentioned in the feedback strings.
        metrics = {"Clear": 100, "Concise": 100, "Conversational": 100}
        for item in report:
            if "brevity" in item['feedback'].lower():
                metrics["Concise"] -= 5
            if "jargon" in item['feedback'].lower():
                metrics["Clear"] -= 5
        return metrics

if __name__ == "__main__":
    # Test run
    auditor = RedHatAuditor()
    results = auditor.run_audit("test_blog.docx")
    print(json.dumps(results, indent=2))
