# GCP Labeler Script

Script interativo para aplicar **labels** de forma segura e prática em diversos recursos do Google Cloud Platform (GCP). Ideal para times que precisam organizar recursos por ambiente, custo, time ou qualquer outra chave de identificação.

---

## 🔧 O que este script faz

1. **Lista os projetos** que você tem acesso (ignora projetos internos como `sys-*`).
2. Permite **selecionar o tipo de recurso** (VMs, buckets, instâncias SQL, etc.).
3. Lista os recursos existentes do tipo selecionado.
4. Você escolhe:

   * Quais recursos quer etiquetar (seleção individual ou `all`).
   * As **labels** no formato `chave=valor,chave2=valor2`.
   * Se deseja rodar em **modo normal** ou **dry-run** (só visualizar comandos).
5. Aplica os labels apenas se eles **não existirem ainda com os mesmos valores** (evita reprocessamento).

---

## 🔒 Recursos suportados

* Compute Engine:

  * instances (VMs)
  * disks
  * snapshots
  * forwarding\_rules
  * addresses
  * vpn\_tunnels
* Cloud Storage (buckets)
* Cloud Run services
* Cloud SQL instances
* Spanner instances
* BigQuery datasets
* GKE clusters
* Artifact Registry repositories
* Pub/Sub topics e subscriptions
* Cloud Functions
* Secret Manager secrets

---

## ⚖️ Segurança embutida

* Não há **nenhum comando de deleção**.
* Labels só são aplicadas se forem diferentes das já existentes.
* Recurso "dry-run" mostra exatamente o que seria executado sem tocar nada.

---

## 🔍 Exemplo de uso passo-a-passo

1. Execute o script:

```bash
python3 gcp-label.py
```

2. Escolha o projeto desejado.

3. Escolha o tipo de recurso (ex: `1` para VMs).

4. Escolha os recursos:

   * `1,3` para aplicar nos itens 1 e 3.
   * `all` para aplicar em todos listados.

5. Insira as labels:

```
sq=financeiro,env=prod
```

6. Escolha se deseja `dry-run` (recomendação para testes).

---

## 🚀 Como rodar sem medo (modo simulação)

Basta responder `s` quando o script perguntar:

```
Executar em modo dry-run? (s/n): s
```

Assim, o script apenas **mostra os comandos** que executaria, sem alterar nada.

---

## 📦 Requisitos

* Python 3.7+
* Google Cloud SDK instalado (com comandos `gcloud` e `bq` configurados)
* Permissões adequadas nos projetos que deseja acessar/modificar

---

## 👁️ Visibilidade e rastreio

* Para revisar mudanças feitas, você pode usar:

```bash
gcloud logging read 'resource.labels.project_id="meu-projeto" AND protoPayload.methodName:"SetLabels"' --limit=20
```

---

## ✨ Contribuições

Pull requests são bem-vindos! Favor usar branches separadas e descrever bem sua sugestão.

---

## 🙏 Agradecimentos

A quem compartilha ferramentas seguras para ajudar a comunidade GCP a crescer com confiança e boas práticas ❤️
