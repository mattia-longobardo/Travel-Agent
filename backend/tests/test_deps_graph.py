def test_get_graph_returns_compiled(monkeypatch):
    import app.deps as deps
    monkeypatch.setattr(deps, "get_openai", lambda: object())
    deps.get_graph.cache_clear()
    g = deps.get_graph()
    assert hasattr(g, "ainvoke")
    deps.get_graph.cache_clear()
