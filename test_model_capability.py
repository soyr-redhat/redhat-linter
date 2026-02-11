#!/usr/bin/env python3
"""
Test the LLM's ability to follow instructions with the current system prompt.
This helps determine if the model is too weak or if there are other issues.
"""

import asyncio
from langchain_ollama import ChatOllama

async def test_model_reasoning(model_name="qwen2.5:3b"):
    print("\n" + "="*60)
    print(f"Testing Model: {model_name}")
    print("="*60)

    llm = ChatOllama(
        model=model_name,
        temperature=0,
        format="json",
        base_url="http://localhost:11434"
    )

    # Test 1: Can it follow JSON format instructions?
    print("\nTest 1: JSON Format Compliance")
    print("-" * 40)

    test_prompt = """
You must output ONLY a JSON object with these keys: {'feedback': '...', 'proposed_text': '...'}

Analyze this text:
"In order to install the software, you will need to complete the steps."

Identify filler words and suggest a more concise version.
"""

    try:
        result = await llm.ainvoke(test_prompt)
        print(f"Response:\n{result.content}\n")

        # Try to parse it
        import json
        parsed = json.loads(result.content)
        print(f"✓ Valid JSON with keys: {list(parsed.keys())}")

        if 'feedback' in parsed and 'proposed_text' in parsed:
            print(f"✓ Contains required keys")
            print(f"  Feedback: {parsed['feedback'][:100]}...")
            print(f"  Proposed: {parsed['proposed_text']}")
        else:
            print(f"✗ Missing required keys")

    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 2: Can it understand context?
    print("\n\nTest 2: Context Understanding")
    print("-" * 40)

    context_prompt = """
You must output ONLY a JSON object with these keys: {'feedback': '...', 'proposed_text': '...'}

Context is marked as [CONTEXT] and the current text to audit is marked as [CURRENT].

[CONTEXT - Previous paragraph]:
Red Hat OpenShift is a container platform.

[CURRENT - body to audit]:
It provides enterprise-grade security.

[CONTEXT - Next paragraph]:
These features include role-based access control.

Analyze the [CURRENT] text. Consider that "It" refers to OpenShift from the previous paragraph.
Provide feedback and a proposed rewrite for ONLY the [CURRENT] text.
"""

    try:
        result = await llm.ainvoke(context_prompt)
        print(f"Response:\n{result.content}\n")

        parsed = json.loads(result.content)
        print(f"✓ Valid JSON")
        print(f"  Feedback: {parsed.get('feedback', 'N/A')}")
        print(f"  Proposed: {parsed.get('proposed_text', 'N/A')}")

        # Check if it understood NOT to include context
        proposed = parsed.get('proposed_text', '')
        if '[CONTEXT]' in proposed or '[CURRENT]' in proposed:
            print(f"  ⚠️  WARNING: Proposed text includes context markers")
        if 'Red Hat OpenShift' in proposed or 'role-based' in proposed:
            print(f"  ⚠️  WARNING: Proposed text may include context paragraphs")

    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 3: Can it identify style issues?
    print("\n\nTest 3: Style Issue Identification")
    print("-" * 40)

    style_prompt = """
You must output ONLY a JSON object with these keys: {'feedback': '...', 'proposed_text': '...'}

Here are some style rules:
- Avoid "in order to" - use "to" instead
- Avoid passive voice
- Be concise and conversational

Analyze this text:
"In order to enable automation, Red Hat Ansible Automation Platform can be utilized by organizations."

Identify violations and provide a better version.
"""

    try:
        result = await llm.ainvoke(style_prompt)
        print(f"Response:\n{result.content}\n")

        parsed = json.loads(result.content)
        feedback = parsed.get('feedback', '')
        proposed = parsed.get('proposed_text', '')

        print(f"✓ Valid JSON")
        print(f"  Feedback: {feedback}")
        print(f"  Proposed: {proposed}")

        # Check if it caught the issues
        issues_caught = []
        if 'in order to' in feedback.lower() or 'order to' in feedback.lower():
            issues_caught.append("'in order to' filler")
        if 'passive' in feedback.lower():
            issues_caught.append("passive voice")
        if 'concise' in feedback.lower() or 'wordy' in feedback.lower():
            issues_caught.append("conciseness")

        if issues_caught:
            print(f"  ✓ Detected issues: {', '.join(issues_caught)}")
        else:
            print(f"  ⚠️  WARNING: May not have detected key issues")

        # Check if proposed is better
        if 'in order to' not in proposed.lower() and len(proposed) < 100:
            print(f"  ✓ Proposed text looks improved")
        else:
            print(f"  ⚠️  WARNING: Proposed text may not be improved")

    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n" + "="*60)
    print("MODEL CAPABILITY TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_model_reasoning())
