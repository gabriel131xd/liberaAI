"""Cliente síncrono e inicialização do servidor de inferência em loopback."""

import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.ai.instrucoes import INSTRUCOES_SIMPLIFICACAO

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
MARGEM_CONTEXTO = 8


class ErroInferencia(Exception):
    """Falha na comunicação ou na geração local."""


class GeracaoIncompleta(ErroInferencia):
    def __init__(self, motivo, corpo):
        super().__init__(f"Geração incompleta ({motivo})")
        self.corpo = corpo


def lerConfiguracao():
    caminho = RAIZ_PROJETO / ".env"
    if not caminho.exists():
        caminho = RAIZ_PROJETO / ".env.example"
    return dict(linha.split("=", 1) for linha in caminho.read_text(encoding="utf-8-sig").splitlines()
                if linha.strip() and not linha.lstrip().startswith("#"))


class ClienteIaLocal:
    """Reutiliza a conexão HTTP durante operações com o modelo configurado."""

    def __init__(self, configuracao=None, transporte=None):
        self.configuracao = lerConfiguracao() if configuracao is None else configuracao
        url = self.configuracao["LLAMA_URL"]
        endereco = urlsplit(url)
        if (
            endereco.scheme != "http"
            or endereco.hostname != "127.0.0.1"
            or endereco.netloc != f"127.0.0.1:{endereco.port}"
            or endereco.path not in ("", "/")
            or endereco.query
            or endereco.fragment
        ):
            raise ValueError("Configure LLAMA_URL com o formato http://127.0.0.1:porta.")
        self.clienteHttp = httpx.Client(
            base_url=url,
            timeout=float(self.configuracao["LLAMA_TIMEOUT"]),
            trust_env=False,
            transport=transporte,
        )

    def __enter__(self):
        return self

    def __exit__(self, *argumentos):
        self.clienteHttp.close()

    def requisitar(self, metodo, caminho, **opcoes):
        try:
            resposta = self.clienteHttp.request(metodo, caminho, **opcoes)
            resposta.raise_for_status()
            corpo = resposta.json()
        except httpx.TimeoutException:
            raise ErroInferencia("Tempo de resposta excedido") from None
        except httpx.HTTPError as erro:
            raise ErroInferencia(f"Servidor local indisponível ou requisição recusada: {erro}") from None
        except ValueError:
            raise ErroInferencia("JSON inválido") from None
        if not isinstance(corpo, dict):
            raise ErroInferencia("Resposta inválida")
        return corpo

    def identificarModelo(self):
        if self.requisitar("GET", "/health").get("status") != "ok":
            raise ErroInferencia("Modelo indisponível")
        modelos = self.requisitar("GET", "/v1/models").get("data")
        if not isinstance(modelos, list) or len(modelos) != 1 or not isinstance(modelos[0], dict):
            raise ErroInferencia("Identificação de modelo inválida")
        identificadorModelo = modelos[0].get("id")
        nomeModeloConfigurado = Path(self.configuracao["LLAMA_MODEL"]).name
        if not isinstance(identificadorModelo, str) or Path(identificadorModelo).name != nomeModeloConfigurado:
            raise ErroInferencia("Modelo carregado difere do configurado")
        return identificadorModelo

    def gerarExplicacao(self, texto, *, ementa=False):
        if not texto.strip():
            raise ValueError("Forneça um texto")
        return self.conversar([
            {"role": "system", "content": INSTRUCOES_SIMPLIFICACAO},
            {"role": "user", "content": ("Ementa:\n" if ementa else "Trecho:\n") + texto},
        ])

    def contarTokensConversa(self, mensagens):
        """Conta o texto renderizado pelo mesmo modelo que fará a geração."""
        mensagensRenderizadas = self.requisitar(
            "POST", "/apply-template", json={"messages": mensagens},
        ).get("prompt")
        if not isinstance(mensagensRenderizadas, str):
            raise ErroInferencia("O modelo de conversa local está indisponível.")
        tokens = self.requisitar("POST", "/tokenize", json={
            "content": mensagensRenderizadas, "parse_special": True, "add_special": True,
        }).get("tokens")
        if not isinstance(tokens, list):
            raise ErroInferencia("Tokenização local indisponível")
        return len(tokens)

    def conversar(self, mensagens, *, formato=None):
        parametros = {
            "model": self.identificarModelo(), "messages": mensagens,
            "temperature": float(self.configuracao["LLAMA_TEMPERATURE"]),
            "top_k": int(self.configuracao["LLAMA_TOP_K"]),
            "repeat_penalty": float(self.configuracao["LLAMA_REPEAT_PENALTY"]),
            "max_tokens": int(self.configuracao["LLAMA_MAX_TOKENS"]),
            "reasoning_budget_tokens": int(self.configuracao["LLAMA_REASONING_BUDGET"]),
        }
        if formato is not None:
            parametros["response_format"] = formato
        corpo = self.requisitar("POST", "/v1/chat/completions", json=parametros)
        try:
            escolha = corpo["choices"][0]
            conteudo = escolha["message"]["content"]
            motivo = escolha["finish_reason"]
        except (KeyError, IndexError, TypeError):
            raise ErroInferencia("Resposta de chat inválida") from None
        if motivo != "stop":
            raise GeracaoIncompleta(motivo, corpo)
        if not isinstance(conteudo, str) or not conteudo.strip():
            raise ErroInferencia("Resposta sem texto")
        return corpo


def iniciarServidor(configuracao):
    """Inicia o executável local depois de conferir os arquivos e a porta."""
    executavel = (RAIZ_PROJETO / configuracao["LLAMA_EXE"]).resolve()
    identificadorModelo = (RAIZ_PROJETO / configuracao["LLAMA_MODEL"]).resolve()
    for arquivo in (executavel, identificadorModelo):
        if not arquivo.is_file():
            raise ErroInferencia(f"Arquivo ausente: {arquivo}")
    with ClienteIaLocal(configuracao) as cliente:
        porta = cliente.clienteHttp.base_url.port or 80
    with socket.socket() as sonda:
        if sonda.connect_ex(("127.0.0.1", porta)) == 0:
            raise ErroInferencia(f"Porta {porta} já ocupada")
    return subprocess.call([
        str(executavel), "-m", str(identificadorModelo),
        "--host", "127.0.0.1", "--port", str(porta),
        "-c", configuracao["LLAMA_CONTEXT"], "-np", "1", "-ngl", "0", "-t", "4",
        "--temp", configuracao["LLAMA_TEMPERATURE"], "--top-k", configuracao["LLAMA_TOP_K"],
        "--repeat-penalty", configuracao["LLAMA_REPEAT_PENALTY"], "--jinja",
    ])


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["serve"]:
            sys.exit(iniciarServidor(lerConfiguracao()))
        with ClienteIaLocal() as cliente:
            print("Modelo:", cliente.identificarModelo())
            print("Cole o texto. Termine com uma linha contendo apenas um ponto.")
            linhas = []
            while (linha := input()) != ".":
                linhas.append(linha)
            print(cliente.gerarExplicacao("\n".join(linhas))["choices"][0]["message"]["content"])
    except (ErroInferencia, ValueError, OSError, EOFError) as erro:
        sys.exit(str(erro))
