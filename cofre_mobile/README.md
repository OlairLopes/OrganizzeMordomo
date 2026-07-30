# Cofre Mobile

App nativo Android/iOS do Cofre, construído com [Flet](https://flet.dev)
(Python → Flutter). Reaproveita a lógica de negócio pura de `../cofre_core`
(mesmo pacote usado pelo app Streamlit `cofre_app.py`).

## Núcleo compartilhado (`cofre_core`)

Este projeto **copia** `../cofre_core` para dentro de `src/cofre_core` para que
o `flet build`/`flet run` consiga empacotá-lo junto com o resto do app (o
build só empacota o que está em `src/`). Sempre que `../cofre_core` mudar,
rode:

```bash
python sync_core.py
```

`src/cofre_core/` está no `.gitignore` — a fonte de verdade é `../cofre_core`,
versionada uma única vez no repositório.

## Rodando em desenvolvimento

```bash
python -m venv .venv
./.venv/Scripts/pip install -e .   # ou: pip install flet[all] flet-charts
python sync_core.py
./.venv/Scripts/flet run --web src/main.py     # como app web (mais rápido p/ iterar)
./.venv/Scripts/flet run src/main.py           # como app desktop
```

## Build Android (testado nesta máquina Windows)

```bash
python sync_core.py
flet build apk --yes --no-rich-output -v
```

O primeiro build baixa o Flutter SDK + Android SDK/NDK automaticamente
(pode demorar bastante). O APK fica em `build/apk/app-release.apk`.

## Build iOS

**Não é possível gerar/testar o `.ipa` a partir de uma máquina Windows** —
o `flet build ipa` exige macOS com Xcode 15+ e CocoaPods, além de uma conta
Apple Developer Program (US$99/ano) para assinatura. Veja
`.github/workflows/ios-build.yml` (Fase 4) para rodar o build num runner
macOS do GitHub Actions.

## O que falta (próximas fases)

- Fase 2: leitura de QR code do cupom fiscal (NFC-e) — via extensão Flet
  nativa (`mobile_scanner`), não pela decodificação em Python usada no app
  desktop (`cv2`/`opencv`, que não roda no Python embarcado do Flet mobile).
- Fase 3: aba Assistente (chat com IA via API da Anthropic).
- Fase 4: pipeline de build iOS via GitHub Actions.
