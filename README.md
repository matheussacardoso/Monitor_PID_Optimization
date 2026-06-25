# Simulador de Processo de Otimização de Parâmetros PID com AWS SNS

Este projeto implementa um simulador de sensores industriais voltado para o monitoramento e otimização de parâmetros de um controlador PID (Proporcional, Integral e Derivativo) aplicado ao controle de tensão. O sistema adota uma arquitetura do tipo Publisher/Subscriber (Pub/Sub) integrada ao serviço AWS SNS (Simple Notification Service) para o disparo de alertas caso os limites de segurança sejam violados.

## Estrutura do Projeto

O diretório do projeto é composto pelos seguintes arquivos:

* **main.py**: Contém o código-fonte principal da aplicação. Ele engloba a classe do simulador do sensor (com comportamento de *random walk*, tendência e picos residuais), a implementação matemática do controlador PID, a classe publicadora do AWS SNS e o *loop* que gerencia e executa as diferentes configurações de parâmetros para os testes.
* **requirements.txt**: Lista as dependências externas necessárias para a execução do projeto. Neste caso, inclui a biblioteca `boto3`, que é o SDK oficial da Amazon Web Services para Python.
* **Dockerfile**: Arquivo de configuração contendo as instruções para a criação da imagem Docker isolada, garantindo que a aplicação rode com as mesmas versões de dependências em qualquer ambiente.
* **.env.example**: Modelo público de configuração das variáveis de ambiente. Serve como guia para a criação do arquivo de credenciais real.
* **.gitignore**: Instrução para o Git ignorar arquivos sensíveis, garantindo que o arquivo `.env` com suas chaves privadas nunca seja enviado para repositórios públicos.

---

## Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:
1. Docker Desktop (ativo e em execução).
2. Uma conta AWS com um Tópico SNS do tipo *Standard* configurado e uma assinatura ativa (E-mail ou SMS) vinculada a ele.
3. Chaves de acesso de um usuário IAM com permissão de publicação no SNS (`AmazonSNSFullAccess`).

---

## Instruções de Configuração e Execução

### Passo 1: Configurar as Variáveis de Ambiente
Na raiz da pasta do projeto, crie um arquivo chamado exatamente `.env`. Abra este arquivo em um editor de texto e preencha-o com as suas credenciais reais da AWS e o identificador único do seu tópico:

```text
AWS_ACCESS_KEY_ID=SUA_ACCESS_KEY_AQUI
AWS_SECRET_ACCESS_KEY=SUA_SECRET_KEY_AQUI
AWS_REGION=us-east-1
AWS_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:Alerta-Tensão-PID
```
### Passo 2: Construir a Imagem Docker 
Abra o seu terminal ou PowerShell, navegue até a pasta do projeto e execute o comando abaixo para realizar o build da imagem customizada:
```docker 
docker build -t simulador-pid-aws .
```

### Passo 3: Executar o Container
Com a imagem construída e o arquivo .env configurado na pasta, execute o container injetando as variáveis de ambiente através da flag --env-file:
```docker 
docker run --rm --env-file .env simulador-pid-aws
```

### Descrição do Cenário de Simulação
O controlador PID gerencia um processo cujo objetivo é estabilizar a tensão no setpoint fixo de 50N, sob uma velocidade operacional constante de 17 mm/s.

- Regra de Negócio: O sistema monitora a tensão em tempo real (passos de 100ms) durante ciclos de 10 segundos para cada conjunto de parâmetros PID testados.

- Alerta de Segurança: Se em qualquer momento a tensão medida desviar mais de 20% do valor desejado (ou seja, se ficar abaixo de 40N ou acima de 60N), o componente Publisher é imediatamente acionado, despachando uma notificação de erro para o Broker AWS SNS, que por sua vez entrega o alerta aos assinantes cadastrados.
