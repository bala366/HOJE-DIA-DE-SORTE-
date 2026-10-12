# DIA DE SORTE CAMPEÃO V8 — Android

## Origem do motor
O arquivo `MOTOR_ORIGINAL_V5_WINDOWS.py` é uma cópia integral do motor V5 do Windows usada como referência. A implementação Android em Java segue as mesmas regras de tirinhas (1 a 8), 255 combinações, ranking das 20 candidatas por atraso e falhas, seleção de 7 dezenas por frequência nos últimos 100 concursos com limite de 4 por paridade, e Mês da Sorte por menor frequência nos últimos 100 concursos e maior atraso.

## Histórico
Toque em **ABRIR HISTÓRICO EM DOWNLOADS** e escolha o arquivo TXT ou CSV no seletor de arquivos do Android. O app lê `1 - 03,05,08,09,19,21,30 - Fevereiro` e arquivos tabulares com concurso, 7 dezenas e mês. Confere quantidade de concursos e rejeições antes de analisar. O nome e os primeiros e últimos resultados aparecem na tela.

## PDF
O botão **SALVAR PDF COLORIDO + RANKING** abre o seletor de destino do Android. Escolha a pasta Downloads e confirme Salvar. O aplicativo grava um PDF com volante amarelo, sete dezenas marcadas, mês escolhido e ranking das 255 combinações; verifica o tamanho do documento após salvar.

## Instalação via GitHub
Suba o conteúdo deste projeto à raiz do repositório, incluindo `.github/workflows/android-apk.yml`. Em Actions, rode o workflow e baixe o artefato APK.

## Verificação
Compare com a V5 Windows usando o mesmo histórico e a mesma posição de tirinha escolhida. O mês sugerido depende das frequências e atrasos do histórico. Esta entrega não foi compilada nem testada em um aparelho Android neste ambiente.
