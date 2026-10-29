# Esquema de eventos e atribuição

O site **não coleta eventos hoje**. Este esquema é o contrato que uma coleta futura teria; `entrelacos/simulacao.py`
gera dados fictícios nesse formato para exercitar o pipeline.

## `eventos_demo.csv`
| coluna | descrição |
|---|---|
| `evento_id` | identificador único do evento |
| `sessao_id` | uma visita; todo evento pertence a uma sessão que começa com `visita` |
| `ts` | data/hora ISO 8601 |
| `tipo` | `visita`, `filtro`, `abrir_detalhes` ou `clicar_pedir` |
| `produto_id` | obrigatório em `abrir_detalhes` e `clicar_pedir` (precisa existir no catálogo) |
| `filtro` | obrigatório em `filtro`: `ela`, `ele`, `ate100` ou `premium` |
| `origem` | `instagram`, `whatsapp_status`, `indicacao` ou `direto` (viria de `?utm_source=`) |
| `dispositivo` | `mobile` ou `desktop` |
| `codigo_pedido` | só em `clicar_pedir`: código `EL-XXXX` gerado no clique e enviado na mensagem do WhatsApp |

## `vendas_demo.csv` (planilha que o vendedor preencheria)
`venda_id`, `data`, `produto_id`, `valor`, `codigo_pedido` (vazio se o vendedor não anotou), `pagamento`.

## Regras de atribuição
- **Venda atribuída** = venda com `codigo_pedido` que casa com um `clicar_pedir`. Só ela entra nas métricas por produto/origem.
- Vendas sem código, ou com código sem clique, contam no total, mas não são atribuíveis. O relatório mostra a **cobertura de receita** para deixar isso explícito.
- `qualidade.py` acusa: ids duplicados, tipos/produtos/filtros inválidos, sessão sem `visita`, clique sem código, código duplicado, venda órfã, venda com produto diferente do clique e venda anterior ao clique.

## Privacidade (LGPD)
Sem IP, sem nome, sem telefone, sem cookie persistente: apenas um id de sessão anônimo. A planilha de vendas **não** deve
guardar dados de cliente. Antes de qualquer coleta real, avisar no rodapé do site e definir prazo de retenção.
