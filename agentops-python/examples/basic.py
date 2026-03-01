from __future__ import annotations

import agentops


agentops.init(api_key="dev-agentops-key", endpoint="http://localhost:8000")


@agentops.track(name="basic_example")
def run() -> str:
    with agentops.track_span(
        "llm",
        "call_model",
        input_data={"messages": [{"role": "user", "content": "hello"}]},
        attributes={"provider": "openai", "model": "gpt-4.1-mini"},
    ) as span:
        answer = "Hello from mocked model"
        span.set_usage(prompt_tokens=12, completion_tokens=7, cost_usd=0.001)
        span.set_output({"text": answer})
        return answer


if __name__ == "__main__":
    print(run())
    agentops.shutdown()
