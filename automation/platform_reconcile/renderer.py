"""Render cloud metadata without changing image releases or arbitrary paths."""
import argparse
import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlparse

from automation.common import ROOT, SERVICES, enable_application, read_yaml, validate, write_yaml

DATABASES = {"identity-service": "identity", "booking-core": "booking",
             "commerce-service": "commerce", "ai-service": "ai"}
REDIS = {"identity-service", "booking-core", "social-service", "ai-service"}
MQ = {"identity-service", "booking-core", "commerce-service", "notification-service"}
MONGO = {"social-service", "content-service", "notification-service", "storage-service"}


def private_addresses(host, vpc):
    addresses = sorted({record[4][0] for record in socket.getaddrinfo(host, None, socket.AF_INET)})
    if not addresses or any(ipaddress.ip_address(address) not in vpc for address in addresses):
        raise ValueError(f"Managed endpoint must resolve inside the platform VPC: {host}")
    return [address + "/32" for address in addresses]


def render(contract):
    validate(contract, "platform-contract-v1.schema.json")
    region = contract["aws_region"]
    account = contract["ecr"]["web"].split(".")[0]
    for component, repository in contract["ecr"].items():
        expected = f"{account}.dkr.ecr.{region}.amazonaws.com/{contract['cluster_name']}/{component}"
        if repository != expected:
            raise ValueError(f"Wrong ECR repository for {component}")
    for role in contract["irsa"].values():
        if not role.startswith(f"arn:aws:iam::{account}:role/"):
            raise ValueError("Cross-account IRSA is not allowed")
    for arn in contract["secret_arns"].values():
        if not arn.startswith(f"arn:aws:secretsmanager:{region}:{account}:secret:badminton/prod/"):
            raise ValueError("Secrets must belong to this platform and project prefix")
    if not contract["public"]["certificate_arn"].startswith(f"arn:aws:acm:{region}:{account}:certificate/"):
        raise ValueError("Certificate must belong to the EKS account and region")
    if "ai" not in contract["database"]:
        raise ValueError("Current AI runtime needs its own PostgreSQL; enable_ai_database must be true")
    vpc = ipaddress.ip_network(contract["vpc_cidr"])
    # Fail before modifying files if any dependency cannot be resolved.
    database_cidrs = {name: private_addresses(db["host"], vpc) for name, db in contract["database"].items()}
    redis_cidrs = private_addresses(contract["cache"]["host"], vpc)
    rabbitmq_cidrs = private_addresses(urlparse(contract["messaging"]["endpoint"]).hostname, vpc)
    mongo_cidrs = contract.get("mongodb_allowed_cidrs", [])
    for cidr in mongo_cidrs:
        network = ipaddress.ip_network(cidr)
        if network.prefixlen < 24:
            raise ValueError("MongoDB egress allow-list must use /24 or narrower CIDRs")
    public = contract["public"]
    role_apps = {
        "external_secrets": "platform-external-secrets",
        "external_dns": "platform-external-dns",
        "aws_load_balancer_controller": "platform-aws-load-balancer-controller",
    }
    for role, name in role_apps.items():
        path = f"applications/{name}.yaml"
        doc = read_yaml(path)
        values = doc["spec"]["source"]["helm"]["valuesObject"]
        values["serviceAccount"]["annotations"]["eks.amazonaws.com/role-arn"] = contract["irsa"][role]
        values["serviceAccount"]["annotations"]["eks.amazonaws.com/sts-regional-endpoints"] = "true"
        if role == "external_dns":
            values.update(domainFilters=sorted(set([public["domain"], public["admin_domain"]])), txtOwnerId=contract["cluster_name"])
            values["extraArgs"]["zone-id-filter"] = public["zone_id"]
        if role == "aws_load_balancer_controller":
            values.update(clusterName=contract["cluster_name"], region=region, vpcId=contract["vpc_id"])
        write_yaml(path, doc)
    store_path = "platform/external-secrets-config/cluster-secret-store.yaml"
    store = read_yaml(store_path)
    store["spec"]["provider"]["aws"]["region"] = region
    write_yaml(store_path, store)
    for component in SERVICES:
        directory = f"environments/production/{component}"
        kpath = directory + "/kustomization.yaml"
        kustomization = read_yaml(kpath)
        # This renderer does not touch images. The registry allow-list is in state.
        config = kustomization["configMapGenerator"][0]
        values = dict(line.split("=", 1) for line in config["literals"])
        values["CORS_ORIGINS"] = f"https://{public['domain']},https://{public['admin_domain']}"
        if component in REDIS:
            values["REDIS_HOST"] = contract["cache"]["host"]
        if component in MQ:
            values["RABBITMQ_ENDPOINT"] = contract["messaging"]["endpoint"]
        if component in DATABASES:
            db = contract["database"][DATABASES[component]]
            values.update(DB_HOST=db["host"], DB_PORT=str(db["port"]), DB_NAME=db["name"])
        config["literals"] = [f"{key}={value}" for key, value in sorted(values.items())]
        write_yaml(kpath, kustomization)
        secret_path = ROOT / directory / "external-secret.yaml"
        if secret_path.exists():
            external = read_yaml(directory + "/external-secret.yaml")
            for item in external["spec"]["data"]:
                key = item["remoteRef"]["key"]
                if ":secret:" in key:
                    key = key.split(":secret:", 1)[1].rsplit("-", 1)[0]
                name = key.removeprefix("badminton/prod/")
                item["remoteRef"]["key"] = contract["secret_arns"][name]
            write_yaml(directory + "/external-secret.yaml", external)
        npath = directory + "/network-policy.yaml"
        network = read_yaml(npath)
        for rule in network["spec"]["ingress"]:
            for peer in rule["from"]:
                if "ipBlock" in peer:
                    peer["ipBlock"]["cidr"] = contract["vpc_cidr"]
        for rule in network["spec"]["egress"]:
            port = rule["ports"][0]["port"]
            cidrs = None
            if port == 5432: cidrs = database_cidrs[DATABASES[component]]
            elif port == 6379: cidrs = redis_cidrs
            elif port == 5671: cidrs = rabbitmq_cidrs
            elif port == 27017: cidrs = mongo_cidrs or ["192.0.2.1/32"]
            if cidrs is not None:
                rule["to"] = [{"ipBlock": {"cidr": cidr}} for cidr in cidrs]
        write_yaml(npath, network)
    path = "environments/production/edge/ingress.yaml"
    edge = read_yaml(path)
    edge["spec"]["rules"][0]["host"] = public["domain"]
    edge["spec"]["rules"][1]["host"] = public["admin_domain"]
    annotations = edge["metadata"]["annotations"]
    annotations["alb.ingress.kubernetes.io/certificate-arn"] = public["certificate_arn"]
    annotations["external-dns.alpha.kubernetes.io/hostname"] = public["domain"] + "," + public["admin_domain"]
    redirect = json.loads(annotations["alb.ingress.kubernetes.io/actions.admin-redirect"])
    redirect["RedirectConfig"]["Host"] = public["admin_domain"]
    annotations["alb.ingress.kubernetes.io/actions.admin-redirect"] = json.dumps(redirect)
    write_yaml(path, edge)
    for path in sorted((ROOT / "applications").glob("platform-*.yaml")):
        enable_application(path.stem)
    (ROOT / "state/production-platform.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    render(json.loads(args.contract.read_text()))
