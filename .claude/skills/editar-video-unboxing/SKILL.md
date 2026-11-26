---
name: editar-video-unboxing
description: Edita vídeos de unboxing/recebidos do Daniel (importação da China) no padrão aprovado — cortes curtos em velocidade normal, narração limpa, cards com a identidade do site dmchoice e efeito de choque. Use sempre que ele pedir para editar um vídeo, montar cortes, colocar narração, cards de fornecedor, chamada inicial ou "comenta quero".
---

# Edição de vídeo de unboxing — padrão do Daniel

Ferramentas em `video-toolkit/scripts/` (detalhes em `video-toolkit/README.md`).
Instale antes: `pip install gdown faster-whisper numpy pillow` (ffmpeg já vem no ambiente).
Trabalhe no scratchpad; vídeos NUNCA vão para o git. Entregue com SendUserFile
e lembre que o ambiente é temporário (ele precisa baixar o arquivo).

## 1. Receber os arquivos
- Ele manda link de pasta/arquivo do Google Drive: `drive.py list|get|getall`.
- Vídeos do iPhone vêm em HEVC .MOV vertical (rotação nos metadados; o ffmpeg trata).
- Cards dos fornecedores em alta: pasta https://drive.google.com/drive/folders/1zGuTcmC6d4spVyvRHVnC0xDQklZyMNFc
  (um PNG por fornecedor, ex.: `WWTOP.png`). Use sempre a versão em alta.

## 2. Mapear o conteúdo
- `analyze.py sheet` com fps=1 em cada clipe; depois fps=2..4 nos trechos que importam.
- `analyze.py cry` em todos os clipes (já apareceu choro de bebê no áudio — tirar).
- `analyze.py peaks` para achar estalos de abas, fita e pacotes rasgando.

## 3. Regras dos cortes (aprovadas)
- Vertical 1080x1920, 30 fps. **Velocidade normal, nunca acelerar.**
- A sensação de rapidez vem de **muitos cortes curtos** (0,6–1,3 s), só nos momentos marcantes.
- **Caixa grande:** sentado com a caixa → fita → uma aba por corte (cada estalo) →
  caixa aberta → **todos** os pacotes saindo, um corte por pacote (tira e levanta) → mostra na mão.
- **Cada produto:** rasga o pacote → corte → tira a caixa → corte → abre → corte →
  tira os itens e mostra → corte → tira o produto → (bolsinha → tira da bolsinha) → closes de detalhe.
- **Corte de barulho:** começa ~0,35 s antes e termina logo que o som acaba
  (`analyze.py snap`). "Estalou/rasgou → corta."
- Nos tênis, incluir a parte em que ele **segura o par e fica olhando**.
- **Closes de detalhe** são importantes (bolsa, itens que acompanham, cada tênis): dê tempo a eles.
- **Tirar:** ele guardando caixa em cima do móvel, faca parada sem cortar nada, choro de bebê,
  itens que ele disser que não entram (ex.: polos), entradas/saídas do quadro.
- Ordem = a que ele descrever. Duração = a que ele pedir (ex.: ≤1:10, depois aceitou 1:23).
- Revise sempre com `render_cuts.py --preview` + folha de quadros antes do render final.

## 4. Narração (gravada por ele depois dos cortes)
- `narration.py transcribe` em cada áudio; escolha **a melhor tomada** de cada frase,
  tire gaguejos, repetições e frases incompletas.
- `narration.py clean`: remove pausas e respirações. **Deixe cada palavra terminar**
  (ele reclamou de "qualida…"): estenda o fim do trecho / use folga_final e confira com `check`.
- **Não alongar o vídeo** para caber a fala: corte as frases menos importantes.
- `narration.py place`: falas emendadas, **sem nenhum espaço vazio**, cada uma perto da imagem do produto.
- Som original a 30% por baixo da voz.

## 5. Cards (identidade do site https://dmchoice.netlify.app)
- `cards.py` já tem o estilo: Archivo 900/800, creme #F4E8D4, degradê #D9530F→#FF8A2A→#F0A54A,
  cartão escuro #0B0806 arredondado, **70% do tamanho**, no topo da tela.
- Todos entram e saem com **efeito de choque** (glitch). Som: **só o ruído elétrico**, sem tom/estalinho.
- Cards padrão deste formato:
  - Abertura: `--big "8[KG]" --small "DIRETO DA [CHINA]" --order big-small --flag` (adapte o peso/origem).
  - Quando ele falar dos links: `--small "TODOS OS LINKS" --big "[NA BIO]"`.
  - Fornecedor citado: `cards.py image` com o PNG em alta, entrando na hora em que ele fala o nome
    (todas as vezes que citar).
  - Final, sobre ele segurando a caixa: `--small "COMENTA" --big "[“QUERO”]" --hold-to-end`,
    entrando quando ele fala "comenta quero".
- Para o tempo exato de cada card: `narration.py check` na narração final com tempos por palavra.

## 6. Montagem e entrega
- `compose.py config.json` → vídeo final. Confira: duração, nenhum silêncio longo,
  transcrição completa, quadros dos cards.
- Mande versões numeradas; quando ele preferir uma versão anterior, volte a ela exatamente.
