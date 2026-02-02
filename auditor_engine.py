import json
from parser import RedHatParser

class RedHatAuditor:
    def __init__(self, model_name="llama3"):
        self.model = model_name
        # The system prompt is the "Policy" the agent must follow
        self.system_prompt = """
        You are the Red Hat Editorial Auditor. 
        You have access to MCP tools to look up official Red Hat Style guides.
        
        PROCEDURE:
        1. For every chunk of text, check for:
           - Sentence Case (Headings)
           - Acronym definitions (First use)
           - Filler words (from brevity_rules.md)
           - Conversational tone (The 5 Cs)
        2. Use the 'search_style_guides' tool whenever you are unsure.
        3. Output your findings in a structured format.
        """

    def audit_document(self, doc_path):
        parser = RedHatParser(doc_path)
        chunks = parser.get_structured_content()
        full_report = []

        print(f"Starting audit for {doc_path}...")

        for chunk in chunks:
            # We pass the 'type' (heading/body) so the AI knows which rules apply
            prompt = f"Type: {chunk['type']}\nText: {chunk['text']}"
            
            # This is a conceptual call to the LLM + MCP Tool
            # In reality, you'd use something like: agent.invoke(prompt)
            response = self.call_agent_with_mcp(prompt)
            
            full_report.append({
                "original": chunk['text'],
                "type": chunk['type'],
                "audit": response
            })

        return full_report

    def call_agent_with_mcp(self, prompt):
        # This is where the LLM decides to call search_style_guides("acronyms")
        # if it sees an acronym it doesn't recognize.
        pass 

# --- Execution ---
if __name__ == "__main__":
    auditor = RedHatAuditor()
    report = auditor.audit_document("internal_draft.docx")
    
    # Save the report for your Streamlit UI to display
    with open("audit_results.json", "w") as f:
        json.dump(report, f, indent=4)
