# Dataset

### Origem

O dataset utilizado neste projeto é sintético, ou seja, foi criado pelo próprio grupo através do script `scripts/build_dataset.py`, localizado na pasta `src/aism/dataset.py`.

Para gerar novamente o dataset, basta executar o seguinte comando:

```bash
python scripts/build_dataset.py
```

A geração dos dados utiliza a seed 42, garantindo que os resultados são sempre os mesmos.

### Licença e utilização

Todos os textos incluídos no dataset foram criados pelo grupo e são fictícios. Não foram utilizados textos pertencentes a empresas reais nem conteúdos de terceiros.

Por esse motivo, os dados podem ser utilizados livremente no âmbito desta disciplina. É importante referir que os avisos apresentados são apenas exemplos e não correspondem a avisos oficiais.

### Porque foi utilizado um dataset sintético?

A escolha de um dataset sintético deve-se à dificuldade em encontrar dados públicos que incluam avisos de apoios, informações sobre empresas e uma referência correta para cada critério de avaliação.

Ao criar o nosso próprio dataset, conseguimos definir as regras utilizadas na avaliação e saber antecipadamente quais são os resultados esperados. Desta forma, a classificação de cada caso é feita de acordo com regras definidas pelo grupo, evitando erros associados à anotação manual.

No entanto, esta abordagem também tem algumas limitações, principalmente por não representar toda a variedade de situações que podem surgir em avisos reais.

### Organização do dataset

O ficheiro `cases.json` contém um total de 30 casos. Cada caso inclui:

- `notice_text`: texto do aviso de apoio.
- `company_text`: informação sobre a empresa, podendo ter alguns campos em falta.
- `criteria`: critérios utilizados na avaliação, incluindo o respetivo nome, tipo, indicação de obrigatoriedade e valor de referência.
- `truth_overall`: resultado global esperado para o caso.
- `split`: indicação do conjunto ao qual o caso pertence.

### Divisão dos dados

Os 30 casos estão divididos em dois grupos:

- **Dev:** contém 6 casos e é utilizado para testar e ajustar os prompts. Os resultados destas experiências ficam guardados em `results/openai_dev/`.
- **Test:** contém os restantes 24 casos e é utilizado nas experiências e avaliações finais.

Esta divisão permite ajustar os prompts sem utilizar os mesmos dados que são usados posteriormente para avaliar os resultados.

### Limitações

Apesar de ser útil para testar o funcionamento do projeto, o dataset apresenta algumas limitações:

- Os textos foram construídos a partir de modelos de frases previamente definidos, existindo apenas duas variantes para cada tipo de critério.
- Foram considerados 10 tipos diferentes de critérios.
- Os exemplos são mais simples e organizados do que os avisos que normalmente existem em situações reais.