# NutriPlan

Aplicação local para formular dietas de menor custo para vacas leiteiras em lactação com exigências NASEM 2021, biblioteca de ingredientes e otimizador nativo do RuFaS.

## Funcionalidades

- Quatro fases de lactação na interface e perfis de primeira lactação ou multípara.
- Cálculo de exigências, seleção de ingredientes e otimização com diagnóstico de restrições.
- Estimativa de FDN, metano e nitrogênio urinário pela dieta candidata quando não há dieta anterior.
- Dieta anterior opcional, cenários locais, análise de sensibilidade, comparação econômica quando os preços são elegíveis, pt-BR/en-US e temas claro/escuro/automático.

## Requisitos e início rápido

O diretório `nutriplan-web/` deve estar dentro do projeto RuFaS, com a biblioteca NASEM de alimentos e as dependências Python instaláveis pelo projeto pai. O iniciador Linux usa Python 3.13 e `uv`; a primeira execução pode precisar de rede. A aplicação depois funciona localmente em `127.0.0.1`.

```bash
cd nutriplan-web
./iniciar_linux.sh
```

Abra `http://127.0.0.1:8765`. Com o ambiente virtual já preparado, pode iniciar com `PYTHONPATH=.. ../venv/bin/python server.py`.

## Testes

Na pasta `nutriplan-web/`:

```bash
env -u DISPLAY MPLBACKEND=Agg MPLCONFIGDIR=/tmp/nutriplan-mpl PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. ../venv/bin/python -m unittest discover -s tests -v
```

Consulte [DOCUMENTACAO_NUTRIPLAN.md](DOCUMENTACAO_NUTRIPLAN.md) para manual completo, parâmetros, arquitetura, métodos, resultados e limitações. O cenário Guelph permanece como fixture técnico de regressão, separado do fluxo de uso.
