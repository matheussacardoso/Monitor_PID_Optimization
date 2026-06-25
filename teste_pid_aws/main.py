import random
import time
from dataclasses import dataclass
import os
import boto3

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
    def __init__(self, nome: str, minimo: float, maximo: float, valor_inicial: float, ruido_pct: float = 0.01, prob_pico: float = 0.02, amplitude_pico_pct: float = 0.15, decaimento_pico: float = 0.25, prob_mudar_tendencia: float = 0.05):
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

# --- ARQUITETURA PUB/SUB (REAL AWS SNS) ---
class SNSTensionPublisher:
    """Publisher real conectado ao AWS SNS."""
    def __init__(self):
        # O boto3 coleta automaticamente as credenciais das variáveis de ambiente
        self.sns_client = boto3.client(
            'sns',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.topic_arn = os.getenv('AWS_SNS_TOPIC_ARN')

    def publicar_alerta(self, teste_nome: str, tensao_atual: float, limite: float):
        mensagem = (
            f"⚠️ [ALERTA SISTEMA CRÍTICO]\n\n"
            f"O teste de otimização PID '{teste_nome}' ultrapassou o limiar de segurança de 20%!\n\n"
            f"📊 Dados da Planta:\n"
            f"- Tensão Atual: {tensao_atual}N\n"
            f"- Limite Crítico: {limite}N\n"
            f"- Parâmetros Fixos: Força 50N, Velocidade 17 mm/s.\n\n"
            f"Ação necessária: Revisar os ganhos Kp, Ki e Kd deste cenário."
        )
        print(f"\n🚀 [Publisher] Enviando evento de falha para o AWS SNS...")
        
        if not self.topic_arn:
            print("❌ Erro: AWS_SNS_TOPIC_ARN não foi configurado nas variáveis de ambiente.")
            return

        try:
            resposta = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Message=mensagem,
                Subject="Alerta de Limiar PID"
            )
            print(f"✅ [Publisher] Sucesso! MessageId: {resposta['MessageId']}")
        except Exception as e:
            print(f"❌ [Erro Publisher] Falha ao publicar na AWS: {e}")

# --- LOOP PRINCIPAL ---
def executar_simulacao_aws():
    SETPOINT_TENSAO = 50.0  
    VELOCIDADE = 17         
    LIMIAR_PERMITIDO_PCT = 0.20  
    
    variacao_maxima = SETPOINT_TENSAO * LIMIAR_PERMITIDO_PCT
    limite_superior = SETPOINT_TENSAO + variacao_maxima
    limite_inferior = SETPOINT_TENSAO - variacao_maxima

    publisher = SNSTensionPublisher()

    # Cenários: O segundo cenário vai falhar de propósito para forçar o SMS
    testes_parametros = [
        {"nome": "Cenario_01_Eficiente", "Kp": 0.6, "Ki": 0.2, "Kd": 0.4},
        {"nome": "Cenario_02_Instavel", "Kp": 7.0, "Ki": 5.0, "Kd": 3.0}
    ]

    duracao_teste_s = 10
    dt = 0.1  
    total_ticks = int(duracao_teste_s / dt)

    print(f"=== INICIANDO SISTEMA COM PRODUÇÃO AWS SNS ===")
    
    for teste in testes_parametros:
        print(f"\n🤖 Rodando: {teste['nome']}...")
        simulador = SimuladorSensor("Sensor_Tensao", 10.0, 90.0, SETPOINT_TENSAO, ruido_pct=0.02)
        pid = ControladorPID(kp=teste['Kp'], ki=teste['Ki'], kd=teste['Kd'], dt=dt)
        alerta_disparado = False
        tensao_atual = SETPOINT_TENSAO

        for tick in range(total_ticks):
            erro = SETPOINT_TENSAO - tensao_atual
            acao = pid.calcular_acao(erro)
            tensao_atual = simulador.proximo_valor(acao)

            if (tensao_atual > limite_superior or tensao_atual < limite_inferior) and not alerta_disparado:
                print(f"🚨 Tensão Crítica: {tensao_atual}N")
                publisher.publicar_alerta(teste['nome'], tensao_atual, limite_superior)
                alerta_disparado = True 

            time.sleep(dt) # Segura 100ms por tick para simular o tempo real dos 10 segundos

        print(f"✓ Finalizado: {teste['nome']}.")

if __name__ == "__main__":
    executar_simulacao_aws()