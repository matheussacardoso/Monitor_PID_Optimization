import random
import time
from dataclasses import dataclass

# --- BASE DO SIMULADOR FORNECIDO ---

@dataclass
class EstadoSensor:
    valor: float
    minimo: float
    maximo: float
    tendencia: float = 0.0           
    pico_residual: float = 0.0       

    @property
    def faixa(self) -> float:
        return self.maximo - self.minimo


class SimuladorSensor:
    def __init__(
        self,
        nome: str,
        minimo: float,
        maximo: float,
        valor_inicial: float,
        ruido_pct: float = 0.01,
        prob_pico: float = 0.02,
        amplitude_pico_pct: float = 0.15,
        decaimento_pico: float = 0.25,
        prob_mudar_tendencia: float = 0.05,
    ):
        self.nome = nome
        self.estado = EstadoSensor(valor=valor_inicial, minimo=minimo, maximo=maximo)
        self.ruido_pct = ruido_pct
        self.prob_pico = prob_pico
        self.amplitude_pico_pct = amplitude_pico_pct
        self.decaimento_pico = decaimento_pico
        self.prob_mudar_tendencia = prob_mudar_tendencia

    def proximo_valor(self, acao_controle: float) -> float:
        st = self.estado
        faixa = st.faixa

        st.valor += acao_controle

        if random.random() < self.prob_mudar_tendencia:
            st.tendencia = random.uniform(-1.0, 1.0)

        ruido = random.uniform(-1.0, 1.0) * self.ruido_pct * faixa
        viés = st.tendencia * self.ruido_pct * faixa * 0.5
        st.valor += ruido + viés

        if random.random() < self.prob_pico:
            direcao = random.choice([-1.0, 1.0])
            st.pico_residual += direcao * self.amplitude_pico_pct * faixa

        st.valor += st.pico_residual * self.decaimento_pico
        st.pico_residual *= (1.0 - self.decaimento_pico)

        if st.valor > st.maximo:
            st.valor = st.maximo
            st.tendencia = -abs(st.tendencia)
        elif st.valor < st.minimo:
            st.valor = st.minimo
            st.tendencia = abs(st.tendencia)

        return round(st.valor, 2)


# --- CONTROLADOR PID ---

class ControladorPID:
    def __init__(self, kp: float, ki: float, kd: float, dt: float = 0.1):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.erro_anterior = 0.0
        self.integral = 0.0

    def calcular_acao(self, erro: float) -> float:
        self.integral += erro * self.dt
        derivativo = (erro - self.erro_anterior) / self.dt
        self.erro_anterior = erro
        return (self.kp * erro) + (self.ki * self.integral) + (self.kd * derivativo)


# --- SIMULADOR MOCK DO AWS SNS (LOCAL) ---

class MockSNSService:
    """Simula o Broker AWS SNS interceptando a chamada e printando no terminal."""
    
    def __init__(self, topico_nome: str):
        self.topico_nome = topico_nome
        # Simula um subscriber cadastrado (seu número de telefone)
        self.subscriber_telefone = "+55 (11) 99999-9999" 

    def publicar_mensagem(self, mensagem: str, assunto: str):
        print(f"\n--- 🛰️ [MOCK AWS SNS BROKER] Mensagem recebida no tópico '{self.topico_nome}' ---")
        print(f"Assunto: {assunto}")
        print(f"---")
        print(f"📱 [SUBSCRIBER SMS DELIVERED] Enviado para {self.subscriber_telefone}:")
        print(mensagem)
        print(f"----------------------------------------------------------------------\n")


class LocalTensionPublisher:
    """Publisher adaptado para usar o serviço simulado (Mock)."""
    def __init__(self):
        # Em vez do boto3, usamos nosso simulador local de SNS
        self.sns_mock = MockSNSService(topico_nome="alerta-urgente-tensao-pid")

    def publicar_alerta(self, teste_nome: str, tensao_atual: float, limite: float):
        mensagem = (
            f"⚠️ [ALERTA] Teste '{teste_nome}' falhou.\n"
            f"Motivo: Tensão fora do limite de 20%.\n"
            f"Medido: {tensao_atual}N | Limite Máx: {limite}N\n"
            f"Configuração: Fixo 50N, 17 mm/s."
        )
        
        # Dispara o evento para o Broker fictício
        self.sns_mock.publicar_mensagem(mensagem, assunto="Alerta de Limiar PID")


# --- LOOP DE EXECUÇÃO ---

def executar_teste_local():
    SETPOINT_TENSAO = 50.0  
    VELOCIDADE = 17         
    LIMIAR_PERMITIDO_PCT = 0.20  
    
    variacao_maxima = SETPOINT_TENSAO * LIMIAR_PERMITIDO_PCT
    limite_superior = SETPOINT_TENSAO + variacao_maxima
    limite_inferior = SETPOINT_TENSAO - variacao_maxima

    # Instanciando o publicador local
    publisher = LocalTensionPublisher()

    # Cenários de teste: Note que a Configuração 03 é muito agressiva e vai estourar o limite
    testes_parametros = [
        {"nome": "Cenário_01_Estável", "Kp": 0.5, "Ki": 0.1, "Kd": 0.2},
        {"nome": "Cenário_02_Instável_Agressivo", "Kp": 6.5, "Ki": 4.0, "Kd": 2.5}
    ]

    duracao_teste_s = 10
    dt = 0.1  
    total_ticks = int(duracao_teste_s / dt)

    print("=== INICIANDO SIMULAÇÃO LOCAL (SEM AWS) ===")
    print(f"Alvo: {SETPOINT_TENSAO}N | Tolerância: {limite_inferior}N até {limite_superior}N\n")

    for teste in testes_parametros:
        print(f"🤖 Testando: {teste['nome']}...")
        
        simulador = SimuladorSensor(
            nome="Sensor_Tensao", 
            minimo=10.0, 
            maximo=90.0, 
            valor_inicial=SETPOINT_TENSAO,
            ruido_pct=0.02
        )
        
        pid = ControladorPID(kp=teste['Kp'], ki=teste['Ki'], kd=teste['Kd'], dt=dt)
        alerta_disparado = False
        tensao_atual = SETPOINT_TENSAO

        for tick in range(total_ticks):
            erro = SETPOINT_TENSAO - tensao_atual
            acao = pid.calcular_acao(erro)
            tensao_atual = simulador.proximo_valor(acao)

            # Validação do Limiar
            if (tensao_atual > limite_superior or tensao_atual < limite_inferior) and not alerta_disparado:
                print(f"💥 [Monitor] Limiar violado no tick {tick}! Valor: {tensao_atual}N")
                
                # O Publisher envia a notificação para o Mock SNS
                publisher.publicar_alerta(teste['nome'], tensao_atual, limite_superior)
                alerta_disparado = True 

            # Roda em velocidade acelerada para o teste ser instantâneo
            # time.sleep(dt) 

        print(f"✓ Fim do teste {teste['nome']}.\n")

if __name__ == "__main__":
    executar_teste_local()