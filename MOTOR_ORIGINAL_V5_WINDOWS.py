# -*- coding: utf-8 -*-
"""Dia de Sorte Campeao V5 - estudo de tirinhas, jogo e mes da sorte."""
import csv, re, os, sys, itertools, random, subprocess
from pathlib import Path
from collections import Counter

TIRAS = [tuple(range(i, min(i+4,32))) for i in range(1,32,4)]
MESES = ['JANEIRO','FEVEREIRO','MARCO','ABRIL','MAIO','JUNHO','JULHO','AGOSTO','SETEMBRO','OUTUBRO','NOVEMBRO','DEZEMBRO']
MESES_ALIAS = {re.sub('[^A-Z]','',s):i+1 for i,s in enumerate(MESES)}
MESES_ALIAS['MARÇO']=3
PASTA = Path(__file__).resolve().parent
SAIDA = PASTA/'Relatorios_Dia_de_Sorte'
SAIDA.mkdir(parents=True,exist_ok=True)

def downloads():
    paths=[Path.home()/'Downloads',Path.home()/'Download']
    for env in ('USERPROFILE','OneDrive','OneDriveConsumer'):
        if os.environ.get(env): paths.extend([Path(os.environ[env])/'Downloads',Path(os.environ[env])/'Download'])
    return [p for p in dict.fromkeys(paths) if p.exists()]

def escolher():
    arquivos=[]
    for pasta in downloads():
        arquivos.extend(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in ('.txt','.csv'))
    arquivos=sorted(set(arquivos),key=lambda p:p.name.lower())
    print('\nARQUIVOS TXT/CSV ENCONTRADOS EM DOWNLOADS:')
    for i,p in enumerate(arquivos,1): print(f'{i:3} - {p.name}  [{p.parent}]')
    print('  0 - Informar caminho completo do arquivo')
    while True:
        x=input('NUMERO do arquivo: ').strip()
        if x=='0':
            p=Path(input('Cole o caminho completo: ').strip().strip('"'))
            if p.is_file():return p
        elif x.isdigit() and 1<=int(x)<=len(arquivos):return arquivos[int(x)-1]
        print('Escolha invalida. Verifique se o historico esta em Downloads.')

def mes_valor(s):
    s=s.strip().upper().replace('Ç','C').replace('Ê','E').replace('É','E')
    if s.isdigit() and 1<=int(s)<=12:return int(s)
    return MESES_ALIAS.get(re.sub('[^A-Z]','',s))

def parse_num(s):
    s=s.strip().strip('"').replace('.0','')
    if re.fullmatch(r'\d{1,2}',s) and 1<=int(s)<=31:return int(s)
    return None

def normalizar(s):
    import unicodedata
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode('ascii').lower()
    return re.sub(r'[^a-z0-9]','',s)

def ler(p):
    raw=None
    for enc in ('utf-8-sig','utf-8','cp1252','latin-1'):
        try:
            raw=p.read_text(encoding=enc)
            break
        except UnicodeError:
            continue
    if raw is None: raise ValueError('Nao foi possivel ler o arquivo.')
    linhas=[x.strip() for x in raw.splitlines() if x.strip()]
    if not linhas: raise ValueError('Arquivo vazio.')

    # Formatos aceitos: CSV com cabecalho (Bola1..7, 1a Dezena..7a Dezena),
    # CSV/TXT sem cabecalho, separado por ponto-e-virgula, virgula, TAB ou espacos.
    delimitador=max((';','\t',','),key=lambda d:sum(l.count(d) for l in linhas[:5]))
    if sum(l.count(delimitador) for l in linhas[:5])>=5:
        rows=list(csv.reader(linhas,delimiter=delimitador))
    else:
        rows=[re.split(r'\s+',l) for l in linhas]
    cab=[normalizar(v) for v in rows[0]]
    indices=[]
    for i,v in enumerate(cab):
        m=re.fullmatch(r'(?:bola|dezena|numero|num|d)([1-7])',v)
        if not m:
            m=re.fullmatch(r'([1-7])(?:a|o)?(?:dezena|bola|numero)',v)
        if m:indices.append((int(m.group(1)),i))
    if len(indices)==7 and len({a for a,_ in indices})==7:
        indices=[i for _,i in sorted(indices)]
        inicio=1
    else:
        indices=None
        inicio=0
    midx=next((i for i,v in enumerate(cab) if v in ('mesdasorte','mesdesorte','mes','messorte','mesdosorte')),None)
    cidx=next((i for i,v in enumerate(cab) if v in ('concurso','numeroconcurso','nconcurso','numerodoconcurso')),None)

    dados=[]; vistos=set(); rejeitadas=0; amostras=[]
    for numero_linha,row in enumerate(rows[inicio:],inicio+1):
        try:
            cols=[str(x).strip().strip('"') for x in row]
            # Formato confirmado no arquivo do usuario:
            # 1 - 03,05,08,09,19,21,30 - Fevereiro
            # Primeiro numero e CONCURSO, nao dezena.
            linha_original = linhas[numero_linha-1]
            especial = re.fullmatch(
                r'\s*(\d+)\s*-\s*((?:\d{1,2}\s*,\s*){6}\d{1,2})\s*-\s*([A-Za-zÀ-ÿ]+)\s*',
                linha_original
            )
            if especial:
                conc = int(especial.group(1))
                dezenas = [parse_num(x) for x in especial.group(2).split(',')]
                mes = mes_valor(especial.group(3))
                if mes is None:
                    raise ValueError('Mes da Sorte nao reconhecido')
            elif indices is not None:
                dezenas=[parse_num(cols[i]) for i in indices]
                mes=mes_valor(cols[midx]) if midx is not None and midx<len(cols) else None
                conc=int(cols[cidx]) if cidx is not None and cidx<len(cols) and cols[cidx].isdigit() else numero_linha
            else:
                # Remove data em formato DD/MM/AAAA ou AAAA-MM-DD.
                cols=[v for v in cols if v and not re.fullmatch(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2}',v)]
                # Detecta numero do concurso no inicio, inclusive em arquivo com
                # muitos campos adicionais depois das 7 dezenas.
                conc=numero_linha
                if len(cols)>=8 and cols[0].isdigit() and (len(cols[0])>=3 or int(cols[0])>31):
                    conc=int(cols.pop(0))
                # Exigir 7 dezenas validas e distintas no inicio do trecho.
                dezenas=[parse_num(v) for v in cols[:7]]
                mes=mes_valor(cols[7]) if len(cols)>=8 else None
                # Se primeira coluna era concurso 1..31, identificar pelo total
                # de campos: 1 concurso + 7 dezenas + mes opcional.
                if (None in dezenas or len(set(dezenas))!=7) and len(cols)>=8 and cols[0].isdigit():
                    alternativa=[parse_num(v) for v in cols[1:8]]
                    if None not in alternativa and len(set(alternativa))==7:
                        conc=int(cols[0]);dezenas=alternativa
                        mes=mes_valor(cols[8]) if len(cols)>=9 else None
            if len(dezenas)!=7 or None in dezenas or len(set(dezenas))!=7:
                raise ValueError('Sete dezenas invalidas')
            if conc in vistos:raise ValueError('Concurso repetido')
            vistos.add(conc)
            dados.append((conc,set(dezenas),mes))
        except (ValueError,IndexError,TypeError) as erro:
            rejeitadas+=1
            if len(amostras)<5:
                amostras.append((numero_linha, ' | '.join(map(str,row))[:170],str(erro)))
    dados.sort(key=lambda x:x[0])
    print(f'\nLINHAS: {len(rows)} | CONCURSOS VALIDOS: {len(dados)} | REJEITADOS: {rejeitadas}')
    if amostras:
        print('EXEMPLOS DE LINHAS IGNORADAS:')
        for linha,conteudo,motivo in amostras:
            print(f' Linha {linha}: {conteudo} [{motivo}]')
    if len(dados)<10:
        print('\nPRIMEIRAS 5 LINHAS ORIGINAIS DO TXT:')
        for l in linhas[:5]:print(l[:250])
        raise ValueError('Leitura insuficiente: envie foto destas linhas para ajustar o formato.')
    print(f'PRIMEIRO: {dados[0][0]} | ULTIMO: {dados[-1][0]}')
    faltantes=sorted(set(range(dados[0][0],dados[-1][0]+1))-set(c for c,_,_ in dados))
    if faltantes:
        print('ATENCAO: concursos faltantes:', faltantes[:30], 'total:', len(faltantes))
        if input('Continuar mesmo assim? (S/N): ').strip().upper()!='S':
            raise ValueError('Historico incompleto: operacao cancelada.')
    if rejeitadas:
        print('ATENCAO: linhas rejeitadas:', rejeitadas)
        if input('Continuar mesmo assim? (S/N): ').strip().upper()!='S':
            raise ValueError('Linhas rejeitadas: operacao cancelada.')
    print('MESES VALIDOS:',sum(m is not None for _,_,m in dados))
    print('PRIMEIRO RESULTADO:', ' '.join(f'{n:02}' for n in sorted(dados[0][1])))
    print('ULTIMO RESULTADO:', ' '.join(f'{n:02}' for n in sorted(dados[-1][1])))
    if input('CONFIRMA A LEITURA? (S/N): ').strip().upper()!='S':
        raise SystemExit('Leitura nao confirmada.')
    return dados

def analisar(dados):
    total=len(dados);res=[]
    for qtd in range(1,9):
        for ids in itertools.combinations(range(8),qtd):
            dezenas=set().union(*(set(TIRAS[i]) for i in ids))
            falhas=0;ultimo=None;seq=0;maxseq=0
            for pos,(_,s,_) in enumerate(dados):
                if not dezenas.intersection(s):
                    falhas+=1;ultimo=pos;seq+=1;maxseq=max(maxseq,seq)
                else:seq=0
            atraso=total-1-ultimo if ultimo is not None else total
            res.append(dict(ids=ids,dezenas=dezenas,qt=len(dezenas),falhas=falhas,atraso=atraso,maxseq=maxseq,ultimo=dados[ultimo][0] if ultimo is not None else None))
    return res

def sugerir(dados,res):
    # Usar 1 ou 2 tiras inteiras (3 a 8 dezenas), evitando blocos grandes
    # cuja ausencia integral e matematicamente muito rara.
    candidatos=[r for r in res if len(r['ids']) in (1,2)]
    candidatos.sort(key=lambda r:(r['atraso'],r['falhas']/len(dados)),reverse=True)
    return candidatos

def escolher_tiras(candidatos):
    print('\nCANDIDATAS A FALHA INTEIRA (historico, NAO previsao):')
    for i,r in enumerate(candidatos[:20],1):
        print(f"{i:2} - T{'+T'.join(str(j+1) for j in r['ids'])} | {len(r['dezenas'])} dz | falhas {r['falhas']} | atraso {r['atraso']} | "+' '.join(f'{d:02}' for d in sorted(r['dezenas'])))
    while True:
        x=input('\nEscolha 1-20, ou 0 para nao retirar tiras: ').strip()
        if x.isdigit() and 0<=int(x)<=20:
            return set() if x=='0' else set(candidatos[int(x)-1]['dezenas'])
        print('Numero invalido.')

def ranking_dezenas(dados):
    # Frieza ponderada: ultimos 30 e 100 concursos, e atraso individual.
    freq30=Counter(n for _,s,_ in dados[-30:] for n in s)
    freq100=Counter(n for _,s,_ in dados[-100:] for n in s)
    ultimo={n:len(dados) for n in range(1,32)}
    for i,(_,s,_) in enumerate(reversed(dados)):
        for n in s:
            if ultimo[n]==len(dados):ultimo[n]=i
    return sorted(range(1,32),key=lambda n:(freq30[n]/min(30,len(dados)),freq100[n]/min(100,len(dados)),-ultimo[n],n))

def escolher_mes(dados):
    validos=[m for _,_,m in dados if m is not None]
    if not validos:
        print('\nO arquivo nao contem Mes da Sorte reconhecivel. Escolha manualmente.')
        sugerido=1
    else:
        freq=Counter(validos[-100:]);atraso={m:len(validos) for m in range(1,13)}
        for i,m in enumerate(reversed(validos)):
            if atraso[m]==len(validos):atraso[m]=i
        ordem=sorted(range(1,13),key=lambda m:(freq[m],-atraso[m],m))
        sugerido=ordem[0]
        print('\nMESES DA SORTE - ultimos ate 100 concursos:')
        for m in ordem:print(f'{m:2} - {MESES[m-1]:10} | saiu {freq[m]:3} | atraso {atraso[m]}')
    x=input(f'Mes sugerido {MESES[sugerido-1]}. ENTER aceita; ou digite 1-12: ').strip()
    return int(x) if x.isdigit() and 1<=int(x)<=12 else sugerido

def pdf_relatorio(jogo,mes,retiradas,dados,res,ranking):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    arq=SAIDA/'DIA_DE_SORTE_CAMPEAO_V5_VOLANTE.pdf'
    c=canvas.Canvas(str(arq),pagesize=A4)
    w,h=A4
    c.setFillColorRGB(0.95,0.70,0.06);c.rect(0,h-88,w,88,fill=1,stroke=0)
    c.setFillColorRGB(0.10,0.10,0.10);c.setFont('Helvetica-Bold',20)
    c.drawCentredString(w/2,h-46,'DIA DE SORTE CAMPEAO V5')
    c.setFont('Helvetica',11);c.drawCentredString(w/2,h-67,'VOLANTE PARA ESTUDO - NAO E COMPROVANTE DE APOSTA')
    c.setFont('Helvetica-Bold',13);c.drawString(46,h-119,'7 DEZENAS MARCADAS')
    x0=52;y0=h-175;cw=70;ch=53
    for n in range(1,32):
        row=(n-1)//7;col=(n-1)%7;x=x0+col*cw;y=y0-row*ch
        marcado=n in jogo
        if marcado:c.setFillColorRGB(0.98,0.78,0.12);c.roundRect(x,y-36,56,43,8,fill=1,stroke=0)
        c.setFillColorRGB(0.2,0.2,0.2);c.setFont('Helvetica-Bold' if marcado else 'Helvetica',17)
        c.drawCentredString(x+28,y-20,f'{n:02}')
    y=h-465;c.setFont('Helvetica-Bold',12);c.drawString(46,y,'MES DA SORTE: '+MESES[mes-1]);y-=30
    c.setFont('Helvetica',10);c.drawString(46,y,'JOGO: '+' '.join(f'{n:02}' for n in sorted(jogo)));y-=22
    c.drawString(46,y,'TIRINHAS RETIRADAS: '+' '.join(f'{n:02}' for n in sorted(retiradas)) if retiradas else 'TIRINHAS RETIRADAS: nenhuma');y-=22
    c.drawString(46,y,f'HISTORICO: {len(dados)} concursos | {dados[0][0]} ate {dados[-1][0]}');y-=25
    c.setFont('Helvetica',9)
    c.drawString(46,y,'Aviso: falhas passadas e atrasos nao aumentam as chances futuras.')
    c.showPage()
    c.setFont('Helvetica-Bold',15);c.drawString(40,h-48,'ESTUDO - 255 COMBINACOES DE TIRINHAS')
    y=h-80;c.setFont('Helvetica',8)
    for r in sorted(res,key=lambda a:(a['qt'],-a['atraso'], -a['falhas'])):
        line=f"T{'+T'.join(str(i+1) for i in r['ids']):13} | {r['qt']:2} dz | falhas {r['falhas']:4} | atraso {r['atraso']:4} | max seq {r['maxseq']:2}"
        if y<45:c.showPage();y=h-50;c.setFont('Helvetica',8)
        c.drawString(40,y,line);y-=12
    c.save()
    if not arq.is_file() or arq.stat().st_size<1000:raise RuntimeError('Falha ao verificar PDF.')
    return arq

def salvar_csv(dados,res,jogo,mes,retiradas):
    p=SAIDA/'DIA_DE_SORTE_V5_RANKING_255.csv'
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['Tirinhas','Qtd dezenas','Dezenas','Falhas','Taxa','Atraso','Maior sequencia','Ultima falha'])
        for r in sorted(res,key=lambda r:(r['qt'],-r['atraso'])):
            w.writerow(['+'.join('T'+str(i+1) for i in r['ids']),r['qt'],' '.join(f'{n:02}' for n in sorted(r['dezenas'])),r['falhas'],f"{100*r['falhas']/len(dados):.2f}%",r['atraso'],r['maxseq'],r['ultimo'] or '-'])
    p2=SAIDA/'DIA_DE_SORTE_V5_JOGO.txt'
    p2.write_text('DIA DE SORTE CAMPEAO V5\nJOGO: '+' '.join(f'{n:02}' for n in sorted(jogo))+'\nMES DA SORTE: '+MESES[mes-1]+'\nTIRAS RETIRADAS: '+' '.join(f'{n:02}' for n in sorted(retiradas))+'\n',encoding='utf-8')
    return p,p2

def main():
    print('='*65+'\n DIA DE SORTE CAMPEAO V5 - WINDOWS\n'+'='*65)
    print('Estudo de falhas e sugestao de jogo, sem garantia de premio.')
    arquivo=escolher();print('\nLENDO:',arquivo)
    dados=ler(arquivo);res=analisar(dados);candidatos=sugerir(dados,res)
    while True:
        retiradas=escolher_tiras(candidatos)
        ranking=ranking_dezenas(dados)
        disponiveis=[n for n in range(1,32) if n not in retiradas]
        # priorizar dezenas mais frequentes recentemente entre as nao retiradas
        # e equilibrar pares/impares por escolha gulosa.
        freq=Counter(n for _,s,_ in dados[-100:] for n in s)
        disponiveis.sort(key=lambda n:(-freq[n],n))
        jogo=[]
        for n in disponiveis:
            if len(jogo)>=7:break
            if sum(x%2==n%2 for x in jogo)<4:jogo.append(n)
        if len(jogo)<7:jogo+= [n for n in disponiveis if n not in jogo][:7-len(jogo)]
        jogo=set(jogo)
        print('\nTIRAS PARA FALHA:',' '.join(f'{n:02}' for n in sorted(retiradas)) or 'nenhuma')
        print('SUGESTAO DE 7 DEZENAS:',' '.join(f'{n:02}' for n in sorted(jogo)))
        x=input('ENTER aceita; R refaz escolha das tiras; M digitar 7 dezenas manualmente: ').strip().upper()
        if x=='R':continue
        if x=='M':
            nums=[int(t) for t in re.findall(r'\d+',input('Digite 7 dezenas de 01 a 31 separadas por espaco: '))]
            if len(nums)!=7 or len(set(nums))!=7 or not all(1<=n<=31 for n in nums):
                print('Jogo invalido. Tente novamente.');continue
            if set(nums)&retiradas:
                print('Jogo contem dezenas das tirinhas retiradas:', sorted(set(nums)&retiradas))
                continue
            jogo=set(nums)
        break
    mes=escolher_mes(dados)
    print('\nJOGO FINAL:', ' '.join(f'{n:02}' for n in sorted(jogo)),'| MES:',MESES[mes-1])
    a,b=salvar_csv(dados,res,jogo,mes,retiradas)
    try:
        p=pdf_relatorio(jogo,mes,retiradas,dados,res,ranking)
        print('\nPDF GERADO E VERIFICADO:',p,'|',p.stat().st_size,'bytes')
    except ImportError:
        print('\nERRO: reportlab nao instalado. Execute INSTALAR_DEPENDENCIAS.bat e rode novamente.')
    print('CSV:',a,'\nTXT:',b,'\nPASTA:',SAIDA)
    if os.name=='nt':os.startfile(str(SAIDA))

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('\nERRO:',e)
    input('\nPressione ENTER para encerrar...')
