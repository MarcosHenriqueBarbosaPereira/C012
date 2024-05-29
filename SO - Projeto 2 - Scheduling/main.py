import time
import random
from collections import defaultdict
from enum import Enum

from multiprocessing.pool import ThreadPool
import threading

# Enum Prioridades --------------------------------------------------------------------------------------------------------
class Prioridades(Enum):
    SEM_PRIORIDADE = 0
    IDOSO = 1
    GESTANTE = 2
    CRIANCA_COLO = 3
    DEFICIENTE = 4

# Enum Servicos -----------------------------------------------------------------------------------------------------------
class Servicos(Enum):
    SAQUE = 0
    PAGAMENTOS = 1
    DEPOSITO = 2
    PRIORITARIO = 3


# Classe Cliente ----------------------------------------------------------------------------------------------------------
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
        # FCFS
        clientes = [Cliente(f"Cliente {i}") for i in range(1, qtd_clientes + 1)]
        return clientes

    @staticmethod
    def gerar_clientes_prioridade(qtd_clientes: int):
        # PS
        clientes = Cliente.gerar_clientes(qtd_clientes)
        return sorted(clientes, key=lambda x: x.prioridade.value)


# Classe Caixa ------------------------------------------------------------------------------------------------------------
class Caixa:
    def __init__(self):
        self.total_atendidos = 0
        self.atendimentos_prioritarios = 0


# Classe Banco ------------------------------------------------------------------------------------------------------------
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
        caixa_nome = threading.current_thread().name
        caixa_nome = caixa_nome.replace('Thread', 'Caixa')
        caixa_nome = caixa_nome.replace(' (worker)', '')
        caixa_nome = caixa_nome.replace(' (thread_func)', '')

        caixa = self.caixas[caixa_nome]

        caixa.total_atendidos += 1

        if prioridade != Prioridades.SEM_PRIORIDADE:
            caixa.atendimentos_prioritarios += 1

        self.qtd_clientes_atendidos += 1

        return caixa_nome
    

# Função de Execução das Threads ------------------------------------------------------------------------------------------------------------    
def thread_func(banco, cliente, index, resultados):
    resultado = banco.atender_cliente(cliente)
    resultados[index] = resultado


class NoSemaphore:
    def __init__(self, banco: Banco, clientes: list[Cliente], qtd_clientes: int):
        self._banco = banco
        self._clientes = clientes
        self._qtd_clientes = qtd_clientes
        self._resultados = {}

    def run(self):
        subprocess = []

        # Inicializa o atendimento dos clientes
        for i, cliente in enumerate(self._clientes):
            
            # Armazena o tempo que o cliente entrou na fila
            cliente.tempo_entrada_fila = time.time()

            t = threading.Thread(target=thread_func, args=(self._banco, cliente, i, self._resultados))
            t.start()
            
            subprocess.append(t)

        for t in subprocess:
            t.join()

    def metricas(self):
        tempos_atendimento = 0

        for response in self._resultados.values():
            try:
                tempos_atendimento += response
            except TimeoutError:
                print("Timeout error...")

        print("\n------------ Métricas - Sem semáforo ------------")

        caixas_quebrados = 0
        for nome, caixa in self._banco.caixas.items():
            print(f"{nome} atendeu {caixa.total_atendidos} cliente(s), sendo {caixa.atendimentos_prioritarios} prioritario(s)")
            caixas_quebrados += 1

        print(f"\nCaixas totais 'criados': {caixas_quebrados}")

        print(f"\nTempo total: {round(tempos_atendimento, 2)} s")

        tempo_medio_fila = self._banco.tempo_total_fila / self._qtd_clientes
        print(f"Tempo médio na fila: {round(tempo_medio_fila, 2)} s")

        print(f"Tempo médio de atendimento: {round(tempos_atendimento / self._banco.qtd_clientes_atendidos, 2)} s")


class Semaphore:
    def __init__(self, banco: Banco, clientes: list[Cliente], qtd_clientes: int):
        self._banco = banco
        self._clientes = clientes
        self._qtd_clientes = qtd_clientes
        self._subprocess = []

    def run(self):
        pool = ThreadPool(processes=self._banco.qtd_caixas)

        # Inicializa o atendimento dos clientes
        while len(self._clientes) > 0:
            # Armazena o tempo que o cliente entrou na fila
            cliente = self._clientes.pop()
            cliente.tempo_entrada_fila = time.time()

            # Armazena o tempo gasto no atendimento
            response = pool.apply_async(self._banco.atender_cliente, args=(cliente,))

            time.sleep(0.001)
            self._subprocess.append(response)

        pool.close()
        pool.join()

    def metricas(self):
        # Aguarda os caixas finalizarem o atendimento e armazena o tempo gasto no atendimento
        tempos_atendimento = 0

        for response in self._subprocess:
            try:
                tempos_atendimento += response.get(timeout=30)
            except TimeoutError:
                print("Timeout error...")

        print("\n------------ Métricas - Com semáforo ------------")

        for nome, caixa in self._banco.caixas.items():
            print(f"{nome} atendeu {caixa.total_atendidos} cliente(s), sendo {caixa.atendimentos_prioritarios} prioritario(s)")

        print(f"\nTempo total: {round(tempos_atendimento, 2)} s")

        tempo_medio_fila = self._banco.tempo_total_fila / self._qtd_clientes
        print(f"Tempo médio na fila: {round(tempo_medio_fila, 2)} s")

        print(f"Tempo médio de atendimento: {round(tempos_atendimento / self._banco.qtd_clientes_atendidos, 2)} s")


# Função Principal ------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    qtd_caixas = 4
    banco_semaphore = Banco(qtd_caixas)
    banco_no_semaphore = Banco(qtd_caixas)

    qtd_clientes = 20

    # FCFS
    clientes = Cliente.gerar_clientes(qtd_clientes)

    # Sem semáforos
    no_semaphore = NoSemaphore(banco_no_semaphore, clientes, qtd_clientes)

    print("\n------------ Iniciando atendimento sem semáforo ------------")
    no_semaphore.run()
    no_semaphore.metricas()

    # PS
    clientes = Cliente.gerar_clientes_prioridade(qtd_clientes)

    # Semáforo
    semaphore = Semaphore(banco_semaphore, clientes, qtd_clientes)

    print("\n------------ Iniciando atendimento com semáforo ------------")
    semaphore.run()
    semaphore.metricas()

    
