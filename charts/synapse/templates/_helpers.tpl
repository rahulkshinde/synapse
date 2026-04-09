{{/*
Expand the name of the chart.
*/}}
{{- define "synapse.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "synapse.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "synapse.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "synapse.labels" -}}
helm.sh/chart: {{ include "synapse.chart" . }}
{{ include "synapse.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "synapse.selectorLabels" -}}
app.kubernetes.io/name: {{ include "synapse.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
ServiceAccount name
*/}}
{{- define "synapse.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "synapse.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Synapse image tag — defaults to appVersion
*/}}
{{- define "synapse.imageTag" -}}
{{- default .Chart.AppVersion .Values.synapse.image.tag }}
{{- end }}

{{/*
Ollama internal URL
*/}}
{{- define "synapse.ollamaUrl" -}}
http://{{ include "synapse.fullname" . }}-ollama:{{ .Values.ollama.service.port }}
{{- end }}

{{/*
ChromaDB internal host
*/}}
{{- define "synapse.chromaHost" -}}
{{ include "synapse.fullname" . }}-chromadb
{{- end }}

{{/*
Prometheus internal URL
*/}}
{{- define "synapse.prometheusUrl" -}}
{{- if .Values.prometheus.enabled }}
http://{{ include "synapse.fullname" . }}-prometheus:{{ .Values.prometheus.service.port }}
{{- else }}
{{- .Values.prometheus.externalUrl }}
{{- end }}
{{- end }}
