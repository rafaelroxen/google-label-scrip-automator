#!/usr/bin/env python3
import subprocess, json, sys

def run(cmd):
    print(f"Executando comando: {' '.join(cmd)}")
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        if p.returncode:
            print("Erro:", p.stderr.strip())
            sys.exit(1)
        return p.stdout
    except subprocess.TimeoutExpired:
        print(f"⏱️ Tempo limite atingido ao rodar: {' '.join(cmd)}")
        sys.exit(1)

def pick_project():
    projs = json.loads(run(["gcloud", "projects", "list", "--format=json"]))
    projs = [p for p in projs if not p['projectId'].startswith("sys-")]
    for i, p in enumerate(projs, 1):
        print(f"{i}) {p['projectId']} — {p['name']}")
    return projs[int(input("Projeto número: ")) -1]['projectId']

def list_resources(cmd, project):
    full_cmd = cmd + ["--project", project, "--format=json", "--limit=50"] if cmd[0] != "bq" else cmd
    return json.loads(run(full_cmd))

def pick_items(items):
    for i, it in enumerate(items, 1):
        name = it.get("name") or it.get("id") or it.get("metadata", {}).get("name") or f"item-{i}"
        print(f"{i}) {name}")
    sel = input("Escolha os números (ex: 1,3) ou 'all' para selecionar todos: ")
    if sel.strip().lower() == "all":
        return items
    return [items[int(x.strip())-1] for x in sel.split(",")]

def ask_labels():
    return input("Labels (chave=valor separados por vírgula): ").strip()

def label_already_exists(resource_labels, new_labels):
    if not resource_labels: return False
    new_labels_dict = dict(label.split("=") for label in new_labels.split(","))
    for k, v in new_labels_dict.items():
        if k not in resource_labels or resource_labels[k] != v:
            return False
    return True

def get_current_labels(cfg, name, project):
    print(f"Verificando labels atuais de: {name}")
    try:
        if "pubsub" in cfg["apply"]:
            desc = run(["gcloud"] + cfg["apply"][:2] + ["describe", name, "--project", project, "--format=json"])
        elif "container" in cfg["apply"]:
            desc = run(["gcloud"] + cfg["apply"][:2] + ["describe", name, "--location", "us-central1", "--project", project, "--format=json"])
        elif "buckets" in cfg["type"]:
            desc = run(["gcloud", "storage", "buckets", "describe", name, "--project", project, "--format=json"])
        elif "sql" in cfg["apply"]:
            desc = run(["gcloud", "sql", "instances", "describe", name, "--project", project, "--format=json"])
        else:
            return {}
        data = json.loads(desc)
        return data.get("labels", {})
    except Exception as e:
        print(f"Erro ao obter labels atuais: {e}")
        return {}

def apply_labels(cfg, item, project, lbls, dry_run=False):
    name = item.get("name") or item.get("id") or item.get("metadata", {}).get("name")
    existing_labels = get_current_labels(cfg, name, project)
    if label_already_exists(existing_labels, lbls):
        print(f"⚠️  Labels já aplicados no recurso '{name}', ignorando.\n")
        return

    if cfg["type"] == "bq":
        dataset_id = item["datasetReference"]["datasetId"]
        label_args = []
        for label in lbls.split(","):
            k,v = label.split("=")
            label_args += ["--set_label", f"{k}:{v}"]
        cmd = cfg["apply"] + label_args + [f"{project}:{dataset_id}"]
    else:
        cmd = cfg["apply"] + [name]
        if cfg["type"] not in ("cloudsql",):
            if "zone" in item:
                cmd += ["--zone", item["zone"].split("/")[-1]]
            elif "region" in item:
                cmd += ["--region", item["region"].split("/")[-1]]
        cmd += [cfg["flag"], lbls, "--project", project, "--quiet"]

    print("->", " ".join(cmd))
    if not dry_run:
        run(cmd)
        print("✔️ Label aplicada com sucesso!\n")
    else:
        print("Modo dry-run: comando não executado.\n")

def main():
    types = {
        ...  # (mantém os tipos anteriores)
    }

    project = pick_project()
    print("\nTipos de recurso disponíveis para aplicar labels:")
    for i, key in enumerate(types, 1):
        print(f"{i}) {key}")
    cfg = types[list(types)[int(input("Escolha o tipo de recurso: ")) - 1]]

    items = list_resources(cfg["list"], project)
    if not items:
        print("Nenhum recurso encontrado.")
        return

    sel = pick_items(items)
    lbls = ask_labels()
    dry = input("Executar em modo dry-run? (s/n): ").lower().startswith("s")

    for it in sel:
        apply_labels(cfg, it, project, lbls, dry_run=dry)

if __name__ == "__main__":
    main()
