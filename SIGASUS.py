# Fluxo do sistema (baseado no funcionamento real do SUS):
#   1. Cadastro do paciente (com validacao de CPF e Cartao SUS/CNS)
#   2. Triagem inicial - Classificacao de Risco (Protocolo de Manchester)
#   3. Agendamento automatico da consulta dentro da UBS
#   4. Comprovante de agendamento na UBS (salvo em arquivo)
#
# Embasamento (SUS real):
#   - Classificacao de risco: Protocolo de Manchester, usado no SUS desde 2008,
#     com 5 cores (Vermelho, Laranja, Amarelo, Verde, Azul) por gravidade.
#   - CNS: Cartao Nacional de Saude possui 15 digitos e identifica o usuario.
#   - Atencao Primaria: o foco do SIGASUS e tornar o agendamento de consultas
#     dentro da UBS mais pratico e acessivel para a populacao.
#     A cor de risco define a PRIORIDADE (quanto antes sera a consulta na UBS).

import unicodedata
from datetime import datetime, timedelta


# FUNCOES AUXILIARES DE VALIDACAO
def normalizar(texto):
    """Remove acentos e coloca em minusculo, para comparar sintomas."""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto


def so_digitos(valor):
    """Retorna apenas os numeros de uma string (remove pontos, tracos etc.)."""
    return "".join(c for c in valor if c.isdigit())


def validar_cpf(cpf):
    """Valida o CPF pelo algoritmo oficial dos digitos verificadores."""
    cpf = so_digitos(cpf)

    if len(cpf) != 11:
        return False
    # CPFs com todos os digitos iguais sao invalidos (ex.: 111.111.111-11)
    if cpf == cpf[0] * 11:
        return False

    # Calcula o 1o e o 2o digito verificador
    for i in range(9, 11):
        soma = 0
        for j in range(i):
            soma += int(cpf[j]) * ((i + 1) - j)
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(cpf[i]):
            return False
    return True


def validar_cns(cns):
    """Valida o Cartao Nacional de Saude (CNS): deve ter 15 digitos."""
    cns = so_digitos(cns)
    return len(cns) == 15


def validar_data(data):
    """Confere se a data de nascimento existe e nao esta no futuro."""
    try:
        nascimento = datetime.strptime(data, "%d/%m/%Y")
    except ValueError:
        return False
    return nascimento <= datetime.now()


def validar_cep(cep):
    """Valida o CEP: deve ter 8 digitos."""
    return len(so_digitos(cep)) == 8


# Mapeamento CEP -> bairro -> UBS real de Campina Grande-PB.
# Cada faixa usa o CEP completo (8 digitos, sem o traco) como numero inteiro.
# Ordem: das faixas mais especificas para as mais amplas (1a correspondencia vence).
FAIXAS_UBS = [
    # (cep_inicial, cep_final, bairro, UBS real)
    (58404450, 58404891, "Cuites", "UBS Jocel Fechine"),
    (58407000, 58407999, "Jose Pinheiro", "UBS Antonio Arruda"),
    (58410000, 58410999, "Catole", "UBS Nossa Senhora Aparecida"),
    (58414000, 58414999, "Liberdade", "UBS Argemiro de Figueiredo"),
    (58428300, 58428610, "Pedregal", "UBS Raimundo Carneiro"),
    (58428700, 58428999, "Bela Vista", "UBS Bela Vista"),
    (58430000, 58430999, "Bodocongo", "UBS Joao Rique"),
    (58432000, 58433615, "Malvinas", "UBS Ricardo Amorim Guedes"),
    (58433700, 58433999, "Ramadinha", "UBS Hindemburgo Nunes"),
    (58441000, 58441999, "Distrito Sao Jose da Mata", "UBS Sao Jose da Mata"),
    (58444000, 58444999, "Catole de Boa Vista", "UBS Catole de Boa Vista"),
    # Area central (Centro / Prata / Monte Santo) - faixa ampla, fica por ultimo
    (58400000, 58401999, "Centro / Prata / Monte Santo", "UBS Bonald Filho"),
]


def encontrar_ubs(cep):
    """Direciona o paciente para a UBS mais proxima conforme o CEP.

    Mapeamento baseado em UBS reais de Campina Grande-PB e nas faixas
    de CEP de cada bairro.
    """
    cep = so_digitos(cep)
    if len(cep) != 8:
        return {"nome": "UBS de referencia (confirme na Secretaria de Saude)",
                "bairro": "Nao identificado pelo CEP"}

    numero = int(cep)
    for inicio, fim, bairro, ubs in FAIXAS_UBS:
        if inicio <= numero <= fim:
            return {"nome": ubs, "bairro": bairro}

    # CEP valido, mas fora das faixas mapeadas (outro bairro ou outra cidade)
    return {
        "nome": "UBS de referencia (confirme na Secretaria de Saude)",
        "bairro": "Nao identificado pelo CEP",
    }



# ETAPA 1 - CADASTRO DO PACIENTE (com validacao)
def cadastrar_paciente():
    print("\n" + "=" * 50)
    print("        ETAPA 1 - CADASTRO DO PACIENTE")
    print("=" * 50)

    nome = ""
    while nome == "":
        nome = input("Nome completo: ").strip()
        if nome == "":
            print(" -> O nome nao pode ficar em branco.")

    # CPF com validacao
    cpf = input("CPF (somente numeros ou com pontuacao): ").strip()
    while not validar_cpf(cpf):
        print(" -> CPF invalido. Digite os 11 numeros corretamente.")
        cpf = input("CPF: ").strip()
    cpf = so_digitos(cpf)

    # Cartao SUS (CNS) com validacao
    cns = input("Numero do Cartao SUS / CNS (15 digitos): ").strip()
    while not validar_cns(cns):
        print(" -> Cartao SUS invalido. O CNS deve ter 15 digitos.")
        cns = input("Cartao SUS / CNS: ").strip()
    cns = so_digitos(cns)

    # Data de nascimento com validacao
    nascimento = input("Data de nascimento (dd/mm/aaaa): ").strip()
    while not validar_data(nascimento):
        print(" -> Data invalida. Use o formato dd/mm/aaaa e uma data real.")
        nascimento = input("Data de nascimento (dd/mm/aaaa): ").strip()

    endereco = input("Endereco: ").strip()


    # CEP com validacao (usado para indicar a UBS mais proxima)
    cep = input("CEP (8 digitos): ").strip()
    while not validar_cep(cep):
        print(" -> CEP invalido. Digite os 8 numeros do CEP.")
        cep = input("CEP (8 digitos): ").strip()
    cep = so_digitos(cep)

    # O bairro e preenchido automaticamente a partir do CEP informado
    bairro = encontrar_ubs(cep)["bairro"]
    print(" -> Bairro identificado pelo CEP:", bairro)

    contato = input("Telefone para contato: ").strip()

    paciente = {
        "nome": nome,
        "cpf": cpf,
        "cartao_sus": cns,
        "nascimento": nascimento,
        "endereco": endereco if endereco else "Nao informado",
        "cep": cep,
        "bairro": bairro,
        "contato": contato if contato else "Nao informado",
    }

    print("\nCadastro realizado e validado com sucesso!")
    return paciente



# ETAPA 2 - TRIAGEM / CLASSIFICACAO DE RISCO
# Protocolo de Manchester (5 cores) - usado pelo SUS
# A cor define a PRIORIDADE da consulta dentro da UBS.
def fazer_triagem():
    print("\n" + "=" * 50)
    print("     ETAPA 2 - TRIAGEM (CLASSIFICACAO DE RISCO)")
    print("        Protocolo de Manchester - SUS")
    print("=" * 50)

    # Sintomas associados a cada cor (do mais grave para o menos grave),
    # com base nos sinais mais indicados pelos medicos na triagem.
    # As listas usam texto SEM acento porque a entrada e normalizada.

    # VERMELHO - Emergencia: risco de morte imediato
    vermelho = [
        "parada", "nao respira", "sem respirar", "inconsciente",
        "desmaiado", "convulsao", "hemorragia", "sangramento intenso",
        "engasgado", "reacao alergica grave", "anafilaxia",
        "dor no peito com falta de ar", "labios roxos",
    ]
    # LARANJA - Muito urgente: quadro grave e instavel
    laranja = [
        "dor no peito", "dor intensa", "falta de ar",
        "dificuldade para respirar", "avc", "boca torta",
        "fraqueza de um lado", "fala enrolada", "infarto",
        "fratura exposta", "queimadura grave", "vomito com sangue",
    ]
    # AMARELO - Urgente: precisa de atendimento rapido
    amarelo = [
        "febre alta", "vomito intenso", "diarreia intensa",
        "desidratacao", "dor abdominal forte", "pressao alta",
        "corte profundo", "dor de cabeca forte", "falta de ar leve",
        "crise asmatica",
    ]
    # VERDE - Pouco urgente: sintomas leves e comuns
    verde = [
        "febre", "gripe", "resfriado", "tosse", "dor de garganta",
        "dor de cabeca", "dor leve", "tontura", "diarreia",
        "dor nas costas", "infeccao urinaria", "alergia leve",
    ]
    # AZUL - Nao urgente: rotina e acompanhamento
    azul = [
        "rotina", "receita", "renovar receita", "resultado de exame",
        "atestado", "acompanhamento", "check up", "vacina",
        "consulta de rotina", "pressao estavel",
    ]

    print("Descreva os sintomas que o paciente esta sentindo.")
    entrada = input("Sintomas: ")
    sintomas = normalizar(entrada)

    # Classificacao por prioridade (verifica do mais grave para o mais leve)
    if any(s in sintomas for s in vermelho):
        cor, nivel = "VERMELHO", "Emergencia"
    elif any(s in sintomas for s in laranja):
        cor, nivel = "LARANJA", "Muito urgente"
    elif any(s in sintomas for s in amarelo):
        cor, nivel = "AMARELO", "Urgente"
    elif any(s in sintomas for s in verde):
        cor, nivel = "VERDE", "Pouco urgente"
    elif any(s in sintomas for s in azul):
        cor, nivel = "AZUL", "Nao urgente"
    else:
        # Sem correspondencia: trata como rotina (nao urgente)
        cor, nivel = "AZUL", "Nao urgente"

    print("\nTriagem concluida.")
    print("Cor de risco:", cor, "(" + nivel + ")")

    return {"cor": cor, "nivel": nivel}



# ETAPA 3 - AGENDAMENTO AUTOMATICO DA CONSULTA NA UBS
# A cor de risco define a PRIORIDADE (quanto antes sera a consulta).
# Todo atendimento e agendado dentro da UBS de referencia.
def agendar_consulta(triagem):
    cor = triagem["cor"]
    hoje = datetime.now()

    # Para cada cor: prazo (em dias), horario e descricao da prioridade.
    regras = {
        "VERMELHO": (0, "08:00", "Prioridade maxima - encaixe no mesmo dia"),
        "LARANJA":  (1, "08:30", "Prioridade alta - proximo dia util"),
        "AMARELO":  (3, "09:00", "Prioridade media - atendimento rapido"),
        "VERDE":    (7, "10:00", "Agendamento normal"),
        "AZUL":     (15, "11:00", "Consulta de rotina / acompanhamento"),
    }

    dias, hora, prioridade = regras[cor]
    consulta = hoje + timedelta(days=dias)

    return {
        "tipo": prioridade,
        "data": consulta.strftime("%d/%m/%Y"),
        "hora": hora,
        "local": "UBS de referencia",
        "medico": "Equipe de Saude da Familia",
    }



# ETAPA 4 - COMPROVANTE E ENCAMINHAMENTO PARA A UBS / UPA
# (exibe na tela e salva em arquivo de texto)
def gerar_comprovante(paciente, triagem, agenda, ubs):
    linhas = []
    linhas.append("=" * 50)
    linhas.append("        COMPROVANTE DE ATENDIMENTO - SIGASUS")
    linhas.append("              Sistema Unico de Saude")
    linhas.append("=" * 50)
    linhas.append("Paciente:       " + paciente["nome"])
    linhas.append("Cartao SUS:     " + paciente["cartao_sus"])
    linhas.append("CPF:            " + paciente["cpf"])
    linhas.append("Contato:        " + paciente["contato"])
    linhas.append("-" * 50)
    linhas.append("Classificacao:  " + triagem["cor"] + " (" + triagem["nivel"] + ")")
    linhas.append("Prioridade:     " + agenda["tipo"])
    linhas.append("Data:           " + agenda["data"])
    linhas.append("Horario:        " + agenda["hora"])
    linhas.append("-" * 50)
    linhas.append("UBS indicada:   " + ubs["nome"])
    linhas.append("Bairro:         " + ubs["bairro"])
    linhas.append("CEP informado:  " + paciente["cep"])
    linhas.append("Responsavel:    " + agenda["medico"])
    linhas.append("=" * 50)

    linhas.append("ATENCAO SR. USUARIO")
    linhas.append("Prioridade do caso: " + triagem["cor"] + " (" + triagem["nivel"] + ")")
    linhas.append("Compareca com um documento com foto na data e horario marcado.")
    linhas.append("=" * 50)

    # Exibe na tela
    print()
    for linha in linhas:
        print(linha)

    # Salva no arquivo (acrescenta ao final, mantendo o historico)
    with open("comprovantes_sigasus.txt", "a", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas))
        arquivo.write("\n\n")

    print("\n(Comprovante salvo no arquivo 'comprovantes_sigasus.txt')")



# PROGRAMA PRINCIPAL - integra as 4 etapas
def main():
    print("=" * 50)
    print("   BEM-VINDO AO SIGASUS")
    print("   Sistema Integrado de Gestao e")
    print("   Agendamento do SUS")
    print("=" * 50)

    continuar = True
    while continuar:
        paciente = cadastrar_paciente()        # Etapa 1
        triagem = fazer_triagem()              # Etapa 2
        agenda = agendar_consulta(triagem)     # Etapa 3
        ubs = encontrar_ubs(paciente["cep"])   # UBS mais proxima pelo CEP
        gerar_comprovante(paciente, triagem, agenda, ubs)  # Etapa 4

        resposta = input("\nDeseja atender outro paciente? (s/n): ").strip().lower()
        if resposta != "s":
            continuar = False

    print("\nObrigado por utilizar o SIGASUS. Cuide da sua saude!")


# Executa o programa
if __name__ == "__main__":
    main()
