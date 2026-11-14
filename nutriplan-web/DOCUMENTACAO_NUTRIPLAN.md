# Documentação do NutriPlan

Estado verificado em 13/11/2026. Aplicação local de Pesquisa Operacional para formular dietas de menor custo para vacas leiteiras em lactação.

## 1. Escopo e fundamento

O NutriPlan usa a implementação instalada do RuFaS e seu padrão NASEM 2021. Calcular **exigências** determina as necessidades do animal informado. Formular uma **dieta** procura quantidades dos ingredientes disponíveis que atendam às restrições com menor custo. A segunda tarefa depende também de composição, preços e limites de inclusão.

Há dois perfis suportados: `first_lactation_cow` (paridade nativa 1) e `multiparous_lactating_cow` (perfil nativo de paridade 2). Ambos usam `AnimalType.LAC_COW`, `AnimalCombination.LAC_COW` e os mesmos métodos lactantes. A seleção de multípara representa esse perfil; o formulário não informa uma contagem exata de lactações superiores a dois ao motor.

As fases `fresh`, `early`, `mid` e `late` são classificações da interface. Não alteram parâmetros, não definem intervalos fixos de dias em lactação e não selecionam quatro modelos científicos diferentes. Bezerras, novilhas e vacas secas não estão habilitadas. O bloqueio de `HEIFER_I` permanece no adaptador.

## 2. Execução local

Na estrutura atual, `nutriplan-web/`, `RUFAS/`, `input/` e `venv/` ficam no mesmo projeto pai. Use `./iniciar_linux.sh` ou, com o ambiente existente:

```bash
PYTHONPATH=.. ../venv/bin/python server.py
```

O servidor escuta em `127.0.0.1`, porta 8765 por padrão; `PORT` permite outra porta. Não há necessidade de serviço externo para formular dietas ou importar CSV. O navegador precisa de JavaScript e armazenamento local para guardar preferências e configurações.

## 3. Fluxo por abas

1. **Animal**: selecione fase e paridade e informe os dados fisiológicos. Perfil da propriedade, CSV e parâmetros complementares ajudam a preencher entradas reais. O contexto alimentar e os cenários ficam em seção recolhível.
2. **Ingredientes e preços**: pesquise, filtre e selecione os alimentos; informe preços e revise limites de inclusão. O checkbox é a única seleção de ingredientes. Clique **Calcular dieta de menor custo** ao final da tabela de preços.
3. **Resultados**: a aba abre automaticamente após uma formulação bem-sucedida. Consulte dieta, custo, restrições e sensibilidade. O botão principal não é repetido nessa aba.
4. **Metodologia**: consulte oito seções sobre ciência, animal, exigências, alimentos, otimização, emissões/energia, interpretação e referências. Inclui navegação interna, fluxo, tabelas e equações confirmadas no código. Não executa otimizações ao abrir.

As abas reutilizam os controles existentes, preservam valores e não executam a otimização. Setas esquerda/direita, Home e End navegam entre abas; Tab entra nos controles. Alterar entradas após uma execução marca o resultado como desatualizado. Idioma e tema não alteram os dados científicos.

Antes da primeira execução, Resultados mostra um estado vazio. Durante o cálculo, o botão em Ingredientes fica desabilitado e mostra processamento, sem confirmação adicional. Falhas ocultam resultados anteriores; quando o campo é identificável, a aplicação abre sua aba/seção e posiciona o foco nele. Uma resposta recebida depois de alterar as entradas não pode restaurar a análise desatualizada.

## 4. Dicionário de entradas

| Entrada | Unidade / contrato | Uso no modelo instalado |
| --- | --- | --- |
| Peso corporal | kg, positivo | Manutenção, crescimento, consumo, minerais, atividade e emissões. |
| Peso adulto | kg, positivo | Tamanho adulto e crescimento relativo; reutilizável da propriedade quando representativo. |
| Dias em lactação | dias inteiros, não negativos | Consumo e componentes fisiológicos; independente da fase escolhida. |
| Produção de leite | kg/dia, não negativa | Exigências para lactação e excreção de nitrogênio. |
| Gordura, proteína verdadeira, lactose | % do leite, 0–100 | Energia do leite e, conforme o componente, proteína/minerais. Proteína verdadeira não significa proteína bruta da dieta. |
| Paridade | primeira lactação / multípara | Perfil nativo 1 / 2, independente da fase. |
| Gestação | sim/não; dia inteiro quando sim | Componentes gestacionais e correções de peso; ausência é `null`, não dia zero presumido. |
| Condição corporal | escala 1–5 | Estimativa nativa de consumo. |
| Intervalo entre partos | dias inteiros, não negativos na validação atual | Crescimento no método nativo; precisa representar uma condição utilizável pelo cálculo. |
| Alojamento | `Barn` / `Grazing` | Atividade; rótulos PT são Confinamento / Pastejo, sem mudar os identificadores. |
| Distância percorrida | m, não negativa | Energia de atividade; usar o significado solicitado pelo método instalado. |
| FDN da dieta | % MS, opcional no modo candidato | Derivada da dieta candidata ou da dieta anterior; entrada técnica explícita permanece acessível. |
| Fósforo do módulo de processo | g/dia, não negativo | Entrada complementar exigida pelo contrato `NutritionRequirements`; não é uma nova restrição independente de fósforo no otimizador. |
| Metano entérico | g/dia | Perda energética; derivado da dieta ou informado com fonte documentada. |
| Nitrogênio urinário | kg/dia | Perda energética; derivado da dieta ou informado com fonte documentada. |
| Preço | moeda/kg natural no preenchimento simples | Convertido para custo/kg MS usando a MS do alimento. Não há moeda presumida quando não foi documentada. |
| Inclusão mínima e máxima | kg MS/animal/dia | Limites por ingrediente no solver. |

Essas faixas são validações de entrada; não certificam plausibilidade zootécnica em toda a faixa. Entradas incompatíveis com as equações podem produzir erro de cálculo, que bloqueia a formulação.

## 5. Números e erros frequentes

`3,66` e `3.66` são equivalentes nos dois idiomas. Não use separadores de milhares: `1.234,56`, `1,234.56` e `1 234` são rejeitados. Um separador isolado sempre é decimal. Não informe símbolos monetários dentro do campo numérico.

O frontend envia números JSON ou `null` para opcionais vazios. O backend normaliza também strings numéricas, rejeita booleanos e números não finitos e verifica limites. Campos obrigatórios vazios permanecem pendentes; não recebem zero. A lista de variações da sensibilidade usa vírgulas para separar itens e ponto para decimais fracionários.

## 6. Perfil da propriedade e origens

Um perfil local guarda nome e até quatro campos: peso adulto, intervalo entre partos, alojamento e distância. São dados do usuário; nenhuma referência científica universal está habilitada. As referências em `data/nutritional_parameter_references.csv` continuam com `auto_fill=false`.

Salvar o perfil ou **Preencher campos vazios** completa entradas vazias do animal e atualiza valores que ainda estão identificados na sessão como provenientes do perfil. Entradas individuais são preservadas. **Restaurar valor padrão** restaura explicitamente o valor disponível no perfil para um campo, inclusive sobre um valor individual. Editar o animal não altera o perfil. Remover o perfil mantém os dados atuais do animal. Uma falha de armazenamento impede a aplicação de um perfil não salvo.

Fase, paridade, peso atual, produção, composição do leite, condição corporal e gestação permanecem individuais. Lactose e fósforo de processo continuam entradas manuais quando ausentes; não recebem valores Guelph.

Os complementares identificam Informado, Perfil da propriedade, Calculado ou Pendente. Valores aplicados do perfil mostram seu nome durante a sessão. O resumo conta todos os complementares preenchidos, informa entre parênteses quantos são automáticos e separa os pendentes dos calculados na formulação. Um campo manual válido conta como preenchido. Esses contadores se referem aos oito complementares; não dispensam os demais dados individuais necessários à análise.

O perfil salvo é aplicado aos campos assim que lido, antes da biblioteca de ingredientes responder. Sem perfil ou com falha de leitura/validação, a interface informa a situação e permite abrir sua configuração. **Configurar perfil** copia somente valores reutilizáveis válidos já informados no animal para campos ainda vazios do editor; é preciso informar o nome real e salvar. Não substitui edições em andamento no editor e não cria parâmetros presumidos.

Ao restaurar uma configuração, valores preenchidos têm prioridade e sua origem específica não é inferida pela igualdade numérica. Campos reutilizáveis vazios são completados pelo perfil salvo, inclusive ao carregar cenários antigos ou registros CSV. Cenários nomeados e snapshots antigos não preservam a origem histórica desses valores, que reaparecem como Informado. O trabalho automático de esquema 2 preserva as origens registradas do perfil quando ainda correspondem ao perfil disponível; não as infere apenas pela igualdade de números.

O catálogo de referências foi novamente inspecionado neste refinamento: todos os registros continuam com `auto_fill=false`. Os números catalogados são exemplos sem aprovação para preenchimento individual. Não há valores exibidos como Referência nem uma ação de restauração de referência científica inexistente. A restauração disponível usa exclusivamente dados reais salvos pelo usuário no perfil.

Os CSV de perfis internos do backend contêm alguns valores de referência antigos usados como fallback quando uma chave é omitida na API. O formulário envia explicitamente seus campos, inclusive `null` nos vazios, e não usa esse fallback como preenchimento científico automático. Clientes diretos da API devem informar todos os parâmetros necessários e não interpretar esses perfis internos como recomendações.

## 7. Importação CSV

Baixe na aba Animal os modelos `data/templates/animals.csv` e `data/templates/property.csv`. Contêm apenas cabeçalhos, sem dados fictícios. Use UTF-8 com BOM opcional e selecione explicitamente `;` ou `,` como separador. Os modelos usam `;`. Com separador de coluna `,`, decimais com vírgula precisam de aspas CSV.

Cabeçalho da propriedade:

```text
property_name;mature_body_weight;calving_interval;housing;distance
```

Nome e ao menos um parâmetro são obrigatórios. Os demais campos podem ficar vazios. Cabeçalho das vacas:

```text
animal_id;animal_category;lactation_subcategory;body_weight_kg;days_in_milk;milk_production;milk_fat;milk_true_protein;pregnant;day_of_pregnancy;body_condition_score_5;milk_lactose;process_based_phosphorus_requirement;mature_body_weight;calving_interval;housing;distance
```

`animal_id` é texto e preserva zeros à esquerda. Categoria usa os dois identificadores da seção 1; fase usa os quatro identificadores estáveis. `pregnant` aceita `true`/`false`: dia de gestação é obrigatório no primeiro caso e vazio no segundo. Os quatro campos reutilizáveis podem ficar vazios no arquivo animal, mantendo os valores atuais. Os demais dados individuais são obrigatórios.

A ordem das colunas pode mudar; seus nomes não podem mudar, repetir ou incluir colunas extras. Limites: 256 KiB, 500 registros e até 100 erros apresentados por tentativa. IDs e nomes precisam ser únicos, sem diferenciar maiúsculas/minúsculas. Arquivo inválido é bloqueado integralmente, com linha física, coluna e motivo.

**Validar e visualizar** não altera o formulário. Selecione um registro, compare Atual/CSV e confirme para aplicar. Se os dados atuais mudarem desde a prévia, é necessária nova revisão. Importar uma vaca mantém dieta, emissões explícitas, ingredientes e preços; revise sua compatibilidade. Importar uma propriedade substitui seu perfil e editor, mantendo o animal. Não existe processamento em lote, importação genérica JSON ou exportação CSV de resultados. `POST /api/csv-preview` valida sem guardar o arquivo no servidor.

## 8. Exigências nutricionais

`services/nutrition.calculate` chama `NASEMRequirementsCalculator.calculate_requirements`. São expostos energia líquida total (Mcal/dia), proteína metabolizável (g/dia), cálcio e fósforo (g/dia) e consumo estimado de MS (kg/dia).

O total de energia reúne manutenção, crescimento, gestação, lactação e atividade calculados pelo RuFaS. Peso, maturidade e paridade influenciam crescimento; a gestação é condicionada às entradas individuais. O consumo lactante depende do perfil fisiológico. A exigência de proteína inclui componentes de manutenção, crescimento, gestação e leite e depende também da FDN dietética.

A prévia isolada não substitui a configuração da ração. Sem contexto dietético completo, exigências dependentes da dieta podem permanecer pendentes. No modo candidato, a proteína é recalculada usando a FDN da dieta em avaliação e novamente na dieta final. O adaptador confirma que a FDN final não alterou as exigências de consumo e energia usadas na otimização; divergência bloqueia o resultado.

FDN, FDN de forragem e gordura são restrições da ração. Não são apresentadas como novas exigências animais calculadas isoladamente. Métodos nativos adicionais, como aminoácidos, não significam que o NutriPlan imponha suas restrições; o conjunto exposto está descrito abaixo.

## 9. Ingredientes e matéria seca

A composição vem de `../input/data/feed/NASEM_Comp_with_TDN.csv`, selecionada pelo ID RuFaS exato. Traduções alteram apenas o nome exibido. A composição catalogada não substitui análise do alimento real.

Para quantidade `xᵢ` em kg MS/dia e fração de MS `dᵢ = DMᵢ/100`, a quantidade natural é `xᵢ/dᵢ`. Para um nutriente informado em % MS, a soma direta é `Σ xᵢ·aᵢ/100`, em kg/dia. A FDN dietética é `100·FDN_kg/Σxᵢ`.

Essas somas descrevem composição bruta. Proteína metabolizável, energia e minerais digestíveis usam os métodos nativos de aproveitamento, não apenas percentuais. Os totais brutos de cálcio/fósforo exibidos em kg/dia não são diretamente comparáveis às exigências digestíveis em g/dia.

## 10. Formulação de menor custo

O custo é `min Σ cᵢxᵢ`, com `cᵢ = preço_naturalᵢ/dᵢ`. Cada `xᵢ` está entre seus limites de inclusão em kg MS/dia. O otimizador nativo `RationOptimizer` usa `scipy.optimize.minimize(method="SLSQP")`. A função objetivo é linear nos preços, mas as restrições NASEM tornam o problema não linear.

São selecionadas onze restrições: cálcio, fósforo, proteína metabolizável mínima/máxima, FDN mínima/máxima, FDN de forragem, gordura máxima, consumo mínimo/máximo e energia líquida NASEM. Coeficientes e limites permanecem nos métodos/constantes nativos, sem reescrita científica no frontend.

O adaptador verifica o sucesso do solver, recalcula todas as folgas (tolerância absoluta `1e-4` nas unidades de cada restrição), confirma limites de inclusão e reconcilia o custo com as quantidades. Uma folga não negativa atende à desigualdade; resultados fora da tolerância são bloqueados. Sucesso numérico não prova mínimo global, segurança biológica ou desempenho produtivo.

## 11. Emissões e energia da dieta candidata

Sem dieta anterior e sem FDN/emissões explícitas, `CandidateRationOptimizer` reutiliza as funções nativas por dieta candidata. A FDN vem da combinação dos alimentos; metano vem da rota IPCC para vacas lactantes de `EntericMethaneCalculator`; nitrogênio urinário vem de `ManureExcretionCalculator.calculate_cow_manure`.

Essas duas rotas selecionadas não dependem de energia metabolizável previamente calculada. Campos energéticos indisponíveis são sinalizados como não disponíveis internamente, e não preenchidos como emissões zero. Não são usados parâmetros lactantes para habilitar novilhas.

`NutritionSupplyCalculator.calculate_NASEM_digestible_energy` calcula a energia digestível da ração considerando composição, consumo, peso e amido. `calculate_NASEM_metabolizable_energy` desconta metano e urina; `calculate_NASEM_net_energy` aplica a eficiência nativa de 0,66. Em base diária, a operação implementada é `EM = ED − 13,28·CH₄_kg − 0,0146·N_urinário_g`, seguida de `EL = 0,66·EM`. A API de emissões usa CH₄ em g/dia e N em kg/dia; as conversões ocorrem no método nativo. As perdas são descontadas uma vez.

O docstring nativo desses métodos menciona Mcal/kg, mas as operações somam energia das quantidades diárias e o otimizador compara o resultado com a exigência total diária. Esta documentação explicita a base diária efetivamente usada; não altera o código científico.

O ponto inicial é determinístico e baseado nos limites/consumo nativo. Não há um laço externo que alterna entre dietas anteriores; as dependências são avaliadas dentro das restrições. A reavaliação final usa a própria solução.

Após sucesso, a FDN e as emissões calculadas são apresentadas nos respectivos campos, com origem Calculado e indicação de dieta candidata/anterior. A FDN da dieta anterior também pode aparecer na prévia de exigências quando o backend já a resolveu. Não há número exibido antes de existir uma derivação válida. Uma entrada explícita existente não é substituída.

Os valores automáticos são apenas apresentação de uma derivação: o payload e os cenários continuam com FDN `null` e emissões vazias nesse modo. A próxima formulação recalcula as dependências, sem congelar emissões anteriores nem aplicar perdas novamente. Alterar uma entrada invalida/limpa valores derivados; a FDN de uma dieta anterior válida é atualizada pela rota existente. Editar um campo calculado converte aquele campo em entrada explícita, sujeita às mesmas validações e exigência de fonte já existentes. Parâmetros fisiológicos manuais não são alterados pela troca de fase.

Dieta anterior opcional mantém o caminho legado: sua composição deriva FDN e emissões, que representam esse contexto anterior. Valores explícitos exigem os dois parâmetros de emissão e fonte; não podem ser combinados com dieta anterior. FDN manual sem dieta anterior exige emissões explícitas. Misturar contextos incompatíveis é rejeitado. A opção avançada não é recomendação de valores fixos.

Isso não executa a simulação completa de um lote `Pen`, suas transições diárias ou todos os módulos ambientais do RuFaS. As emissões são estimativas dos caminhos selecionados, não medições nem validação ambiental integral.

## 12. Interpretação e sensibilidade

A dieta informa kg MS e kg natural por ingrediente, custo diário por animal, consumo, composição e atendimento das restrições. Leia as unidades e a origem dos preços. Valores sem moeda documentada aparecem como unidades monetárias, sem presumir reais. A projeção mensal multiplica por 30; não estima lucro ou resposta de leite.

Energia líquida e proteína metabolizável aparecem nas exigências e no diagnóstico de restrições; os totais de composição não são uma análise completa de sua oferta aproveitável. A sensibilidade repete otimizações variando o preço selecionado e apresenta viabilidade/custo por experimento; não mede resposta biológica e não substitui o resultado-base.

A comparação com dieta anterior só faz sentido com preços elegíveis, unidades, datas, local e fontes compatíveis. Ausência dessa base não invalida automaticamente a formulação nutricional. Falha do solver também não prova que nenhuma dieta viável exista: ingredientes, limites e ponto de partida podem impedir encontrá-la.

## 13. Persistência e compatibilidade

Preferências, perfil e cenários ficam no navegador e na origem local da aplicação. O perfil usa `nutriplan.property.v1`; o trabalho atual e os cenários mantêm seus contratos versionados. Limpar dados do navegador ou usar outra porta pode tornar esses registros indisponíveis. Não há sincronização remota.

### Salvamento automático privado

O trabalho atual usa a chave histórica `nutriplan.working.v1`, agora com **`schema_version: 2`** no conteúdo. A chave foi mantida para localizar configurações anteriores. O perfil aplicado permanece em `nutriplan.property.v1`; cenários nomeados ficam em `nutriplan.scenarios.v1`. Idioma e tema usam chaves próprias e não são removidos pelo controle de limpeza da formulação.

São preservados fase, paridade, peso, todos os parâmetros fisiológicos/complementares, checkbox de gestação inclusive em edição incompleta, ingredientes por ID RuFaS, disponibilidade, limites de inclusão, preços e proveniência, dieta anterior e fonte, emissões explícitas e fonte, registros de preços importados e nome/descrição da configuração. O rascunho do editor da propriedade também é guardado, mesmo antes de salvar/aplicar o perfil. A ação **Salvar perfil** continua definindo o perfil reutilizável; editar seu rascunho não o transforma silenciosamente em entrada científica do animal.

Os valores são guardados na representação informada, incluindo vírgula decimal e zeros finais. Texto numérico ainda incompleto pode ser restaurado como rascunho: não é convertido em zero nem declarado válido para otimização. Os parsers numéricos existentes continuam validando antes do cálculo. A origem de campos aplicados automaticamente pelo perfil é preservada quando corresponde ao perfil disponível. Valores calculados de FDN/emissões continuam excluídos das entradas explícitas persistidas, para serem recalculados pela dieta.

Alterações são agrupadas por **400 ms** de inatividade. O estado é comparado ao último salvo, evitando gravar novamente apenas por navegar, trocar idioma ou renderizar resultados. `pagehide` e a transição da página para segundo plano fazem o salvamento final, incluindo a última edição. O estado do salvamento é mostrado abaixo das abas. Uma falha de acesso/quota é informada; o formulário permanece na tela e o snapshot anterior não é apagado.

### Restauração e compatibilidade

Ao abrir, o frontend lê e valida o snapshot local e aplica os campos, sem enviar a configuração à API de validação de cenários e sem executar otimização. A prévia nutricional segue utilizando o servidor local, como antes. A biblioteca fornece os nomes e a composição correspondentes aos IDs estáveis; o conteúdo pessoal não vira uma referência genérica nem um arquivo do projeto.

A validação local verifica versão, identificação da aplicação, método, biblioteca, categorias/fases, estrutura de parâmetros, tipos, quantidade de ingredientes, IDs únicos/conhecidos e formato das fontes. O hash da biblioteca, quando disponível nas duas pontas, também participa da compatibilidade. Um snapshot antigo de versão 1 é adaptado em memória, sem sobrescrever o original durante a leitura; uma nova edição grava a versão 2.

Snapshots corrompidos, de versão desconhecida ou incompatíveis são preservados na chave original. O salvamento fica pausado, com mensagem visível, para impedir que um formulário vazio substitua os dados. Se a incompatibilidade só for identificada após carregar a biblioteca, os campos já restaurados também permanecem disponíveis para revisão. Não existe reparação automática de JSON corrompido. Cenários nomeados corrompidos são mantidos e não são substituídos por uma lista vazia ao tentar salvar outro cenário.

Resultados de otimização, diagnóstico antigo, valores do solver e respostas de sensibilidade não são persistidos. Ao abrir novamente, a interface informa que a configuração foi restaurada e exige novo cálculo. Com entradas e biblioteca compatíveis, basta acessar **Ingredientes e preços** e calcular; o sucesso continua abrindo **Resultados**. Alterações invalidam a análise anterior.

### Controles locais

Em **Animal → Dados neste navegador**:

- **Restaurar última configuração** fica disponível quando há um snapshot compatível e alterações ainda não salvas. A restauração pede confirmação antes de descartar essas alterações. Não é um histórico de versões: após o salvamento automático, a última configuração é a edição atual.
- **Limpar dados salvos** pede confirmação e remove somente as três chaves de formulação, perfil e cenários do NutriPlan. Mantém idioma, tema, outros armazenamentos e os campos atualmente na tela. O salvamento fica desativado para esses campos até uma nova edição, evitando recriar os dados apagados ao fechar a aba. Uma nova edição volta a salvá-los, conforme a mensagem exibida. Se houver falha na limpeza, o formulário é mantido e a aplicação tenta recompor as chaves já removidas.

### Privacidade e limites

Nenhuma configuração pessoal é adicionada ao código-fonte, CSVs, fixtures ou arquivos do projeto. O mecanismo de persistência não escreve no servidor, não cria conta/banco de dados e não envia dados a serviços externos. Os cálculos, prévias e operações de cenários solicitadas continuam usando as APIs locais existentes; esses envios para processamento local não são armazenamento remoto. Não são emitidos logs de conteúdo dos snapshots.

`localStorage` permanece após recargas e encerramento normal do navegador no mesmo perfil, computador e origem. Trocar protocolo, `localhost`/`127.0.0.1`, porta, perfil ou navegador acessa outro armazenamento. Modo privado, bloqueio de armazenamento, limpeza dos dados do site, remoção do perfil e limites de quota podem impedir a retenção. O armazenamento não é um cofre criptografado nem uma cópia de segurança externa; quem tem acesso ao mesmo perfil/origem pode acessar esses dados.

### Verificação da persistência

A suíte atual contém **56 testes**, incluindo `tests/test_local_persistence.py`: debounce e salvamento final, snapshot completo, restauração sem requisições de validação/otimização, números com vírgula, gestação incompleta, rascunho da propriedade, migração da versão 1, proteção contra JSON corrompido/versão futura/ID desconhecido, erro de armazenamento, confirmação de limpeza/restauração e preservação das preferências. A otimização de configurações serializadas e restauradas foi comparada nas duas paridades, com custos reproduzidos e restrições atendidas. Os dados vêm exclusivamente do fixture científico já existente e de valores sintéticos; nenhuma configuração pessoal foi criada como fixture.

No navegador isolado, todos os campos e cinco preços foram comparados antes/depois da recarga, incluindo a última edição. A dieta restaurada executou a otimização e atendeu às onze restrições. Fechar a aba e abrir uma nova no mesmo perfil restaurou a configuração e manteve o resultado antigo oculto. Limpar os dados manteve o formulário em uso; após recarga, os campos/ingredientes ficaram vazios e idioma/tema foram preservados. O encerramento/reinício do processo inteiro do navegador não é controlável pelas ferramentas desta sessão e não foi automatizado; o teste realizado foi fechamento/reabertura da aba com novo contexto JavaScript e o mesmo armazenamento persistente.

Fases persistem por identificadores estáveis. Um cenário antigo sem fase mantém os valores fisiológicos e exige seleção manual, sem classificação automática por dias em lactação. Resultados não são restaurados como se fossem novos cálculos. Carregar cenário mantém a prioridade de seus valores preenchidos; lacunas reutilizáveis podem ser completadas pelo perfil da propriedade.

## 14. Arquitetura e manutenção

`index.html` concentra os controles, internacionalização e persistência; `styles.css` fornece tokens e temas. `server.py` serve a interface e as APIs locais. `services/numbers.py` centraliza números Python; `nutrition.py` valida perfis/exigências; `native_ration.py` integra a otimização; `emissions.py` resolve dependências dietéticas; `csv_import.py` valida importação. Preços, cenários, sensibilidade e comparação econômica permanecem em serviços próprios.

O motor original fica em `../RUFAS/`. Atualizações do RuFaS exigem reexecutar regressões e revisar contratos, unidades, métodos privados reutilizados e critérios de restrição. A biblioteca de alimentos precisa corresponder à versão instalada. Não alterar equações para ajustar resultados esperados.

## 15. Verificação da fase 15E

Comando da suíte atual:

```bash
env -u DISPLAY MPLBACKEND=Agg MPLCONFIGDIR=/tmp/nutriplan-mpl PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. ../venv/bin/python -m unittest discover -s tests -q
```

Resultado em 13/11/2026: **32 testes aprovados**. Incluem números e proteína do leite, ambas as paridades, emissões pela dieta candidata, reconciliação energética, custos anteriores à fase 15A, Guelph do manifesto retido, cenários/sensibilidade, perfil, CSV/backend e navegação sem cálculo.

No navegador real foram verificados CSV inválido e válido, prévia/seleção/confirmação, duas paridades sem dieta anterior nem emissões manuais (11/11 restrições em cada execução), PT/EN, sensibilidade com cinco variações viáveis, abas, temas claro/escuro/automático e largura móvel de 390 px. Os custos com os limites padrão da interface diferem dos limites específicos do fixture; não são uma nova referência científica.

Os dados Guelph de `data/reference_rations.json` e `data/experimental_validation_manifest.json` continuam referências computacionais internas. Não existe botão de preenchimento demonstrativo. Regressão preservada comprova comportamento computacional nesse caso, sem equivaler a validação biológica independente.

Os documentos históricos e a suíte antiga de 96 testes não estavam presentes nesta cópia ao retomar a fase 15. Não foram reconstruídos como se fossem evidências executadas. O número acima se refere à suíte atual disponível e complementada; a recuperação desses arquivos depende de uma cópia confiável.

## 16. Limitações e critérios de uso

Exigir entradas fisiológicas reais, composição representativa, preços válidos e revisão profissional das quantidades. Não interpretar nenhuma classificação de fase como prescrição. A aplicação não cobre todos os nutrientes, aminoácidos, respostas produtivas, manejo de lote, variações individuais ou todas as categorias animais possíveis do RuFaS.

Valores derivados são estimativas. Não há referência automática universal aprovada para preencher campos ausentes. A viabilidade matemática, as regressões computacionais e a validação biológica são evidências diferentes e precisam permanecer separadas.

### Verificação adicional da etapa 16D

A tela Metodologia usa o mesmo sistema PT/EN e tokens de tema da aplicação, sem nova dependência, API ou alteração científica. As âncoras `#methodology-science`, `animal`, `requirements`, `feeds`, `optimization`, `energy`, `results` e `references` (todas com o prefixo `methodology-`) selecionam a aba correspondente e posicionam o foco na seção. Outros fragmentos não selecionam essa aba.

Os testes novos verificam as oito seções/links, ausência de campos de entrada na Metodologia, tradução de todos os seus textos visíveis e retorno PT→EN→PT, além de navegação por fragmento sem requisição de cálculo. O teste de abas foi ampliado para a quarta aba. A suíte atual passou com **34 testes**, incluindo as regressões nutricionais anteriores. Foram mantidas as equações, APIs e resultados do motor.

No navegador, a navegação entre Resultados e Metodologia, a troca PT/EN e a navegação interna preservaram exatamente os valores dos controles, o custo e o texto das onze restrições da execução anterior. O acesso direto a `#methodology-energy` selecionou a aba e posicionou o foco na seção. Foram inspecionados os temas claro/escuro/automático e a largura móvel de 390 px, com abas em duas linhas e largura do documento de 375 px, sem transbordamento horizontal. Não houve erros ou avisos no console na sessão final.

### Refinamento de valores e fluxo de otimização — 13/11/2026

O botão único passou para o final de Ingredientes e preços. A validação reutiliza os parsers e o backend existentes, acrescentando contexto de aba/campo aos erros. A API científica, os serviços de produção e o RuFaS não foram modificados. O perfil agora completa lacunas também na restauração, mantendo entradas individuais e mostrando valores derivados conhecidos nos controles.

A suíte atual contém **41 testes**. Os novos casos cobrem solicitação única durante processamento, abertura de Resultados somente após sucesso, foco no animal quando a validação falha, erro do solver sem resultados antigos, descarte de resposta após edição e mensagem clara em falha de conexão. Foram ampliados os testes do perfil para atualização de valores automáticos sem substituir os manuais, exposição dos derivados e exclusão destes das entradas explícitas. As regressões científicas retidas continuam incluídas.

No navegador foram exercitados o estado vazio, perfil com quatro campos, edição/restauração, troca de fases e paridade, gestação, persistência com campo vazio e campo manual, preços ausentes e proteína inválida. As duas paridades formularam sem dieta anterior nem emissões manuais, com onze restrições atendidas; repetir a multípara preservou o custo. Um conjunto sem ingredientes suficientes para atender ao modelo produziu falha segura do solver, permanecendo em Ingredientes e ocultando a análise anterior. As quantias usadas nesses testes pertencem ao caso de regressão, sem serem padrões de preenchimento do produto.

PT/EN e temas claro, escuro e automático foram verificados. Nas larguras de 1440, 1024, 768 e 390 px, a largura do documento permaneceu abaixo da viewport; o botão ficou ao final da tabela, com largura adaptada no celular. A sessão final não apresentou erros ou avisos no console. Uma interrupção do servidor temporário durante a revisão também demonstrou a preservação dos campos sem reexibir resultados; a mensagem de conexão foi corrigida e recebeu regressão automatizada. A execução final com os dados restaurados voltou a atender às onze restrições.

### Correção do carregamento dos valores reutilizáveis — 13/11/2026

Foi rastreado o fluxo `loadPropertyProfile` → `applyPropertyProfile` → inputs → `collectProfileParameters` → validação de `services/nutrition.py`. O diagnóstico distingue ausência de dados de falha de carregamento:

| Hipótese | Evidência e conclusão |
| --- | --- |
| Catálogo sem números utilizáveis | `data/nutritional_parameter_references.csv` tem quatro candidatos numéricos e um candidato categórico, mas todos os registros têm `auto_fill=false`. Os candidatos são exemplos ou não possuem validação aplicável. Não existe referência aprovada para preencher o formulário. |
| Nenhum perfil configurado | Não há perfil de propriedade pré-configurado. O perfil real fica em `localStorage`, chave `nutriplan.property.v1`, por navegador e origem (protocolo, host e porta). Uma origem sem esse registro reproduziu o estado de sete pendências. O servidor não permite confirmar se existe um perfil no navegador particular do relato; não foi presumida sua ausência. |
| Valores salvos não chegavam imediatamente ao animal | O carregador lia o perfil e preenchia apenas seu editor. A aplicação ao animal ficava na continuação de `fetch('/api/nasem-feeds')`. Uma resposta demorada ou falha dessa requisição deixava campos reutilizáveis vazios mesmo com perfil válido. Um teste antes da correção confirmou intervalo, alojamento e distância vazios após carregar um perfil que os continha. |
| Mecanismo desconectado dos inputs | A função de aplicação já escrevia nos inputs corretos e preservava campos manuais. O defeito estava na ordem de inicialização. Agora `loadPropertyProfile` aplica o perfil validado imediatamente, sem depender dos ingredientes nem executar otimização. |
| Critérios por animal impedindo preenchimento | Os quatro campos do perfil são dados fornecidos pelo usuário para a propriedade e não têm filtro oculto por fase/paridade. As duas paridades usam os caminhos lactantes existentes. Os exemplos do catálogo mencionam condições como Holstein/freestall, mas continuam não aprovados; selecionar fase/paridade não os torna referências aplicáveis. |

O contador antigo destacava apenas aplicações automáticas: sete campos manuais válidos ainda produziam “0 automáticos”. O resumo corrigido mostra, por exemplo, `7 preenchidos (0 automáticos) · 0 pendentes · 1 calculado na formulação`. Sem qualquer fonte válida, continua mostrando sete pendências, acompanhado da explicação de perfil/referências ausentes. Um perfil completo em uma análise vazia produz quatro preenchidos automáticos, três pendências individuais e FDN calculada na formulação.

| Parâmetros | Fonte efetivamente permitida | Comportamento |
| --- | --- | --- |
| Peso adulto, intervalo entre partos, alojamento e distância | Perfil real salvo pelo usuário neste navegador/endereço | Aparecem nos próprios campos ao carregar e reutilizar o perfil. Edições individuais têm prioridade. Restaurar usa o valor salvo verificável. |
| FDN dietética | Dieta anterior válida ou dieta candidata, pelos métodos nativos já integrados | O valor derivado conhecido é exibido; antes de existir a dieta necessária, não recebe número presumido. |
| Metano e N urinário | Caminhos nativos de emissões já existentes | Permanecem derivados da dieta no modo automático; apresentação e exclusão dos valores automáticos do payload explícito foram preservadas. |
| Escore corporal e lactose | Informação individual do usuário | Não há referência individual aprovada no catálogo. Permanecem pendentes quando ausentes. |
| Fósforo do módulo de processo | Dado fornecido com fundamento ou saída aplicável do módulo de processo | O formulário atual não fornece o estado necessário para derivação autônoma; não foi inserido zero nem um valor do fixture. |

A hierarquia preserva dado individual editado, perfil salvo, derivação nativa e, somente se houvesse uma aprovada, referência aplicável. Não foram criados números por fase, referências por raça ou novos cálculos. O backend continua tratando `null` explícito como dado ausente, sem substituir pelos valores de exemplo dos perfis internos. Não há restauração de referência científica oferecida quando tal referência não existe; a restauração disponível identifica o perfil do usuário como origem.

Verificação: **45 testes aprovados** pelo comando da seção 15, incluindo novos casos para aplicação imediata do perfil, contagem de valores manuais nos dois idiomas, diagnóstico sem perfil, indicação de perfil inválido e preservação de ausências no backend nas duas paridades. As regressões anteriores de custos, exigências, energia, emissões e restrições continuaram aprovadas.

No navegador isolado, foi verificado configurar o perfil a partir de valores manuais reais do formulário, salvar, carregar, editar, preservar edição nas trocas de paridade/fase e restaurar o valor salvo. Uma falha HTTP 503 deliberada somente no servidor temporário de teste impediu o carregamento dos ingredientes; ainda assim, os quatro valores salvos apareceram no animal com sua origem. O servidor de produção não foi alterado. Foram conferidos PT/EN, temas claro/escuro e a indicação de campos efetivamente sem referência. Valores usados nesses testes não são padrões distribuídos com a aplicação.

## 17. Referências verificadas

- National Academies of Sciences, Engineering, and Medicine. 2021. *Nutrient Requirements of Dairy Cattle: Eighth Revised Edition*. National Academies Press. [DOI 10.17226/25806](https://doi.org/10.17226/25806); [texto publicado no NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/NBK600603/).
- RuFaS — Ruminant Farm Systems: [repositório oficial](https://github.com/RuminantFarmSystems/RuFaS) e [documentação oficial](https://ruminantfarmsystems.github.io/RuFaS/). A descrição desta integração é fundamentada na cópia instalada, não presume funcionalidades de versões futuras.
- Evidência local: `RUFAS/biophysical/animal/nutrients/nasem_requirements_calculator.py`, `nutrition_supply_calculator.py`, `ration/ration_optimizer.py`, `digestive_system/enteric_methane_calculator.py`, `digestive_system/manure_excretion_calculator.py` e os serviços/testes descritos acima, todos relativos à raiz correspondente.
