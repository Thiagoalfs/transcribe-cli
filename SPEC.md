# Spec: TurboTranscribe — Sistema de Transcrição de Áudio

## Objective
Criar um sistema de transcrição de áudio para texto com timestamps, estilo TurboScribe.ai, usando Whisper Large V3 Turbo via Groq API. O sistema deve permitir escolher o idioma do áudio ou autodetectar, e exportar para TXT e SRT.

## Tech Stack
- **Linguagem:** Python 3.14
- **API:** Groq (whisper-large-v3-turbo)
- **Dependências:** requests, python-dotenv
- **Formatos de entrada:** mp3, wav, m4a, ogg, webm, opus, flac
- **Formatos de saída:** TXT, SRT

## Commands
```bash
# Transcrever um arquivo
python3 /opt/data/scripts/turbotranscribe.py <arquivo_audio> [--idioma pt|en|es|...|auto] [--formato txt|srt|ambos]

# Exemplo
python3 /opt/data/scripts/turbotranscribe.py audio.mp3 --idioma auto --formato ambos
```

## Project Structure
```
/opt/data/scripts/
├── turbotranscribe.py          # Script principal
├── transcribe_core.py          # Lógica de transcrição (Groq API)
├── export_srt.py               # Exportador SRT
├── export_txt.py               # Exportador TXT
└── tests/
    ├── test_transcribe.py      # Testes de transcrição
    ├── test_export_srt.py      # Testes de exportação SRT
    └── test_export_txt.py      # Testes de exportação TXT
```

## Code Style
- Funções pequenas e focadas
- Type hints em todas as funções
- Docstrings em português
- Tratamento de erros com mensagens claras
- Constantes no topo do arquivo

## Testing Strategy
- **Framework:** pytest
- **Testes unitários:** funções de exportação (SRT/TXT) com dados mock
- **Testes de integração:** transcrição real com arquivo de teste
- **Cobertura:** 80%+ no módulo de exportação

## Boundaries
- **Always:** Validar formato de entrada, tratar erros da API, limpar arquivos temporários
- **Ask first:** Adicionar novos formatos de saída, mudar a API de transcrição
- **Never:** Hardcoded API keys, ignorar erros de rede, salvar arquivos sem validação

## Success Criteria
- [ ] Transcrever um arquivo de áudio com sucesso via Groq API
- [ ] Gerar arquivo TXT com timestamps no formato `[HH:MM:SS] texto`
- [ ] Gerar arquivo SRT com timestamps no formato `HH:MM:SS,mmm --> HH:MM:SS,mmm`
- [ ] Permitir escolha de idioma (pt, en, es, etc.) ou autodetect
- [ ] Funcionar com formatos: mp3, wav, m4a, ogg, webm, opus
- [ ] Tratar erros de forma clara (arquivo não encontrado, API error, etc.)

## Open Questions
- O usuário quer que o sistema seja uma CLI ou uma web app?
- Precisa de suporte a vídeos (extrair áudio) ou só áudio?
- Quer que o sistema rode como um serviço (background) ou sob demanda?
