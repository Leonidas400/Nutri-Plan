# NutriPlan

Aplicação local de Pesquisa Operacional para formular dietas de bovinos leiteiros com o motor RuFaS e as exigências NASEM 2021. O solver é o SLSQP do SciPy.

A documentação completa e a metodologia estão em [../README.md](../README.md). A versão em PDF é [../NutriPlan_Documentacao_e_Metodologia.pdf](../NutriPlan_Documentacao_e_Metodologia.pdf).

## Iniciar

A partir da raiz do projeto:

```bash
./nutriplan-web/iniciar_linux.sh
```

Ou com o ambiente já instalado:

```bash
cd nutriplan-web
PYTHONPATH=.. ../venv/bin/python server.py
```

Abra `http://127.0.0.1:8765`. A variável `PORT` permite outra porta.

## Fluxo da interface

1. **Animal** — categoria, peso, produção atual, composição do leite, parâmetros fisiológicos, quantidade de animais e emissões opcionais.
2. **Dieta otimizada** — seleção de alimentos, preços, limites mínimo/máximo em kg MS/dia, inclusão fixa e cálculo.
3. **Resultados** — custo, consumo, matéria seca, leite, exigências, restrições, emissões e composição.
4. **Metodologia** — fundamentação NASEM/RuFaS, modelo, restrições, solver e limitações.

A produção atual é o piso. O sistema testa níveis superiores de leite em passos de 1 kg/dia e usa o maior nível viável como **Dieta maximizada**.

O seletor **Por animal / Por rebanho** altera apenas a apresentação: no escopo de rebanho, os valores são multiplicados pela quantidade de animais. A otimização continua sendo feita por animal representativo.

## Dieta otimizada

- **Grupos recomendados**: alimentos organizados em volumosos, energéticos, proteicos e minerais/corretivos.
- **Personalizado**: seleção livre com filtros.
- Preços são informados por kg de matéria natural e convertidos internamente para R$/kg de matéria seca.
- **Fixar** define inclusão mínima igual à máxima.
- A seleção vazia usa os alimentos recomendados que tenham preço.
- A seleção manual exige pelo menos dois alimentos e preço válido.

## Resultados

O seletor de escopo fica no topo da tela. No escopo por rebanho, custo, alimento, matéria seca, leite e nutrientes são multiplicados pela quantidade de animais. A composição percentual da MS não muda.

A dieta é uma solução local do SLSQP. A maximização de leite é uma varredura discreta, não uma prova de ótimo global. O resultado deve ser interpretado como a melhor solução viável encontrada, não como previsão biológica da produção.

## Testes

```bash
cd nutriplan-web
MPLBACKEND=Agg PYTHONPATH=.:.. ../venv/bin/python -m unittest discover -s tests -q
```
