# TranscribeCLI

Sistema de transcrição de áudio para texto com timestamps, estilo TurboScribe.ai, usando Whisper Large V3 Turbo via Groq API.

## Funcionalidades

- **Transcrição de áudio** com timestamps precisos
- **Detecção automática de idioma** ou seleção manual
- **Exportação em SRT** (legendas) e **TXT** (texto com timestamps)
- **Histórico** de transcrições com metadados
- **CLI interativa** simples e intuitiva
- **Gratuito** — usa modelos free do Nous Portal

## Formatos suportados

**Entrada:** MP3, WAV, M4A, OGG, WEBM, OPUS, FLAC

**Saída:** SRT, TXT

**Idiomas:** Português, Inglês, Espanhol, Francês, Alemão, Italiano, Chinês, Japonês, Coreano + detecção automática

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/Thiagoalfs/transcribercli.git
cd transcribercli
```

### 2. Instalar dependências

```bash
pip install requests
```

### 3. Configurar API key do Groq

1. Crie uma conta em [Groq](https://groq.com)
2. Gere uma API key em [console.groq.com](https://console.groq.com)
3. Crie um arquivo `.env` na **raiz do projeto** (não em `/opt/data/.env`):

```env
GROQ_API_KEY=sua_chave_aqui
```

> **Importante:** O arquivo `.env` está no `.gitignore` e não será enviado ao GitHub.

## Como usar

### Executar a CLI

```bash
python3 transcribecli.py
```

### Fluxo de uso

1. **Menu principal** — escolha uma opção:
   - `1` — Transcrever
   - `2` — Histórico
   - `3` — Sair

2. **Selecionar arquivo** — abra o seletor de arquivo e escolha um áudio

3. **Escolher idiomas** — selecione o idioma de origem e de saída

4. **Ver resultado** — a transcrição aparece com timestamps

5. **Menu pós-transcrição**:
   - `1` — Configurar palavras por timestamp
   - `2` — Exportar SRT
   - `3` — Exportar TXT
   - `4` — Voltar ao menu principal

### Exemplo de uso

```
============================================================
  TranscribeCLI - Transcrição de Áudio com Timestamps
============================================================

Opções:
  1. Transcrever
  2. Histórico
  3. Sair

Escolha: 1

Selecione um arquivo de áudio...
Formatos suportados: .flac, .m4a, .mp3, .ogg, .opus, .wav, .webm

[Seletor de arquivo abre...]

Idioma de origem:
  auto   - Detectar automaticamente
  pt     - Português
  en     - Inglês
  ...

Idioma [auto]: pt

Transcrevendo...

============================================================
  Resultado da Transcrição
============================================================

[00:00:00] Olá, bem-vindo ao TranscribeCLI
[00:00:03] Este é um exemplo de transcrição
[00:00:06] Com timestamps precisos

Opções:
  1. Configurar palavras por timestamp
  2. Exportar SRT
  3. Exportar TXT
  4. Voltar ao menu principal

Escolha: 2
SRT exportado: ~/.turbotranscribe/transcripts/transcript.srt
```

## Estrutura do projeto

```
transcribercli/
├── transcribecli.py      # CLI principal
├── transcribe_core.py    # Módulo de transcrição (Groq API)
├── export_srt.py         # Exportador SRT
├── export_txt.py         # Exportador TXT
├── history.py            # Sistema de histórico
├── tests/                # Testes unitários
│   ├── test_export_srt.py
│   ├── test_export_txt.py
│   └── test_transcribe_core.py
├── .env                  # API keys (não versionado)
├── .gitignore            # Arquivos ignorados pelo git
└── README.md             # Este arquivo
```

## Histórico

O histórico é salvo em `~/.turbotranscribe/history.json` e inclui:
- Data da transcrição
- Nome do arquivo
- Idioma de origem e destino
- Duração do áudio
- Número de palavras

## Testes

```bash
# Instalar pytest
pip install pytest pytest-cov

# Rodar testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=. --cov-report=term-missing
```

## Requisitos

- Python 3.10+
- Conta Groq (API key)
- Dependências: `requests`

## Licença

MIT License — veja o arquivo [LICENSE](LICENSE) para detalhes.

## Contribuição

Contribuições são bem-vindas! Abra uma issue ou envie um pull request.
