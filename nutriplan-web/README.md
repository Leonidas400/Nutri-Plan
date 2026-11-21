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

1. Em **Animal**, escolha fase e paridade e informe o peso, a produção e a composição do leite. Campos numéricos aceitam ponto ou vírgula decimal.
2. Em **Dieta atual**, cadastre opcionalmente os alimentos do lote e suas quantidades em kg de matéria seca por animal/dia. O total é atualizado durante a edição. Os preços informados nessa seção servem para a comparação de custo.
3. Em **Dieta otimizada**, pesquise por nome nos grupos ou no catálogo personalizado de 175 alimentos. A seleção vazia usa o conjunto recomendado com preços disponíveis. Para formular com uma lista própria, marque de 2 a 25 ingredientes. Revise os preços e clique **Calcular dieta otimizada**. A produção informada é a meta de referência e o sistema testa até sete metas superiores, em passos de 1 kg/dia.
4. Em **Resultados**, consulte o custo por animal/dia, o consumo de matéria seca, a meta de leite e a composição da dieta. O resumo destaca a maior meta viável entre as testadas. O diagnóstico, os detalhes de metas e emissões, a comparação de dietas e a sensibilidade estão disponíveis pela API.
5. Em **Metodologia**, consulte o modelo de custo, as onze restrições, os critérios do SLSQP e a interpretação das metas e emissões.

**Emissões — configuração opcional.** Deixe metano (g/dia) e nitrogênio urinário (kg/dia) em branco para usar as estimativas RuFaS da dieta candidata. Para uma análise com dados próprios, preencha os dois valores. As emissões utilizadas são retornadas pela API de formulação.

Os dados da análise ficam disponíveis enquanto a página está aberta. Ao recarregá-la, a formulação começa vazia e o navegador reaplica as preferências de idioma e tema. Os catálogos distribuídos com o motor são lidos automaticamente.

## Interpretação

O SLSQP do SciPy busca um mínimo local sob restrições não lineares. A viabilidade de uma meta indica que o modelo encontrou uma dieta que atende às exigências calculadas para ela. A produção observada depende do animal e do manejo. Os dados Guelph distribuídos com o projeto servem para regressão computacional. Consulte o [manual técnico](DOCUMENTACAO_NUTRIPLAN.md).

## Verificar esta versão

Na pasta `nutriplan-web`, o comando abaixo descobre os 42 testes Python da aplicação. Os testes HTTP iniciam seu próprio servidor em uma porta local temporária. O motor RuFaS deve estar disponível para os cálculos. A suíte de testes do simulador tem execução independente.

```bash
MPLBACKEND=Agg PYTHONPATH=.:.. ../venv/bin/python -m unittest discover -s tests -v
```

Com o servidor em execução, o teste de interface percorre a formulação com dados Guelph, o comparador, as metas e as sensibilidades de preço e disponibilidade. Verifica as cinco abas, a navegação por teclado na Metodologia, os dois idiomas, os temas, três larguras e zoom de 200%.

```bash
node tests/phase17_browser.cjs
node --test tests/audit_e2e.cjs
```

O fluxo de navegador é uma verificação adicional à contagem do Python. Ele também verifica que o preenchimento acompanha a navegação entre abas, que recarregar a página abre Animal e limpa a análise e que os dados antigos no navegador são preservados. O roteiro de auditoria cruza as duas paridades com e sem dieta atual, valida os formulários e exerce a interface nas larguras de 320, 390, 768, 1280 e 1440 px. Os roteiros usam Playwright e um navegador Chromium com sandbox habilitada. Se já estiverem instalados fora do projeto, aponte `NODE_PATH` para o diretório dos módulos Node e `CHROMIUM_PATH` para o executável do navegador. `NUTRIPLAN_URL` seleciona a origem do servidor de teste. A aplicação em execução dispensa essas ferramentas.
