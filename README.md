# OneMoreShort

Factory local para Shorts com geração visual manual: pesquisa, roteiro, cinco prompts, ingestão de cinco clipes, edição e upload opcional.

## Fluxo

1. Execute python -m app.cli new
2. Execute python -m app.cli export-prompts ID
3. Gere os cinco vídeos manualmente e coloque-os em storage/manual_input/ID/.
4. Execute python -m app.cli collect-clips ID
5. Execute python -m app.cli finish ID

Use nomes segment_01.mp4 a segment_05.mp4. O resultado final fica em storage/renders/ID/OneMoreShort_Final.mp4.
