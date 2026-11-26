"""Respostas simuladas para testar o cliente, sem carregar pesos."""
import httpx
import pytest

from app.ai.cliente import ErroInferencia, ClienteIaLocal, lerConfiguracao


@pytest.mark.parametrize("caso,mensagemEsperada", [
    ("ok", None), ("offline", "indisponível"), ("timeout", "excedido"),
    ("json", "JSON"), ("estrutura", "inválida"), ("length", "incompleta"),
])
def testeCliente(caso, mensagemEsperada):
    configuracao = lerConfiguracao()

    def responder(requisicao):
        if caso == "offline":
            raise httpx.ConnectError("simulado")
        if caso == "timeout":
            raise httpx.ReadTimeout("simulado")
        if requisicao.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if requisicao.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": configuracao["LLAMA_MODEL"]}]})
        assert requisicao.url.path == "/v1/chat/completions"
        if caso == "json":
            return httpx.Response(200, content=b"{")
        if caso == "estrutura":
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"choices": [{"finish_reason": "length" if caso == "length" else "stop",
                                                      "message": {"content": "Teste simulado"}}]})

    with ClienteIaLocal(configuracao, httpx.MockTransport(responder)) as cliente:
        if mensagemEsperada:
            with pytest.raises(ErroInferencia, match=mensagemEsperada):
                cliente.gerarExplicacao("Trecho simulado")
        else:
            assert cliente.gerarExplicacao("Trecho simulado")["choices"][0]["message"]["content"] == "Teste simulado"
