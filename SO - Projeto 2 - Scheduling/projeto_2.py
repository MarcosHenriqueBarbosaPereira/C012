import time
import random
from collections import defaultdict
from enum import Enum

from multiprocessing.pool import ThreadPool
from threading import current_thread


class Prioridades(Enum):
    SEM_PRIORIDADE = 0
    IDOSO = 1
    GESTANTE = 2
    CRIANCA_COLO = 3
    DEFICIENTE = 4


class Servicos(Enum):
    SAQUE = 0
    PAGAMENTOS = 1
    DEPOSITO = 2
    PRIORITARIO = 3


class Cliente:
    def __init__(self, nome):
        self.nome = nome
        self.servico = random.choice(list(Servicos))
        self.tempo_entrada_fila = None
        if self.servico == Servicos.PRIORITARIO:
            self.prioridade = random.choice([p for p in Prioridades if p != Prioridades.SEM_PRIORIDADE])
        else:
            self.prioridade = Prioridades.SEM_PRIORIDADE

    @staticmethod
    def gerar_clientes(qtd_clientes: int):
        clientes = [Cliente(f"Cliente {i}") for i in range(1, qtd_clientes + 1)]
        return sorted(clientes, key=lambda x: x.prioridade.value)


class Caixa:
    def __init__(self):
        self.total_atendidos = 0
        self.atendimentos_prioritarios = 0


class Banco:
    def __init__(self, qtd_caixas: int):
        self.qtd_caixas = qtd_caixas
        self.caixas = defaultdict(Caixa)
        self.tempo_total_fila = 0
        self.qtd_clientes_atendidos = 0

    def atender_cliente(self, cliente: Cliente):
        # Armazena o tempo de início do atendimento
        tempo_inicio = time.time()

        caixa = self.metricas_caixa(cliente.prioridade)
        if cliente.prioridade == Prioridades.SEM_PRIORIDADE:
            print(f"\n{caixa} está atendendo o cliente {cliente.nome} para {cliente.servico.name}")
        else:
            print(f"\n{caixa} está atendendo o cliente {cliente.nome} - {cliente.prioridade.name} para {cliente.servico.name}")

        # Armazena o tempo que o cliente permaneceu na fila
        if cliente.tempo_entrada_fila is not None:
            tempo_fila = time.time() - cliente.tempo_entrada_fila
            self.tempo_total_fila += tempo_fila

        # Simula o tempo gasto para atendimento
        time.sleep(random.randint(1, 5))

        # Calcula o tempo de atendimento
        tempo_fim = time.time()
        tempo_atendimento = tempo_fim - tempo_inicio

        print(f"{cliente.nome} atendido por {caixa}")
        return tempo_atendimento

    def metricas_caixa(self, prioridade: Prioridades):
        caixa_nome = current_thread().name
        caixa_nome = caixa_nome.replace('Thread', 'Caixa')
        caixa_nome = caixa_nome.replace(' (worker)', '')

        caixa = self.caixas[caixa_nome]

        caixa.total_atendidos += 1

        if prioridade != Prioridades.SEM_PRIORIDADE:
            caixa.atendimentos_prioritarios += 1

        self.qtd_clientes_atendidos += 1

        return caixa_nome


if __name__ == '__main__':
    qtd_caixas = 1
    banco = Banco(qtd_caixas)

    qtd_clientes = 20
    clientes = Cliente.gerar_clientes(qtd_clientes)

    pool = ThreadPool(processes=banco.qtd_caixas)

    subprocess = []

    # Inicializa o atendimento dos clientes
    while len(clientes) > 0:
        # Armazena o tempo que o cliente entrou na fila
        cliente = clientes.pop()
        cliente.tempo_entrada_fila = time.time()

        # Armazena o tempo gasto no atendimento
        response = pool.apply_async(banco.atender_cliente, args=(cliente,))
        
        subprocess.append(response)

    pool.close()
    pool.join()

    # Aguarda os caixas finalizarem o atendimento e armazena o tempo gasto no atendimento
    tempos_atendimento = 0

    for response in subprocess:
        try:
            tempos_atendimento += response.get(timeout=30)
        except TimeoutError:
            print("Timeout error...")

    print("\n------------ Métricas ------------")

    for nome, caixa in banco.caixas.items():
        print(f"{nome} atendeu {caixa.total_atendidos} cliente(s), sendo {caixa.atendimentos_prioritarios} prioritario(s)")

    print(f"\nTempo total: {round(tempos_atendimento, 2)} s")

    tempo_medio_fila = banco.tempo_total_fila / qtd_clientes
    print(f"Tempo médio na fila: {round(tempo_medio_fila, 2)} s")

    print(f"Tempo médio de atendimento: {round(tempos_atendimento / banco.qtd_clientes_atendidos, 2)} s")
