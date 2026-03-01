# agentops-python

Minimal SDK for AgentOps MVP.

## Install

```bash
cd agentops-python
pip install -e .
```

## Usage

```python
import agentops

agentops.init(api_key="dev-agentops-key", endpoint="http://localhost:8000")

@agentops.track(name="demo_agent")
def run_agent(question: str) -> str:
    with agentops.track_span("llm", "call_model", input_data={"messages": [{"role": "user", "content": question}]}) as span:
        answer = f"Echo: {question}"
        span.set_usage(prompt_tokens=12, completion_tokens=8)
        span.set_output({"text": answer})
    return answer

run_agent("hello")
agentops.shutdown()
```
