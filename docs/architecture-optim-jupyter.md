# Architecture — Système modulaire d'optimisation de notebooks Jupyter

> [JRE] Globalement, il faut faire attention à la syntaxe Markdown et respecter les règles de linting. Le fichier fourni est corrigé, sauf pour les languages des bloque triple back ticks.

**Version** : 0.2 — Consolidation post-Q&A
**Date** : 2025-02-14
**Auteur** : Jean Remacle / Claude (architecture collaborative)
**Statut** : Draft — en attente de validation avant implémentation

---

## Table des matières

1. [Vision et objectifs](#1-vision-et-objectifs)
2. [Décisions d'architecture consolidées](#2-décisions-darchitecture-consolidées)
3. [Architecture des domaines](#3-architecture-des-domaines)
4. [Modèle de données du Benchmark Framework](#4-modèle-de-données-du-benchmark-framework)
5. [Infrastructure et compute](#5-infrastructure-et-compute)
6. [Repos GitHub et interfaces](#6-repos-github-et-interfaces)
7. [Stratégie MVP vs cible](#7-stratégie-mvp-vs-cible)
8. [Plan de phases révisé](#8-plan-de-phases-révisé)
9. [Risques et mitigations](#9-risques-et-mitigations)
10. [Questions ouvertes restantes](#10-questions-ouvertes-restantes)

---

## 1. Vision et objectifs

### Énoncé de vision

Construire un système modulaire et autonome capable de :

1. **Lire** un notebook Jupyter contenant des exercices (cursus JHU "Applied Generative AI")
2. **Comprendre** les instructions (texte, images, fichier d'accompagnement)
3. **Résoudre** les exercices en explorant plusieurs approches (algorithmiques et/ou hyperparamètres)
4. **Mesurer** et comparer les solutions via un framework de benchmark générique
5. **Produire** le notebook complété + export HTML (livrable JHU) + document comparatif
6. **Persister** l'état sur GitHub pour reprise depuis n'importe quel environnement

### Contraintes transversales

| Contrainte | Détail |
| --- | --- |
| **Langue du code** | Anglais (prompts, noms de variables, documentation technique) |
| **Langue de planification** | Français (ce document, tâches de gouvernance) |
| **Livrable final** | HTML généré depuis le notebook complété |
| **Portabilité** | Doit fonctionner en local (Docker/Vagrant) ou cloud (GitHub Actions, GPU à la demande) |
| **Secrets** | GitHub Secrets (gratuit, suffisant pour cette envergure) |
| **Budget** | Solutions gratuites ou coût marginal (GPU Terraform start/stop) |

---

## 2. Décisions d'architecture consolidées

Synthèse des réponses [JRE] et des choix qui en découlent :

### D1 — Approche MVP pour le Notebook Processor

**Décision** : Démarrer avec Claude Code comme agent interactif (le plus simple), puis évoluer vers un pipeline API autonome.

**Justification** : Jean veut "rapidement une version qui fonctionne". Claude Code lit directement le notebook, réfléchit, écrit le code — aucune infrastructure supplémentaire à construire.

**Chemin d'évolution** :

> [JRE] ne pas laisser de bloque de code sans lanhuage, utiliser éventuellement des plugins type Mermaid.

```
MVP (Phase 1)         →  V2 (Phase future)
─────────────────────    ──────────────────────────────
Claude Code interactif    Pipeline Python autonome
  lit .ipynb                appelle API Anthropic
  modifie les cellules      exécution via papermill
  exécute manuellement      CI/CD automatique
  exporte HTML              rapport auto-généré
```

### D2 — Exécution réelle des notebooks

**Décision** : Le notebook final doit être exécuté pour capturer les outputs.

**MVP** : Exécution manuelle dans Claude Code (ou Jupyter local).
**Cible** : Exécution automatisée via `papermill` dans un environnement contrôlé.

### D3 — Benchmark : itérations + approches + hyperparamètres

**Décision** : Le framework couvre les deux dimensions — approches algorithmiques différentes ET variations de paramètres au sein d'une même approche.

**Implication** : Le modèle de données doit supporter une hiérarchie `approach → iteration → parameters`.

### D4 — Génération automatique des classes de mesure

**Décision** : Le système (orchestrateur / agent) analyse les instructions et génère dynamiquement les classes de test/mesure. Ces classes peuvent utiliser des décorateurs Python.

**Implication** : Nécessite un template de classe de mesure + capacité de code generation. En MVP, les classes sont écrites manuellement ; en cible, elles sont générées par l'agent.

### D5 — Orchestrateur pilote les runs

**Décision** : L'orchestrateur génère un plan, lance les tests nécessaires, et persiste l'état d'avancement.

**Implication** : Fichier d'état (`state.json` ou équivalent) versionné sur GitHub, consultable pour reprise.

### D6 — Infrastructure hybride local/cloud

**Décision** : Pas contraint au cloud. Procédure de setup qui récupère les dépendances depuis internet. Compute local via Docker/VirtualBox/Vagrant, ou cloud via GitHub Actions + GPU Terraform.

### D7 — GPU à la demande

**Décision** : Provisionner une ressource GPU via Terraform, démarrée/arrêtée avec les cycles de test.

**Cible** : Module Terraform pour AWS/GCP spot instances avec auto-shutdown. En MVP, GPU local ou Colab manuel.

> [JRE] Colab n'est pas encore possible au Luxembourg. Il va falloir prendre du GPU ou Tensor sur du compute Cloud. J'ai une préférence pour Oracle OCI, suaf si une évidence donne un autre gagnant. Je préfère Oracle pour ses tarifs compétitifs et son infrastructure réseau simple. Ensuite, je dirais GCP vu ses possibilités mutiples pour du compute type Tensor ou GPU.
> Mon routeur permet le WireGuard, ça ne serait pas mal de gérer les interconnexion via WireGuard. Mon routeur est un Fritz!Box 7530 AX.

---

## 3. Architecture des domaines

### 3.1 — Domaine A : Notebook Processor

```
┌─────────────────────────────────────────────────────────┐
│                   NOTEBOOK PROCESSOR                     │
│                                                          │
│  input/                                                  │
│  ├── assignment.ipynb         ← notebook original        │
│  ├── instructions.md (opt.)   ← consignes additionnelles │
│  └── images/ (opt.)           ← exemples visuels         │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │   1. PARSE   │ → │  2. SOLVE    │ → │  3. BUILD    │ │
│  │              │   │              │   │              │ │
│  │ Lire .ipynb  │   │ Compléter    │   │ Reconstruire │ │
│  │ Extraire     │   │ cellules     │   │ .ipynb       │ │
│  │ instructions │   │ code +       │   │ Exécuter     │ │
│  │ Interpréter  │   │ markdown     │   │ Exporter     │ │
│  │ images       │   │ (multi-sol.) │   │ HTML         │ │
│  └──────────────┘   └──────┬───────┘   └──────────────┘ │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │ BENCHMARK FWK  │ (Domaine B)        │
│                    │ (si multi-sol.)│                    │
│                    └────────────────┘                    │
│                                                          │
│  output/                                                 │
│  ├── assignment_completed.ipynb  ← notebook complété     │
│  ├── assignment_completed.html   ← livrable JHU          │
│  └── comparison_report.md        ← rapport comparatif    │
│                                                          │
│  done/                                                   │
│  └── (copie exacte de input/)    ← archivage             │
└─────────────────────────────────────────────────────────┘
```

**Composants techniques (MVP)** :

| Composant | Outil | Rôle |
| --- | --- | --- |
| Parser | `nbformat` (Python) | Lire/écrire .ipynb programmatiquement |
| Solver | Claude Code (interactif) | Comprendre les instructions, écrire le code |
| Executor | `papermill` ou kernel Jupyter | Exécuter le notebook complet |
| Exporter | `nbconvert` | Convertir .ipynb → HTML |
| Archiver | `shutil` / script bash | Copier input/ → done/ |

### 3.2 — Domaine B : Benchmark Framework

C'est le cœur générique du système. Il est **totalement découplé** du Notebook Processor et peut servir à tout projet de comparaison.

```
┌───────────────────────────────────────────────────────────────────┐
│                      BENCHMARK FRAMEWORK                          │
│                                                                   │
│  Configuration (JSON)                                             │
│  ├── iterations.json    ← registre des solutions/itérations       │
│  ├── metrics.json       ← définitions des mesures + classes       │
│  ├── runs.json          ← définitions des exécutions à lancer     │
│  └── results.json       ← résultats horodatés des runs           │
│                                                                   │
│  Engine                                                           │
│  ├── runner.py          ← exécute un run (itérations × métriques) │
│  ├── registry.py        ← charge/valide les fichiers JSON         │
│  ├── reporter.py        ← génère le document comparatif           │
│  └── metrics/           ← classes de mesure (générées ou écrites) │
│      ├── base.py        ← classe abstraite BaseMetric             │
│      ├── timing.py      ← exemple : mesure de temps               │
│      └── ml_quality.py  ← exemple : accuracy, F1, RMSE           │
│                                                                   │
│  Iteration Sources (code à benchmarker)                           │
│  └── iterations/                                                  │
│      ├── v1_baseline/   ← code de la première approche            │
│      ├── v2_optimized/  ← code de la deuxième approche            │
│      └── v3_tuned/      ← variante avec hyperparamètres ajustés   │
│                                                                   │
│  Output                                                           │
│  └── reports/                                                     │
│      ├── results.json          ← données brutes                   │
│      └── comparison_report.md  ← document narratif                │
└───────────────────────────────────────────────────────────────────┘
```

### 3.3 — Domaine C : Orchestration

```
┌─────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR                               │
│                                                                  │
│  state.json              ← état d'avancement (versionné GitHub)  │
│  plan.json               ← plan généré par l'orchestrateur       │
│                                                                  │
│  Responsabilités :                                               │
│  1. Analyser les instructions du notebook                        │
│  2. Générer un plan d'exécution (quelles itérations, quels runs) │
│  3. Déclencher le Benchmark Framework                            │
│  4. Mettre à jour l'état d'avancement                            │
│  5. Persister sur GitHub (commit/push)                           │
│  6. Permettre la reprise sur un autre environnement              │
│                                                                  │
│  MVP : L'orchestrateur, c'est TOI (Claude Code interactif)       │
│  Cible : Script Python autonome avec API Anthropic                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Modèle de données du Benchmark Framework

### 4.1 — `iterations.json`

Registre de toutes les solutions/variantes testées.

```json
{
  "$schema": "iterations-schema.json",
  "project": "assignment-03-sentiment-analysis",
  "iterations": [
    {
      "id": "v1-baseline",
      "name": "Baseline TF-IDF + Logistic Regression",
      "description": "Approche classique avec vectorisation TF-IDF et régression logistique",
      "approach": "classical-ml",
      "source_path": "iterations/v1_baseline/",
      "entry_point": "main.py",
      "parameters": {},
      "parent": null,
      "created_at": "2025-02-14T10:00:00Z",
      "tags": ["baseline", "classical"]
    },
    {
      "id": "v2-transformer",
      "name": "DistilBERT Fine-tuned",
      "description": "Fine-tuning de DistilBERT sur le dataset",
      "approach": "transformer",
      "source_path": "iterations/v2_transformer/",
      "entry_point": "main.py",
      "parameters": {
        "learning_rate": 2e-5,
        "epochs": 3,
        "batch_size": 16
      },
      "parent": null,
      "created_at": "2025-02-14T12:00:00Z",
      "tags": ["transformer", "fine-tuning"]
    },
    {
      "id": "v2-transformer-lr5e5",
      "name": "DistilBERT LR=5e-5",
      "description": "Même approche, learning rate augmenté",
      "approach": "transformer",
      "source_path": "iterations/v2_transformer/",
      "entry_point": "main.py",
      "parameters": {
        "learning_rate": 5e-5,
        "epochs": 3,
        "batch_size": 16
      },
      "parent": "v2-transformer",
      "created_at": "2025-02-14T14:00:00Z",
      "tags": ["transformer", "hyperparameter-tuning"]
    }
  ]
}
```

**Points de design** :

- `parent` permet de tracer la filiation (quelle itération dérive de quelle autre)
- `approach` groupe les itérations par famille d'approche
- `parameters` est un dict libre pour les hyperparamètres (permet le tuning)
- `source_path` + `entry_point` = le code reste séparé et exécutable indépendamment

### 4.2 — `metrics.json`

Définition des mesures disponibles et des classes Python qui les implémentent.

```json
{
  "$schema": "metrics-schema.json",
  "metrics": [
    {
      "id": "accuracy",
      "name": "Classification Accuracy",
      "description": "Proportion of correct predictions",
      "type": "ml_quality",
      "class": "benchmarks.metrics.ml_quality.AccuracyMetric",
      "higher_is_better": true,
      "unit": "%"
    },
    {
      "id": "f1_macro",
      "name": "F1 Score (Macro)",
      "description": "Harmonic mean of precision and recall, macro-averaged",
      "type": "ml_quality",
      "class": "benchmarks.metrics.ml_quality.F1MacroMetric",
      "higher_is_better": true,
      "unit": ""
    },
    {
      "id": "exec_time",
      "name": "Execution Time",
      "description": "Wall-clock time for training + inference",
      "type": "performance",
      "class": "benchmarks.metrics.timing.ExecutionTimeMetric",
      "higher_is_better": false,
      "unit": "seconds"
    },
    {
      "id": "gpu_memory",
      "name": "Peak GPU Memory",
      "description": "Maximum GPU memory allocated during execution",
      "type": "performance",
      "class": "benchmarks.metrics.timing.GpuMemoryMetric",
      "higher_is_better": false,
      "unit": "MB"
    }
  ]
}
```

**Design** :

- `class` est une référence Python fully-qualified, instanciée dynamiquement par le runner
- `higher_is_better` guide le reporter pour déterminer la "meilleure" solution
- En cible, l'orchestrateur (agent) génère ce fichier à partir des instructions

### 4.3 — `runs.json`

Définition des runs à exécuter. Un run = sous-ensemble d'itérations × sous-ensemble de métriques.

```json
{
  "$schema": "runs-schema.json",
  "runs": [
    {
      "id": "run-001",
      "name": "Baseline vs Transformer — Quality",
      "description": "Comparer la qualité ML des deux approches principales",
      "iteration_ids": ["v1-baseline", "v2-transformer"],
      "metric_ids": ["accuracy", "f1_macro"],
      "status": "pending",
      "created_at": "2025-02-14T15:00:00Z"
    },
    {
      "id": "run-002",
      "name": "Transformer LR Sweep — Full",
      "description": "Comparer les variantes de learning rate sur toutes les métriques",
      "iteration_ids": ["v2-transformer", "v2-transformer-lr5e5"],
      "metric_ids": ["accuracy", "f1_macro", "exec_time", "gpu_memory"],
      "status": "pending",
      "created_at": "2025-02-14T15:30:00Z"
    }
  ]
}
```

### 4.4 — `results.json`

Résultats des exécutions. Fichier **append-only** (on ne supprime jamais de résultats).

```json
{
  "$schema": "results-schema.json",
  "results": [
    {
      "run_id": "run-001",
      "iteration_id": "v1-baseline",
      "metric_id": "accuracy",
      "value": 82.3,
      "unit": "%",
      "executed_at": "2025-02-14T16:00:00Z",
      "environment": {
        "platform": "linux-x86_64",
        "python": "3.11.7",
        "gpu": null
      },
      "metadata": {
        "dataset_size": 10000,
        "train_split": 0.8
      }
    },
    {
      "run_id": "run-001",
      "iteration_id": "v2-transformer",
      "metric_id": "accuracy",
      "value": 91.7,
      "unit": "%",
      "executed_at": "2025-02-14T16:05:00Z",
      "environment": {
        "platform": "linux-x86_64",
        "python": "3.11.7",
        "gpu": "NVIDIA T4"
      },
      "metadata": {
        "dataset_size": 10000,
        "train_split": 0.8
      }
    }
  ]
}
```

**Design** :

- `environment` capture le contexte d'exécution (reproductibilité)
- `metadata` est libre pour stocker des infos spécifiques au run
- Le fichier est dénormalisé volontairement (chaque résultat est auto-porteur)

### 4.5 — Classe abstraite `BaseMetric`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import time


@dataclass
class MetricResult:
    """Résultat d'une mesure individuelle."""
    metric_id: str
    value: float
    unit: str
    metadata: dict[str, Any] | None = None


class BaseMetric(ABC):
    """Classe abstraite pour toutes les métriques du benchmark."""

    metric_id: str
    higher_is_better: bool
    unit: str

    @abstractmethod
    def measure(self, iteration_path: str, entry_point: str,
                parameters: dict) -> MetricResult:
        """
        Exécute la mesure sur une itération donnée.

        Args:
            iteration_path: Chemin vers le code de l'itération
            entry_point: Fichier d'entrée à exécuter
            parameters: Hyperparamètres de l'itération

        Returns:
            MetricResult avec la valeur mesurée
        """
        ...

    def setup(self) -> None:
        """Hook optionnel : préparation avant la mesure."""
        pass

    def teardown(self) -> None:
        """Hook optionnel : nettoyage après la mesure."""
        pass
```

### 4.6 — Exemple avec décorateur

```python
import functools
import time
from .base import BaseMetric, MetricResult


def timed(func):
    """Décorateur pour mesurer le temps d'exécution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        # Injecte le temps dans le résultat si c'est un MetricResult
        if isinstance(result, MetricResult) and result.metadata is not None:
            result.metadata["wall_time_seconds"] = elapsed
        return result
    return wrapper


def requires_gpu(func):
    """Décorateur qui vérifie la disponibilité GPU avant exécution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("GPU required but not available")
        return func(*args, **kwargs)
    return wrapper
```

---

## 5. Infrastructure et compute

### 5.1 — Environnement local (MVP)

```
┌──────────────────────────────────────────────┐
│  Environnement local (Mac mini M1 / laptop)  │
│                                               │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │ Claude Code │  │ Docker / Vagrant     │   │
│  │ (interactif)│  │ ┌──────────────────┐ │   │
│  │             │  │ │ Python 3.11+     │ │   │
│  │ Lit input/  │  │ │ Jupyter kernel   │ │   │
│  │ Modifie nb  │  │ │ papermill        │ │   │
│  │ Lance bench │  │ │ nbconvert        │ │   │
│  └──────┬──────┘  │ │ torch (CPU/MPS)  │ │   │
│         │         │ └──────────────────┘ │   │
│         │         └──────────────────────┘   │
│         │                                     │
│         ▼                                     │
│  GitHub (state, code, résultats)              │
└──────────────────────────────────────────────┘
```

**Setup script** (à fournir dans chaque repo) :

- `Makefile` ou `just` avec cibles : `setup`, `run`, `test`, `benchmark`, `export-html`
- `Dockerfile` pour environnement reproductible
- `Vagrantfile` (optionnel) pour environnement complet avec GPU passthrough

### 5.2 — Environnement cloud (cible)

```
┌────────────────────────────────────────────────────────┐
│  GitHub Actions                                         │
│                                                         │
│  on: push / workflow_dispatch / repository_dispatch      │
│                                                         │
│  Job 1: Validate & Test (runner gratuit)                │
│  ├── Lint, tests unitaires, validation JSON schemas     │
│                                                         │
│  Job 2: Benchmark (conditionnel)                        │
│  ├── Si GPU nécessaire :                                │
│  │   ├── Terraform apply → GPU instance (spot)          │
│  │   ├── SSH → exécute les runs                         │
│  │   ├── Récupère results.json                          │
│  │   └── Terraform destroy → arrêt GPU                  │
│  ├── Sinon :                                            │
│  │   └── Exécute sur runner GitHub (CPU)                │
│                                                         │
│  Job 3: Report                                          │
│  ├── Génère comparison_report.md                        │
│  ├── Commit results + report sur GitHub                 │
│  └── Notification (optionnel)                           │
└────────────────────────────────────────────────────────┘
```

### 5.3 — Gestion des secrets

| Secret | Usage | Stockage |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Appels API Claude (cible) | GitHub Secrets |
| `CLOUD_CREDENTIALS` | Terraform GPU provisioning | GitHub Secrets |
| `GIT_TOKEN` | Push automatique des résultats | GitHub Secrets (auto) |

GitHub Secrets est gratuit et suffisant. HashiCorp Vault serait pertinent uniquement si le nombre de secrets explose ou si on a besoin de rotation automatique — ce n'est pas le cas ici.

---

## 6. Repos GitHub et interfaces

### 6.1 — Découpage en repos

| Repo | Visibilité | Contenu | Dépendances |
| --- | --- | --- | --- |
| **`benchmark-framework`** | Public | Framework générique de benchmark (JSON schemas, runner, reporter, classes de base) | Aucune |
| **`notebook-processor`** | Public | Pipeline de traitement de notebooks (parse, solve, build, export) | `benchmark-framework` (pip install) |
| **`jhu-coursework`** | Privé | Notebooks spécifiques JHU, itérations, résultats, rapports | `notebook-processor`, `benchmark-framework` |
| **`project-orchestrator`** | Privé | État d'avancement, plans, coordination inter-repos | Consulte les 3 autres |

### 6.2 — Interface entre repos

#### **Mécanisme principal : pip installable + GitHub Releases**

```
benchmark-framework (v0.1.0, v0.2.0, ...)
        ↓ pip install git+https://...
notebook-processor
        ↓ pip install git+https://...
jhu-coursework (utilise les deux comme dépendances)
```

#### **Communication inter-repos pour l'orchestration**

| Mécanisme | Usage |
|---|---|
| `pyproject.toml` dependencies | Intégration code (import Python) |
| GitHub Releases + tags sémantiques | Versioning des interfaces |
| `state.json` dans `project-orchestrator` | État d'avancement global |
| `repository_dispatch` events (cible) | Déclenchement cross-repo via GitHub Actions |

#### **Interface contract pour travail asynchrone**

Chaque repo expose une interface Python stable, documentée, avec des types. Même si le code interne change, l'interface reste stable. Cela permet à un Claude Code de travailler sur le benchmark-framework pendant qu'un autre travaille sur le notebook-processor.

```python
# benchmark_framework/api.py — interface publique stable
def load_iterations(path: str) -> list[Iteration]: ...
def load_metrics(path: str) -> list[MetricDefinition]: ...
def execute_run(run: RunDefinition) -> list[RunResult]: ...
def generate_report(results: list[RunResult]) -> str: ...
```

### 6.3 — Travail multi-agent (Claude Code parallèle)

**Scénario envisagé** :

```
Claude Code #1 (Orchestrateur)
  │  Génère le plan, dispatche les tâches
  │  Met à jour state.json
  │
  ├── Claude Code #2 (Benchmark Framework)
  │     Implémente runner, metrics, reporter
  │     Push sur benchmark-framework repo
  │     Interface : api.py avec types stables
  │
  └── Claude Code #3 (Notebook Processor)
        Implémente parse, solve, build
        Dépend de l'interface (pas de l'implémentation)
        Peut utiliser des mocks en attendant
```

**En pratique pour le MVP** : travail séquentiel. Un seul Claude Code à la fois, qui commit/push régulièrement. L'état sur GitHub permet de reprendre d'un autre terminal ou machine.

---

## 7. Stratégie MVP vs cible

### Matrice de fonctionnalités

| Fonctionnalité | MVP (P1-P2) | Cible (P3+) |
| --- | --- | --- |
| **Lecture notebook** | `nbformat` — Claude Code lit et comprend | Pipeline automatisé |
| **Interprétation images** | Claude vision (interactif) | API vision intégrée |
| **Complétion code** | Claude Code écrit le code | API Anthropic + chaîne de prompts |
| **Complétion markdown** | Claude Code rédige | API Anthropic |
| **Exécution notebook** | Manuelle (Jupyter/CLI) | `papermill` automatisé |
| **Export HTML** | `nbconvert` CLI | Intégré au pipeline |
| **Benchmark — config** | JSON écrit manuellement | Généré par l'agent |
| **Benchmark — classes** | Classes écrites manuellement | Générées dynamiquement |
| **Benchmark — runs** | Lancé manuellement | Orchestrateur automatique |
| **Benchmark — rapport** | Markdown template | Rapport narratif auto-généré |
| **Compute GPU** | Local (MPS) ou Colab | Terraform spot instance |
| **CI/CD** | Commit/push manuels | GitHub Actions complet |
| **État d'avancement** | `state.json` commit manuellement | Auto-commit par Actions |

---

## 8. Plan de phases révisé

### Phase 0 — Architecture & Fondations (cette phase)

| Tâche | Livrable | Effort |
| --- | --- | --- |
| Consolider les décisions | Ce document ✓ | 1 session |
| Valider avec Jean | Annotations / corrections | 1 session |
| Créer les repos GitHub (vides, avec README + structure) | 4 repos initialisés | 30 min |
| Définir les JSON schemas | `*-schema.json` dans benchmark-framework | 1h |
| Écrire le CLAUDE.md de chaque repo | Instructions pour Claude Code | 1h |

### Phase 1 — Benchmark Framework (repo autonome)

| Tâche | Livrable | Dépendances |
| --- | --- | --- |
| 1.1 Classe `BaseMetric` + `MetricResult` | `benchmarks/metrics/base.py` | Aucune |
| 1.2 JSON schemas (iterations, metrics, runs, results) | `schemas/*.json` | Aucune |
| 1.3 Registry (chargement + validation JSON) | `benchmarks/registry.py` | 1.1, 1.2 |
| 1.4 Runner (exécution séquentielle) | `benchmarks/runner.py` | 1.1, 1.3 |
| 1.5 Métriques de base (timing, accuracy) | `benchmarks/metrics/timing.py`, `ml_quality.py` | 1.1 |
| 1.6 Reporter (génération Markdown) | `benchmarks/reporter.py` | 1.4 |
| 1.7 Tests unitaires + CI basique | `tests/`, `.github/workflows/test.yml` | 1.1–1.6 |
| 1.8 Packaging (pyproject.toml, installable) | pip installable depuis GitHub | 1.7 |

**Critère de sortie** : On peut définir des itérations, métriques, et runs en JSON, lancer un benchmark, et obtenir un rapport Markdown. Le tout installable via `pip install git+https://github.com/jremacle/benchmark-framework`.

### Phase 2 — Notebook Processor (MVP)

| Tâche | Livrable | Dépendances |
| --- | --- | --- |
| 2.1 Parser de notebook | `processor/parser.py` — extrait cellules, instructions, images | Aucune |
| 2.2 Structure projet + CLAUDE.md | Prompts et instructions pour Claude Code | Aucune |
| 2.3 Builder de notebook | `processor/builder.py` — reconstruit .ipynb | 2.1 |
| 2.4 Executor (wrapper papermill) | `processor/executor.py` | 2.3 |
| 2.5 Exporter HTML (wrapper nbconvert) | `processor/exporter.py` | 2.4 |
| 2.6 Archiver (input/ → done/) | `processor/archiver.py` | Aucune |
| 2.7 Intégration benchmark-framework | `processor/benchmark_bridge.py` | Phase 1 |
| 2.8 CLI unifié | `python -m processor run input/` | 2.1–2.7 |

**Critère de sortie** : On peut lancer `python -m processor run input/` et obtenir dans `output/` le notebook complété + HTML + rapport (si benchmark activé). Les fichiers originaux sont dans `done/`.

### Phase 3 — Intégration CI/CD

| Tâche | Livrable | Dépendances |
| --- | --- | --- |
| 3.1 GitHub Actions : test + lint (les deux repos) | `.github/workflows/` | P1, P2 |
| 3.2 GitHub Actions : benchmark on demand | Workflow `workflow_dispatch` | P1 |
| 3.3 Dockerfile pour environnement reproductible | `Dockerfile` dans chaque repo | P1, P2 |
| 3.4 Makefile / Justfile | Cibles standardisées | P1, P2 |
| 3.5 State management (state.json auto-commit) | Script de sync état | P2 |

### Phase 4 — Premier cas d'usage JHU

| Tâche | Livrable | Dépendances |
| --- | --- | --- |
| 4.1 Traiter un notebook JHU réel de bout en bout | Notebook complété + HTML | P2 |
| 4.2 Créer 2-3 itérations alternatives | Itérations dans jhu-coursework | P1 |
| 4.3 Lancer le benchmark, produire le rapport | `comparison_report.md` | P1, 4.2 |
| 4.4 Retrospective : ajuster l'architecture | Mise à jour de ce document | P0–P3 |

### Phase 5 (future) — Automatisation avancée

- Pipeline API Anthropic autonome (remplacement de Claude Code interactif)
- Génération dynamique des classes de métriques par l'agent
- GPU Terraform à la demande
- Multi-agent parallèle (plusieurs Claude Code)
- Cowork pour la gouvernance de haut niveau

---

## 9. Risques et mitigations

| # | Risque | Impact | Probabilité | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Sur-ingénierie : trop de structure avant d'avoir un cas d'usage réel | Retard, frustration | Élevée | MVP strict en P1-P2. Itérer après P4. |
| R2 | Limites de Claude Code pour comprendre des notebooks complexes | Qualité des solutions | Moyenne | Fichier d'instructions supplémentaire, images annotées |
| R3 | Coût GPU pour le benchmark | Budget | Basse | Spot instances, auto-shutdown, commencer en CPU/MPS |
| R4 | Complexité de l'orchestration multi-agent | Cohérence du code | Moyenne | Séquentiel d'abord, parallèle plus tard |
| R5 | Dépendance aux APIs Anthropic (quotas, coûts) | Blocage | Basse | Claude Code via abonnement, pas d'API supplémentaire en MVP |
| R6 | Notebooks JHU avec des dépendances exotiques | Échec d'exécution | Moyenne | Docker avec environnement contrôlé, `requirements.txt` par assignment |

---

## 10. Questions ouvertes restantes

Avant de lancer P1, il me reste quelques points à éclaircir :

### Q-A — Nommage du fichier de registre

Tu as proposé de renommer `solutions.json` → `iterations.json`. Après réflexion, `iterations.json` capture bien l'idée d'évolution progressive. Alternatives considérées : `variants.json`, `candidates.json`, `approaches.json`. **Je recommande `iterations.json`** car c'est le terme que tu utilises naturellement. Confirmation ?

> [JRE] `iterations`

### Q-B — Granularité des itérations

Dans le modèle proposé, une itération peut être un changement d'approche OU un changement de paramètres (via le champ `parent` + `parameters`). Est-ce que cette modélisation te convient, ou préfères-tu séparer les deux concepts (approach vs tuning run) ?

> [JRE] Cette modélisation me convient

### Q-C — Premier notebook de test

As-tu un notebook JHU spécifique en tête pour servir de premier cas d'usage (Phase 4) ? Ça aiderait à calibrer la complexité du Notebook Processor.

> [JRE] fichier ajouter en attachement, dès la première sesssion Claude Code, ce sont des fichiers volumineux (trop d'images innutiles).

### Q-D — Compte GitHub

Tes repos iront sous `jremacle` (personnel) ou une organisation dédiée ? Ça impacte la structure des URLs et les permissions.

> [JRE] repos sous `jeanremacle`, c'est effectivement personel.

### Q-E — Cowork pour la planification

Tu as mentionné Cowork pour la planification de haut niveau. Veux-tu que je prépare un prompt/projet Cowork qui décompose les phases ci-dessus en tâches atomiques avec des fichiers à créer ? Ou préfères-tu d'abord valider cette architecture et lancer P1 directement avec Claude Code ?

> [JRE] Comme proposé en [R1], je vais suivre la recommendation du MVP P1 + P2 avec Claude Code. Mais effectivement mon idée initiale ètait d'utiliser Cowork comme agent autonome continu.
