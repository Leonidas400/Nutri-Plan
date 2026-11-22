# NutriPlan

Aplicação local de Pesquisa Operacional para formular dietas de vacas em lactação com as exigências NASEM 2021 e o motor de formulação RuFaS. O RuFaS usa o algoritmo SLSQP da biblioteca SciPy. O custo e as quantidades são expressos por animal por dia.

## Iniciar no Ubuntu

A partir da raiz do projeto, execute `./nutriplan-web/iniciar_linux.sh` e abra [NutriPlan local](http://127.0.0.1:8765). O inicializador prepara o Python 3.13 e as dependências declaradas no `pyproject.toml` do RuFaS, incluindo SciPy. Com o ambiente já instalado, também é possível executar o servidor diretamente.

```bash
cd nutriplan-web
PYTHONPATH=.. ../venv/bin/python server.py
```

A variável `PORT` permite escolher outra porta. A primeira instalação pode precisar de internet. A formulação usa os arquivos e o motor locais.

## Formular e comparar

1. Em **Animal**, escolha a **categoria animal**: vaca de primeira lactação, vaca multípara, novilha I/II/III ou vaca seca. Para lactantes, informe fase, produção atual, meta e composição do leite. Para novilhas, informe o ganho diário em **kg/dia**. Para vaca seca, informe o intervalo entre partos e, se gestante, o dia de gestação. Campos numéricos aceitam ponto ou vírgula decimal.
2. Em **Dieta atual**, cadastre opcionalmente os alimentos do lote e suas quantidades em kg de matéria seca por animal/dia. O total é atualizado durante a edição. Os preços informados nessa seção servem para a comparação de custo.
3. Em **Dieta otimizada**, pesquise por nome nos grupos ou no catálogo personalizado de 175 alimentos. A seleção vazia usa o conjunto recomendado com preços disponíveis. Para formular com uma lista própria, marque de 2 a 25 ingredientes. Revise os preços e clique **Calcular dieta otimizada**. A produção atual é o piso que a dieta não pode reduzir; a meta não pode ser menor que ele. O sistema formula a meta e testa sete metas abaixo e sete acima da referência, em passos de 1 kg/dia.
4. Em **Resultados**, a tela é dividida em três partes: **Custo das dietas** (comparação entre custo minimizado e máximo de produção: custo/dia, kg ingeridos, massa seca e leite em L/dia), **Gráficos e tabelas** (fronteira e resumo das etapas) e **Informações sobre a dieta** (composição e detalhes técnicos recolhíveis, com restrições e oferta na mesma tabela comparando as duas dietas). Para lactantes, a fronteira usa o **leite produzido** no eixo X e o botão **Explorar dietas** gera soluções viáveis não ótimas. Se o potencial de produção ficar abaixo da produção atual, a formulação é rejeitada. Para novilhas e vaca seca, não há meta/piso de leite; o resultado mostra as exigências do estágio.
5. Em **Metodologia**, consulte o modelo de custo, as onze restrições, os critérios do SLSQP, o piso de leite, os limites de inclusão e a interpretação das metas e emissões.

**Limites e inclusão fixa.** Na tabela de ingredientes, **Mín.** e **Máx.** são em kg MS por animal/dia e começam com os limites do catálogo NASEM. Marcar **Fixar** copia o mínimo para o máximo, mantendo o alimento em quantidade fixa.

**Emissões — configuração opcional.** Deixe metano (g/dia) e nitrogênio urinário (kg/dia) em branco para usar as estimativas RuFaS da dieta candidata. Para uma análise com dados próprios, preencha os dois valores. As emissões utilizadas são retornadas pela API de formulação.

Os dados da análise ficam disponíveis enquanto a página está aberta. Ao recarregá-la, a formulação começa vazia e o navegador reaplica as preferências de idioma e tema. Os catálogos distribuídos com o motor são lidos automaticamente.

## Etapas de vida

O NutriPlan formula para vacas lactantes e para **novilha I, novilha II, novilha III e vaca seca**. Esses estágios usam as exigências NASEM de mantença, crescimento, gestação e atividade, sem meta de leite, sem piso e sem fronteira custo × leite. O objetivo continua sendo o menor custo da dieta.

As emissões de metano e nitrogênio urinário usam as rotas nativas do RuFaS para cada estágio: vaca lactante, novilha e vaca seca. Para novilha e vaca seca sem dieta atual, informe a FDN da dieta; ela é necessária porque o consumo estimado depende da FDN. O resumo das etapas guarda os resultados apenas na sessão atual; recarregar a página limpa o resumo.

## Interpretação

O SLSQP do SciPy busca um mínimo local sob restrições não lineares. A viabilidade de uma meta indica que o modelo encontrou uma dieta que atende às exigências calculadas para ela. A produção observada depende do animal e do manejo. Os dados Guelph distribuídos com o projeto servem para regressão computacional. Consulte o [manual técnico](DOCUMENTACAO_NUTRIPLAN.md).

## Verificar esta versão

Na pasta `nutriplan-web`, o comando abaixo descobre os 48 testes Python da aplicação. Os testes HTTP iniciam seu próprio servidor em uma porta local temporária. O motor RuFaS deve estar disponível para os cálculos. A suíte de testes do simulador tem execução independente.

```bash
MPLBACKEND=Agg PYTHONPATH=.:.. ../venv/bin/python -m unittest discover -s tests -v
```

Os testes cobrem a fórmula de energia do leite, as rotas NEL/MP, o piso contra a produção atual, as duas paridades, a varredura bilateral, a exploração de dietas alternativas, os estágios novilha I/II/III e vaca seca, a validação de composição e os contratos HTTP. Os roteiros de navegador citados em versões anteriores não estão incluídos nesta cópia; a suíte Python não depende deles.
