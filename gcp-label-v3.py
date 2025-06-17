#!/usr/bin/env python3
import subprocess, json, sys, csv


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        print("Erro:", p.stderr.strip())
        sys.exit(1)
    return p.stdout


def check_auth():
    try:
        run(["gcloud", "auth", "list"])
    except Exception:
        print("\n❌ Você não está autenticado com o gcloud. Execute `gcloud auth login`.\n")
        sys.exit(1)


def check_permissions(project):
    try:
        run(["gcloud", "projects", "get-iam-policy", project, "--format=json"])
    except:
        print(f"\n❌ Sem permissão para acessar o projeto '{project}'.\n")
        sys.exit(1)


def pick_project():
    projs = json.loads(run(["gcloud", "projects", "list", "--format=json"]))
    projs = [p for p in projs if not p['projectId'].startswith("sys-")]
    for i, p in enumerate(projs, 1):
        print(f"{i}) {p['projectId']} — {p['name']}")
    return projs[int(input("Projeto número: ")) - 1]['projectId']


def list_resources(cmd, project):
    if cmd[0] == "bq":
        return json.loads(run(cmd))
    return json.loads(run(cmd + ["--project", project, "--format=json"]))


def pick_items(items):
    for i, it in enumerate(items, 1):
        name = None
        if isinstance(it, dict):
            if "metadata" in it and "name" in it["metadata"]:
                name = it["metadata"]["name"]
            elif "name" in it:
                name = it["name"]
            elif "id" in it:
                name = str(it["id"])
        name = name or f"item-{i}"
        print(f"{i}) {name}")
    sel = input("Escolha os números (ex: 1,3) ou 'all' para selecionar todos: ")
    if sel.strip().lower() == "all":
        return items
    return [items[int(x.strip()) - 1] for x in sel.split(",")]


def ask_labels():
    return input("Labels (chave=valor separados por vírgula): ").strip()


def apply_labels(cfg, item, project, lbls, dry_run=False):
    if cfg["type"] == "cloud-run":
        name = item["metadata"]["name"]
        region = item["metadata"]["labels"].get("cloud.googleapis.com/location")
        if not region:
            print(f"❌ Região não encontrada para o serviço {name}. Ignorando.")
            return
        cmd = cfg["apply"] + [name, "--region", region, cfg["flag"], lbls, "--project", project, "--quiet"]

    elif cfg["type"] == "buckets":
        name = f"gs://{item['name']}"
        cmd = cfg["apply"] + [name, cfg["flag"], lbls, "--project", project, "--quiet"]

    elif cfg["type"] == "bq":
        dataset_id = item["datasetReference"]["datasetId"]
        label_args = []
        for label in lbls.split(","):
            k, v = label.split("=")
            label_args += ["--set_label", f"{k}:{v}"]
        cmd = cfg["apply"] + label_args + [f"{project}:{dataset_id}"]

    else:
        name = item.get("name") or item.get("id") or item.get("metadata", {}).get("name")
        cmd = cfg["apply"] + [name]
        if cfg["type"] != "cloudsql":
            if "zone" in item:
                cmd += ["--zone", item["zone"].split("/")[-1]]
            elif "region" in item:
                cmd += ["--region", item["region"].split("/")[-1]]
        cmd += [cfg["flag"], lbls, "--project", project, "--quiet"]

    print("->", " ".join(cmd))
    if not dry_run:
        try:
            run(cmd)
            print("✔️ Label aplicada com sucesso!\n")
        except SystemExit:
            print("❌ Falha ao aplicar label.\n")
    else:
        print("🔍 Modo dry-run: comando não executado.\n")


def main():
    check_auth()
    project = pick_project()
    check_permissions(project)

    types = {
        "disks": {"list": ["gcloud", "compute", "disks", "list"], "apply": ["gcloud", "compute", "disks", "update"], "flag": "--update-labels", "type": "compute"},
        "snapshots": {"list": ["gcloud", "compute", "snapshots", "list"], "apply": ["gcloud", "compute", "snapshots", "update"], "flag": "--update-labels", "type": "compute"},
        "buckets": {"list": ["gcloud", "storage", "buckets", "list"], "apply": ["gcloud", "storage", "buckets", "update"], "flag": "--update-labels", "type": "buckets"},
        "addresses": {"list": ["gcloud", "compute", "addresses", "list"], "apply": ["gcloud", "alpha", "compute", "addresses", "update"], "flag": "--update-labels", "type": "compute"},
        "vpn_tunnels": {"list": ["gcloud", "compute", "vpn-tunnels", "list"], "apply": ["gcloud", "compute", "vpn-tunnels", "update"], "flag": "--update-labels", "type": "compute"},
        "cloud_run_services": {"list": ["gcloud", "run", "services", "list", "--platform=managed"], "apply": ["gcloud", "run", "services", "update", "--platform=managed"], "flag": "--update-labels", "type": "cloud-run"},
        "cloud_sql": {"list": ["gcloud", "sql", "instances", "list"], "apply": ["gcloud", "beta", "sql", "instances", "patch"], "flag": "--update-labels", "type": "cloudsql"},
        "spanner_instances": {"list": ["gcloud", "spanner", "instances", "list"], "apply": ["gcloud", "spanner", "instances", "update"], "flag": "--update-labels", "type": "spanner"},
        "bq_datasets": {"list": ["bq", "ls", "--format=json"], "apply": ["bq", "update"], "flag": None, "type": "bq"},
        "gke_clusters": {"list": ["gcloud", "container", "clusters", "list"], "apply": ["gcloud", "container", "clusters", "update"], "flag": "--update-labels", "type": "compute"}
    }

    print("\nTipos de recurso disponíveis para aplicar labels:")
    for i, key in enumerate(types, 1):
        print(f"{i}) {key}")
    resource_key = list(types)[int(input("Escolha o tipo de recurso: ")) - 1]
    cfg = types[resource_key]

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
