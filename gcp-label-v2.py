#!/usr/bin/env python3
import subprocess, json, sys

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        print("Erro:", p.stderr.strip())
        sys.exit(1)
    return p.stdout

def pick_project():
    projs = json.loads(run(["gcloud", "projects", "list", "--format=json"]))
    projs = [p for p in projs if not p['projectId'].startswith("sys-")]
    for i, p in enumerate(projs, 1):
        print(f"{i}) {p['projectId']} — {p['name']}")
    return projs[int(input("Projeto número: ")) -1]['projectId']

def list_resources(cmd, project):
    if cmd[0] == "bq":
        return json.loads(run(cmd))
    return json.loads(run(cmd + ["--project", project, "--format=json"]))

def pick_items(items):
    for i, it in enumerate(items, 1):
        name = it.get("name") or it.get("id") or it.get("metadata", {}).get("name") or f"item-{i}"
        print(f"{i}) {name}")
    sel = input("Escolha os números (ex: 1,3): ")
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
    except:
        return {}

def apply_labels(cfg, item, project, lbls):
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
    run(cmd)
    print("✔️ Label aplicada com sucesso!\n")

def main():
    types = {
        "instances": {"list": ["gcloud","compute","instances","list"], "apply": ["gcloud","compute","instances","update"], "flag":"--update-labels", "type":"compute"},
        "disks": {"list": ["gcloud","compute","disks","list"], "apply": ["gcloud","compute","disks","update"], "flag":"--update-labels", "type":"compute"},
        "snapshots": {"list": ["gcloud","compute","snapshots","list"], "apply": ["gcloud","compute","snapshots","update"], "flag":"--update-labels", "type":"compute"},
        "buckets": {"list": ["gcloud","storage","buckets","list"], "apply": ["gcloud","storage","buckets","update"], "flag":"--update-labels", "type":"buckets"},
        "forwarding_rules": {"list": ["gcloud","compute","forwarding-rules","list"], "apply": ["gcloud","compute","forwarding-rules","update"], "flag":"--update-labels", "type":"compute"},
        "addresses": {"list": ["gcloud","compute","addresses","list"], "apply": ["gcloud","alpha","compute","addresses","update"], "flag":"--update-labels", "type":"compute"},
        "vpn_tunnels": {"list": ["gcloud","compute","vpn-tunnels","list"], "apply": ["gcloud","compute","vpn-tunnels","update"], "flag":"--update-labels", "type":"compute"},
        "cloud_run_services": {"list": ["gcloud","run","services","list","--platform=managed"], "apply": ["gcloud","run","services","update","--platform=managed"], "flag":"--update-labels", "type":"cloud-run"},
        "cloud_sql": {"list": ["gcloud","sql","instances","list"], "apply": ["gcloud","beta","sql","instances","patch"], "flag":"--update-labels", "type":"cloudsql"},
        "spanner_instances": {"list": ["gcloud","spanner","instances","list"], "apply": ["gcloud","spanner","instances","update"], "flag":"--update-labels", "type":"spanner"},
        "bq_datasets": {"list": ["bq","ls","--format=json"], "apply": ["bq","update"], "flag": None, "type":"bq"},
        "pubsub_topics": {"list": ["gcloud","pubsub","topics","list"], "apply": ["gcloud","pubsub","topics","update"], "flag":"--update-labels", "type":"compute"},
        "pubsub_subs": {"list": ["gcloud","pubsub","subscriptions","list"], "apply": ["gcloud","pubsub","subscriptions","update"], "flag":"--update-labels", "type":"compute"},
        "gke_clusters": {"list": ["gcloud","container","clusters","list"], "apply": ["gcloud","container","clusters","update"], "flag":"--update-labels", "type":"compute"},
        "artifact_repos": {"list": ["gcloud","artifacts","repositories","list"], "apply": ["gcloud","artifacts","repositories","update"], "flag":"--update-labels", "type":"compute"},
        "cloud_functions": {"list": ["gcloud","functions","list"], "apply": ["gcloud","functions","deploy"], "flag":"--update-labels", "type":"compute"},
        "secrets": {"list": ["gcloud","secrets","list"], "apply": ["gcloud","secrets","update"], "flag":"--update-labels", "type":"compute"},
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

    for it in sel:
        apply_labels(cfg, it, project, lbls)

if __name__ == "__main__":
    main()
