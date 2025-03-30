# Prometheus Todoist Exporter Helm Chart

A Helm chart for deploying the Prometheus Todoist Exporter in Kubernetes.

## Introduction

This chart deploys the [Prometheus Todoist Exporter](https://github.com/echohello-dev/prometheus-todoist-exporter) on a Kubernetes cluster using the Helm package manager.

## Prerequisites

- Kubernetes 1.16+
- Helm 3.0+
- A Todoist API token

## Installation

1. Add your Todoist API token to the deployment:

```bash
helm install todoist-exporter ./prometheus-todoist-exporter \
  --namespace monitoring --create-namespace \
  --set todoist.apiToken="your-todoist-api-token"
```

## Configuration

The following table lists the configurable parameters of the Prometheus Todoist Exporter chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `ghcr.io/echohello-dev/prometheus-todoist-exporter` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `imagePullSecrets` | Image pull secrets | `[]` |
| `nameOverride` | Override the name of the chart | `""` |
| `fullnameOverride` | Override the full name of the chart | `""` |
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.annotations` | Service account annotations | `{}` |
| `serviceAccount.name` | Service account name | `""` |
| `podAnnotations` | Pod annotations | Prometheus scrape annotations |
| `podSecurityContext` | Pod security context | `{}` |
| `securityContext` | Container security context | `{}` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Kubernetes service port | `9090` |
| `resources` | CPU/Memory resource requests/limits | limits: 100m/128Mi, requests: 50m/64Mi |
| `nodeSelector` | Node selector | `{}` |
| `tolerations` | Tolerations | `[]` |
| `affinity` | Affinity | `{}` |
| `serviceMonitor.enabled` | Enable ServiceMonitor for Prometheus Operator | `false` |
| `serviceMonitor.namespace` | ServiceMonitor namespace | `""` |
| `serviceMonitor.interval` | ServiceMonitor scrape interval | `30s` |
| `serviceMonitor.scrapeTimeout` | ServiceMonitor scrape timeout | `10s` |
| `serviceMonitor.additionalLabels` | Additional ServiceMonitor labels | `{}` |
| `exporter.port` | Exporter port | `9090` |
| `exporter.metricsPath` | Metrics path | `/metrics` |
| `exporter.collectionInterval` | Seconds between metric collections | `60` |
| `exporter.completedTasksDays` | Days to look back for completed tasks | `7` |
| `exporter.completedTasksHours` | Hours to look back for completed tasks | `24` |
| `todoist.apiToken` | Todoist API token | `""` |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install` or in a values.yaml file.

## Example: Using with Prometheus Operator

If you're using the Prometheus Operator, enable the ServiceMonitor:

```bash
helm install todoist-exporter ./prometheus-todoist-exporter \
  --namespace monitoring --create-namespace \
  --set todoist.apiToken="your-todoist-api-token" \
  --set serviceMonitor.enabled=true
```

## Example: Custom Configuration

Create a custom values file:

```yaml
# values.yaml
exporter:
  collectionInterval: 30
  completedTasksDays: 14
  completedTasksHours: 48

resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

service:
  type: NodePort

serviceMonitor:
  enabled: true
```

Then install the chart:

```bash
helm install todoist-exporter ./prometheus-todoist-exporter \
  --namespace monitoring --create-namespace \
  --set todoist.apiToken="your-todoist-api-token" \
  --values values.yaml
```

## Uninstalling the Chart

To uninstall/delete the `todoist-exporter` deployment:

```bash
helm uninstall todoist-exporter --namespace monitoring
```
