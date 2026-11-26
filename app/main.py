from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.core.configuracao import DESCRICAO_APLICACAO, NOME_APLICACAO, VERSAO_APLICACAO


app = FastAPI(title=NOME_APLICACAO, version=VERSAO_APLICACAO, description=DESCRICAO_APLICACAO)


class Health(BaseModel):
    status: Literal["ok"]


@app.get("/health")
def health() -> Health:
    return Health(status="ok")
