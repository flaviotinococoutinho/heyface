# Como evoluir o projeto

Prefiro mudanças pequenas, com uma responsabilidade clara e uma forma de verificar o comportamento. Código e commits ficam em inglês; documentação de uso fica em português direto.

- Comece pelo domínio afetado. Um método de reconhecimento novo implementa a porta de extração e define seu próprio espaço vetorial; não acrescente condicionais em todos os casos de uso.
- Use objetos de valor quando houver uma regra a proteger. Não crie uma classe só para embrulhar uma string sem restrições.
- Deixe as operações puras separadas de HTTP, filesystem e inferência. Injete as dependências externas pelas portas existentes.
- Centralize limites ajustáveis. Dimensões e versões da representação são contrato; trocar um número de dimensão exige migração, não só configuração.
- Use guard clauses, nomes claros, composição e funções curtas. Evite booleanos de modo que multipliquem responsabilidades, estado global mutável e abstrações sem uso concreto.
- Adicione testes para regras, falhas e fronteiras de segurança. Testes de mock não substituem `smoke`, que usa os extratores e o banco reais. Correspondência da mesma imagem não prova generalização.
- Não registre fotos, base64, tokens, vetores ou dados pessoais em logs. Os arquivos privados ficam em `.local` e `.secrets`.
- Rode `./heyface test`, `./heyface smoke` quando afetar integração, e o build do frontend quando ele mudar.
- Antes de publicar, rode `python3 scripts/publication_check.py --staged` e `--history`. A CI repete a inspeção do histórico.

Commits seguem `tipo(escopo): descrição`, por exemplo `feat(people): support birth date filters`, `fix(access): reset locale between requests` ou `docs(operations): explain snapshot recovery`. Separe mudanças de people, animals, access, web e ambiente quando forem independentes.
