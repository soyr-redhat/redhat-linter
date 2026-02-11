#!/usr/bin/env python3
"""
Quick diagnostic script to test MCP server functionality.
Run this to verify:
1. Vector store initializes correctly
2. Style guides are loaded
3. Search is working
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser import load_guides
from redhat_style_server import initialize_vector_store, search_style_guides

def test_guides_loading():
    print("\n" + "="*60)
    print("TEST 1: Loading Style Guides")
    print("="*60)

    guides = load_guides("guides")
    print(f"✓ Loaded {len(guides)} guide(s)")

    for name, content in guides.items():
        preview = content[:200].replace('\n', ' ')
        print(f"  - {name}: {len(content)} chars")
        print(f"    Preview: {preview}...")

    return guides

def test_vector_store():
    print("\n" + "="*60)
    print("TEST 2: Vector Store Initialization")
    print("="*60)

    store = initialize_vector_store()
    if store is None:
        print("✗ FAILED: Vector store is None")
        return False

    print("✓ Vector store initialized successfully")

    # Check how many documents are in the store
    try:
        collection = store._collection
        count = collection.count()
        print(f"✓ Vector store contains {count} document chunks")
    except Exception as e:
        print(f"⚠️  Could not get document count: {e}")

    return True

def test_search():
    print("\n" + "="*60)
    print("TEST 3: Semantic Search")
    print("="*60)

    test_queries = [
        "passive voice",
        "acronyms",
        "filler words",
        "conversational tone",
        "5 Cs"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        result = search_style_guides(query, top_k=2)

        if "Error" in result or "No specific" in result:
            print(f"✗ FAILED: {result}")
        else:
            # Show first 150 chars of result
            preview = result[:300].replace('\n', ' ')
            print(f"✓ SUCCESS: {preview}...")

def main():
    print("\n" + "="*60)
    print("MCP SERVER DIAGNOSTIC TEST")
    print("="*60)

    try:
        test_guides_loading()
        if test_vector_store():
            test_search()
        else:
            print("\n✗ Skipping search test due to vector store failure")

        print("\n" + "="*60)
        print("DIAGNOSTIC COMPLETE")
        print("="*60)

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
