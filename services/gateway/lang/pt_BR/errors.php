<?php

return [
    'unauthorized' => 'Informe uma chave de acesso válida.',
    'forbidden' => 'Esta chave não tem permissão para esta operação.',
    'not_found' => 'Recurso não encontrado.',
    'person_not_found' => 'Cadastro não encontrado.',
    'invalid_request' => 'Confira os campos enviados e tente novamente.',
    'invalid_base64' => 'A imagem em base64 é inválida.',
    'invalid_image' => 'Não foi possível ler a imagem. Envie um JPEG ou PNG válido.',
    'unsupported_image' => 'Use uma imagem JPEG ou PNG.',
    'image_too_large' => 'Use uma imagem de até 5 MB e 16 milhões de pixels.',
    'no_face' => 'Nenhum rosto foi encontrado. Use uma foto frontal e bem iluminada.',
    'multiple_faces' => 'A imagem contém mais de um rosto. Recorte apenas uma pessoa.',
    'face_too_small' => 'O rosto está muito pequeno. Use uma foto mais próxima.',
    'low_face_confidence' => 'O rosto não está nítido o suficiente. Tente outra foto.',
    'vision_busy' => 'O processamento está ocupado. Tente novamente em instantes.',
    'vision_unavailable' => 'O processamento está temporariamente indisponível.',
    'storage_unavailable' => 'A busca está temporariamente indisponível.',
    'invalid_embedding' => 'Não foi possível representar esta imagem. Tente outra foto.',
    'rate_limited' => 'Limite de consultas atingido. Aguarde antes de tentar novamente.',
    'calibration_required' => 'Este método precisa de uma calibração para a espécie escolhida.',
];
