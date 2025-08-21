# Tutorial
Sempre mantenha este tutorial. Antes de iniciar uma nova tarefa, apague todo o conteúdo abaixo deste bloco e escreva apenas o que foi feito, como foi feito e por que foi feito.

## Registro de alterações
- **Objetivo**: destravar `mypy --strict` sem alterar código de produção.
- **Como**: ajuste do `mypy.ini` para focar apenas módulos principais e relaxar as checagens em `tests.*`; criação de stub extra para `pytesseract`.
- **Por que**: permite verificar partes principais do projeto sem que os arquivos não tipados bloqueiem o processo.
