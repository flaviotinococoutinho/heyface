# Reconhecimento e calibração

## Representações

| Método | Uso | Representação | Situação |
| --- | --- | --- | --- |
| FaceNet + MTCNN | Rosto humano | 512 dimensões, crop 160, norma unitária | Disponível no cadastro e na busca |
| SFace + YuNet | Rosto humano | 128 dimensões, alinhamento próprio | Disponível no cadastro e na busca |
| DINOv2 Small | Animal recortado | 384 dimensões, crop 224 | Busca global disponível |
| DINOv2 + SIFT calibrados | Padrões animais | Score global + correspondências locais | Exige calibração local por espécie |

Os pesos vêm de origens públicas fixadas em `models/manifest.json`, com versão e SHA-256. Não são incluídos no Git. Na inicialização, o script verifica inclusive arquivos já baixados. Runtime não precisa acessar a internet.

FaceNet e SFace não compartilham o espaço de comparação. O cadastro salva os dois vetores nomeados; a consulta seleciona apenas o espaço correspondente. Os landmarks são cinco coordenadas na imagem original, identificadas por uma ordem explícita. Não representam todos os pontos de uma malha facial.

## Animais e as referências

[WildFusion](https://arxiv.org/abs/2408.12934) combina similaridade global e correspondências locais, calibra os sinais e os funde. A implementação daqui usa a mesma ideia de calibração monotônica, com DINOv2 Small e SIFT. É uma variante reduzida para CPU: não reproduz todos os extratores, experimentos ou resultados do artigo. A fusão só reordena o conjunto de candidatos recuperado pelo vetor global; não recupera um animal que ficou fora desse conjunto.

[PetFace](https://arxiv.org/abs/2407.13555) orienta a avaliação por identidade animal e a necessidade de separar indivíduos entre partições. O [repositório oficial](https://github.com/mapooon/PetFace) restringe código, checkpoints e dataset à pesquisa não comercial, e o acesso aos dados requer solicitação. Por isso, esses materiais não são baixados nem redistribuídos por este projeto. Não afirmamos que o extrator global foi treinado no PetFace. Dados obtidos legitimamente podem alimentar o protocolo local de pares abaixo.

DINOv2 é um extrator visual geral. Não há garantia de identificação individual por espécie sem uma avaliação própria. A foto deve conter um único animal, recortado pelo responsável. Imagens de corpo e padrões de pelagem também podem ser comparadas, desde que o protocolo mantenha enquadramentos comparáveis.

## Calibrar a fusão

A calibração recebe um CSV com estas colunas:

```csv
image_a,image_b,identity_a,identity_b,label,split,global_score,local_score
```

`global_score` é o cosseno dos vetores da mesma representação. `local_score` é a contagem de correspondências produzida por `local_match_count`. `label` vale 1 para o mesmo indivíduo e 0 para indivíduos diferentes. Use os nomes `calibration`, `validation` e `test` no campo `split`.

Cada partição precisa conter positivos e negativos. Identidades não podem aparecer em mais de uma partição. Não use a mesma foto dos dois lados de um par nem repita pares. O mínimo técnico de quatro pares por partição só permite executar o programa; está muito longe de justificar uma estimativa de desempenho confiável. Monte um conjunto representativo da espécie, dos indivíduos e das condições de captura que você pretende atender.

Se você tem as imagens e seus rótulos, o próprio ambiente calcula os scores. Monte `.local/pairs.csv` com as primeiras seis colunas (sem os scores); os caminhos das imagens são relativos à raiz do projeto. Todas as imagens devem ser recortes individuais preparados sob o mesmo protocolo. O comando recusa sobrescrever um relatório anterior.

```sh
./heyface score-pairs --pairs .local/pairs.csv --scores .local/scores.csv
./heyface calibrate --scores .local/scores.csv --tenant local --species cat
```

O fluxo é offline:

1. Valida rótulos, pares e separação de identidades.
2. Ajusta regressão isotônica nos pares de `calibration` e interpola curvas monotônicas com PCHIP.
3. Usa evolução diferencial, seed fixa e orçamento limitado, para escolher pesos pela perda de Brier em `validation`.
4. Compara a solução com pesos iguais e mantém o baseline se ele for melhor na validação.
5. Calcula Brier e ROC AUC em `test`, sem usar esse conjunto para escolher pesos.
6. Salva curvas, versão, espécie, peso, hash do CSV lógico e relatório em `.local/calibrations/<tenant>/<species>.json`. Preserva uma cópia da calibração anterior.

O objetivo da metaheurística é ajustar a combinação de sinais. Não há otimização evolutiva em cada consulta. Com só dois sinais, uma busca simples de peso também é um comparador importante; não pressupomos que a metaheurística seja a melhor solução. Brier/AUC de pares também não substituem recall@k, false matches e avaliação de identificação aberta em dados reais.

Sem o arquivo correto, a API recusa a fusão. Não usa um peso arbitrário como se estivesse calibrado. A busca global permanece disponível.

## Contratos e licenças

O contrato da representação inclui pesos, preprocessing, dimensão e normalização. Mudanças nesses itens exigem nova versão e reindexação; curvas antigas não podem ser reutilizadas silenciosamente.

- [FaceNet PyTorch](https://github.com/timesler/facenet-pytorch): implementação MIT; considere separadamente as condições dos pesos e dos dados de treinamento VGGFace2.
- [OpenCV Zoo](https://github.com/opencv/opencv_zoo): verifique os arquivos de licença de YuNet e SFace nos diretórios dos artefatos fixados.
- [DINOv2 Small no timm](https://huggingface.co/timm/vit_small_patch14_dinov2.lvd142m): ficha e licença Apache-2.0 do artefato usado.
- [Wildlife Tools](https://github.com/WildlifeDatasets/wildlife-tools): referência de calibração/fusão; a aplicação mantém implementação própria.

Nenhum resultado publicado pelos autores é apresentado como resultado deste projeto. O smoke usa imagens fictícias e testa infraestrutura, não acurácia biométrica.
