# Fiel Finance Mobile

App nativo Android/iOS do Fiel Finance, construído com [Flet](https://flet.dev)
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
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 flet build apk --yes --no-rich-output -v
```

O primeiro build baixa o Flutter SDK + Android SDK/NDK automaticamente
(pode demorar bastante). O APK fica em `build/apk/cofre-mobile.apk`.

### Problemas conhecidos nesta máquina (projeto dentro do OneDrive)

- **`PermissionError` / `OSError: Cannot call rmtree on a symbolic link`** durante
  "Packaging Python app": o OneDrive converte pastas recém-criadas dentro de
  `build/` em "cloud placeholders" (reparse points) quase em tempo real, e o
  `flet build` não consegue apagá-las para recriar. Solução aplicada nesta
  máquina: `cofre_mobile/build` é uma **junction** do NTFS apontando para
  `C:\Users\olair\AppData\Local\cofre_mobile_build` (fora da árvore
  sincronizada pelo OneDrive). Para recriar, caso a junction se perca:
  ```powershell
  $src = "cofre_mobile\build"; $dst = "C:\Users\olair\AppData\Local\cofre_mobile_build"
  Move-Item $src $dst   # se `build` ainda existir como pasta normal
  cmd /c mklink /J $src $dst
  ```
- **`UnicodeEncodeError` (cp1252)** ao rodar `flutter_launcher_icons` ou outras
  ferramentas Dart que imprimem emoji/Unicode: o console legado do Windows não
  suporta esses caracteres. Contornado definindo `PYTHONUTF8=1` e
  `PYTHONIOENCODING=utf-8` antes do `flet build` (já incluído no comando acima).
- Se um build travar/crashar no meio, pode sobrar um processo `dart.exe`
  órfão segurando arquivos de `build/flutter` — mate-o (`Stop-Process`) antes
  de tentar de novo, ou rode `flutter clean` dentro de `build/flutter` se o
  próximo build falhar com `PathNotFoundException` em `app.so`.

## Build iOS

**Não é possível gerar/testar o `.ipa` a partir de uma máquina Windows** —
o `flet build ipa` exige macOS com Xcode 15+ e CocoaPods, além de uma conta
Apple Developer Program (US$99/ano) para assinatura. Veja
`.github/workflows/ios-build.yml` (Fase 4) para rodar o build num runner
macOS do GitHub Actions.

## Fase 2 (concluída): QR code e importação de extrato

- Leitura de QR code do cupom fiscal (NFC-e) via `flet_qrscanner` (extensão
  Flet nativa que embrulha o `mobile_scanner` do Flutter), já que a
  decodificação em Python usada no app desktop (`cv2`/`opencv`) não roda no
  Python embarcado do Flet mobile. Reaproveita `cofre_core.nfce` e o mesmo
  fallback de 3 níveis do desktop: itens da nota → valor total → formulário
  manual. Requer a permissão `camera` (já declarada em `pyproject.toml`).
- Importação de extrato CSV/OFX (`dialogs/import_dialog.py`), equivalente ao
  do app desktop, mas usando `csv.DictReader` da stdlib em vez de pandas
  (pandas é pesado demais para empacotar no celular).
- `cofre_core` ganhou um fallback de import (`requests`/`beautifulsoup4`
  opcionais) para continuar funcionando em ambientes sem essas libs.

## O que falta (próximas fases)

- Fase 3: aba Assistente (chat com IA via API da Anthropic).
- Fase 4: pipeline de build iOS via GitHub Actions.
