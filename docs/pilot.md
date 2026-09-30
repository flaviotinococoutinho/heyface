# Da demonstração ao seu cenário

Heyface é uma busca visual sobre um catálogo que você controla. A foto reduz o conjunto de candidatos; os dados cadastrais ajudam a refinar; a pessoa que conhece o contexto confere o resultado.

O primeiro teste leva de uma imagem a um cadastro fictício. Um piloto responde a outra pergunta: isso economiza tempo e encontra candidatos úteis no trabalho de quem vai usar?

## Escolha um problema pequeno

| Cenário | O que experimentar | Como perceber valor |
| --- | --- | --- |
| Catálogo autorizado de pessoas | Encontrar um cadastro pela foto e restringir por cidade/nome | Menos tempo para localizar o registro correto |
| Abrigo ou clínica veterinária | Comparar fotos de animais da mesma espécie | Candidato conhecido entre os primeiros resultados |
| Projeto de campo | Organizar comparações de padrões visuais em uma espécie | Lista de candidatos menor para revisão especializada |
| Produto com aplicativo | Capturar/enviar foto e consultar o catálogo pela API | Fluxo compreensível, tempo de resposta aceitável e falhas recuperáveis |

Escolha um cenário, um responsável pela avaliação e um catálogo delimitado. O método para humanos usa um rosto por imagem. Para animais, a comparação global parte de um recorte confirmado; a fusão exige calibração da espécie. A referência de pesquisa não garante desempenho para qualquer espécie ou condição.

## Primeiro contato

```sh
./heyface try
```

No Windows: `.\heyface.ps1 try`. O comando prepara o ambiente, cadastra os exemplos e exibe a chave local. Abra http://localhost:8088, conecte o acesso e escolha **Testar com uma pessoa** ou **Testar com um animal**.

Observe o cadastro encontrado, a ordenação, os dados e os filtros. Mude a cidade do filtro e veja a lista se restringir. Troque o método humano para comparar o comportamento. O score não é uma confirmação automática de identidade.

A consulta do exemplo usa a mesma foto cadastrada. Ela demonstra o caminho completo do produto; não mede reconhecimento em fotos novas.

## Piloto com imagens diferentes

Separe fotos de cadastro e consulta. Use fotos de momentos distintos, sem reaproveitar o mesmo arquivo recortado nas duas partes. Inclua iluminação, enquadramentos e condições presentes no uso esperado. Acrescente consultas cujo indivíduo não está no catálogo.

Registre antes do teste:

- Qual tarefa será feita e como ela é resolvida hoje.
- Quem pode aparecer no catálogo e como a autorização é registrada.
- Quais filtros estarão disponíveis para a pessoa que busca.
- Quantos candidatos ela consegue revisar e qual espera considera aceitável.
- O que deve acontecer quando não houver candidato útil.

Monte uma planilha com consulta, resultado esperado, posição do candidato correto, tempo até encontrar o cadastro e observação do avaliador. O responsável pelo catálogo confirma o resultado esperado. Evite usar o conjunto de avaliação para escolher pesos ou cortes de score.

## Medir sem misturar objetivos

| Medida | O que responde |
| --- | --- |
| Acerto entre os primeiros K candidatos | O cadastro correto aparece em uma lista que alguém consegue revisar? |
| Consultas sem indivíduo cadastrado | O fluxo ajuda a encerrar a busca sem forçar uma correspondência? |
| Tempo da tarefa e tempo da API | A busca economiza trabalho e responde na rede esperada? |
| Taxa de rejeição de imagens | As orientações de captura funcionam para o público? |
| Uso dos filtros | Quais dados realmente ajudam a reduzir candidatos? |

O [benchmark do índice](operations.md) mede distância/latência com vetores sintéticos. A [calibração animal](recognition.md) mede combinações de representações em pares rotulados. Nenhum dos dois substitui a avaliação da tarefa com fotos e pessoas do piloto.

## O que oferecer em um piloto

Uma entrega pequena pode incluir preparação do catálogo, conexão da API ao fluxo existente, orientação de captura, acompanhamento dos resultados e um relatório de decisão. O valor está na tarefa que ficou mais fácil de concluir. Use as medidas do piloto para decidir se faz sentido ampliar volume, incluir uma espécie, criar o app ou oferecer operação gerenciada.

O ambiente atual é local e usa chaves por espaço de trabalho. Um serviço compartilhado ainda exige uma camada de contas, operação HTTPS, política de retenção e dimensionamento conforme o uso. A [arquitetura](architecture.md) mostra onde essas integrações entram.

Para relatar o teste, use o [formulário de feedback](https://github.com/flaviotinococoutinho/heyface/issues/new?template=pilot-feedback.yml). Descreva o cenário e o resultado, sem anexar chaves, imagens pessoais ou dados cadastrais.
