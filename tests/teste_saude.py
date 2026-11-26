import asyncio

import httpx

from app.main import app


def testeSaude():
    async def verificar():
        async with app.router.lifespan_context(app):
            transporte = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transporte, base_url="http://test") as cliente:
                resposta = await cliente.get("/health")
        assert resposta.status_code == 200
        assert resposta.headers["content-type"] == "application/json"
        assert resposta.json() == {"status": "ok"}

    asyncio.run(verificar())


def testeDocumentacao():
    async def verificar():
        transporte = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://test") as cliente:
            assert (await cliente.get("/docs")).status_code == 200
            esquema = (await cliente.get("/openapi.json")).json()
        assert esquema["info"]["title"] == "LiberaAI"
        assert esquema["info"]["version"] == "0.1.0"
        assert "get" in esquema["paths"]["/health"]

    asyncio.run(verificar())
