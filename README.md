# NutriPlan — documentação e metodologia

Documento técnico do NutriPlan, aplicação local de Pesquisa Operacional para formular dietas de bovinos leiteiros com o motor RuFaS e as exigências NASEM 2021.

**Estado documentado:** novembro de 2026.

## 1. Visão geral

O NutriPlan é uma aplicação local em Python + HTML/JS que formula dietas de mínimo custo para bovinos leiteiros usando:

- **RuFaS** como motor de cálculo e otimização;
- **NASEM 2021** como padrão nutricional;
- **SLSQP**, do SciPy, como solver não linear.

A otimização é feita **por animal/dia**. A interface permite alternar a apresentação entre **Por animal** e **Por rebanho**. No escopo de rebanho, os valores são multiplicados pela quantidade de animais informada; o solver continua trabalhando com um animal representativo.

A produção atual é o piso e o ponto de partida do cálculo. O sistema formula a dieta para a produção atual e testa níveis superiores de leite em passos de 1 kg/dia. O maior nível viável encontrado é exibido como **Dieta maximizada**.

## 2. Escopo

O NutriPlan aceita seis categorias:

| Categoria | Grupo RuFaS | Caminho nutricional |
| --- | --- | --- |
| Vaca de primeira lactação | `LAC_COW` | Lactante |
| Vaca multípara | `LAC_COW` | Lactante |
| Novilha I | `GROWING` | Crescimento |
| Novilha II | `GROWING` | Crescimento |
| Novilha III | `CLOSE_UP` | Crescimento |
| Vaca seca | `CLOSE_UP` | Seca |

As fases `fresh`, `early`, `mid` e `late` são classificações de interface para lactantes. Elas não alteram parâmetros nem selecionam modelos científicos diferentes; o cálculo usa os dias em lactação informados.

Bezerras e simulação completa de vida não fazem parte do escopo. Os estágios não lactantes usam exigências de mantença, crescimento, gestação e atividade, sem leite, sem piso e sem varredura de produção.

## 3. Requisitos e execução local

A estrutura esperada é:

```text
Nutri-Plan-/
├── nutriplan-web/
├── RUFAS/
├── input/
└── venv/
```

A partir da raiz do projeto:

```bash
./nutriplan-web/iniciar_linux.sh
```

Ou, com o ambiente já instalado:

```bash
cd nutriplan-web
PYTHONPATH=.. ../venv/bin/python server.py
```

O servidor escuta em `127.0.0.1`, porta `8765`. A variável `PORT` permite outra porta.

A aplicação não depende de serviço externo para formular dietas. O navegador precisa de JavaScript. As preferências de idioma e tema ficam no armazenamento local do navegador.

## 4. Interface atual

A navegação tem quatro abas: **Animal**, **Dieta otimizada**, **Resultados** e **Metodologia**.

### 4.1 Animal

Reúne:

- categoria animal;
- subcategoria da lactação;
- peso corporal;
- quantidade de animais;
- dias em lactação;
- ganho diário de novilha, quando aplicável;
- gestação e dia de gestação;
- produção atual;
- composição do leite;
- fósforo do módulo de processo;
- parâmetros complementares;
- emissões opcionais.

A produção atual é o piso da dieta e o ponto de partida da maximização. A FDN da dieta não é digitada: ela é derivada da ração formulada.

### 4.2 Dieta otimizada

É a etapa de configuração do problema. O usuário define quais alimentos podem entrar na ração, seus preços e seus limites de inclusão.

A tela oferece:

- **Grupos recomendados**: alimentos separados em volumosos, energéticos, proteicos e minerais/corretivos;
- **Personalizado**: lista própria, com filtros e seleção manual;
- busca por nome;
- filtro por categoria RuFaS;
- filtro “somente selecionados”;
- prévia de composição do alimento;
- tabela editável de preços e limites;
- inclusão fixa;
- botão **Calcular dieta otimizada**.

Na tabela:

| Coluna | Significado |
| --- | --- |
| Ingrediente | Alimento selecionado. |
| Valor do preço | Preço em R$/kg de matéria natural. |
| Mín. kg MS/dia | Inclusão mínima em kg de matéria seca por animal/dia. |
| Máx. kg MS/dia | Inclusão máxima em kg de matéria seca por animal/dia. |
| Fixar | Define mínimo igual ao máximo, tornando a inclusão obrigatória. |
| Ação | Remove o alimento da lista. |

A seleção manual exige pelo menos dois alimentos e preço válido para todos. Se a seleção estiver vazia, o motor usa o conjunto recomendado que tenha preço cadastrado.

### 4.3 Resultados

A tela mostra a solução encontrada pelo solver. O seletor no topo alterna entre **Por animal** e **Por rebanho**; a troca não refaz a otimização.

Blocos exibidos:

1. **Custo e consumo** — cards com custo/dia, kg ingeridos, matéria seca e leite produzido. Em estágios sem lactação, o card de leite não aparece.
2. **Exigências nutricionais** — energia líquida, proteína metabolizável, cálcio, fósforo, matéria seca e FDN da dieta.
3. **Detalhes técnicos** — restrições com mínimo exigido, oferta e máximo exigido; emissões com metano e nitrogênio urinário.
4. **Composição da dieta** — barras de participação na MS e tabela com kg/dia, kg MS/dia e % MS.

Valores do rebanho são calculados como:

```text
valor do rebanho = valor por animal × quantidade de animais
```

O seletor altera apenas a apresentação, não o modelo de otimização.

### 4.4 Metodologia

A aba Metodologia descreve a fundamentação NASEM/RuFaS, o modelo matemático, as restrições, o solver SLSQP, as emissões, os estágios de vida e as limitações. Ela deve ser lida em conjunto com este documento.

## 5. Entradas e unidades

### 5.1 Dados do animal

| Entrada | Unidade | Uso |
| --- | --- | --- |
| Categoria animal | — | Seleciona o modelo fisiológico e o grupo RuFaS. |
| Peso corporal | kg | Manutenção, consumo, crescimento, minerais e emissões. |
| Peso adulto | kg | Maturidade e crescimento relativo. |
| Escore de condição corporal | 1–5 | Estimativa de consumo e reservas. |
| Dias em lactação | dias | Exigências de lactação. |
| Dia de gestação | dias | Exigências de gestação. |
| Ganho diário de novilha | kg/dia | Exigências de crescimento. |
| Intervalo entre partos | dias | Contexto fisiológico. |
| Gordura do leite | % | Energia por kg de leite. |
| Proteína verdadeira do leite | % | Energia e proteína do leite. |
| Lactose | % | Energia por kg de leite. |
| Produção atual | kg/dia | Piso de produção e ponto de partida da maximização. |
| Alojamento | Barn/Grazing | Energia de atividade. |
| Distância percorrida | m | Energia de atividade. |
| Fósforo do processo | g/dia | Componente da exigência de fósforo. |
| Quantidade de animais | cabeças | Multiplicação dos resultados do rebanho. |

### 5.2 Emissões

Os campos de metano entérico e nitrogênio urinário são opcionais. Se ambos ficarem vazios, o RuFaS estima as emissões a partir da dieta candidata. As emissões entram no cálculo de energia metabolizável e no potencial de leite.

## 6. Alimentos

O catálogo de composição é:

```text
input/data/feed/NASEM_Comp_with_TDN.csv
```

Ele contém matéria seca, proteína bruta, FDN, amido, gordura, minerais, frações proteicas e demais campos NASEM. A leitura é feita por `feed_library()` em `nutriplan-web/services/native_ration.py`.

O endpoint `/api/nasem-feeds` expõe o catálogo para a interface.

O modo automático usa a lista `RECOMMENDED_FEED_IDS` e somente alimentos com preço cadastrado. O modo manual usa os alimentos selecionados pelo usuário.

## 7. Preços e custo

### 7.1 Origem dos preços

Preços pré-cadastrados:

```text
input/data/feed/feed_prices.csv
```

Formato:

```csv
rufas_id,price_brl_kg
1,2.8
```

O valor é interpretado como **R$/kg de matéria natural**. O usuário também pode informar o preço diretamente na tabela da aba Dieta otimizada.

A API aceita:

- `kg_as_fed`;
- `kg_dm`;
- `metric_ton_as_fed`;
- moeda de três letras;
- fonte, data e observações.

### 7.2 Conversão para matéria seca

O custo usado pelo solver é por kg de matéria seca:

```text
custo por kg MS = preço por kg natural / fração de MS
```

Exemplo:

- preço = R$ 1,20/kg natural;
- matéria seca = 40% (fração 0,40);
- custo por kg MS = 1,20 / 0,40 = R$ 3,00/kg MS.

Se a dieta usar 2 kg MS desse alimento:

```text
custo do alimento = 2 × 3,00 = R$ 6,00/animal/dia
```

A implementação está em `nutriplan-web/services/native_ration.py` e `nutriplan-web/services/prices.py`.

### 7.3 Custo total

O custo por animal/dia é:

```text
C = Σ x_i · c_i
```

Onde:

- `x_i` = kg MS do alimento `i` por animal/dia;
- `c_i` = custo por kg MS do alimento `i`.

O resultado inclui `cost_day` e `cost_month = cost_day × 30`. O custo do rebanho é apenas `cost_day × N` na interface.

## 8. Metodologia de otimização

### 8.1 Variáveis de decisão

Para cada alimento `i`:

```text
x_i = kg de matéria seca do alimento i por animal/dia
```

O vetor de decisão é contínuo. Não há variável binária de seleção. Os alimentos selecionados entram com limites mínimo e máximo.

Variáveis derivadas:

```text
q_i = x_i / (DM_i / 100)     # kg de matéria natural/dia
c_i = p_i / (DM_i / 100)     # R$/kg MS
```

### 8.2 Função objetivo

```text
minimizar C(x) = Σ c_i x_i
```

O objetivo é linear. As não linearidades estão nas restrições nutricionais e no potencial de leite.

### 8.3 Restrições

O solver usa o padrão NASEM do RuFaS com 11 restrições:

| Restrição | Forma geral |
| --- | --- |
| Energia líquida | oferta NEL ≥ exigência NEL |
| Proteína metabolizável mínima | oferta MP ≥ exigência MP |
| Proteína metabolizável máxima | oferta MP ≤ 1,5 × exigência de referência |
| Cálcio | oferta Ca ≥ exigência Ca |
| Fósforo | oferta P ≥ exigência P |
| FDN mínimo | FDN da dieta ≥ 25% MS |
| FDN máximo | FDN da dieta ≤ 45% MS |
| FDN de forragem | FDN de forragem ≥ 15% MS |
| Gordura | gordura da dieta ≤ 7% MS |
| Ingestão mínima | MS ingerida ≥ 70% da exigência de MS |
| Ingestão máxima | MS ingerida ≤ 130% da exigência de MS |

Além dessas:

- `l_i ≤ x_i ≤ u_i` para cada alimento;
- pelo menos dois alimentos distintos;
- preço obrigatório;
- piso de produção atual no potencial de leite.

Os limites de ingestão usam uma margem de 30%. As constantes de FDN, FDN de forragem, gordura e fator de proteína estão em `RUFAS/biophysical/animal/animal_module_constants.py`.

As restrições efetivas estão em `RUFAS/biophysical/animal/ration/ration_optimizer.py`. O arquivo `nutriplan-web/data/nutritional_constraint_rules.csv` serve à prévia e à visualização, não substitui o solver.

### 8.4 Solver

O problema é resolvido com **SLSQP**:

```python
minimize(..., method="SLSQP", bounds=..., constraints=...)
```

O SLSQP é um solver local. Ele encontra um ponto que satisfaz condições locais de KKT, mas não prova que não existe solução melhor em outra região.

### 8.5 Potencial de leite e piso

Depois de formular a ração, o sistema calcula o leite permitido pela própria dieta em duas rotas:

```text
leite_NEL = (EL_oferta − exigências não lactantes) ÷ energia por kg de leite
leite_MP  = (PM_oferta − PM não lactante) × 0,69 ÷ (proteína verdadeira/100 × 1000)
```

O leite permitido é o menor valor entre as duas rotas. Se ficar abaixo da produção atual, a solução é rejeitada. Essa métrica é um teto do modelo NASEM 2021, não uma previsão biológica.

### 8.6 Maximização por varredura

A maximização não é uma segunda função objetivo. O fluxo é:

1. usar a produção atual como piso;
2. testar níveis de leite em passos de 1 kg/dia;
3. testar até sete níveis acima da produção atual;
4. para cada nível, minimizar o custo;
5. escolher o maior nível viável encontrado.

Isso é uma **maximização discreta por enumeração**. Pode existir um nível viável entre dois pontos testados, acima do limite de +7 kg/dia, ou um ponto que falhe por causa do solver local.

### 8.7 Estágios não lactantes

Novilhas e vaca seca não têm leite, piso ou varredura. A FDN da dieta é derivada da ração otimizada por iteração até convergir. O objetivo continua sendo o menor custo.

## 9. Resultados e interpretação

O resultado principal é uma solução viável de mínimo custo local. Para lactantes, é a maior dieta viável encontrada na varredura.

A tela de Resultados permite:

- ver custo, consumo, matéria seca e leite;
- alternar entre animal e rebanho;
- conferir exigências e restrições;
- ver a oferta de nutrientes;
- conferir emissões estimadas;
- analisar a composição da dieta;
- imprimir o resultado no escopo selecionado.

O valor do rebanho é uma agregação de apresentação. O modelo não otimiza animais com características diferentes.

## 10. API e mapa de arquivos

| Componente | Arquivo |
| --- | --- |
| Interface | `nutriplan-web/index.html` |
| Estilos | `nutriplan-web/styles.css` |
| Servidor HTTP | `nutriplan-web/server.py` |
| Varredura de leite | `nutriplan-web/services/milk_targets.py` |
| Integração RuFaS | `nutriplan-web/services/native_ration.py` |
| Exigências NASEM | `nutriplan-web/services/nutrition.py` |
| Potencial de leite | `nutriplan-web/services/milk_potential.py` |
| Preços | `nutriplan-web/services/prices.py` |
| Objetivo e restrições | `RUFAS/biophysical/animal/ration/ration_optimizer.py` |
| Catálogo de alimentos | `input/data/feed/NASEM_Comp_with_TDN.csv` |
| Preços padrão | `input/data/feed/feed_prices.csv` |
| Perfis animais | `nutriplan-web/data/animal_profiles.csv` |

Rotas principais:

| Rota | Uso |
| --- | --- |
| `GET /api/nasem-feeds` | Catálogo de alimentos. |
| `POST /api/nutritional-requirements` | Exigências do animal. |
| `POST /api/rufas-native` | Formulação da dieta. |
| `POST /api/sensitivity-analysis` | Análise de sensibilidade pela API. |
| `POST /api/economic-comparison` | Comparação econômica pela API. |

## 11. Validação

A suíte Python tem **48 testes**, cobrindo:

- fórmula de energia do leite;
- rotas NEL/MP;
- piso de produção;
- paridades;
- varredura de leite;
- exploração de alternativas;
- novilha I/II/III e vaca seca;
- validação de composição;
- limites e inclusão fixa;
- contratos HTTP.

Comando:

```bash
cd nutriplan-web
MPLBACKEND=Agg PYTHONPATH=.:.. ../venv/bin/python -m unittest discover -s tests -q
```

O caso Guelph é usado como regressão computacional. A validação é computacional, não biológica de campo.

## 12. Limitações e otimalidade

Principais limitações:

- solver local, sem certificado de ótimo global;
- problema não convexo;
- maximização de leite discreta e limitada a sete níveis acima da produção atual;
- um animal representativo, não o rebanho inteiro;
- preços e composições dependem dos dados informados;
- ausência de validação biológica de campo;
- não otimiza lucro, margem, disponibilidade física ou curva de lactação;
- não simula o ciclo de vida completo.

Para garantia de ótimo global seria necessário:

- usar um solver global de NLP/MINLP;
- ou provar convexidade/reformular o modelo;
- ou resolver a maximização de leite como uma única otimização explícita;
- e reportar gap de otimalidade e tolerâncias.

Sem isso, o texto correto é “melhor solução encontrada” ou “solução local do SLSQP”.

## 13. Referências

- National Academies of Sciences, Engineering, and Medicine. 2021. *Nutrient Requirements of Dairy Cattle: Eighth Revised Edition*. [DOI 10.17226/25806](https://doi.org/10.17226/25806).
- National Research Council. 2001. *Nutrient Requirements of Dairy Cattle: Seventh Revised Edition*. [DOI 10.17226/9825](https://doi.org/10.17226/9825).
- RuFaS — Ruminant Farm Systems. [Repositório](https://github.com/RuminantFarmSystems/RuFaS) e [documentação](https://ruminantfarmsystems.github.io/RuFaS/).
- IPCC. 2006. *Guidelines for National Greenhouse Gas Inventories*, volume 4, capítulo 10.
- SciPy. [SLSQP](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html).
