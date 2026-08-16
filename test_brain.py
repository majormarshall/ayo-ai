import ollama, json

models = [m.model for m in ollama.list().models]
print("Ollama models available:", models)

if models:
    result = ollama.chat(
        model=models[0],
        messages=[{"role": "user", "content": "Say hello as Ayo AI. Return JSON only: {\"text\":\"...\",\"action\":null,\"params\":{}}"}],
        format="json"
    )
    print("Brain test OK:", result.message.content[:200])
else:
    print("No models. Run: ollama pull llama3.2")
