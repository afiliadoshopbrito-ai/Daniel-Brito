# video-toolkit — edição de unboxing no padrão do Daniel

Scripts usados para editar os vídeos de recebidos/importação da China:
cortes curtos em velocidade normal, narração limpa e cards com a
identidade do site (dmchoice) com efeito de "choque".

As regras de estilo (o que cortar, como narrar, quais cards) estão em
[`.claude/skills/editar-video-unboxing/SKILL.md`](../.claude/skills/editar-video-unboxing/SKILL.md).

## Requisitos
```bash
pip install gdown faster-whisper numpy pillow   # ffmpeg precisa estar instalado
```

## Passo a passo
```bash
S=video-toolkit/scripts

# 1) Baixar do Google Drive (pasta/arquivo "qualquer pessoa com o link")
python3 $S/drive.py getall "<url da pasta>" videos/

# 2) Mapear os clipes
python3 $S/analyze.py sheet videos/IMG_0001.MOV 0 180 1 mapa.jpg   # um quadro por segundo
python3 $S/analyze.py cry   videos/IMG_0001.MOV                      # choro de bebê?
python3 $S/analyze.py peaks videos/IMG_0001.MOV 40 70                # estalos / rasgos
python3 $S/analyze.py snap  videos/IMG_0001.MOV 56.4 0.8             # corte que termina no fim do barulho

# 3) Lista de cortes -> vídeo-base (+ prévia rotulada para revisar)
#    cortes.txt:  <arquivo> <inicio_s> <duracao_s> <rotulo>
python3 $S/render_cuts.py cortes.txt previa --preview
python3 $S/render_cuts.py cortes.txt base           # base.video.mp4 + base.orig.wav

# 4) Narração
python3 $S/narration.py transcribe narr/QD1.m4a          # achar as melhores tomadas
python3 $S/narration.py words narr/QD1.m4a 40 45          # acertar ponto de corte
python3 $S/narration.py clean secoes.json narr_out        # tira pausas/respirações
python3 $S/narration.py place narr_out ordem.json 83.3    # emenda sem buracos -> narr_out/narracao.wav
python3 $S/narration.py check narr_out/narracao.wav       # conferir palavras e tempos

# 5) Cards com efeito de choque
python3 $S/cards.py text fx/title --big "8[KG]" --small "DIRETO DA [CHINA]" --order big-small --flag
python3 $S/cards.py text fx/links --small "TODOS OS LINKS" --big "[NA BIO]"
python3 $S/cards.py image fx/fornecedor cards/WWTOP.png
python3 $S/cards.py text fx/comenta --small "COMENTA" --big "[“QUERO”]" --hold-to-end

# 6) Montagem final
python3 $S/compose.py config.json
```

Exemplo de `secoes.json` (trechos escolhidos de cada áudio, em segundos;
o 4º número opcional dá folga no fim para a palavra terminar):
```json
{"intro":  [["narr/QD8.m4a", 1.0, 5.3], ["narr/QD8.m4a", 5.6, 10.05]],
 "conjunto": [["narr/QD10.m4a", 37.75, 42.32, 0.06]],
 "cta":    [["narr/QD11.m4a", 0.4, 7.85]]}
```

Exemplo de `config.json`: veja o cabeçalho de `scripts/compose.py`.

## Fontes
`fonts/Archivo-800.ttf` e `fonts/Archivo-900.ttf` (Archivo, SIL Open Font
License — `fonts/OFL.txt`), as mesmas do site.
