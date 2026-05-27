import datetime
import calendar
import uuid
import unicodedata
from sqlalchemy.orm import Session
from app import models

FERIADOS_FIXOS = ["01/01", "21/04", "01/05", "07/09", "12/10", "02/11", "15/11", "25/12"]

def normalize(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').upper().strip()

def is_dia_util(date_obj):
    if date_obj.weekday() >= 5: return False
    dia_mes = date_obj.strftime("%d/%m")
    if dia_mes in FERIADOS_FIXOS: return False
    return True

def get_enesimo_dia_util(ano, mes, n):
    data = datetime.date(ano, mes, 1)
    count = 0
    while data.month == mes:
        if is_dia_util(data):
            count += 1
            if count == n:
                return data
        data += datetime.timedelta(days=1)
    last_day = calendar.monthrange(ano, mes)[1]
    return datetime.date(ano, mes, last_day)

def calcular_data_complexa(competencia_date, dia_regra, desloca, antecipa_fds):
    if not dia_regra: return None
    try:
        desloca = int(desloca) if desloca else 0
        mes_total = competencia_date.month + desloca - 1
        ano_destino = competencia_date.year + (mes_total // 12)
        mes_destino = (mes_total % 12) + 1
        
        dia_str = str(dia_regra).upper().strip()
        
        if "U" in dia_str:
            n_dia = int(dia_str.replace("U", ""))
            data_final = get_enesimo_dia_util(ano_destino, mes_destino, n_dia)
        else:
            dia_fixo = int(dia_str)
            last_day = calendar.monthrange(ano_destino, mes_destino)[1]
            if dia_fixo > last_day: dia_fixo = last_day
            data_final = datetime.date(ano_destino, mes_destino, dia_fixo)
            if normalize(antecipa_fds) == "S":
                if data_final.weekday() == 6:
                    data_final -= datetime.timedelta(days=2)
                elif data_final.weekday() == 5:
                    data_final -= datetime.timedelta(days=1)
                    
        return data_final
    except Exception:
        return None

def verify_tag_match(tags_cliente, grupos_regra):
    g_regra = [normalize(g).strip() for g in str(grupos_regra).split(',') if g.strip()]
    if "GLOBAL" in g_regra or "TODOS" in g_regra: return True
    if not g_regra: return False
    t_cli = [normalize(t).strip() for t in str(tags_cliente).split(',') if t.strip()]
    return any(g in t_cli for g in g_regra)

def run_task_engine(db: Session, tenant_id: str, force_competencia=None):
    """
    Gera tarefas baseado nos clientes e regras (Híbrido Whitelist/Blacklist).
    SEM NENHUM ENVIO DE E-MAIL (Apenas manipulação do Banco de Dados).
    """
    if force_competencia:
        hoje = force_competencia
    else:
        hoje = datetime.date.today()
        
    inicio_mes = datetime.date(hoje.year, hoje.month, 1)
    mes_ano_ref = inicio_mes.strftime("%m/%Y")
    
    clientes = db.query(models.Cliente).filter(models.Cliente.tenant_id == tenant_id, models.Cliente.status == "ATIVO").all()
    regras = db.query(models.RegraObrigacao).filter(models.RegraObrigacao.tenant_id == tenant_id).all()
    
    novas = 0
    atualizadas = 0
    
    for cli in clientes:
        exc_str = normalize(cli.excecoes)
        lista_excecoes = [x.strip() for x in exc_str.split(',') if x.strip()]
        cli_regime = normalize(cli.regime)
        
        for reg in regras:
            obrig_norm = normalize(reg.obrigacao)
            
            # Whitelist e Blacklist
            possui_tag = verify_tag_match(cli.perfis_ativos, reg.grupo_regra)
            eh_excecao = obrig_norm in lista_excecoes
            regime_regra = normalize(reg.regime)
            regime_bate = (regime_regra == "TODOS" or regime_regra == cli_regime)
            
            meses_str = str(reg.meses or "")
            mes_bate = False
            if not meses_str.strip():
                mes_bate = True
            else:
                try:
                    meses_arr = [int(m.strip()) for m in meses_str.split(',') if m.strip()]
                    if inicio_mes.month in meses_arr: mes_bate = True
                except:
                    mes_bate = True
            
            if possui_tag and not eh_excecao and regime_bate and mes_bate:
                dt_prazo = calcular_data_complexa(inicio_mes, reg.dia, reg.desloca, reg.antecipa_fds)
                if not dt_prazo: continue
                
                tarefa_existente = db.query(models.Tarefa).filter(
                    models.Tarefa.tenant_id == tenant_id,
                    models.Tarefa.mes_ano == mes_ano_ref,
                    models.Tarefa.cliente == cli.cliente,
                    models.Tarefa.obrigacao == reg.obrigacao
                ).first()
                
                dep_norm = normalize(reg.departamento)
                resp = cli.responsavel or "SISTEMA"
                if "FISCAL" in dep_norm: resp = cli.fiscal or resp
                elif "CONTABIL" in dep_norm: resp = cli.contabil or resp
                elif "PESSOAL" in dep_norm: resp = cli.pessoal or resp
                elif "SOCIETARIO" in dep_norm: resp = cli.societario or resp
                
                if not tarefa_existente:
                    nova_tarefa = models.Tarefa(
                        tenant_id=tenant_id,
                        mes_ano=mes_ano_ref,
                        cliente=cli.cliente,
                        obrigacao=reg.obrigacao,
                        vencimento=dt_prazo,
                        departamento=reg.departamento,
                        status="PENDENTE",
                        acao=reg.acao,
                        responsavel=resp,
                        id_controle=str(uuid.uuid4()),
                        nivel=cli.nivel
                    )
                    db.add(nova_tarefa)
                    novas += 1
                else:
                    if tarefa_existente.status == "PENDENTE":
                        tarefa_existente.vencimento = dt_prazo
                        tarefa_existente.responsavel = resp
                        atualizadas += 1
                        
    db.commit()
    return {"mes_referencia": mes_ano_ref, "novas": novas, "atualizadas": atualizadas}
