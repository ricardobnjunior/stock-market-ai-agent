# Guia de Testes - Stock Market AI Agent

Este guia vai te ajudar a testar 100% das funcionalidades do projeto.

---

## 1. Preparação

### 1.1 Verificar se a API Key está configurada

Abra o arquivo `.env` e confirme que sua chave está lá:

```
OPENROUTER_API_KEY=sk-or-v1-sua-chave-aqui
```

### 1.2 Escolher método de execução

Você pode testar de duas formas:
- **Opção A**: Docker (recomendado)
- **Opção B**: Localmente com Python

---

## 2. Executando o Projeto

### Opção A: Com Docker

```bash
# 1. Construir a imagem
docker build -t stock-agent .

# 2. Rodar o container
docker run -p 8501:8501 stock-agent
```

### Opção B: Localmente

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Entrar na pasta src
cd src

# 3. Rodar o Streamlit
streamlit run app.py
```

### 2.1 Acessar a aplicação

Abra o navegador em: **http://localhost:8501**

Você deve ver:
- Título "Stock Market AI Agent"
- Campo de chat na parte inferior
- Sidebar com informações e botão "Clear Chat"

---

## 3. Testes Funcionais

Copie e cole cada pergunta no chat e verifique a resposta.

### 3.1 Preço Atual de Ações

| Pergunta | Resultado Esperado |
|----------|-------------------|
| `What is the current price of Tesla?` | Deve retornar o preço atual da TSLA em USD |
| `What's Apple's stock price?` | Deve retornar o preço atual da AAPL |
| `Current price of NVDA` | Deve retornar o preço atual da Nvidia |

**Validação**: O agente deve retornar um valor numérico em dólares.

---

### 3.2 Preço de Criptomoedas

| Pergunta | Resultado Esperado |
|----------|-------------------|
| `What is the Bitcoin price?` | Deve retornar o preço do BTC-USD |
| `How much is Ethereum right now?` | Deve retornar o preço do ETH-USD |

**Validação**: Valores devem ser compatíveis com preços reais de mercado.

---

### 3.3 Preço de Ontem

| Pergunta | Resultado Esperado |
|----------|-------------------|
| `What was the Bitcoin price yesterday?` | Deve retornar o preço de fechamento de ontem |
| `Tesla's closing price yesterday?` | Deve retornar o preço de fechamento da TSLA |

**Validação**: Deve mencionar uma data e um preço.

---

### 3.4 Variação Percentual

| Pergunta | Resultado Esperado |
|----------|-------------------|
| `What's the percentage change in Tesla compared to yesterday?` | Deve calcular a variação % |
| `How much did Apple change since yesterday?` | Deve mostrar variação em % |

**Validação**: Deve retornar um valor percentual (positivo ou negativo).

---

### 3.5 Média de Preços

| Pergunta | Resultado Esperado |
|----------|-------------------|
| `Calculate the average stock price of Apple over the last week` | Média dos últimos 7 dias |
| `What's the average price of NVDA for the last 5 days?` | Média dos últimos 5 dias |

**Validação**: Deve retornar um preço médio e idealmente o período.

---

### 3.6 Operações Matemáticas

| Pergunta | Resultado Esperado |
|----------|-------------------|
| `What is 15% of 720?` | Deve calcular: 108 |
| `Calculate (500 - 450) / 450 * 100` | Deve calcular: ~11.11% |

**Validação**: Resultado matemático correto.

---

### 3.7 Contexto de Conversa

Teste se o agente mantém contexto:

```
1. Pergunta: "What's the current price of Tesla?"
2. Pergunta: "And what about yesterday?"
3. Pergunta: "What's the percentage change?"
```

**Validação**: O agente deve entender que você ainda está falando sobre Tesla.

---

### 3.8 Comparações

| Pergunta | Resultado Esperado |
|----------|-------------------|
| `Compare Tesla and Apple prices` | Deve buscar e comparar os dois preços |

---

## 4. Testes de Interface

### 4.1 Sidebar

- [ ] A sidebar aparece com informações sobre o agente
- [ ] O botão "Clear Chat" funciona e limpa o histórico

### 4.2 Chat

- [ ] Mensagens do usuário aparecem alinhadas à direita
- [ ] Mensagens do agente aparecem alinhadas à esquerda
- [ ] O spinner "Thinking..." aparece enquanto processa

### 4.3 Erros

Teste com a API key errada para verificar tratamento de erros:
- Deve mostrar mensagem de erro amigável

---

## 5. Checklist Final

### Requisitos do Desafio

| Requisito | Status |
|-----------|--------|
| Interface conversacional (Streamlit) | [ ] |
| Integração com LLM (OpenRouter) | [ ] |
| Preço atual de ações | [ ] |
| Preço de criptomoedas | [ ] |
| Preço de ontem | [ ] |
| Variação percentual | [ ] |
| Média de preços | [ ] |
| Operações matemáticas | [ ] |
| Dockerfile funcionando | [ ] |
| README com instruções | [ ] |

---

## 6. Exemplos Completos para Teste Rápido

Cole essas perguntas em sequência para um teste rápido:

```
What was the Bitcoin price yesterday?
```

```
And the current price of Tesla?
```

```
What's the percentage change compared to yesterday?
```

```
Can you calculate the average stock price of Apple over the last week?
```

---

## 7. Troubleshooting

### Erro: "OPENROUTER_API_KEY not found"
- Verifique se o arquivo `.env` existe e contém a chave

### Erro: "Could not fetch price"
- Verifique sua conexão com a internet
- O ticker pode estar incorreto

### Docker não encontra o .env
- Certifique-se de que o `.env` está na raiz do projeto
- Rebuilde a imagem: `docker build -t stock-agent .`

### Streamlit não inicia
- Verifique se está na pasta `src/`
- Verifique se as dependências foram instaladas

---

## 8. Dicas para a Apresentação

1. **Mostre o código limpo**: Destaque a separação em `tools.py`, `agent.py` e `app.py`
2. **Mostre o Docker**: Execute `docker build` e `docker run` ao vivo
3. **Teste ao vivo**: Faça as perguntas do exemplo do desafio
4. **Mencione melhorias possíveis**:
   - Cache de preços
   - Gráficos com histórico
   - Mais indicadores financeiros
   - Testes unitários
   - Rate limiting
