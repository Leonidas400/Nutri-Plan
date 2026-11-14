# NutriPlan

Aplicação local para formular dietas de menor custo para vacas leiteiras em lactação com exigências NASEM 2021, biblioteca de ingredientes e otimizador nativo do RuFaS.

Consulte o manual em [DOCUMENTACAO_NUTRIPLAN.md](DOCUMENTACAO_NUTRIPLAN.md) para parâmetros, unidades, metodologia e limitações.

## Funcionalidades

- Quatro fases de lactação na interface e perfis de primeira lactação ou multípara.
- Cálculo de exigências, seleção de ingredientes e otimização com diagnóstico de restrições.
- Estimativa de FDN, metano e nitrogênio urinário pela dieta candidata quando não há dieta anterior.
- Ponto inicial determinístico no adaptador de otimização, para repetir resultados com entradas idênticas sem depender da inicialização aleatória do RuFaS.
- Perfil local da propriedade para reutilizar valores informados, preservando os dados individuais da vaca.
- Dieta anterior opcional, cenários locais, análise de sensibilidade, comparação econômica quando os preços são elegíveis, pt-BR/en-US e temas claro/escuro/automático.

## Requisitos e início rápido

O diretório `nutriplan-web/` deve estar dentro do projeto RuFaS, com a biblioteca NASEM de alimentos e as dependências Python instaláveis pelo projeto pai. O iniciador Linux usa Python 3.13 e `uv`; a primeira execução pode precisar de rede. A aplicação depois funciona localmente em `127.0.0.1`.

```bash
cd nutriplan-web
./iniciar_linux.sh
```

Abra `http://127.0.0.1:8765`. Com o ambiente virtual já preparado, pode iniciar com `PYTHONPATH=.. ../venv/bin/python server.py`.

## Entradas numéricas

Nos campos de animal, preços e quantidades, ponto e vírgula são aceitos como separador decimal: `3.66` e `3,66` representam o mesmo valor nos dois idiomas. Não use separadores de milhares; entradas como `1.234,56`, `1,234.56` ou `1 234` são rejeitadas. Um único separador sempre indica decimais (`1,234` significa `1.234`).

O frontend envia números JSON nos campos preenchidos e `null` nos opcionais vazios. O backend também aceita strings numéricas conforme esse contrato e rejeita booleanos, números não finitos e valores fora dos limites do campo. Dias em lactação, dias de gestação e intervalo entre partos precisam ser inteiros. Campos obrigatórios vazios ficam pendentes; não são convertidos em zero.

A FDN pode continuar vazia no modo de dieta candidata, assim como as emissões estimadas automaticamente. As unidades não mudam: composição do leite em %, pesos em kg, preços da tabela por kg natural e quantidades da dieta em kg MS/dia. A lista de variações de sensibilidade mantém seu contrato próprio: vírgulas separam os itens; para variações fracionárias, use ponto decimal.

## Navegação por abas

**Animal** reúne dados fisiológicos, perfil da propriedade, importação CSV, complementares e contexto alimentar/cenários. **Ingredientes e preços** mantém catálogo, filtros, seleção, preços e o botão **Calcular dieta de menor custo** ao final da tabela. **Resultados** abre automaticamente após sucesso e reúne dieta, restrições e sensibilidade. Durante o cálculo, o botão é desabilitado; erros direcionam à aba/campo correspondente e ocultam a análise anterior. Trocar de aba mantém os mesmos controles e valores; isso não executa cálculos. Use setas esquerda/direita ou Home/End quando o foco estiver nas abas, e Tab para acessar o conteúdo. Alterar dados após uma otimização marca os resultados como desatualizados e exige novo cálculo.

**Metodologia** explica o caminho dos dados até a dieta, em oito seções bilíngues com navegação interna, tabelas, equações verificadas e referências. Abrir essa aba preserva a análise e não executa otimizações. Links como `#methodology-energy` abrem diretamente a seção correspondente.

## Salvamento automático neste navegador

A configuração completa da formulação é salva automaticamente em `localStorage`: animal, complementares, ingredientes/IDs, preços, limites, dieta anterior, entradas explícitas e rascunho da propriedade. As gravações são agrupadas durante a digitação e finalizadas ao sair da página. Ao reabrir no mesmo navegador/perfil/endereço, os campos são restaurados sem executar otimização nem recuperar resultados antigos como novos.

Em **Animal → Dados neste navegador**, é possível restaurar a última configuração ainda diferente da edição atual ou limpar os dados salvos, mediante confirmação. Limpar mantém os campos em uso e desativa seu salvamento até uma nova edição; preserva idioma e tema. Dados incompatíveis/corrompidos são mantidos e bloqueiam sua substituição automática.

O conteúdo fica somente no armazenamento do navegador, nunca em CSVs, fixtures ou arquivos de configuração do projeto. A chave `nutriplan.working.v1` usa esquema interno 2 e lê o esquema antigo 1. Não há sincronização externa. Modo privado, limpeza dos dados do site, outra porta/endereço ou outro perfil podem impedir a recuperação. Consulte o manual para limites de privacidade, compatibilidade e os testes realizados.

## Perfil da propriedade e preenchimento

Abra **Perfil da propriedade**, informe um nome e preencha os dados conhecidos que representem o rebanho ou sistema em análise. É possível salvar apenas parte dos quatro campos. O perfil é informado pelo usuário; não constitui uma referência nutricional universal.

| Classificação | Campos e tratamento |
| --- | --- |
| Individuais | Fase da lactação, paridade, peso corporal, dias em lactação, produção, gordura e proteína verdadeira do leite, condição corporal e gestação. Permanecem específicos da análise; a fase não preenche valores fisiológicos. |
| Reutilizáveis da propriedade | Peso adulto (kg), intervalo entre partos (dias), alojamento (`Barn`/`Grazing`) e distância percorrida (m). Use valores representativos do animal/lote e ajuste individualmente quando necessário. |
| Complementares individuais | Lactose (%) e fósforo do módulo de processo (g/dia). Continuam manuais e obrigatórios no cálculo atual; não são copiados de exemplos ou do perfil da propriedade. |
| Derivados | FDN e emissões podem vir da dieta candidata ou da dieta atual registrada; consumo e exigências são calculados pelos métodos nativos. As entradas explícitas avançadas continuam disponíveis. |
| Referência científica automática | Nenhuma habilitada: as referências locais em `data/nutritional_parameter_references.csv` permanecem com `auto_fill=false`. Não há valores Guelph, raça ou fase usados como padrões universais. |

**Salvar perfil** guarda os dados neste navegador e preenche campos vazios ou ainda identificados na sessão como provenientes do perfil. Valores individuais são mantidos. **Preencher campos vazios** repete essa aplicação. Nos complementares, **Restaurar valor padrão** aplica explicitamente o valor salvo de um campo, inclusive quando existe um valor individual diferente. Editar o animal não modifica o perfil; para editar o perfil, altere seus próprios campos e salve novamente.

O perfil preenche campos reutilizáveis vazios assim que é lido, sem esperar a biblioteca de ingredientes, e também ao restaurar configuração, cenário ou CSV. Valores já preenchidos têm prioridade e não são reclassificados a partir de igualdade numérica com o perfil.

Os complementares mostram **Informado**, **Perfil da propriedade**, **Calculado** ou **Pendente**. O resumo conta todos os campos preenchidos, separando automáticos, pendentes e os que serão calculados na formulação. Cenários nomeados antigos aparecem como informados; o trabalho automático de esquema 2 também preserva origens registradas do perfil, sem inferi-las só pela igualdade numérica. FDN e emissões derivadas conhecidas aparecem nos campos; alterações invalidam essas derivações, e elas não são salvas/enviadas como entradas explícitas. **Referência** não é exibida: o catálogo atual permanece sem referências aprovadas para preenchimento automático. Se faltar um dado obrigatório, a prévia e a validação indicam o campo pendente.

Sem perfil salvo neste navegador/endereço, use **Configurar perfil**. A ação abre o editor e aproveita valores reutilizáveis válidos já informados, sem preencher campos com exemplos. Salve o perfil com os dados reais da propriedade. Trocar entre `localhost` e `127.0.0.1`, portas ou navegadores utiliza outro armazenamento local. Escore corporal, lactose e fósforo de processo permanecem individuais e pendentes quando não há dado válido.

Há um perfil local por navegador e endereço da aplicação, na chave `nutriplan.property.v1`. Ele persiste após recarga; limpar dados do navegador pode removê-lo. **Remover perfil salvo** mantém os valores atuais do animal. Uma falha de armazenamento é informada e não aplica valores de um perfil que não pôde ser salvo. O perfil não é sincronizado nem enviado como um novo modelo ao backend: somente os parâmetros aplicados seguem pelo contrato existente.

## Importação CSV padronizada

Em **Importar dados CSV**, baixe o modelo de vacas ou da propriedade. Os arquivos locais em `data/templates/animals.csv` e `data/templates/property.csv` contêm somente o cabeçalho, sem dados de exemplo. Salve a planilha como UTF-8 (BOM opcional), selecione o tipo e o separador (`;` ou `,`) e clique **Validar e visualizar**. Os modelos usam `;`; decimais com vírgula precisam estar entre aspas se o separador de colunas também for vírgula.

O modelo de propriedade usa `property_name;mature_body_weight;calving_interval;housing;distance`. Nome e ao menos um parâmetro são obrigatórios; os demais valores podem ficar vazios. As unidades são kg, dias e metros, e alojamento usa `Barn` ou `Grazing`.

O modelo de vacas exige os cabeçalhos abaixo (a ordem pode mudar, sem renomear, repetir ou acrescentar colunas):

```text
animal_id;animal_category;lactation_subcategory;body_weight_kg;days_in_milk;milk_production;milk_fat;milk_true_protein;pregnant;day_of_pregnancy;body_condition_score_5;milk_lactose;process_based_phosphorus_requirement;mature_body_weight;calving_interval;housing;distance
```

`animal_id` identifica cada registro sem duplicações e preserva zeros à esquerda. `animal_category` aceita `first_lactation_cow` ou `multiparous_lactating_cow`; a fase aceita `fresh`, `early`, `mid`, `late`. `pregnant` usa `true` ou `false`: dia de gestação inteiro é obrigatório quando verdadeiro e fica vazio quando falso. Peso corporal é positivo em kg; produção de leite está em kg/dia; gordura, proteína verdadeira e lactose em %; escore corporal em escala 1–5; fósforo de processo em g/dia. Dias em lactação e intervalo entre partos são inteiros. Campos de peso adulto, intervalo, alojamento e distância podem ficar vazios no arquivo animal: nesse caso, os valores atuais são mantidos e eventuais faltas continuam pendentes. Os demais campos individuais são obrigatórios.

A prévia mostra campo atual e importado. Escolha apenas um registro para análise, confira a substituição e marque a confirmação antes de aplicar. Se o formulário mudar após a prévia, será necessária nova revisão. Uma linha inválida bloqueia **todo o arquivo**; a tabela informa linha física, coluna e erro (até 100 erros por tentativa). O limite é 256 KiB e 500 registros; nomes de propriedades e IDs não podem se repetir, desconsiderando maiúsculas/minúsculas.

Aplicar uma vaca mantém a dieta anterior, emissões explícitas, ingredientes e preços atuais; revise se esse contexto é adequado ao novo animal. Aplicar uma propriedade substitui seu perfil local, incluindo campos vazios, e mantém os dados do animal; use depois **Preencher campos vazios** se desejar aplicá-lo ao animal. A importação não executa otimizações, não faz processamento em lote e não acrescenta importação JSON ou exportação de resultados. A validação usa `POST /api/csv-preview`, sem persistência do arquivo no servidor.

## Testes

Na pasta `nutriplan-web/`:

```bash
env -u DISPLAY MPLBACKEND=Agg MPLCONFIGDIR=/tmp/nutriplan-mpl PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. ../venv/bin/python -m unittest discover -s tests -v
```

A regressão de entradas numéricas está em `tests/test_numeric_inputs.py`. Ela usa os dados Guelph retidos em `data/reference_rations.json` e `data/experimental_validation_manifest.json` como referência computacional interna, separada do fluxo de uso.

`tests/test_property_profile.py` cobre persistência do perfil, preservação de entradas individuais, restauração explícita, estados de origem, validação dos campos permitidos e falha de armazenamento.

`tests/test_csv_import.py` cobre importação, confirmação, seleção e rotas HTTP; `test_tabs.py` verifica teclado e preservação sem cálculo; `test_methodology.py` verifica as oito seções, âncoras e tradução PT/EN com retorno ao texto original. Na conclusão da etapa 16D, a suíte atual contém 34 testes. A suíte histórica de 96 testes não está presente nesta cópia; não foi incluída nessa contagem.

Após a correção do carregamento dos perfis, a suíte atual tem 45 testes. `tests/test_optimization_flow.py` cobre processamento, solicitação única, transição após sucesso, erros direcionados e resposta desatualizada. Os testes de perfil também verificam apresentação dos derivados, aplicação antes dos ingredientes, contagem dos valores manuais e diagnóstico de ausência/erro. As ausências explícitas no backend são testadas nas duas paridades para impedir preenchimento com exemplos internos.

Com a persistência privada, a suíte passa a 56 testes. `tests/test_local_persistence.py` verifica a serialização completa, reabertura, migração, proteção de dados incompatíveis/corrompidos, limpeza com confirmação, falhas de armazenamento e otimização após restauração nas duas paridades.
