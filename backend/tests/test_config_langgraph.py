def test_langgraph_importable():
    import langgraph  # noqa
    from langchain_openai import ChatOpenAI  # noqa
    from langgraph.checkpoint.memory import MemorySaver  # noqa
