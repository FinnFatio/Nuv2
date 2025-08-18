# Etapas do Projeto

Este documento resume os marcos e prioridades do cronograma até M3.

## M0 — Kickoff e Setup
**Período:** Semana 0  
**Prioridades:**  
- **P0:** Repositório inicial configurado e CI básico em operação  
- **P1:** Guia de contribuição publicado  
**Definition of Done:**  
- Todos conseguem clonar, instalar dependências e executar `pytest` com sucesso  
- Fluxo de revisão de código definido

## M1 — Coleta e Normalização de Dados
**Período:** Semanas 1–2  
**Prioridades:**  
- **P0:** Estruturar pipeline para ingestão de dados brutos  
- **P1:** Ferramentas de limpeza e normalização  
**Definition of Done:**  
- Dados de exemplo processados de ponta a ponta  
- Resultados reproduzíveis com scripts versionados

## M2 — API de Ações
**Período:** Semanas 3–4  
**Prioridades:**  
- **P0:** Implementar endpoint `POST /act`  
- **P1:** Plugin da ontologia de ações integrado à API  
**Definition of Done:**  
- Testes cobrindo cenários principais de `POST /act`  
- Plugin carregado dinamicamente conforme ontologia publicada

## M3 — Consolidação
**Período:** Semana 5  
**Prioridades:**  
- **P0:** Documentação de uso e deploy  
- **P1:** Monitoramento e métricas básicas  
**Definition of Done:**  
- Release v1.0 publicada  
- Ambiente de produção monitorado

### Observações Finais
- O plugin da ontologia de ações deve permitir a adição de novos verbos sem necessidade de alterar o core da aplicação.  
- O endpoint `POST /act` será a porta de entrada para executar ações; sua especificação final deve garantir autenticação, validação contra a ontologia e retorno estruturado de erros.

