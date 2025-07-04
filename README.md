# Agendador de Lembrete Semanal

Este projeto envia lembretes por e-mail para funcionários que não preencheram seus resumos semanais.

## Como funciona

- Roda automaticamente toda sexta-feira às 17h (configurado via GitHub Actions).
- Integração com API da empresa, banco PostgreSQL e envio via Microsoft Graph.

## Deploy

1. Suba este projeto no GitHub.
2. Conecte o repositório ao Railway.
3. O GitHub Actions cuidará do agendamento semanal.
