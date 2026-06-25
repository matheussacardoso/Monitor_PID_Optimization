import random
import time
import os
import boto3

# --- ARQUITETURA PUB/SUB (REAL AWS SNS) ---

class SNSTensionPublisher:
    """Publisher real conectado ao AWS SNS."""
    def __init__(self):
        # O boto3 coleta automaticamente as credenciais passadas via variáveis de ambiente
        self.sns_client = boto3.client(
            'sns',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.topic_arn = os.getenv('AWS_SNS_TOPIC_ARN')

    def publicar_alerta(self, teste_nome: str, tensao_atual: float, limite: float):
        mensagem = (
            f"⚠️ [ALERTA SISTEMA CRÍTICO]\n\n"
            f"O teste de otimização '{teste_nome}' ultrapassou o limiar de segurança de 20%!\n\n"
            f"📊 Dados da Planta:\n"
            f"- Tensão Atual: {tensao_atual}N\n"
            f"- Limite Crítico Superior: {limite}N\n"
            f"- Parâmetros Fixos: Força 50N, Velocidade 17 mm/s.\n\n"
            f"Ação necessária: Revisar os parâmetros deste cenário."
        )
        print(f"🚀 [Publisher] Enviando evento de falha para o AWS SNS...")
        
        if not self.topic_arn:
            print("❌ Erro: AWS_SNS_TOPIC_ARN não foi configurado nas variáveis de ambiente.")
            return

        try:
            resposta = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Message=mensagem,
                Subject="Alerta de Limiar PID Simplificado"
            )
            print(f"✅ [Publisher] Sucesso! MessageId: {resposta['MessageId']}")
        except Exception as e:
            print(f"❌ [Erro Publisher] Falha ao publicar na AWS: {e}")


# --- LOOP PRINCIPAL ---

def executar_simulacao_aws_simplificada():
    # Configurações do cenário fixo
    SETPOINT_TENSAO = 50.0  
    VELOCIDADE = 17         
    LIMIAR_PERMITIDO_PCT = 0.20  
    
    # Cálculo dos limites (40N até 60N)
    variacao_maxima = SETPOINT_TENSAO * LIMIAR_PERMITIDO_PCT
    limite_superior = SETPOINT_TENSAO + variacao_maxima
    limite_inferior = SETPOINT_TENSAO - variacao_maxima

    publisher = SNSTensionPublisher()

    # Definição estrita de 10 testes: 8 estáveis e 2 instáveis
    testes_config = [
        {"nome": "Teste_01_Estavel", "estavel": True},
        {"nome": "Teste_02_Estavel", "estavel": True},
        {"nome": "Teste_03_Instavel", "estavel": False}, # 💥 Instável 1 (Gera Alerta)
        {"nome": "Teste_04_Estavel", "estavel": True},
        {"nome": "Teste_05_Estavel", "estavel": True},
        {"nome": "Teste_06_Estavel", "estavel": True},
        {"nome": "Teste_07_Instavel", "estavel": False}, # 💥 Instável 2 (Gera Alerta)
        {"nome": "Teste_08_Estavel", "estavel": True},
        {"nome": "Teste_09_Estavel", "estavel": True},
        {"nome": "Teste_10_Estavel", "estavel": True},
    ]

    duracao_teste_s = 10
    dt = 0.1  
    total_ticks = int(duracao_teste_s / dt) # 100 ticks por teste (Totalizando 10s por teste)

    print(f"=== INICIANDO SISTEMA COM PRODUÇÃO AWS SNS (SIMPLIFICADO) ===")
    print(f"Alvo: {SETPOINT_TENSAO}N | Velocidade: {VELOCIDADE}mm/s")
    print(f"Zona de Segurança: {limite_inferior}N até {limite_superior}N\n")

    for teste in testes_config:
        print(f"🤖 Rodando: {teste['nome']}...")
        alerta_disparado = False

        for tick in range(total_ticks):
            if teste["estavel"]:
                # Valores seguros flutuando perto de 50N (nunca quebram o limite)
                tensao_atual = round(random.uniform(46.0, 54.0), 2)
            else:
                # Se for instável, força um pico fora do limite no meio do teste (tick 50)
                if tick == total_ticks // 2:
                    tensao_atual = round(random.uniform(61.5, 72.0), 2) # Estoura os 60N
                else:
                    tensao_atual = round(random.uniform(46.0, 54.0), 2)

            # Validação do Limiar
            if (tensao_atual > limite_superior or tensao_atual < limite_inferior) and not alerta_disparado:
                print(f"🚨 Tensão Crítica Detectada: {tensao_atual}N no tick {tick}")
                publisher.publicar_alerta(teste['nome'], tensao_atual, limite_superior)
                alerta_disparado = True 

            # Mantém o delay para simular o tempo real de 10s por teste
            # (Se quiser que rode instantaneamente, basta comentar a linha abaixo)
            time.sleep(dt) 

        print(f"✓ Finalizado: {teste['nome']}.\n")

if __name__ == "__main__":
    executar_simulacao_aws_simplificada()