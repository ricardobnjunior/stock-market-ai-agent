# Guia de Apresentação - Stock Market AI Agent

> **Duração:** 30 minutos (Q&A Session)
> **Formato:** Apresentação da solução + Discussão de desafios + Melhorias possíveis

---

## Estrutura Sugerida (30 min)

| Tempo | Seção | Duração |
|-------|-------|---------|
| 0:00 - 0:02 | Introdução pessoal | 2 min |
| 0:02 - 0:10 | Demonstração ao vivo | 8 min |
| 0:10 - 0:18 | Arquitetura e código | 8 min |
| 0:18 - 0:23 | Desafios enfrentados | 5 min |
| 0:23 - 0:28 | Melhorias possíveis | 5 min |
| 0:28 - 0:30 | Perguntas finais | 2 min |

---

## 1. Introdução (2 min)

**O que falar:**
- Seu nome e background brevemente
- Agradecer pela oportunidade
- Visão geral do que você construiu

**Exemplo de fala:**
> "Construí um agente de IA conversacional que permite aos usuários consultar preços de ações e criptomoedas em tempo real, calcular variações percentuais, médias de preços e realizar operações matemáticas. Vou demonstrar o funcionamento e depois discutir as decisões técnicas."

---

## 2. Demonstração ao Vivo (8 min)

### 2.1 Iniciar a aplicação

```bash
cd src
streamlit run app.py
```

### 2.2 Perguntas para demonstrar (na ordem)

Faça estas perguntas exatamente como estão no desafio:

```
What was the Bitcoin price yesterday?
```
> Mostra: busca de preço histórico de crypto

```
And the current price of Tesla?
```
> Mostra: busca de preço atual de ação

```
What's the percentage change compared to yesterday?
```
> Mostra: contexto conversacional (entende que é sobre Tesla)

```
Can you calculate the average stock price of Apple over the last week?
```
> Mostra: cálculo de média

**Pergunta extra para impressionar:**
```
What is 15% of 720?
```
> Mostra: operações matemáticas

### 2.3 Pontos para destacar durante a demo

- **Streaming:** "Notem que o texto aparece em tempo real, não de uma vez só"
- **Feedback visual:** "Aqui vocês podem ver o que está acontecendo por trás - qual tool está sendo chamada"
- **Resultados das tools:** "O sistema mostra o resultado bruto da API antes de formatar a resposta"

---

## 3. Arquitetura e Código (8 min)

### 3.1 Estrutura do Projeto

```
stock-market-ai-agent/
├── src/
│   ├── app.py      → Interface Streamlit
│   ├── agent.py    → Lógica do agente + LLM
│   └── tools.py    → Funções de mercado + cálculos
├── Dockerfile      → Containerização
├── .env            → API key (não commitado)
└── README.md       → Documentação
```

**O que falar:**
> "Separei o código em três módulos com responsabilidades distintas: interface, agente e ferramentas. Isso facilita manutenção e testes."

### 3.2 Fluxo de Dados

```
Usuário → Streamlit → Agent → OpenRouter API
                        ↓
                   Tool Calling
                        ↓
                    yfinance
                        ↓
                   Resposta
```

---

## 4. DOMÍNIO DO CÓDIGO - Explicação Detalhada

### 4.1 tools.py - Ferramentas de Mercado

#### Mapeamento de Tickers (linhas 12-26)
```python
TICKER_ALIASES = {
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "tesla": "TSLA",
    "apple": "AAPL",
    # ...
}
```
**O que faz:** Converte nomes comuns para símbolos do Yahoo Finance.
**Por que:** Usuários falam "Bitcoin", mas yfinance precisa de "BTC-USD".
**Como explicar:** "Criei um dicionário que mapeia linguagem natural para tickers válidos."

#### Função normalize_ticker (linhas 29-32)
```python
def normalize_ticker(ticker: str) -> str:
    normalized = ticker.lower().strip()
    return TICKER_ALIASES.get(normalized, ticker.upper())
```
**O que faz:** Normaliza o input do usuário.
**Por que:** Garante que "TESLA", "tesla", "Tesla" funcionem igual.
**Como explicar:** "Converto para minúsculo, busco no dicionário, e se não achar, assumo que é um ticker válido em maiúsculo."

#### EXTRA: Múltiplos Fallbacks no get_current_price (linhas 35-87)
```python
# Method 1: Try fast_info (most reliable)
try:
    fast = stock.fast_info
    price = fast.get("lastPrice") or fast.get("regularMarketPrice")
except:
    pass

# Method 2: Try info dict
if price is None:
    try:
        info = stock.info
        price = info.get("regularMarketPrice") or info.get("currentPrice")
    except:
        pass

# Method 3: Try history as last resort
if price is None:
    hist = stock.history(period="5d")
    if not hist.empty:
        price = float(hist["Close"].iloc[-1])
```
**O que faz:** Tenta 3 métodos diferentes para obter o preço.
**Por que:** yfinance é instável - às vezes `fast_info` falha, às vezes `info` retorna vazio.
**Como explicar:** "O yfinance não é 100% confiável, então implementei três níveis de fallback. Se o primeiro método falhar, tenta o segundo, e assim por diante."

#### Definição das Tools (linhas 250-346)
```python
TOOLS = [
    {
        "name": "get_current_price",
        "description": "Get the current price of a stock or cryptocurrency...",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock symbol or name..."
                }
            },
            "required": ["ticker"]
        }
    },
    # ...
]
```
**O que faz:** Define o schema das tools no formato OpenAI Function Calling.
**Por que:** O LLM precisa saber quais funções existem e quais parâmetros aceitar.
**Como explicar:** "Cada tool tem nome, descrição e schema JSON dos parâmetros. O LLM usa isso para decidir qual função chamar."

#### Registry de Funções (linhas 350-357)
```python
TOOL_FUNCTIONS = {
    "get_current_price": get_current_price,
    "get_price_yesterday": get_price_yesterday,
    # ...
}
```
**O que faz:** Mapeia nome da tool → função Python.
**Por que:** Quando o LLM retorna `"name": "get_current_price"`, preciso saber qual função executar.
**Como explicar:** "É um dicionário que conecta o nome retornado pelo LLM com a função real a ser executada."

---

### 4.2 agent.py - Lógica do Agente

#### Configuração OpenRouter (linhas 15-16)
```python
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"
```
**O que faz:** Define endpoint e modelo padrão.
**Por que:** OpenRouter é compatível com API OpenAI, permite trocar modelos facilmente.
**Como explicar:** "Uso OpenRouter porque oferece acesso a vários modelos com uma única API. Posso trocar de gpt-4o-mini para outro modelo só mudando essa linha."

#### System Prompt (linhas 18-32)
```python
SYSTEM_PROMPT = """You are a helpful financial assistant...

You have access to tools that can:
- Get current prices for stocks and cryptocurrencies
- Get yesterday's closing prices
...

Common ticker mappings: Bitcoin=BTC-USD, Tesla=TSLA...
"""
```
**O que faz:** Define o comportamento e conhecimento do agente.
**Por que:** Orienta o LLM sobre seu papel e capacidades.
**Como explicar:** "O system prompt é crucial. Ele diz ao modelo quem ele é, o que pode fazer, e dou dicas dos mapeamentos de tickers para ajudar nas respostas."

#### EXTRA: Descrições para Feedback (linhas 34-42)
```python
TOOL_DESCRIPTIONS = {
    "get_current_price": "Fetching current price",
    "get_price_yesterday": "Fetching yesterday's price",
    # ...
}
```
**O que faz:** Mensagens amigáveis para mostrar ao usuário.
**Por que:** Em vez de mostrar "get_current_price", mostro "Fetching current price: Bitcoin".
**Como explicar:** "Isso é para UX. O usuário vê uma mensagem clara do que está acontecendo, não o nome técnico da função."

#### Função call_llm (linhas 53-96)
```python
def call_llm(
    messages: list,
    tools: Optional[list] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    stream: bool = False,
) -> dict | requests.Response:
```
**Parâmetros importantes:**
- `messages`: Histórico da conversa
- `tools`: Lista de funções disponíveis
- `stream`: Se True, retorna Response para streaming

```python
if tools:
    payload["tools"] = [
        {"type": "function", "function": tool} for tool in tools
    ]
    payload["tool_choice"] = "auto"
```
**O que faz:** Formata as tools no padrão OpenAI.
**Por que:** A API espera `{"type": "function", "function": {...}}`.
**Como explicar:** "Transformo minhas definições de tools no formato que a API espera. O `tool_choice: auto` deixa o modelo decidir se precisa usar alguma tool."

#### EXTRA: Parse de SSE Stream (linhas 109-125)
```python
def parse_sse_stream(response: requests.Response) -> Generator[str, None, None]:
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
```
**O que faz:** Processa Server-Sent Events (SSE) da API.
**Por que:** Streaming retorna dados linha por linha no formato `data: {...}`.
**Como explicar:** "Quando ativo streaming, a API não retorna JSON completo. Ela envia chunks no formato SSE. Cada linha começa com 'data: ' seguido de JSON. Faço parse de cada chunk e extraio só o conteúdo novo."

#### EXTRA: run_agent_with_streaming (linhas 128-218)
```python
def run_agent_with_streaming(
    user_message: str,
    conversation_history: list,
    on_status: Optional[Callable[[str, str], None]] = None,
) -> Generator[str | dict, None, None]:
```
**O que faz:** Função principal que orquestra tudo com suporte a streaming.
**Retorna:** Generator que pode retornar:
- `{"status": "..."}` → Atualização de status
- `{"tool_call": "...", "result": {...}}` → Resultado de tool
- `str` → Chunk de texto da resposta
- `{"done": True, "history": [...]}` → Fim da execução

**Fluxo detalhado:**

```python
# 1. Monta mensagens com histórico
messages = [{"role": "system", "content": SYSTEM_PROMPT}]
messages.extend(conversation_history)  # Histórico anterior
messages.append({"role": "user", "content": user_message})  # Nova mensagem
```
**Como explicar:** "Sempre incluo o system prompt, todo o histórico da conversa, e a nova mensagem. Isso permite contexto conversacional."

```python
# 2. Primeira chamada (sem streaming) para ver se precisa de tools
response = call_llm(messages, tools=TOOLS, stream=False)
assistant_message = response["choices"][0]["message"]
```
**Como explicar:** "A primeira chamada não pode ser streaming porque preciso saber se o modelo quer usar tools. Se fizesse streaming, não conseguiria capturar as tool_calls."

```python
# 3. Se tem tool_calls, executa cada uma
if assistant_message.get("tool_calls"):
    for tool_call in assistant_message["tool_calls"]:
        tool_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])

        # Mostra status para o usuário
        yield {"status": status_msg, "state": "running"}

        # Executa a tool
        tool_result = execute_tool(tool_name, arguments)

        # Mostra resultado
        yield {"tool_call": tool_name, "args": arguments, "result": ...}

        # Adiciona resultado às mensagens
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": tool_result,
        })
```
**Como explicar:** "Se o modelo decidiu usar tools, executo cada uma, mostro o status e resultado para o usuário, e adiciono os resultados às mensagens para a próxima chamada."

```python
# 4. Segunda chamada com streaming para resposta final
stream_response = call_llm(messages, tools=TOOLS, stream=True)
for chunk in parse_sse_stream(stream_response):
    full_response += chunk
    yield chunk  # Envia cada pedaço para a UI
```
**Como explicar:** "Depois de executar as tools, faço uma segunda chamada com streaming. O modelo agora tem os dados reais e gera a resposta final, que vou enviando chunk por chunk para a interface."

```python
# 5. Atualiza histórico
updated_history = conversation_history.copy()
updated_history.append({"role": "user", "content": user_message})
updated_history.append({"role": "assistant", "content": full_response})
yield {"done": True, "history": updated_history}
```
**Como explicar:** "No final, atualizo o histórico com a nova troca de mensagens e sinalizo que terminou."

---

### 4.3 app.py - Interface Streamlit

#### Session State (linhas 19-23)
```python
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
```
**O que faz:** Inicializa estados persistentes.
**Por que:** Streamlit reroda o script inteiro a cada interação. Session state persiste dados.
**Diferença:**
- `messages`: Para exibir na UI (inclui formatação)
- `conversation_history`: Para enviar ao LLM (formato da API)

#### Exibição do Histórico (linhas 26-28)
```python
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
```
**O que faz:** Renderiza todas as mensagens anteriores.
**Por que:** Como Streamlit reroda o script, preciso redesenhar o chat completo.

#### EXTRA: Status Container (linhas 39-43)
```python
status_container = st.status("Processing...", expanded=True)
response_placeholder = st.empty()
```
**O que faz:**
- `st.status`: Caixa expansível que mostra progresso
- `st.empty`: Placeholder que será atualizado com streaming

**Como explicar:** "O st.status é um componente do Streamlit que mostra etapas de um processo. Uso para mostrar qual tool está sendo executada. O st.empty é um placeholder que atualizo a cada chunk do streaming."

#### EXTRA: Processamento do Generator (linhas 49-98)
```python
for item in run_agent_with_streaming(prompt, st.session_state.conversation_history):
    if isinstance(item, dict):
        if "status" in item:
            # Atualiza o status
            status_container.update(label=item["status"], state="running")

        elif "tool_call" in item:
            # Mostra resultado da tool
            with status_container:
                if "price" in result:
                    st.success(f"**{result.get('symbol')}**: ${result['price']}")
                # ...

        elif "done" in item:
            # Finaliza
            st.session_state.conversation_history = item["history"]
            status_container.update(label="Complete", state="complete", expanded=False)

    else:
        # É um chunk de texto - streaming
        full_response += item
        response_placeholder.markdown(full_response + "▌")
```
**O que faz:** Processa cada item do generator e atualiza a UI.
**Por que:** O generator retorna diferentes tipos de dados, preciso tratar cada um.
**Como explicar:**
- "Quando recebo um dict com 'status', atualizo a caixa de status"
- "Quando recebo 'tool_call', mostro o resultado formatado com ícones"
- "Quando recebo 'done', salvo o histórico e fecho a caixa"
- "Quando recebo string, é chunk de streaming - adiciono ao texto com cursor ▌"

#### EXTRA: Cursor de Streaming (linha 98)
```python
response_placeholder.markdown(full_response + "▌")
```
**O que faz:** Mostra texto com cursor piscando.
**Por que:** Dá feedback visual de que ainda está gerando.
**Como explicar:** "O caractere ▌ simula um cursor. A cada chunk novo, atualizo o placeholder. No final, removo o cursor mostrando só o texto final."

---

## 5. Resumo: O que foi ALÉM do Pedido

| Feature Extra | Onde está | Como funciona |
|---------------|-----------|---------------|
| **Streaming** | `agent.py:109-125`, `app.py:95-98` | Parse SSE + atualização incremental |
| **Feedback visual** | `agent.py:34-42`, `app.py:39-56` | st.status + TOOL_DESCRIPTIONS |
| **Fallbacks yfinance** | `tools.py:53-75` | 3 métodos: fast_info → info → history |
| **Contexto conversacional** | `agent.py:146-148`, `app.py:19-23` | Histórico em session_state |
| **Formatação de resultados** | `app.py:71-88` | Ícones, cores, formatos por tipo |

---

## 6. Desafios Enfrentados (5 min)

### 6.1 yfinance Instável

**Problema:**
> "O yfinance às vezes retorna dados vazios ou falha silenciosamente, especialmente para criptomoedas."

**Solução:**
> "Implementei três métodos de fallback: `fast_info`, `info` e `history`. Se um falha, tenta o próximo."

### 6.2 Streaming com Tool Calling

**Problema:**
> "Não é possível fazer streaming na primeira chamada quando o modelo precisa decidir qual tool usar."

**Solução:**
> "Faço a primeira chamada sem streaming para capturar as tool calls, executo as tools, e só então faço streaming na resposta final."

### 6.3 Contexto Conversacional

**Problema:**
> "O usuário pode perguntar 'What's the percentage change compared to yesterday?' sem mencionar qual ativo."

**Solução:**
> "Mantenho o histórico de conversas no session_state do Streamlit e envio para o LLM em cada requisição."

### 6.4 Mapeamento de Tickers

**Problema:**
> "Usuários falam 'Bitcoin' mas o yfinance precisa de 'BTC-USD'."

**Solução:**
> "Criei um dicionário de aliases que mapeia nomes comuns para símbolos corretos."

---

## 7. Melhorias Possíveis (5 min)

### 7.1 Curto Prazo (fácil de implementar)

| Melhoria | Descrição |
|----------|-----------|
| **Cache de preços** | Evitar chamadas repetidas ao yfinance em curto intervalo |
| **Rate limiting** | Proteger contra uso excessivo da API |
| **Mais tickers** | Expandir o dicionário de aliases |
| **Testes unitários** | Cobertura para as tools e agent |

### 7.2 Médio Prazo

| Melhoria | Descrição |
|----------|-----------|
| **Gráficos** | Usar Plotly para mostrar histórico visual |
| **Alertas de preço** | Notificar quando atingir certo valor |
| **Comparação de ativos** | Gráfico comparativo entre ações |
| **Indicadores técnicos** | RSI, médias móveis, etc. |

### 7.3 Longo Prazo

| Melhoria | Descrição |
|----------|-----------|
| **Múltiplos LLMs** | Fallback entre provedores |
| **Banco de dados** | Persistir histórico de conversas |
| **Autenticação** | Login de usuários |
| **API própria** | Expor como serviço REST |

---

## 8. Perguntas Prováveis e Respostas

### Sobre Arquitetura

**P: Por que não usou LangChain?**
> "O desafio permitia usar a API diretamente ou LangChain. Optei pela API direta com tool calling porque resulta em código mais simples, menos dependências, e maior controle sobre o fluxo. LangChain seria útil para casos mais complexos, mas para este escopo, a abordagem direta foi suficiente."

**P: Por que OpenRouter e não OpenAI direto?**
> "OpenRouter oferece acesso a múltiplos modelos com uma única API. Facilita trocar de modelo sem mudar código. Também permite usar modelos alternativos se necessário."

**P: Como funciona o streaming?**
> "A API retorna Server-Sent Events (SSE). Cada linha vem no formato 'data: {json}'. Faço parse de cada chunk, extraio o conteúdo do delta, e atualizo a UI em tempo real com st.empty()."

**P: Por que duas chamadas ao LLM?**
> "A primeira chamada precisa ser sem streaming para capturar as tool_calls. Não tem como saber se o modelo vai querer usar tools enquanto faz streaming. Depois de executar as tools, a segunda chamada pode ser com streaming porque é só gerar texto."

### Sobre o Código

**P: Como você trata erros do yfinance?**
> "Implementei três métodos de fallback com try/except em cada um. Primeiro tento fast_info, depois info, depois history. Se todos falharem, retorno uma mensagem de erro amigável."

**P: O que acontece se a API key estiver errada?**
> "O requests.raise_for_status() levanta uma exceção. O try/except no app.py captura e mostra um erro de configuração na interface, sem expor detalhes técnicos."

**P: Como mantém o contexto da conversa?**
> "Uso duas variáveis no session_state: messages para UI e conversation_history para o LLM. A cada mensagem, adiciono ao histórico e envio tudo para a API. O system prompt sempre vai primeiro."

**P: O que é o Generator e por que usou?**
> "Generator é uma função que usa yield em vez de return. Permite retornar valores incrementalmente sem carregar tudo em memória. Uso para streaming: a cada chunk que chega da API, faço yield e a UI atualiza imediatamente."

### Sobre os Extras

**P: Por que implementou streaming se não foi pedido?**
> "Melhora significativamente a UX. Sem streaming, o usuário fica olhando para uma tela vazia por vários segundos. Com streaming, ele vê o texto sendo gerado em tempo real e tem feedback de que algo está acontecendo."

**P: Como funciona o feedback visual das tools?**
> "Criei um dicionário TOOL_DESCRIPTIONS que mapeia nome técnico para mensagem amigável. Quando uma tool é chamada, mostro a mensagem dentro do st.status. Quando retorna, mostro o resultado formatado com ícones dependendo do tipo de dado."

---

## 9. Checklist Pré-Apresentação

### Ambiente
- [ ] Docker rodando ou ambiente local configurado
- [ ] `.env` com API key válida
- [ ] Testar todas as perguntas da demo antes
- [ ] Internet estável (yfinance precisa de conexão)

### Código
- [ ] Repositório atualizado no GitHub
- [ ] README completo e legível
- [ ] Nenhum arquivo sensível commitado

### Conhecimento
- [ ] Entender o fluxo completo: User → Streamlit → Agent → LLM → Tools → Response
- [ ] Saber explicar cada função principal
- [ ] Saber explicar os extras e por que implementou

### Apresentação
- [ ] Compartilhamento de tela testado
- [ ] Terminal com fonte legível
- [ ] Browser aberto em `localhost:8501`

---

## 10. Dicas Finais

1. **Seja honesto sobre limitações** - Mostra maturidade técnica
2. **Mencione trade-offs** - "Escolhi X porque Y, mas Z seria alternativa"
3. **Demonstre curiosidade** - "Uma coisa que eu gostaria de explorar mais é..."
4. **Prepare-se para erros** - Se algo falhar na demo, explique o que deveria acontecer
5. **Mantenha a calma** - 30 minutos passam rápido, não precisa correr

---

## Frases Úteis

- "Uma decisão técnica importante foi..."
- "O principal desafio que enfrentei foi..."
- "Se tivesse mais tempo, eu teria..."
- "Uma alternativa que considerei foi..."
- "O trade-off aqui é..."
- "Isso vai além do requisito porque..."

---

**Boa sorte na apresentação!**
