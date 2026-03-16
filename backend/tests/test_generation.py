from rag.generation import build_prompt


def test_build_prompt_includes_context():
    chunks = [{"filename": "test.md", "text": "Python is a language."}]
    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
    messages = build_prompt(chunks, "What is Python?", history)
    assert messages[0]["role"] == "system"
    assert any("Python is a language" in m["content"] for m in messages)
    assert any(m["content"] == "Hi" for m in messages)
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "What is Python?"


def test_build_prompt_empty_history():
    chunks = [{"filename": "a.md", "text": "Content"}]
    messages = build_prompt(chunks, "Question?", [])
    assert len(messages) == 3
    assert messages[-1]["content"] == "Question?"
