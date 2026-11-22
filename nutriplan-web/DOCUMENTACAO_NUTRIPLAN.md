# Documentação do NutriPlan

Estado verificado em 21/11/2026. Aplicação local de Pesquisa Operacional para formular dietas de menor custo para bovinos leiteiros em diferentes estágios.

## 1. Escopo e fundamento

O NutriPlan usa a implementação instalada do RuFaS e seu padrão NASEM 2021. Calcular **exigências** determina as necessidades do animal informado. Formular uma **dieta** procura quantidades dos ingredientes disponíveis que atendam às restrições com menor custo. A segunda tarefa depende também de composição, preços e limites de inclusão.

Há seis perfis suportados: `first_lactation_cow` e `multiparous_lactating_cow` (`AnimalType.LAC_COW`, `AnimalCombination.LAC_COW`), `heifer_I` e `heifer_II` (`HEIFER_I`/`HEIFER_II`, `GROWING`), `heifer_III` (`HEIFER_III`, `CLOSE_UP`) e `dry_cow` (`DRY_COW`, `CLOSE_UP`). Os quatro primeiros usam os métodos lactantes; os demais usam as exigências NASEM de mantença, crescimento, gestação e atividade, sem meta de leite.

As fases `fresh`, `early`, `mid` e `late` são classificações da interface para lactantes. Não alteram parâmetros, não definem intervalos fixos de dias em lactação e não selecionam quatro modelos científicos diferentes. Bezerras continuam fora do escopo; novilhas e vaca seca estão habilitadas. O objetivo de todos os estágios é o menor custo sujeito às exigências NASEM; leite, piso de leite e fronteira custo × leite existem somente para lactantes.

## 2. Execução local

Na estrutura atual, `nutriplan-web/`, `RUFAS/`, `input/` e `venv/` ficam no mesmo projeto pai. Use `./iniciar_linux.sh` ou, com o ambiente existente:

```bash
PYTHONPATH=.. ../venv/bin/python server.py
```

O servidor escuta em `127.0.0.1`, porta 8765 por padrão; `PORT` permite outra porta. Não há necessidade de serviço externo para formular dietas. O navegador precisa de JavaScript. O armazenamento local guarda as preferências de idioma e tema.

## 3. Fluxo por abas

1. **Animal** reúne dados individuais, parâmetros complementares e emissões opcionais.
2. **Dieta atual** reúne a composição opcional do lote, as quantidades em kg MS por animal/dia e o consumo total. Enquanto houver linha incompleta ou quantidade inválida, o total aparece como travessão. Os preços opcionais servem ao comparador. Se a lista estiver vazia, a formulação segue diretamente com os dados do animal e os ingredientes disponíveis.
3. **Dieta otimizada** apresenta busca, grupos, seleção personalizada e tabela de preços. A seleção vazia usa o conjunto recomendado com preço. Uma seleção manual admite de 2 a 25 alimentos. **Calcular dieta otimizada** executa a análise integrada.
4. **Resultados** abre após o cálculo e mostra custo, consumo, meta, resumo da maior meta viável e composição da dieta. O diagnóstico, a avaliação nutricional, as emissões, o comparador, a lista detalhada de metas e a sensibilidade estão disponíveis pela API.
5. **Metodologia** contém doze seções com índice navegável por teclado, equações e uma tabela com as onze restrições verificadas.

As abas reutilizam os controles existentes, preservam valores e não executam a otimização. Setas esquerda/direita, Home e End navegam entre abas; Tab entra nos controles. Alterar entradas após uma execução marca o resultado como desatualizado. Idioma e tema não alteram os dados científicos.

Antes da primeira execução, Resultados mostra um estado vazio. Durante o cálculo, o botão em Ingredientes fica desabilitado e mostra processamento, sem confirmação adicional. Falhas ocultam resultados anteriores; quando o campo é identificável, a aplicação abre sua aba/seção e posiciona o foco nele. Uma resposta recebida depois de alterar as entradas não pode restaurar a análise desatualizada.

## 4. Dicionário de entradas

| Entrada | Unidade / contrato | Uso no modelo instalado |
| --- | --- | --- |
| Peso corporal | kg, positivo | Manutenção, crescimento, consumo, minerais, atividade e emissões. |
| Peso adulto | kg, positivo | Tamanho adulto e crescimento relativo. |
| Dias em lactação | dias inteiros, não negativos, apenas lactantes | Consumo e componentes fisiológicos; independente da fase escolhida. |
| Ganho diário de novilha | kg/dia, não negativo, obrigatório em novilhas | Crescimento no método nativo. O RuFaS usa kg/dia, não g/dia. |
| Produção de leite | kg/dia, não negativa, apenas lactantes | Exigências para lactação e excreção de nitrogênio. |
| Gordura, proteína verdadeira, lactose | % do leite, 0–100 por componente e no máximo 100 na soma | Energia do leite e, conforme o componente, proteína/minerais. Proteína verdadeira não significa proteína bruta da dieta. |
| Paridade | primeira lactação / multípara | Perfil nativo 1 / 2, independente da fase. |
| Gestação | sim/não; dia inteiro quando sim | Componentes gestacionais e correções de peso; ausência é `null`, não dia zero presumido. |
| Condição corporal | escala 1–5 | Estimativa nativa de consumo. |
| Intervalo entre partos | dias inteiros positivos, lactantes e vaca seca | Crescimento no método nativo; precisa representar uma condição utilizável pelo cálculo. |
| Alojamento | `Barn` / `Grazing` | Atividade; rótulos PT são Confinamento / Pastejo, sem mudar os identificadores. |
| Distância percorrida | m, não negativa | Energia de atividade; usar o significado solicitado pelo método instalado. |
| FDN da dieta | % MS, opcional no modo candidato | Derivada da dieta candidata ou da dieta anterior; entrada técnica explícita permanece acessível. |
| Fósforo do módulo de processo | g/dia, não negativo, lactantes | Valor calculado pelo módulo de processo. A restrição de fósforo usa o maior valor entre essa entrada e a exigência estimada pelo NASEM. Nos demais estágios, assume 0. |
| Metano entérico | g/dia | Perda energética. Estimado na formulação ou informado pelo usuário. |
| Nitrogênio urinário | kg/dia | Perda energética. Estimado na formulação ou informado pelo usuário. |
| Preço | moeda/kg natural no preenchimento simples | Convertido para custo/kg MS usando a MS do alimento. Não há moeda presumida quando não foi documentada. |
| Inclusão mínima e máxima | kg MS/animal/dia | Limites por ingrediente no solver. |

Essas faixas são validações de entrada; não certificam plausibilidade zootécnica em toda a faixa. Entradas incompatíveis com as equações podem produzir erro de cálculo, que bloqueia a formulação.

## 5. Números e erros frequentes

`3,66` e `3.66` são equivalentes nos dois idiomas. Não use separadores de milhares: `1.234,56`, `1,234.56` e `1 234` são rejeitados. Um separador isolado sempre é decimal. Não informe símbolos monetários dentro do campo numérico.

O frontend envia números JSON ou `null` para opcionais vazios. O backend normaliza também strings numéricas, rejeita booleanos e números não finitos e verifica limites. Campos obrigatórios vazios permanecem pendentes; não recebem zero. A API de sensibilidade recebe as variações em uma lista JSON.

## 6. Parâmetros complementares e origens

Informe peso adulto, intervalo entre partos, alojamento e distância em **Animal → Parâmetros complementares**. Fase, paridade, peso atual, produção, composição do leite, condição corporal e gestação são dados individuais. Lactose e fósforo de processo são informados manualmente.

A interface indica quais parâmetros foram informados, calculados ou estão pendentes. Se a FDN for deixada em branco, o cálculo usa a composição da dieta atual para avaliar seu contexto quando disponível e a composição da dieta candidata durante a formulação. Os números catalogados em `data/nutritional_parameter_references.csv` são exemplos e continuam com `auto_fill=false`.

Os CSV de perfis internos do backend contêm alguns valores de referência antigos usados como fallback quando uma chave é omitida na API. O formulário envia explicitamente seus campos, inclusive `null` nos vazios, e não usa esse fallback como preenchimento científico automático. Clientes diretos da API devem informar todos os parâmetros necessários e não interpretar esses perfis internos como recomendações.

## 7. Catálogos e entrada de dados

O produtor informa os dados pelo formulário. Os serviços locais leem os catálogos distribuídos de composição, preços, referências e perfis nutricionais internos.

## 8. Exigências nutricionais

`services/nutrition.calculate` chama `NASEMRequirementsCalculator.calculate_requirements`. São expostos energia líquida total (Mcal/dia), proteína metabolizável (g/dia), cálcio e fósforo (g/dia) e consumo estimado de MS (kg/dia).

O total de energia reúne manutenção, crescimento, gestação, lactação e atividade calculados pelo RuFaS. Peso, maturidade e paridade influenciam crescimento; a gestação é condicionada às entradas individuais. O consumo lactante depende do perfil fisiológico. A exigência de proteína inclui componentes de manutenção, crescimento, gestação e leite e depende também da FDN dietética.

A prévia isolada não substitui a configuração da ração. Sem contexto dietético completo, exigências dependentes da dieta podem permanecer pendentes. No modo candidato, a proteína é recalculada usando a FDN da dieta em avaliação e novamente na dieta final. O adaptador confirma que a FDN final não alterou as exigências de consumo e energia usadas na otimização; divergência bloqueia o resultado.

FDN, FDN de forragem e gordura são restrições da ração. Não são apresentadas como novas exigências animais calculadas isoladamente. Métodos nativos adicionais, como aminoácidos, não significam que o NutriPlan imponha suas restrições; o conjunto exposto está descrito abaixo.

## 9. Ingredientes e matéria seca

O catálogo personalizado expõe 175 alimentos, incluindo os que ficam fora dos grupos de lactantes. Os grupos e o conjunto automático mantêm o recorte de ingredientes recomendado. A composição vem de `../input/data/feed/NASEM_Comp_with_TDN.csv`, selecionada pelo ID RuFaS exato. Traduções alteram apenas o nome exibido. A composição catalogada não substitui análise do alimento real.

Para quantidade `xᵢ` em kg MS/dia e fração de MS `dᵢ = DMᵢ/100`, a quantidade natural é `xᵢ/dᵢ`. Para um nutriente informado em % MS, a soma direta é `Σ xᵢ·aᵢ/100`, em kg/dia. A FDN dietética é `100·FDN_kg/Σxᵢ`.

Essas somas descrevem composição bruta. Proteína metabolizável, energia e minerais digestíveis usam os métodos nativos de aproveitamento, não apenas percentuais. Os totais brutos de cálcio e fósforo ficam disponíveis na API em kg/dia. As verificações nutricionais usam a oferta digestível em g/dia.

Cada alimento selecionado tem limites **mínimo** e **máximo** de inclusão em kg MS por animal/dia. A API `GET /api/nasem-feeds` expõe `lower_limit` e `limit` do catálogo NASEM; a interface usa esses valores como padrão editável. A opção **Fixar** copia o mínimo para o máximo (`min = max`), mantendo o alimento em quantidade fixa. O resultado da formulação lista essas inclusões em `fixed_inclusions`. Os produtos proprietários do TCC não existem no catálogo; a inclusão fixa usa os alimentos NASEM equivalentes disponíveis.

## 10. Modelo matemático, solver e restrições

Cada `xᵢ` é a quantidade de um ingrediente em kg de matéria seca por animal/dia, limitada por `lᵢ ≤ xᵢ ≤ uᵢ`. O custo diário é `min C(x) = Σᵢ (pᵢ/dᵢ) xᵢ`, com `pᵢ` em moeda por kg natural e `dᵢ` como fração de matéria seca. Logo, `pᵢ/dᵢ` é o custo por kg MS e `xᵢ/dᵢ` é a quantidade em kg natural. O preço deve usar uma moeda compatível entre os ingredientes. Na seleção manual, `lᵢ` e `uᵢ` começam nos limites do catálogo e podem ser editados; **Fixar** define `lᵢ = uᵢ`. O conjunto automático usa os limites do catálogo, com 0 e 100 kg MS/dia para valores ausentes. O custo é linear nas quantidades. As relações de oferta nutricional e de participação na dieta tornam o problema não linear.

O motor de formulação é o `RationOptimizer` do RuFaS. O cálculo nutricional usa as relações do NASEM 2021 integradas ao RuFaS. O otimizador chama `scipy.optimize.minimize` com `method="SLSQP"`, a função de custo, uma dieta inicial, os limites e as restrições. O método **Sequential Least Squares Programming** ajusta as quantidades por aproximações quadráticas sucessivas e lida com restrições não lineares. No NutriPlan, o ponto inicial é determinístico e depende dos limites e do consumo estimado.

A chamada usa os padrões do SciPy para `maxiter=100` e `ftol=1e-6`. Esse critério de precisão considera o gradiente da Lagrangiana, as violações de restrições, o tamanho do passo e a mudança no custo. A verificação posterior exige sucesso do solver, folgas finitas maiores ou iguais a `-1e-4` nas unidades de cada restrição, quantidades finitas de pelo menos `-1e-6` kg MS/dia e respeito aos limites de inclusão com tolerância de `1e-4` kg MS/dia. O custo recalculado deve coincidir com o valor do solver usando tolerâncias absoluta de `1e-4` e relativa de `1e-5`. Falhas de convergência, oferta insuficiente e limites incompatíveis podem impedir a formulação. A convergência indica uma solução local cujas restrições devem ser conferidas. [Documentação do SLSQP no SciPy](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html)

Cada linha abaixo é uma desigualdade com folga nominal maior ou igual a zero. Os limites individuais de inclusão são separados dessas onze restrições.

| Restrição | Unidade | Condição e origem |
| --- | --- | --- |
| Consumo mínimo | kg MS/dia | Soma de quantidades ≥ 70% do consumo estimado pelo NASEM. |
| Consumo máximo | kg MS/dia | Soma de quantidades ≤ 130% do consumo de referência usado na inicialização. A margem de 30% em torno da estimativa vem do RuFaS. |
| Energia líquida | Mcal/dia | Oferta líquida depois das perdas ≥ exigência total NASEM. |
| Proteína metabolizável mínima | g/dia | Oferta nativa ≥ exigência NASEM, que depende da FDN. |
| Proteína metabolizável máxima | g/dia | Oferta nativa ≤ 1,5 vez a exigência de referência. O modo com FDN candidata usa a exigência recalculada para a candidata nos dois limites. |
| FDN total mínima | % da MS total | FDN ≥ 25%, limite do RuFaS. |
| FDN total máxima | % da MS total | FDN ≤ 45%, limite do RuFaS. |
| FDN de forragem mínima | % da MS total | FDN das forragens ≥ 15% do total de MS, limite do RuFaS. |
| Gordura máxima | % da MS total | Extrato etéreo ≤ 7%, limite do RuFaS. |
| Cálcio mínimo | g/dia | Oferta digestível calculada pelo RuFaS ≥ exigência NASEM de cálcio. |
| Fósforo mínimo | g/dia | Oferta digestível calculada pelo RuFaS ≥ o maior valor entre a exigência NASEM e o fósforo de processo informado. |

Os métodos nativos para oferta digestível de cálcio e fósforo referenciam NRC 2001. Proteína bruta e amido entram na composição e em cálculos dietéticos, sem desigualdades próprias neste fluxo. Aminoácidos também ficam fora do conjunto de restrições ativas.

## 11. Emissões e energia da dieta candidata

Com os dois campos de emissões vazios, `CandidateRationOptimizer` aplica as funções nativas a cada dieta candidata. O metano e o nitrogênio urinário vêm das rotas IPCC e de excreção do estágio: vaca lactante, novilha ou vaca seca. O metano depende do consumo e da energia bruta estimada da composição. A rota de nitrogênio urinário usa a diferença entre nitrogênio total do esterco e nitrogênio fecal, com o piso da equação nativa de 0,022 kg/dia. Nessa rota, as quantidades de nitrogênio dependem do consumo e da proteína bruta. Com dieta atual, o cálculo da exigência proteica usa a FDN dessa dieta e rejeita uma entrada manual divergente. Sem dieta atual, uma FDN manual é aceita. Quando ambas estão ausentes, o modelo recalcula a FDN e a exigência proteica de cada candidata.

Essas duas rotas selecionadas não dependem de energia metabolizável previamente calculada. Campos energéticos indisponíveis são sinalizados como não disponíveis internamente, e não preenchidos como emissões zero. Não são usados parâmetros lactantes para habilitar novilhas.

`NutritionSupplyCalculator.calculate_NASEM_digestible_energy` calcula a energia digestível da ração considerando composição, consumo, peso e amido. `calculate_NASEM_metabolizable_energy` desconta metano e urina; `calculate_NASEM_net_energy` aplica a eficiência nativa de 0,66. Em base diária, a operação implementada é `EM = ED − 13,28·CH₄_kg − 0,0146·N_urinário_g`, seguida de `EL = 0,66·EM`. A API de emissões usa CH₄ em g/dia e N em kg/dia; as conversões ocorrem no método nativo. As perdas são descontadas uma vez.

O docstring nativo desses métodos menciona Mcal/kg, mas as operações somam energia das quantidades diárias e o otimizador compara o resultado com a exigência total diária. Esta documentação explicita a base diária efetivamente usada; não altera o código científico.

As dependências da candidata são avaliadas dentro das restrições. A reavaliação final usa a própria solução.

Após sucesso, a API de formulação retorna os valores em g/dia para metano e kg/dia para nitrogênio urinário com a origem da estimativa. Os campos manuais continuam vazios no modo automático. Na aba Animal, a FDN derivada pode aparecer com a indicação de dieta candidata ou anterior. Ela é recalculada quando as entradas mudam.

Dois valores manuais finitos e não negativos substituem as estimativas, inclusive com dieta anterior ou FDN manual. Para formular, preencha ambos os campos ou deixe os dois vazios.

O modelo automático requer dados fisiológicos e dietéticos compatíveis. O código RuFaS consultado oferece equações dependentes desses dados e coeficientes para seu cálculo. A ausência de uma estimativa aplicável produz uma falha de cálculo.

Isso não executa a simulação completa de um lote `Pen`, suas transições diárias ou todos os módulos ambientais do RuFaS. As emissões são estimativas dos caminhos selecionados, não medições nem validação ambiental integral.

## 12. Interpretação, comparação e sensibilidade

A aba Resultados mostra custo por animal/dia, consumo de matéria seca, meta de leite e composição em kg MS e matéria natural. A resposta da API inclui a adequação das onze restrições, suas folgas e os totais de composição. A moeda deriva dos registros de preços. Uma cotação legada sem moeda permanece em unidades monetárias.

O comparador usa as quantidades próprias de cada dieta e os métodos nativos do otimizador para energia líquida (Mcal/dia) e proteína metabolizável (g/dia). Soma o consumo e a FDN em kg/dia. Ambas usam o mesmo contexto fisiológico e as mesmas exigências de referência. No modo automático, cada dieta fornece suas próprias perdas energéticas. No modo manual, ambas usam o par informado. A diferença é a dieta formulada menos a atual. Zero numa coluna de quantidade indica inclusão ou retirada. Valores nutricionais indisponíveis aparecem como travessão. O número de restrições satisfeitas usa a tolerância da verificação final.

Para comparar custos, o serviço aplica uma cotação atual por alimento às duas dietas. O preço simples editado na interface usa BRL/kg natural. Alimentos exclusivos da dieta anterior aceitam cotação atual própria. Os preços de catálogo requerem confirmação de atualidade. A ausência de preço ou moeda comum preserva a comparação nutricional e omite o custo comparado. As diferenças descrevem preços atuais. O endpoint econômico histórico permanece separado da interface principal.

A sensibilidade repete a formulação nativa para variações de preço ou disponibilidade de um ingrediente. Usa os dados da análise aberta e mantém fixa a produção informada na aba Animal. As variações são hipotéticas.

## 13. Dados durante a análise

Os valores preenchidos ficam disponíveis durante a navegação entre abas. Ao abrir ou recarregar, a aplicação inicia na aba Animal com o formulário vazio. Apenas idioma e tema persistem entre visitas.

## 14. Implementação e verificação

A exigência nutricional e a formulação são calculadas por serviços diferentes. Todos os fluxos que formulam uma dieta chegam ao mesmo adaptador `services/native_ration.optimize_native`, que chama `RationOptimizer.attempt_optimization` para NASEM.

| Rota | Serviço e papel |
| --- | --- |
| `GET /api/health` | Diagnóstico do motor RuFaS e identificação do solver SLSQP e da biblioteca SciPy. |
| `GET /api/animal-categories`, `GET /api/nasem-feeds` | Categorias habilitadas e catálogo de alimentos. |
| `POST /api/nutritional-requirements` | `services/nutrition.calculate` calcula as exigências. |
| `POST /api/rufas-native` | `services/milk_targets.formulate` delega ao adaptador nativo. A entrada deve identificar a categoria animal. |
| `POST /api/sensitivity-analysis` | `services/sensitivity.run_sensitivity` recebe `configuration` com os dados da formulação, além de `mode`, `rufas_id` e `variations`. Cada experimento chama o adaptador nativo para a mesma meta. |
| `POST /api/economic-comparison` | `services/economic_comparison.compare_diets_economically` avalia custos de dietas fornecidas. |

O comparador é executado durante a formulação e retornado pela API e usa `services/diet_comparison.compare_rations` para avaliar quantidades já definidas, com funções nativas de oferta e restrições. A interface apresenta nomes em português ou inglês.

Os testes usam o caso interno Guelph de `data/reference_rations.json` e o conjunto de candidatos do manifesto experimental. Com primípara, dieta anterior e os mesmos parâmetros do ensaio histórico, a referência é 26,425466 unidades monetárias/animal/dia e 21,902898 kg MS/dia. Para reproduzir também a margem de energia histórica, o teste usa como entradas manuais o metano e o nitrogênio urinário daquele ensaio. Esse valor econômico pertence aos preços do caso. O teste de navegador reproduz o caso Guelph pela interface com os limites históricos e a API local. Os comandos de execução estão no [README](README.md).

A Fase 17.1 começou com dez testes Python descobertos e um roteiro de navegador separado. O manifesto experimental registra execuções antigas de 64 e 75 testes com descoberta em `tests/`. O material histórico cita uma execução de 94 e módulos específicos de nutrição, preços, sensibilidade e regressão por HTTP. Esses arquivos estavam ausentes da cópia local na abertura da Fase 17. A evidência disponível não identifica a operação que os retirou ou os 94 casos individualmente.

A suíte Python atual reúne 48 testes: onze de `services/milk_potential`, cinco de metas, sete de formulação nativa (incluindo o piso, as duas paridades, a exploração e os limites/oferta das restrições), quatro de validação de entradas, quatro de limites/inclusão fixa, dois de fronteira, nove de estágios de vida e seis HTTP. O caso Guelph e os dados de entrada são compartilhados. Os testes HTTP exercitam o servidor real com porta temporária e conferem `milk_potential`, `fixed_inclusions`, a fronteira, os estágios sem leite, as exigências e o código de erro quando a meta fica abaixo da produção atual. Os roteiros de navegador citados em versões anteriores não estão incluídos nesta cópia; a suíte Python não depende deles.

Para reproduzir a suíte do simulador nesta revisão, use **pytest 9.0.3**. Uma execução completa anterior registrou 7.311 aprovações e 69 avisos. No pytest 9.2.0, os quatro testes de `_build_bounds_user_defined_ration` encontram um `TypeError` ao construir `pytest.approx` para uma lista de tuplas, antes da comparação dos limites. A incompatibilidade está na asserção da suíte do simulador. O comando do README para a aplicação usa `unittest`.

## 15. Limitações e evidência

O manifesto experimental preserva o estudo IFG de Daniel Brandão Silva Brito como referência histórica independente de programação linear. Seu método e seus resultados publicados ficam registrados como evidência bibliográfica e não participam de nenhuma rota de formulação. [Manifesto experimental](data/experimental_validation_manifest.json)

A formulação cobre os dois perfis lactantes habilitados, as restrições nativas e as composições catalogadas. Inputs do animal, análise real dos alimentos e representatividade dos preços limitam o uso em campo. Curvas de lactação, disponibilidade física por período, lucro, validação biológica externa e resposta produtiva individual exigem informações adicionais.

## 16. Referências

- National Academies of Sciences, Engineering, and Medicine. 2021. *Nutrient Requirements of Dairy Cattle: Eighth Revised Edition*. National Academies Press. [DOI 10.17226/25806](https://doi.org/10.17226/25806) · [NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/NBK600603/)
- National Research Council. 2001. *Nutrient Requirements of Dairy Cattle: Seventh Revised Edition*. Referência dos métodos de oferta mineral citada no código do RuFaS. [DOI 10.17226/9825](https://doi.org/10.17226/9825)
- RuFaS — Ruminant Farm Systems. A descrição da integração usa o código da cópia instalada. [Repositório oficial](https://github.com/RuminantFarmSystems/RuFaS) · [Documentação oficial](https://ruminantfarmsystems.github.io/RuFaS/)
- IPCC. 2006. *Guidelines for National Greenhouse Gas Inventories*, volume 4, capítulo 10. Referência citada pelo cálculo nativo de metano. [IPCC](https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html)
- SciPy. Parâmetros e critério de parada do SLSQP. [Manual do SciPy](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html)
- Evidência local: `RUFAS/biophysical/animal/nutrients/nasem_requirements_calculator.py`, `nutrition_supply_calculator.py`, `ration/ration_optimizer.py`, `digestive_system/enteric_methane_calculator.py`, `digestive_system/manure_excretion_calculator.py` e os serviços/testes descritos acima, todos relativos à raiz correspondente.

## 17. Formulação por metas de leite

**Calcular dieta otimizada** envia uma requisição a `POST /api/rufas-native` com `evaluate_milk_targets: true` e `milk_reference_kg_day` para categorias lactantes. Para novilhas e vaca seca, a chamada não envia meta de leite e retorna uma única formulação. O backend avalia a meta informada (`parameters.milk_production`) e, quando a referência pode ser avaliada, testa sete metas abaixo e sete acima da referência, em passos de 1 kg de leite por animal/dia. O intervalo e a resolução limitam o custo computacional a quinze chamadas ao SLSQP. As restrições de ingestão, energia, proteína, minerais e inclusão de cada ingrediente avaliam a compatibilidade fisiológica de cada meta. O intervalo da busca não representa um limite fisiológico individual.

A **produção atual** é um piso separado da meta e não pode ser maior que ela. Depois de formular cada dieta, `services/milk_potential.py` calcula o leite permitido pela própria ração em duas rotas. Pela energia, `leite_NEL = (EL_oferta − exigências não lactantes) ÷ energia por kg de leite`, com energia por kg `0,0929×gordura + (0,0547/0,93)×proteína verdadeira + 0,0395×lactose` (Mcal/kg). Pela proteína, `leite_MP = (PM_oferta − PM não lactante) × 0,69 ÷ (proteína verdadeira/100 × 1000)`. O leite permitido é o menor valor entre as duas rotas. Se ele ficar abaixo da produção atual, a formulação normal é rejeitada com `error_code: milk_floor_violation`. Na exploração de alternativas, metas abaixo do piso são resolvidas com `allow_below_reference` e retornam `milk_status: below_reference`; elas aparecem como hipotéticas e nunca viram a dieta principal. O resultado expõe `milk_potential` com as duas rotas, a referência, a margem e o estado `maintained`, `increased`, `below_reference` ou `unavailable`. Essa métrica é um teto do modelo NASEM 2021, não uma previsão biológica da produção observada.

Cada tentativa usa os mesmos dados do animal, preços e ingredientes, recalcula as exigências para sua meta de leite e minimiza `Σ xᵢ pᵢ / dᵢ`. A variável `xᵢ` representa kg MS por animal/dia, `pᵢ` é o preço por kg natural e `dᵢ` é a fração de matéria seca. A dieta só é aceita após sucesso do solver e conferência das restrições, dos limites e do custo. Em caso de falha, a resposta da API conserva o estado da tentativa e o código do solver quando disponível. Falhas de estimativa de emissões ficam registradas na tentativa correspondente, e as outras metas continuam sendo avaliadas.

A resposta identifica `reference_result`, `highest_feasible_result` e `target_results`. Cada tentativa bem-sucedida guarda custo, consumo, composição em kg MS e kg natural, e a contagem das restrições atendidas. Os contratos de API para uma meta fixa ou uma lista explícita de metas continuam disponíveis a outros consumidores. A sensibilidade usa a produção informada para isolar o efeito da variação escolhida.

Uma alternativa é **não dominada** se nenhuma outra solução viável testada tem custo igual ou menor e meta igual ou maior com pelo menos uma melhoria estrita. A interface apresenta a dieta da meta informada e destaca a maior meta viável entre as metas testadas. Se somente uma meta superior tiver solução, ela passa a ser a solução principal exibida. Quando as quantidades por ingrediente coincidem, o painel usa uma única coluna de composição. Uma meta maior pode exigir gasto adicional. A escolha de um compromisso econômico exige uma regra, como o preço marginal recebido pelo leite ou um orçamento informado.

O resultado inclui `frontier`, a lista resumida das metas não dominadas, e, quando a exploração é solicitada, `alternative_solutions` e `exploration_frontier`. A exploração perturba as dietas ótimas, mantém apenas as que atendem às restrições nativas e avalia custo e leite permitido. É uma amostra local, não uma enumeração de todas as dietas possíveis. A interface mostra uma tabela com meta, custo, leite permitido, margem, status e a marca de não dominada, além de um gráfico SVG de custo por leite permitido. O botão **Explorar dietas** acrescenta a nuvem de soluções viáveis não ótimas, com pontos dominados em cinza e abaixo do piso em âmbar; a linha da fronteira é apenas uma referência visual, pois a varredura é discreta e cada ponto é uma solução local do SLSQP.

A análise calcula dietas de custo local para um conjunto discreto de metas. A produção observada depende da curva de lactação, do histórico individual e do manejo. Uma falha indica que a execução ficou sem solução encontrada. [Critérios do SLSQP no SciPy](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html)


## 18. Etapas de vida

O NutriPlan habilita `heifer_I`, `heifer_II`, `heifer_III` e `dry_cow` no mesmo motor NASEM. Novilhas usam `GROWING` ou `CLOSE_UP`; a vaca seca usa `CLOSE_UP`. As exigências incluem mantença, crescimento, gestação e atividade; a lactação é zero. Não há meta, piso nem fronteira de leite nesses estágios.

Para novilha e vaca seca sem dieta atual, a FDN da dieta é obrigatória: o consumo estimado pelo NASEM depende da FDN. Com uma dieta atual, a FDN é derivada da composição. As emissões também são específicas do estágio. Novilhas usam `EntericMethaneCalculator.calculate_heifer_methane` e `ManureExcretionCalculator.calculate_heifer_manure`; vacas secas usam as rotas de `calculate_cow_methane`/`calculate_cow_manure` com `is_lactating=False`. As estimativas alimentam a restrição de energia líquida e o resultado da formulação.

O formulário adapta os campos por categoria: lactantes mantêm produção atual, meta, composição, leite e process P; novilhas mostram o ganho diário em kg/dia; vacas secas mostram o intervalo entre partos e o dia de gestação. O card **Resumo das etapas** acumula, apenas na sessão atual, categoria, peso, DMI, NEL, MP e custo por animal/dia. Recarregar a página limpa o resumo. Bezerras continuam fora do escopo e não usam o `RationOptimizer`.
