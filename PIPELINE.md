# Pipeline manual

new cria o ID persistente. export-prompts monta roteiro/storyboard/bible e exporta os prompts. collect-clips exige exatamente cinco clipes válidos e produz o concat normalizado. finish cria áudio, captions e render final; com upload.enabled: true, envia o resultado ao YouTube.

Se faltar clipe ou ele estiver inválido, corrija somente a caixa de entrada da produção e execute collect-clips novamente.
