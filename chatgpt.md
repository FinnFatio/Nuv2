# Tutorial
Sempre mantenha este tutorial. Antes de iniciar uma nova tarefa, apague todo o conteúdo abaixo deste bloco e escreva apenas o que foi feito, como foi feito e por que foi feito.

## Registro de alterações
- **Objetivo**: tornar o parser de toolcalls tolerante à ausência de `</toolcall>` e manter validações de nome/argumentos.
- **Como**: ajustar `_parse_toolcalls` em `agent_local.py` para auto-fechar a tag usando o menor sufixo JSON balanceado, validar `name` e `args` (regex e cap de 2 KB) e adicionar testes cobrindo casos simples, aninhados, lixo após `}`, múltiplas aberturas, limite de args e nomes inválidos.
- **Por que**: reduzir atrito com modelos que omitem a tag final, sem afetar fluxos existentes.
